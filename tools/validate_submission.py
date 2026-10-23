#!/usr/bin/env python3
"""Static preflight for the canonical submission directory.

This deliberately does not pretend to invoke the official Kaggle compiler.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment-specific
    print(f"BLOCKED: PyYAML is required; install requirements-dev.txt ({exc})")
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / "submission"
EXPECTED_MODEL = "gemma-4-31b-it-qat-w4a16-ct"
ROOT_CONFIG_NAMES = {"agent.yaml", "agent.yml", "root_agent.yaml", "root_agent.yml"}
ALLOWED_EXTENSIONS = {".yaml", ".yml", ".md", ".txt", ".py", ".json", ".safetensors"}
ALLOWED_TOOLS = {
    "run_command", "submit_patch", "get_status", "read_file", "edit_file",
    "write_file", "search_similar_code", "get_code_neighbors", "get_code_subgraph",
}
INCLUDE_RE = re.compile(r"!include\s+([^\s#]+)")


class IncludePathLoader(yaml.SafeLoader):
    pass


def _include_constructor(loader: IncludePathLoader, node: yaml.Node) -> str:
    return loader.construct_scalar(node)


IncludePathLoader.add_constructor("!include", _include_constructor)


def parse_yaml(path: Path):
    try:
        return yaml.load(path.read_text(encoding="utf-8"), Loader=IncludePathLoader)
    except Exception as exc:
        raise ValueError(f"YAML parse failed for {path.relative_to(ROOT)}: {exc}") from exc


def validate_submission(submission: Path = SUBMISSION) -> list[str]:
    errors: list[str] = []
    warnings: list[str] = []
    if not submission.is_dir():
        return [f"submission directory does not exist: {submission}"]

    root_configs = [p for p in submission.iterdir() if p.is_file() and p.name in ROOT_CONFIG_NAMES]
    if len(root_configs) != 1:
        errors.append(f"expected exactly one root config, found {len(root_configs)}")
        root_config = None
    else:
        root_config = root_configs[0]

    files = [p for p in submission.rglob("*") if p.is_file()]
    for path in files:
        if path.is_symlink():
            errors.append(f"symlink is not allowed: {path.relative_to(submission)}")
            continue
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            errors.append(f"unsupported extension {path.suffix or '<none>'}: {path.relative_to(submission)}")
        if ".." in path.relative_to(submission).parts:
            errors.append(f"path traversal component: {path.relative_to(submission)}")

    if root_config:
        try:
            config = parse_yaml(root_config)
            if not isinstance(config, dict):
                errors.append("agent root YAML must be a mapping")
                config = {}
            if config.get("model") != EXPECTED_MODEL:
                errors.append(f"model must be exactly {EXPECTED_MODEL}")
            tools = config.get("tools")
            if not isinstance(tools, list):
                errors.append("agent tools must be a YAML list")
            else:
                for tool in tools:
                    if not isinstance(tool, str):
                        errors.append(f"tool declarations must be documented strings; got {tool!r}")
                    elif tool not in ALLOWED_TOOLS:
                        errors.append(f"undeclared/unknown tool name: {tool}")
                if len(tools) != len(set(t for t in tools if isinstance(t, str))):
                    warnings.append("duplicate tool declarations found")
            for key in ("instruction", "generate_content_config"):
                value = config.get(key)
                if isinstance(value, str) and value.startswith("!include "):
                    value = value[len("!include "):].strip()
                # Parsed YAML constructors return only the included path.
                if not isinstance(value, str) or not value:
                    errors.append(f"{key} must be a non-empty !include path")
        except ValueError as exc:
            errors.append(str(exc))

    # Verify every !include from its containing YAML file; forbid traversal and absolute paths.
    for yaml_path in [p for p in files if p.suffix.lower() in {".yaml", ".yml"}]:
        try:
            text = yaml_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"YAML file is not UTF-8: {yaml_path.relative_to(submission)}")
            continue
        for match in INCLUDE_RE.finditer(text):
            raw = match.group(1).strip().strip("\"'")
            rel = Path(raw)
            if rel.is_absolute() or ".." in rel.parts:
                errors.append(f"unsafe !include path {raw!r} in {yaml_path.relative_to(submission)}")
                continue
            target = (yaml_path.parent / rel).resolve()
            try:
                target.relative_to(submission.resolve())
            except ValueError:
                errors.append(f"!include escapes submission root: {raw!r}")
                continue
            if not target.is_file():
                errors.append(f"missing !include target {raw!r} from {yaml_path.relative_to(submission)}")

    eval_path = submission / "eval_config.yaml"
    if eval_path.exists():
        try:
            evaluation_config = parse_yaml(eval_path)
            if not isinstance(evaluation_config, dict) or not isinstance(evaluation_config.get("evaluation"), dict):
                errors.append("eval_config.yaml must contain root-level mapping evaluation:")
            else:
                eval_fields = evaluation_config["evaluation"]
                allowed_eval = {"timeout_seconds", "max_tool_calls", "max_time_minutes", "max_turns"}
                extra = set(eval_fields) - allowed_eval
                if extra:
                    errors.append(f"unknown evaluation keys: {', '.join(sorted(extra))}")
                for field, value in eval_fields.items():
                    if field not in allowed_eval:
                        continue
                    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
                        errors.append(f"evaluation.{field} must be a positive number")
        except ValueError as exc:
            errors.append(str(exc))

    sampling_path = submission / "configs" / "sampling.yaml"
    if not sampling_path.is_file():
        errors.append("missing configs/sampling.yaml")
    else:
        try:
            sampling = parse_yaml(sampling_path)
            if not isinstance(sampling, dict):
                errors.append("configs/sampling.yaml must be a mapping")
                sampling = {}
            tokens = sampling.get("max_output_tokens")
            if not isinstance(tokens, int) or isinstance(tokens, bool) or not (1 <= tokens <= 32768):
                errors.append("max_output_tokens must be an integer from 1 to 32768")
            thinking = sampling.get("thinking_config", {})
            if not isinstance(thinking, dict):
                errors.append("thinking_config must be a mapping")
            else:
                budget = thinking.get("thinking_budget")
                if budget is not None and (not isinstance(budget, int) or isinstance(budget, bool) or not 0 <= budget <= 32768):
                    errors.append("thinking_budget must be an integer from 0 to 32768")
        except ValueError as exc:
            errors.append(str(exc))

    prompt_dir = submission / "prompts"
    prompt_files = list(prompt_dir.glob("*.md")) if prompt_dir.exists() else []
    if not prompt_files:
        errors.append("at least one prompts/*.md file is required by this candidate")
    for path in prompt_files:
        content = path.read_text(encoding="utf-8")
        # The ADK parser can interpret identifier-shaped braces as state templates.
        if re.search(r"\{\s*[A-Za-z_][A-Za-z0-9_? .-]*\s*\}", content):
            errors.append(f"possible ADK state-template braces in {path.relative_to(submission)}")

    # Emit non-fatal context and config warnings.
    if root_config and len(files) > 20:
        warnings.append(f"submission contains {len(files)} files; inspect whether all are needed")

    for message in warnings:
        print(f"WARN: {message}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission-dir", type=Path, default=SUBMISSION)
    args = parser.parse_args()
    errors = validate_submission(args.submission_dir.resolve())
    if errors:
        print("STATIC VALIDATION: FAIL")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("STATIC VALIDATION: PASS")
    print("Scope: file layout, YAML parse, includes, model/tool names, budgets and prompt-template scan.")
    print("Not tested: official Kaggle compiler, current wheelhouse, Gemma inference or leaderboard score.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
