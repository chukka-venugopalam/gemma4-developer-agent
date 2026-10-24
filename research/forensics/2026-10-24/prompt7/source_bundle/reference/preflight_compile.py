"""PRE-FLIGHT COMPILE of an unpacked submission directory against the harness wheels that are INSTALLED
(or unpacked in <harness_dir>).  Version-tolerant: helper imports that moved between swegemma releases fall back to
what adk_submission itself provides.

    python -I preflight_compile.py <harness_dir | -> <submission_dir>

  <harness_dir>  directory holding unpacked wheels (adk_submission/, swegemma/, adk_eval_core/ and their *.dist-info),
                 or '-' when the wheels are already pip-installed (e.g. in a Kaggle notebook with the wheelhouse attached).
  <submission_dir>  the UNZIPPED submission (agent.yaml at its top level). Unzip into a fresh empty folder first.

Prints ONE JSON object: installed versions, one entry per step, VERDICT_compile_submission = PASS | FAIL.
Always exits 0; the verdict is in the JSON.  Set PREFLIGHT_FORCE_FALLBACK=1 to exercise the fallback code paths.

WHAT A PASS MEANS: the organizers' YAML loader, schema, tool/model registries and generation constraints, in the
installed version, accept the directory.  WHAT IT DOES NOT MEAN: nothing here starts vLLM, runs Gemma, uses a sandbox,
or runs the real scorer (scripts/inference.py is not public).  Fallback mode uses stub tools and a stub model, so the
thinking-config bridge is not exercised.
"""
from __future__ import annotations

import importlib.metadata as md
import json
import os
import sys
import traceback
from pathlib import Path

harness_dir, sub_dir = sys.argv[1], Path(sys.argv[2])
if harness_dir != "-":
    sys.path.insert(0, harness_dir)
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
FORCE_FALLBACK = os.environ.get("PREFLIGHT_FORCE_FALLBACK") == "1"
MODEL = "gemma-4-31b-it-qat-w4a16-ct"

report: dict = {"submission_dir": str(sub_dir), "harness_dir": harness_dir, "force_fallback": FORCE_FALLBACK,
                "versions": {}, "steps": [], "notes": []}
for dist in ("swegemma", "adk-submission", "adk-eval-core", "google-adk"):
    try:
        report["versions"][dist] = md.version(dist)
    except Exception as e:  # noqa: BLE001
        report["versions"][dist] = f"UNKNOWN ({type(e).__name__})"


def step(name, fn):
    try:
        val = fn()
        report["steps"].append({"step": name, "ok": True, "detail": val})
        return True, val
    except BaseException as e:  # noqa: BLE001 - record every failure
        report["steps"].append({"step": name, "ok": False, "exc_type": f"{type(e).__module__}.{type(e).__name__}",
                                "message": str(e), "traceback_tail": traceback.format_exc().strip().splitlines()[-10:]})
        return False, None


# ---------------------------------------------------------------- imports that exist in every release seen so far
from adk_submission import ToolRegistry, compile_submission  # noqa: E402
from adk_submission.discovery import validate_directory  # noqa: E402
from swegemma.config import build_submission_limits  # noqa: E402

limits, gen_constraints = build_submission_limits()
try:
    from swegemma.config import ALLOWED_ADAPTER_EXTENSIONS  # noqa: E402
except ImportError:
    ALLOWED_ADAPTER_EXTENSIONS = frozenset({".safetensors"})


# ---------------------------------------------------------------- step 1: directory structure
step("validate_directory", lambda: str(validate_directory(sub_dir, limits).config_path))


# ---------------------------------------------------------------- step 2: exactly one declared model == competition model
def single_model():
    fn = None
    if not FORCE_FALLBACK:
        for mod in ("swegemma.models", "swegemma.models.discovery"):
            try:
                fn = getattr(__import__(mod, fromlist=["x"]), "validate_single_declared_model")
                report["notes"].append(f"single-model check: swegemma helper from {mod}")
                break
            except (ImportError, AttributeError):
                continue
    if fn is not None:
        return fn(sub_dir)
    from adk_submission.discovery import discover_declared_models  # fallback (used by the 0.2.11 official notebook)
    try:
        names = discover_declared_models(str(sub_dir))
    except TypeError:
        names = discover_declared_models(str(sub_dir), None)
    names = {str(n).removeprefix("openai/") for n in names}
    report["notes"].append("single-model check: FALLBACK adk_submission.discovery.discover_declared_models")
    if names != {MODEL}:
        raise ValueError(f"declared models {sorted(names)} != exactly [{MODEL!r}]")
    return MODEL


step("single_declared_model", single_model)


# ---------------------------------------------------------------- step 3: adapters
def adapters():
    from adk_submission import discover_adapters
    try:
        m = discover_adapters(str(sub_dir), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)
    except TypeError:
        m = discover_adapters(str(sub_dir))
    return sorted(getattr(m, "adapters", {}).keys()), m


