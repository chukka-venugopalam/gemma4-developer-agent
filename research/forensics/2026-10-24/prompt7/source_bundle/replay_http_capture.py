"""FAKE-MODEL REPLAY - NOT A GEMMA TEST - NOT A SCORE TEST - NOT THE OFFICIAL EVALUATOR.

Compiles an unpacked submission with the INSTALLED harness (real LiteLlm model objects, real thinking-config resolver),
then drives ONE bounded ADK conversation against a local scripted OpenAI-compatible HTTP server and records what the
agent actually SENDS.  Question answered: do the thinking-disabled settings in the submission reach the request body?

    python -I replay_http_capture.py <harness_dir | -> <submission_dir> [--out result.json]

Scripted behaviour (per distinct agent system prompt): call `code_analyzer` once if it is offered, call `get_status`
once, then (root only) call `submit_patch` once through a FAKE sandbox object, then answer "done (scripted)".
The fake sandbox returns a canned diff, so the submit_patch result proves tool plumbing only, never real patch capture.

Checks recorded: agent loads, declared tools resolve, tool arguments parse, issue text reaches the system prompt,
tool results flow back, no undeclared tool is offered/called, submit_patch sets patch_submitted, no raw {template}
braces or include errors.  Exit code is always 0; read VERDICT in the JSON.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

for _k in ("NO_PROXY", "no_proxy"):
    os.environ[_k] = ",".join(filter(None, [os.environ.get(_k, ""), "127.0.0.1", "localhost"]))
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
MODEL = "gemma-4-31b-it-qat-w4a16-ct"
SENTINEL = "ISSUE-SENTINEL-7f3a: parse_request() drops the trailing slash"

CAPTURED: list[dict] = []
STATE: dict = {"calls_by_agent": {}, "n": 0}
LOCK = threading.Lock()


def find_think_keys(o, path=""):
    out = {}
    if isinstance(o, dict):
        for k, v in o.items():
            p = f"{path}.{k}" if path else str(k)
            if any(s in str(k).lower() for s in ("think", "reason")):
                out[p] = v
            out.update(find_think_keys(v, p))
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence
        pass

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}")
        msgs = body.get("messages", [])
        system = "\n".join(str(m.get("content")) for m in msgs if m.get("role") == "system")
        tools = {t["function"]["name"]: t["function"] for t in body.get("tools", []) if t.get("type") == "function"}
        with LOCK:
            STATE["n"] += 1
            n = STATE["n"]
            key = hash(system)
            seen = STATE["calls_by_agent"].setdefault(key, set())
            CAPTURED.append({
                "n": n, "path": self.path, "model": body.get("model"), "stream": bool(body.get("stream")),
                "top_level_keys": sorted(body.keys()),
                "thinking_related_fields": find_think_keys(body),
                "tools_offered": sorted(tools), "n_messages": len(msgs),
                "issue_in_system_prompt": "ISSUE-SENTINEL" in system,
                "issue_in_any_message": "ISSUE-SENTINEL" in json.dumps(msgs),
                "raw_template_braces_left": "{problem_description" in system,
                "system_prompt_head": system[:80],
            })
            call = None
            if n > 24:
                self.send_response(500); self.end_headers(); return
            if "code_analyzer" in tools and "code_analyzer" not in seen:
                props = list((tools["code_analyzer"].get("parameters") or {}).get("properties", {}))
                call = ("code_analyzer", {(props[0] if props else "request"): "parse_request trailing slash"})
            elif "get_status" in tools and "get_status" not in seen:
                call = ("get_status", {})
            elif "submit_patch" in tools and "submit_patch" not in seen:
                call = ("submit_patch", {})
            if call:
                seen.add(call[0])
        if call:
            message = {"role": "assistant", "content": None, "tool_calls": [
                {"id": f"call_{n}", "type": "function", "function": {"name": call[0], "arguments": json.dumps(call[1])}}]}
            finish = "tool_calls"
        else:
            message = {"role": "assistant",
                       "content": "TARGET: parse_request\nROOT CAUSE: x\nFIX PLAN: y\nCONFIDENCE: high" if "ISSUE TO INVESTIGATE" in system
                       and "code_analyzer" not in tools else "done (scripted)"}
            finish = "stop"
        usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        if body.get("stream"):
            self.send_response(200); self.send_header("content-type", "text/event-stream"); self.end_headers()
            delta = dict(message); delta.pop("role", None)
            if "tool_calls" in delta:
                delta["tool_calls"] = [dict(tc, index=0) for tc in delta["tool_calls"]]
            chunks = [{"id": "c", "object": "chat.completion.chunk", "created": int(time.time()), "model": MODEL,
                       "choices": [{"index": 0, "delta": {"role": "assistant", **delta}, "finish_reason": None}]},
                      {"id": "c", "object": "chat.completion.chunk", "created": int(time.time()), "model": MODEL,
                       "choices": [{"index": 0, "delta": {}, "finish_reason": finish}], "usage": usage}]
            for c in chunks:
                self.wfile.write(f"data: {json.dumps(c)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            return
        payload = json.dumps({"id": "c", "object": "chat.completion", "created": int(time.time()), "model": MODEL,
                              "choices": [{"index": 0, "message": message, "finish_reason": finish}], "usage": usage}).encode()
        self.send_response(200); self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload))); self.end_headers(); self.wfile.write(payload)


class FakeSandbox:
    """Stands in for the Docker/subprocess sandbox. Returns a canned diff. NOT a real sandbox."""
    def exec(self, container_id, cmd, *a, **k):
        out = "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a\n+b\n" if "git diff" in cmd else ""
        return SimpleNamespace(exit_code=0, stdout=out, stderr="")

    def __getattr__(self, name):  # any other sandbox call: harmless no-op
        return lambda *a, **k: SimpleNamespace(exit_code=0, stdout="", stderr="")


def agent_summary(a):
    ab = getattr(getattr(a, "model", None), "_additional_args", None)
    return {"name": a.name, "model_class": type(getattr(a, "model", None)).__name__,
            "extra_body_on_model": (ab or {}).get("extra_body") if isinstance(ab, dict) else None,
            "tools": [getattr(t, "name", getattr(t, "__name__", type(t).__name__)) for t in getattr(a, "tools", [])],
            "sub_agents": [agent_summary(s) for s in getattr(a, "sub_agents", [])],
            "agent_tools": [agent_summary(t.agent) for t in getattr(a, "tools", []) if hasattr(t, "agent")]}


async def run(url: str, SUB: Path) -> dict:
    from google.adk.apps import App
    from google.adk.models.lite_llm import LiteLlm
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    from adk_submission import ModelRegistry, ToolRegistry, compile_submission
    from swegemma.config import build_submission_limits
    from swegemma.context import SwegemmaContext

    out: dict = {"submission_dir": str(SUB)}
    limits, gc = build_submission_limits()
    models = ModelRegistry()
    models.register(MODEL, LiteLlm(model=f"openai/{MODEL}", api_base=url, api_key="EMPTY", num_retries=0))
    ctx = SwegemmaContext(docker_manager=FakeSandbox(), container_id="fake", problem_statement=SENTINEL, task_id="t", repo="r",
                          max_tool_calls=40, max_time_minutes=4.5)
    tr = ToolRegistry()
    for k, v in ctx.create_tools().items():
        tr.register(k, v)
    agent = compile_submission(submission_dir=SUB, tool_registry=tr, model_registry=models, limits=limits,
                               generation_constraints=gc, script_timeout=180)
    out["compiled_agents"] = agent_summary(agent)
    svc = InMemorySessionService()
    sess = await svc.create_session(app_name="replay", user_id="u", state={"problem_description": SENTINEL})
    runner = Runner(app=App(name="replay", root_agent=agent), session_service=svc)
    nudge = ("Please continue your work using the available tools, or call submit_patch when "
             "you have completed and verified your changes.")
    msg, events = "## Problem Statement\n" + SENTINEL + "\n\nResolve it.", []
    for inv in range(1, 5):
        evs = []
        async for ev in runner.run_async(user_id="u", session_id=sess.id,
                                         new_message=types.Content(role="user", parts=[types.Part(text=msg)])):
            kinds = []
            for p in (ev.content.parts if ev.content and ev.content.parts else []):
                if p.function_call:
                    kinds.append(f"call:{p.function_call.name}")
                if p.function_response:
                    kinds.append(f"resp:{p.function_response.name}")
                if p.text:
                    kinds.append("text:" + p.text[:30].replace("\n", " "))
            evs.append({"author": ev.author, "parts": kinds})
        events.append({"invocation": inv, "events": evs})
        if any(k.startswith("text:done") for e in evs for k in e["parts"]):
            break
        msg = nudge
    out["events"] = events
    out["ctx_after"] = {"patch_submitted": bool(getattr(ctx, "patch_submitted", False)),
                        "submitted_patch_chars": len(getattr(ctx, "submitted_patch", "") or ""),
                        "tool_calls_used": ctx.tool_calls_used}
    return out


def start_server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/v1"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("harness_dir")
    ap.add_argument("submission_dir")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    if args.harness_dir != "-":
        sys.path.insert(0, args.harness_dir)
    SUB = Path(args.submission_dir)
    CAPTURED.clear(); STATE.update(calls_by_agent={}, n=0)
    srv, url = start_server()
    try:
        res = asyncio.run(run(url, SUB))
        res["VERDICT"] = "RAN_TO_COMPLETION"
    except BaseException as e:  # noqa: BLE001
        res = {"VERDICT": "EXCEPTION", "exc_type": f"{type(e).__module__}.{type(e).__name__}", "message": str(e),
               "traceback_tail": traceback.format_exc().strip().splitlines()[-14:]}
    srv.shutdown()
    res["label"] = "FAKE-MODEL REPLAY - NOT A GEMMA TEST - NOT A SCORE TEST"
    res["http_requests_captured"] = list(CAPTURED)
    allowed = {"run_command", "read_file", "edit_file", "write_file", "get_status", "submit_patch",
               "search_similar_code", "get_code_neighbors", "get_code_subgraph", "code_analyzer"}
    offered = {t for c in CAPTURED for t in c["tools_offered"]}
    res["checks"] = {
        "undeclared_tools_offered": sorted(offered - allowed),
        "issue_reached_a_system_prompt": any(c["issue_in_system_prompt"] for c in CAPTURED),
        "issue_reached_the_root_conversation": any(c["issue_in_any_message"] for c in CAPTURED),
        "raw_template_braces_left": any(c["raw_template_braces_left"] for c in CAPTURED),
        "patch_submitted_via_fake_sandbox": res.get("ctx_after", {}).get("patch_submitted"),
        "thinking_fields_seen_in_any_request": sorted({k for c in CAPTURED for k in c["thinking_related_fields"]}),
    }
    text = json.dumps(res, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
