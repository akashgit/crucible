#!/usr/bin/env python3
"""Verify Crucible project files exist and are valid."""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestCLI(unittest.TestCase):
    def test_bin_crucible_exists(self):
        self.assertTrue((ROOT / "bin" / "crucible").exists())

    def test_bin_crucible_executable(self):
        self.assertTrue(os.access(ROOT / "bin" / "crucible", os.X_OK))

    def test_bin_crucible_valid_bash(self):
        result = subprocess.run(
            ["bash", "-n", str(ROOT / "bin" / "crucible")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"Syntax error: {result.stderr}")

    def test_bin_crucible_help(self):
        result = subprocess.run(
            [str(ROOT / "bin" / "crucible"), "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage:", result.stdout)
        self.assertIn("--max-loops", result.stdout)
        self.assertIn("--project-dir", result.stdout)
        self.assertIn("--verbose", result.stdout)

    def test_bin_crucible_no_args_error(self):
        result = subprocess.run(
            [str(ROOT / "bin" / "crucible")],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No task provided", result.stderr)


class TestPluginManifest(unittest.TestCase):
    def test_plugin_json_exists(self):
        self.assertTrue((ROOT / ".claude-plugin" / "plugin.json").exists())

    def test_old_plugin_json_removed(self):
        self.assertFalse((ROOT / "plugin.json").exists())

    def test_plugin_json_valid(self):
        data = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
        self.assertEqual(data["name"], "crucible")
        self.assertIn("description", data)
        self.assertIn("author", data)

    def test_plugin_version_semver(self):
        data = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
        parts = data["version"].split(".")
        self.assertEqual(len(parts), 3)
        for part in parts:
            int(part)


class TestHooksFormat(unittest.TestCase):
    def test_hooks_json_valid(self):
        data = json.loads((ROOT / "hooks" / "hooks.json").read_text())
        self.assertIn("hooks", data)

    def test_hooks_command_hooks_have_command_field(self):
        data = json.loads((ROOT / "hooks" / "hooks.json").read_text())
        for event, matcher_groups in data["hooks"].items():
            for group in matcher_groups:
                for hook in group["hooks"]:
                    if hook["type"] == "command":
                        self.assertIn("command", hook)

    def test_hooks_use_plugin_root(self):
        content = (ROOT / "hooks" / "hooks.json").read_text()
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", content)

    def test_hooks_stop_has_async_rewake(self):
        data = json.loads((ROOT / "hooks" / "hooks.json").read_text())
        stop_hooks = data["hooks"]["Stop"]
        all_hooks = [h for g in stop_hooks for h in g["hooks"]]
        self.assertTrue(any(h.get("asyncRewake") for h in all_hooks))

    def test_crucible_hooks_script_exists(self):
        self.assertTrue((ROOT / "scripts" / "crucible-hooks.sh").exists())

    def test_crucible_hooks_executable(self):
        self.assertTrue(os.access(ROOT / "scripts" / "crucible-hooks.sh", os.X_OK))

    def test_crucible_hooks_valid_bash(self):
        result = subprocess.run(
            ["bash", "-n", str(ROOT / "scripts" / "crucible-hooks.sh")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"Syntax error: {result.stderr}")

    def test_capture_task_script_exists(self):
        self.assertTrue((ROOT / "scripts" / "capture-task.sh").exists())

    def test_capture_task_executable(self):
        self.assertTrue(os.access(ROOT / "scripts" / "capture-task.sh", os.X_OK))


class TestAdversaryPrompt(unittest.TestCase):
    def test_adversary_md_exists(self):
        self.assertTrue((ROOT / "agents" / "adversary.md").exists())

    def test_adversary_has_frontmatter(self):
        content = (ROOT / "agents" / "adversary.md").read_text()
        self.assertTrue(content.startswith("---"))
        self.assertIn("name: adversary", content)
        self.assertIn("model: sonnet", content)
        self.assertIn("maxTurns:", content)

    def test_adversary_has_phase1(self):
        content = (ROOT / "agents" / "adversary.md").read_text()
        self.assertIn("PHASE 1", content)
        self.assertIn("Verification Planning", content)

    def test_adversary_has_phase2(self):
        content = (ROOT / "agents" / "adversary.md").read_text()
        self.assertIn("PHASE 2", content)
        self.assertIn("Verification Execution", content)

    def test_adversary_has_explicit_rules(self):
        content = (ROOT / "agents" / "adversary.md").read_text()
        self.assertIn("You MUST run what was built", content)
        self.assertIn("Every finding MUST include the command you ran", content)
        self.assertIn("Do NOT report theoretical concerns", content)
        self.assertIn("Break confidence rather than validate", content)
        self.assertIn("Material findings only", content)
        self.assertIn("maximum of 3 argue-back loops", content)

    def test_adversary_has_severity_definitions(self):
        content = (ROOT / "agents" / "adversary.md").read_text()
        self.assertIn("Critical", content)
        self.assertIn("Major", content)
        self.assertIn("Minor", content)

    def test_adversary_has_report_format(self):
        content = (ROOT / "agents" / "adversary.md").read_text()
        self.assertIn("report.md", content)
        self.assertIn("Verdict", content)

    def test_adversary_has_convergence_criteria(self):
        content = (ROOT / "agents" / "adversary.md").read_text()
        self.assertIn("Convergence", content)
        self.assertIn("3 argue-back loops", content)


class TestScripts(unittest.TestCase):
    def test_parse_diff_exists(self):
        self.assertTrue((ROOT / "scripts" / "parse-diff.sh").exists())

    def test_parse_diff_executable(self):
        self.assertTrue(os.access(ROOT / "scripts" / "parse-diff.sh", os.X_OK))

    def test_parse_diff_valid_bash(self):
        result = subprocess.run(
            ["bash", "-n", str(ROOT / "scripts" / "parse-diff.sh")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"Syntax error: {result.stderr}")


class TestDocumentation(unittest.TestCase):
    def test_readme_exists(self):
        self.assertTrue((ROOT / "README.md").exists())

    def test_claude_md_exists(self):
        self.assertTrue((ROOT / "CLAUDE.md").exists())

    def test_readme_has_installation(self):
        content = (ROOT / "README.md").read_text()
        self.assertIn("install", content.lower())

    def test_readme_has_plugin_install(self):
        content = (ROOT / "README.md").read_text()
        self.assertIn("claude plugin install", content)

    def test_readme_has_cli_usage(self):
        content = (ROOT / "README.md").read_text()
        self.assertIn("bin/crucible", content)


class TestEvalHarness(unittest.TestCase):
    def test_score_py_exists(self):
        self.assertTrue((ROOT / "eval" / "score.py").exists())

    def test_score_py_valid_syntax(self):
        result = subprocess.run(
            [sys.executable, "-c", f"import ast; ast.parse(open('{ROOT / 'eval' / 'score.py'}').read())"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"Syntax error: {result.stderr}")

    def test_score_py_runs(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "eval" / "score.py")],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, f"Error: {result.stderr}")
        output = json.loads(result.stdout)
        self.assertIn("results", output)
        names = [r["name"] for r in output["results"]]
        self.assertIn("syntax_check", names)


if __name__ == "__main__":
    unittest.main()
