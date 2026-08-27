# Crucible

Adversarial verification plugin for Claude Code. Crucible spawns an independent agent that plans verification while you work, then executes that plan against your changes — running what was built, finding real problems with evidence, and arguing back until issues are resolved.

## How It Works

```
You start a Claude Code session with a task
    |
    |--- Primary agent works on the task (normal Claude Code)
    |
    '--- Crucible captures your task (UserPromptSubmit hook)
         |
         |-- PHASE 1 (while you work):
         |   Adversary reads your original task.
         |   "What would correct look like? What tests prove this works?"
         |   Builds a verification plan BEFORE seeing any code.
         |   Writes plan to .crucible/verification-plan.md
         |
         '-- PHASE 2 (when you finish):
             Stop hook captures the diff via parse-diff.sh
             Adversary executes its verification plan against actual code
             Runs what was built --- starts servers, calls APIs, executes scripts
             Classifies findings: Critical / Major / Minor
             Every finding has evidence: command + output
             Argues back if Critical/Major issues found (up to 3 loops)
             Writes report to .crucible/report.md
```

## Install

```bash
claude plugin install /path/to/crucible
```

This registers Crucible as a plugin. Hooks fire automatically on every session, the skill is available as `/crucible-verify`, and the adversary agent can be invoked directly with `@crucible:adversary`.

To install for a specific scope:

```bash
claude plugin install /path/to/crucible --scope project   # team-wide via version control
claude plugin install /path/to/crucible --scope user       # personal (default)
```

### Enable / Disable

```bash
claude plugin enable crucible
claude plugin disable crucible
```

## Usage

### Automatic mode (hooks)

With Crucible installed, verification runs fully automatically:
1. When you submit a prompt, the UserPromptSubmit hook captures your task and spawns the adversary for Phase 1 planning (runs async while you work).
2. When Claude finishes responding, the Stop hook captures the diff and spawns the adversary for Phase 2 execution (runs async, re-wakes the session with findings).
3. The adversary's report is written to `.crucible/report.md`. If Critical or Major findings exist, they are delivered back to your session automatically via `asyncRewake`.

### Manual mode (skill)

At any point during a session, type:

```
/crucible-verify
```

This skips Phase 1 planning and goes straight to Phase 2 execution against the current diff.

**Options:**
- `/crucible-verify --focus security` — narrow verification to security concerns
- `/crucible-verify --focus performance` — focus on performance
- `/crucible-verify --strict` — fail on any finding, including Minor

### Direct agent invocation

You can invoke the adversary agent directly:

```
@crucible:adversary verify this change for security issues
```

### Reading the Report

After verification, check `.crucible/report.md`:

```
# Crucible Verification Report

## Summary
- Verdict: PASS | FAIL
- Iterations: 1
- Findings: 0 Critical, 1 Major, 2 Minor

## Major Findings
### Missing input validation on /api/users endpoint
What: POST /api/users accepts empty body without error
Command: curl -X POST http://localhost:3000/api/users -d '{}'
Output: {"id": 5, "name": null}
Impact: Creates user records with null required fields
Status: OPEN
```

## What Crucible Is NOT

- **Not an MCP server.** No separate process, no SDK, no TypeScript.
- **Not a linter.** Crucible runs your code, not static analysis.
- **Not a test framework.** Crucible verifies from the outside, as a skeptical user.
- **Not a cost tracker.** Use Claude Code's `--max-cost` flag for cost control.

## Cost Control

Crucible uses whatever model your Claude Code session runs. To control costs:

```bash
claude --max-cost 5.00   # Set a session cost limit
```

The adversary is a Claude Code subprocess — it shares your session's cost budget.

## Troubleshooting

**Adversary not spawning:** Verify Crucible is installed and enabled: `claude plugin list`. The hooks fire automatically when the plugin is active.

**No diff captured:** `parse-diff.sh` requires a git repository with committed changes. If you're working in a new repo with no commits, make an initial commit first.

**Large diffs causing timeouts:** Diffs over 50K characters are truncated. If your session makes very large changes, use `/crucible-verify --focus <area>` to narrow the scope.

**"No changes detected":** The diff parser checks `git diff HEAD~1 HEAD` first (committed changes — the most common case after the primary agent commits). If no committed diff is found, it falls back to `git diff HEAD` (uncommitted), then `git diff --cached` (staged only).

## Architecture

```
crucible/
├── .claude-plugin/
│   └── plugin.json                 # Plugin manifest (required for detection)
├── hooks/
│   └── hooks.json                  # Lifecycle hook definitions
├── agents/
│   └── adversary.md                # Adversary system prompt (the core product)
├── skills/
│   └── crucible-verify/
│       └── SKILL.md                # Manual /crucible-verify trigger
├── scripts/
│   ├── crucible-hooks.sh           # Hook dispatcher (task capture + adversary spawning)
│   └── parse-diff.sh               # Diff parser for feeding adversary
├── eval/
│   └── score.py                    # 5-dimension eval harness
├── tests/
│   ├── test_plugin_structure.py    # Structural validation tests
│   └── e2e/                        # End-to-end test scenarios
├── README.md                       # This file
└── CLAUDE.md                       # Build instructions
```

## Zero Dependencies

Crucible has no external dependencies. No npm packages, no pip packages, no TypeScript, no SDK, no MCP server. Everything is shell scripts, markdown, and JSON configuration. Claude Code provides all the infrastructure: subprocess spawning, tool access, cost control.