ok_ad, ad = step("discover_adapters", adapters)
manifest = None
if ok_ad:
    report["steps"][-1]["detail"], manifest = ad


# ---------------------------------------------------------------- step 4: full compile
def build_tools():
    if not FORCE_FALLBACK:
        try:
            from swegemma.tools import create_tools
            return dict(create_tools(None)), "swegemma.tools.create_tools(None)"
        except Exception:  # noqa: BLE001
            pass
        try:
            from swegemma.context import SwegemmaContext
            return dict(SwegemmaContext(problem_statement="x", task_id="t", repo="r").create_tools()), "SwegemmaContext.create_tools()"
        except Exception:  # noqa: BLE001
            pass

    def run_command(command: str) -> str: return ""
    def read_file(filepath: str, start_line: int | None = None, end_line: int | None = None) -> str: return ""
    def write_file(filepath: str, content: str) -> str: return ""
    def edit_file(filepath: str, old_string: str, new_string: str, allow_multiple: bool = False) -> str: return ""
    def get_status() -> str: return ""
    def submit_patch() -> str: return ""
    def get_code_neighbors(node: str, edge_type: str | None = None, max_neighbors: int = 50) -> str: return ""
    def search_similar_code(query: str, k: int = 10) -> str: return ""
    def get_code_subgraph(nodes: list[str]) -> str: return ""
    stubs = {f.__name__: f for f in (run_command, read_file, write_file, edit_file, get_status, submit_patch,
                                     get_code_neighbors, search_similar_code, get_code_subgraph)}
    return stubs, "FALLBACK stub tools (names + signatures only)"


def build_models():
    if not FORCE_FALLBACK:
        for mod in ("swegemma.models.registry", "swegemma.models"):
            try:
                setup = getattr(__import__(mod, fromlist=["x"]), "setup_gemma_model_registry")
                try:
                    reg = setup(api_base="http://127.0.0.1:8000/v1", served_model=MODEL, adapter_manifest=manifest)
                except TypeError:
                    reg = setup(api_base="http://127.0.0.1:8000/v1", api_key="EMPTY")
                resolver = None
                try:
                    from swegemma.models.registry import resolve_swegemma_adapter as r
                    resolver = lambda b, i: r(b, i, reg)  # noqa: E731
                except Exception:  # noqa: BLE001
                    pass
                return reg, resolver, f"{mod}.setup_gemma_model_registry"
            except (ImportError, AttributeError):
                continue
    from adk_submission import ModelRegistry
    from google.adk.models.base_llm import BaseLlm

    class _StubLlm(BaseLlm):
        model: str = "stub-compile-only"

        @classmethod
        def supported_models(cls):
            return [r".*"]

        async def generate_content_async(self, llm_request, stream=False):
            raise RuntimeError("stub model: compile-only")
            yield  # noqa: unreachable - makes this an async generator

    reg = ModelRegistry()
    reg.register(MODEL, _StubLlm())
    return reg, None, "FALLBACK adk_submission.ModelRegistry + stub model"


def describe(agent):
    gcc = getattr(agent, "generate_content_config", None)
    return {
        "name": agent.name, "type": type(agent).__name__,
        "model": getattr(getattr(agent, "model", None), "model", str(getattr(agent, "model", None))),
        "instruction_chars": len(agent.instruction) if isinstance(getattr(agent, "instruction", None), str) else None,
        "tools": [getattr(t, "name", getattr(t, "__name__", type(t).__name__)) for t in getattr(agent, "tools", [])],
        "generate_content_config": gcc.model_dump(exclude_none=True) if gcc is not None else None,
        "sub_agents": [describe(s) for s in getattr(agent, "sub_agents", [])],
        "agent_tools": [{"tool": getattr(t, "name", "?"), "skip_summarization": getattr(t, "skip_summarization", None),
                         "inner": describe(t.agent)} for t in getattr(agent, "tools", []) if hasattr(t, "agent")],
    }


def do_compile():
    tools, tools_src = build_tools()
    models, resolver, models_src = build_models()
    report["notes"].append(f"compile tools: {tools_src}")
    report["notes"].append(f"compile models: {models_src}")
    registry = ToolRegistry()
    for k, v in tools.items():
        registry.register(k, v)
    kw = dict(submission_dir=sub_dir, tool_registry=registry, model_registry=models, limits=limits,
              generation_constraints=gen_constraints)
    attempts = [dict(kw, adapter_manifest=manifest, adapter_resolver_fn=resolver, script_timeout=180),
                dict(kw, adapter_resolver_fn=resolver) if resolver else dict(kw)]
    last = None
    for a in attempts:
        try:
            return describe(compile_submission(**a))
        except TypeError as e:  # signature drift between releases: retry with the smaller kwarg set
            last = e
            report["notes"].append(f"compile_submission signature mismatch, retrying with fewer kwargs: {e}")
    raise last


ok_c, _ = step("compile_submission", do_compile)
report["VERDICT_compile_submission"] = "PASS" if ok_c else "FAIL"
print(json.dumps(report, indent=2, default=str))
