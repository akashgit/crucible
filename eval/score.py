#!/usr/bin/env python3
"""Crucible eval harness — 5 dimensions measuring plugin quality.

Dimensions:
  syntax_check     (0.15): Shell scripts parse, JSON/YAML configs are valid
  plugin_structure (0.20): Required plugin files exist and have expected content
  adversary_prompt (0.30): adversary.md has both phases, explicit rules, severity defs
  hook_wiring      (0.20): hooks.json references correct events and real files
  e2e_validation   (0.15): End-to-end test scenarios pass

Output: {"results": [{"name": str, "score": float, "weight": float, "passed": bool, "details": str}, ...]}
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def eval_syntax_check() -> dict:
    """Verify shell scripts parse and JSON configs are valid."""
    errors = []
    checks = 0

    for sh_file in ROOT.rglob("*.sh"):
        if ".git" in sh_file.parts or ".factory" in sh_file.parts:
            continue
        checks += 1
        result = subprocess.run(
            ["bash", "-n", str(sh_file)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            errors.append(f"{sh_file.name}: {result.stderr.strip()}")

    for json_file in [ROOT / ".claude-plugin" / "plugin.json", ROOT / "hooks" / "hooks.json"]:
        if json_file.exists():
            checks += 1
            try:
                json.loads(json_file.read_text())
            except json.JSONDecodeError as e:
                errors.append(f"{json_file.name}: {e}")

    if checks == 0:
        return {"name": "syntax_check", "score": 0.0, "weight": 0.15,
                "passed": False, "details": "No files to check"}

    score = max(0.0, 1.0 - len(errors) / checks)
    return {
        "name": "syntax_check",
        "score": round(score, 3),
        "weight": 0.15,
        "passed": len(errors) == 0,
        "details": "; ".join(errors) if errors else f"All {checks} files valid",
    }


def eval_plugin_structure() -> dict:
    """Check that required plugin files exist with expected content."""
    required = {
        ".claude-plugin/plugin.json": lambda p: "crucible" in p.read_text(),
        "hooks/hooks.json": lambda p: "hooks" in p.read_text(),
        "agents/adversary.md": lambda p: len(p.read_text()) > 100,
        "skills/crucible-verify/SKILL.md": lambda p: len(p.read_text()) > 50,
        "scripts/parse-diff.sh": lambda p: os.access(p, os.X_OK),
        "eval/score.py": lambda p: p.exists(),
        "README.md": lambda p: len(p.read_text()) > 50,
        "CLAUDE.md": lambda p: len(p.read_text()) > 50,
    }

    present = 0
    valid = 0
    missing = []

    for rel_path, validator in required.items():
        full_path = ROOT / rel_path
        if full_path.exists():
            present += 1
            try:
                if validator(full_path):
                    valid += 1
                else:
                    missing.append(f"{rel_path} (invalid content)")
            except Exception as e:
                missing.append(f"{rel_path} (error: {e})")
        else:
            missing.append(f"{rel_path} (missing)")

    total = len(required)
    score = valid / total if total > 0 else 0.0

    return {
        "name": "plugin_structure",
        "score": round(score, 3),
        "weight": 0.20,
        "passed": valid == total,
        "details": f"{valid}/{total} valid" + (f" — missing: {', '.join(missing)}" if missing else ""),
    }


def eval_adversary_prompt() -> dict:
    """Evaluate adversary.md for completeness and quality."""
    adversary_path = ROOT / "agents" / "adversary.md"
    if not adversary_path.exists():
        return {"name": "adversary_prompt", "score": 0.0, "weight": 0.30,
                "passed": False, "details": "agents/adversary.md not found"}

    content = adversary_path.read_text()
    checks = {}

    checks["has_phase1"] = "PHASE 1" in content and "Planning" in content
    checks["has_phase2"] = "PHASE 2" in content and "Execution" in content

    explicit_rules = [
        "You MUST run what was built",
        "Every finding MUST include the command you ran",
        "Do NOT report theoretical concerns",
        "Break confidence rather than validate",
        "Material findings only",
        "maximum of 3 argue-back loops",
    ]
    rules_found = sum(1 for rule in explicit_rules if rule in content)
    checks["has_explicit_rules"] = rules_found == len(explicit_rules)

    checks["has_severity_critical"] = "Critical" in content and ("security" in content.lower() or "data loss" in content.lower())
    checks["has_severity_major"] = "Major" in content and "spec" in content.lower()
    checks["has_severity_minor"] = "Minor" in content and "style" in content.lower()

    checks["has_iteration_cap"] = "3" in content and ("loop" in content.lower() or "iteration" in content.lower())
    checks["has_convergence"] = "Convergence" in content or "convergence" in content
    checks["has_report_format"] = "report.md" in content and "Verdict" in content
    checks["has_evidence_requirement"] = "command" in content.lower() and "output" in content.lower()

    passed = sum(checks.values())
    total = len(checks)
    score = passed / total if total > 0 else 0.0

    failed = [k for k, v in checks.items() if not v]
    details = f"{passed}/{total} checks passed"
    if failed:
        details += f" — failed: {', '.join(failed)}"
    details += f" (rules: {rules_found}/{len(explicit_rules)})"

    return {
        "name": "adversary_prompt",
        "score": round(score, 3),
        "weight": 0.30,
        "passed": score >= 0.8,
        "details": details,
    }


def eval_hook_wiring() -> dict:
    """Verify hooks.json references correct events and real files."""
    hooks_path = ROOT / "hooks" / "hooks.json"
    if not hooks_path.exists():
        return {"name": "hook_wiring", "score": 0.0, "weight": 0.20,
                "passed": False, "details": "hooks/hooks.json not found"}

    try:
        data = json.loads(hooks_path.read_text())
    except json.JSONDecodeError as e:
        return {"name": "hook_wiring", "score": 0.0, "weight": 0.20,
                "passed": False, "details": f"Invalid JSON: {e}"}

    checks = {}

    hooks = data.get("hooks", {})
    checks["has_hooks_key"] = "hooks" in data

    checks["has_session_start"] = "UserPromptSubmit" in hooks
    checks["has_session_end"] = "Stop" in hooks

    stop_hooks = hooks.get("Stop", [])
    commands = []
    for entry in stop_hooks:
        for hook in entry.get("hooks", []):
            commands.append(hook.get("command", ""))
    combined = " ".join(commands)
    references_parse_diff = "parse-diff.sh" in combined
    if not references_parse_diff:
        for cmd in commands:
            if "crucible-hooks.sh" in cmd:
                script_path = ROOT / "scripts" / "crucible-hooks.sh"
                if script_path.exists() and "parse-diff.sh" in script_path.read_text():
                    references_parse_diff = True
                    break
    checks["stop_references_parse_diff"] = references_parse_diff

    checks["parse_diff_exists"] = (ROOT / "scripts" / "parse-diff.sh").exists()
    checks["parse_diff_executable"] = os.access(ROOT / "scripts" / "parse-diff.sh", os.X_OK)

    submit_hooks = hooks.get("UserPromptSubmit", [])
    has_task_capture = False
    for entry in submit_hooks:
        for hook in entry.get("hooks", []):
            cmd = hook.get("command", "")
            if "task" in cmd or "crucible" in cmd.lower():
                has_task_capture = True
    checks["submit_captures_task"] = has_task_capture

    passed = sum(checks.values())
    total = len(checks)
    score = passed / total if total > 0 else 0.0

    failed = [k for k, v in checks.items() if not v]
    details = f"{passed}/{total} checks passed"
    if failed:
        details += f" — failed: {', '.join(failed)}"

    return {
        "name": "hook_wiring",
        "score": round(score, 3),
        "weight": 0.20,
        "passed": score >= 0.8,
        "details": details,
    }


def eval_e2e_validation() -> dict:
    """Check end-to-end test scenarios exist and are runnable."""
    e2e_dir = ROOT / "tests" / "e2e"
    if not e2e_dir.exists():
        return {"name": "e2e_validation", "score": 0.0, "weight": 0.15,
                "passed": False, "details": "tests/e2e/ directory not found"}

    checks = {}

    scenario_files = list(e2e_dir.glob("scenario-*.md"))
    checks["has_scenarios"] = len(scenario_files) >= 3

    expected = ["scenario-math.md", "scenario-featurebench.md", "scenario-programming.md"]
    for name in expected:
        path = e2e_dir / name
        checks[f"has_{name}"] = path.exists() and len(path.read_text()) > 100

    readme = e2e_dir / "README.md"
    checks["has_readme"] = readme.exists() and len(readme.read_text()) > 50

    run_script = e2e_dir / "run-scenario.sh"
    checks["has_run_script"] = run_script.exists()
    if run_script.exists():
        checks["run_script_executable"] = os.access(run_script, os.X_OK)
        result = subprocess.run(
            ["bash", "-n", str(run_script)],
            capture_output=True, text=True, timeout=10,
        )
        checks["run_script_valid_syntax"] = result.returncode == 0
    else:
        checks["run_script_executable"] = False
        checks["run_script_valid_syntax"] = False

    passed = sum(checks.values())
    total = len(checks)
    score = passed / total if total > 0 else 0.0

    failed = [k for k, v in checks.items() if not v]
    details = f"{passed}/{total} checks passed"
    if failed:
        details += f" — failed: {', '.join(failed)}"

    return {
        "name": "e2e_validation",
        "score": round(score, 3),
        "weight": 0.15,
        "passed": score >= 0.7,
        "details": details,
    }


EVALS = [eval_syntax_check, eval_plugin_structure, eval_adversary_prompt,
         eval_hook_wiring, eval_e2e_validation]


def main() -> None:
    results = []
    for fn in EVALS:
        try:
            results.append(fn())
        except Exception as e:
            results.append({
                "name": fn.__name__.replace("eval_", ""),
                "score": 0.0,
                "weight": 0.0,
                "passed": False,
                "details": f"Eval crashed: {e}",
            })

    output = {"results": results}
    json.dump(output, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
