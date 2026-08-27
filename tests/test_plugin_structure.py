#!/usr/bin/env python3
"""Verify Crucible plugin files exist and are valid."""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestPluginManifest(unittest.TestCase):
    def test_plugin_json_exists(self):
        self.assertTrue((ROOT / "plugin.json").exists())

    def test_plugin_json_valid(self):
        data = json.loads((ROOT / "plugin.json").read_text())
        self.assertEqual(data["name"], "crucible")
        self.assertEqual(data["version"], "0.1.0")
        self.assertIn("description", data)
        self.assertIn("hooks", data)
        self.assertIn("agents", data)
        self.assertIn("skills", data)

    def test_plugin_version_semver(self):
        data = json.loads((ROOT / "plugin.json").read_text())
        parts = data["version"].split(".")
        self.assertEqual(len(parts), 3)
        for part in parts:
            int(part)


class TestHooksConfig(unittest.TestCase):
    def test_hooks_json_exists(self):
        self.assertTrue((ROOT / "hooks" / "hooks.json").exists())

    def test_hooks_json_valid(self):
        data = json.loads((ROOT / "hooks" / "hooks.json").read_text())
        self.assertIn("hooks", data)
        hooks = data["hooks"]
        self.assertIn("UserPromptSubmit", hooks)
        self.assertIn("Stop", hooks)

    def test_stop_hook_references_parse_diff(self):
        data = json.loads((ROOT / "hooks" / "hooks.json").read_text())
        stop_hooks = data["hooks"]["Stop"]
        commands = []
        for entry in stop_hooks:
            for hook in entry.get("hooks", []):
                commands.append(hook.get("command", ""))
        combined = " ".join(commands)
        self.assertIn("parse-diff.sh", combined)


class TestAdversaryPrompt(unittest.TestCase):
    def test_adversary_md_exists(self):
        self.assertTrue((ROOT / "agents" / "adversary.md").exists())

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


class TestSkill(unittest.TestCase):
    def test_skill_md_exists(self):
        self.assertTrue(
            (ROOT / "skills" / "crucible-verify" / "SKILL.md").exists()
        )

    def test_skill_has_instructions(self):
        content = (ROOT / "skills" / "crucible-verify" / "SKILL.md").read_text()
        self.assertIn("crucible-verify", content)
        self.assertIn("--focus", content)
        self.assertIn("--strict", content)


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

    def test_readme_has_usage(self):
        content = (ROOT / "README.md").read_text()
        self.assertIn("crucible-verify", content)


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
        self.assertIn("plugin_structure", names)
        self.assertIn("adversary_prompt", names)
        self.assertIn("hook_wiring", names)
        self.assertIn("e2e_validation", names)


if __name__ == "__main__":
    unittest.main()
