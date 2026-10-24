#!/usr/bin/env python3
"""Static checks for the canonical declarative Gemma submission."""
from pathlib import Path
import re
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "submission"
MODEL = "gemma-4-31b-it-qat-w4a16-ct"
ALLOWED_EXTENSIONS = {".yaml", ".yml", ".md", ".txt", ".py", ".json", ".safetensors"}
REQUIRED = ["agent.yaml", "eval_config.yaml", "configs/sampling.yaml", "prompts/system.md"]
ALLOWED_TOOLS = {
    "run_command", "read_file", "edit_file", "write_file", "get_status",
    "submit_patch", "get_code_neighbors", "search_similar_code", "get_code_subgraph",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path: Path):
    class IncludeLoader(yaml.SafeLoader):
        pass
    IncludeLoader.add_constructor("!include", lambda loader, node: loader.construct_scalar(node))
    try:
        return yaml.load(path.read_text(encoding="utf-8"), Loader=IncludeLoader)
    except Exception as exc:
        fail(f"invalid YAML in {path.relative_to(ROOT)}: {type(exc).__name__}: {exc}")


def validate() -> list[str]:
    if not SRC.is_dir():
        fail("submission/ directory does not exist")
    notes = []
    for rel in REQUIRED:
        p = SRC / rel
        if not p.is_file():
            fail(f"missing required file: submission/{rel}")

    all_files = sorted(p for p in SRC.rglob("*") if p.is_file())
    if not all_files:
        fail("submission contains no files")
    for p in all_files:
        if p.suffix.lower() not in ALLOWED_EXTENSIONS:
            fail(f"unsupported file extension: {p.relative_to(SRC)}")
        if p.is_symlink():
            fail(f"symlink is not allowed: {p.relative_to(SRC)}")

    for p in all_files:
        text = p.read_text(encoding="utf-8", errors="replace")
        for target in re.findall(r"!include\s+([^\s]+)", text):
            resolved = (p.parent / target).resolve()
            if SRC.resolve() not in resolved.parents:
                fail(f"include escapes submission root: {p.relative_to(SRC)} -> {target}")
            if not resolved.is_file():
                fail(f"include target missing: {p.relative_to(SRC)} -> {target}")

    agent = load_yaml(SRC / "agent.yaml")
    sampling = load_yaml(SRC / "configs/sampling.yaml")
    evaluation = load_yaml(SRC / "eval_config.yaml")
    if not isinstance(agent, dict): fail("agent.yaml must be a mapping")
    if agent.get("model") != MODEL: fail(f"model must be exactly {MODEL}")
    if agent.get("agent_class", "LlmAgent") != "LlmAgent": fail("agent_class must be LlmAgent")
    tools = agent.get("tools")
    if not isinstance(tools, list): fail("agent.yaml tools must be a list")
    found_tools = {str(t) for t in tools if isinstance(t, str)}
    unknown = found_tools - ALLOWED_TOOLS
    missing = ALLOWED_TOOLS - found_tools
    if unknown: fail(f"unknown tool names declared: {sorted(unknown)}")
    if missing: fail(f"this candidate is expected to declare all documented tools; missing: {sorted(missing)}")
    if agent.get("instruction") != "prompts/system.md": fail("instruction must include prompts/system.md")
    if agent.get("generate_content_config") != "configs/sampling.yaml": fail("sampling include must point to configs/sampling.yaml")

    if not isinstance(sampling, dict): fail("sampling.yaml must be a mapping")
    if int(sampling.get("max_output_tokens", 0)) <= 0 or int(sampling.get("max_output_tokens", 0)) > 32768:
        fail("max_output_tokens must be within 1..32768")
    thinking = sampling.get("thinking_config", {})
    if not isinstance(thinking, dict): fail("thinking_config must be a mapping")
    if not 0 <= int(thinking.get("thinking_budget", 4096)) <= 32768: fail("thinking_budget must be within 0..32768")

    if not isinstance(evaluation, dict) or not isinstance(evaluation.get("evaluation"), dict):
        fail("eval_config.yaml must contain an evaluation mapping")
    e = evaluation["evaluation"]
    for key in ("timeout_seconds", "max_tool_calls", "max_time_minutes", "max_turns"):
        if not isinstance(e.get(key), int) or e[key] <= 0: fail(f"evaluation.{key} must be a positive integer")

    prompt = (SRC / "prompts/system.md").read_text(encoding="utf-8")
    if "{" in prompt or "}" in prompt: fail("prompt contains braces that may be interpreted as state templates")
    notes.append(f"Required files: {len(REQUIRED)}/{len(REQUIRED)}")
    notes.append(f"Submission files: {len(all_files)}")
    notes.append(f"Declared tools: {len(found_tools)}")
    notes.append(f"Model: {MODEL}")
    notes.append(f"Evaluation budget: {e['max_time_minutes']} min / {e['max_tool_calls']} calls / {e['max_turns']} turns")
    return notes


if __name__ == "__main__":
    for note in validate(): print(f"PASS: {note}")
    print("PASS: static submission validation only; official harness compilation is separate")
