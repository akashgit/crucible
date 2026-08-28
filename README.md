# Crucible

Adversarial verification plugin for Claude Code. Add `@crucible` to any prompt and an independent agent plans verification while you work, then executes that plan against your changes — running what was built, finding real problems with evidence, and looping with fixes until issues are resolved.

Crucible is **opt-in**: prompts without `@crucible` are completely ignored.

## How It Works

```
You submit a prompt containing @crucible
    |
    |--- Claude works on your task (normal session)
    |
    '--- Crucible runs in parallel:
         |
         |-- PHASE 1 (while Claude works):
         |   Reads your original task
         |   Builds a verification plan BEFORE seeing any code
         |   Writes plan to .crucible/verification-plan.md
         |
         '-- PHASE 2 (when Claude finishes):
             Captures the diff (committed, uncommitted, or untracked files)
             Spinner shows "Crucible: verifying your changes..."
             Executes verification plan against actual code
             Runs what was built — starts servers, calls APIs, executes scripts
             Classifies findings: Critical / Major / Minor
             Every finding has evidence: command + output
             |
             '-- VERIFY-FIX LOOP:
                 If findings exist, injects them back into the session
                 Claude reads the findings and fixes the issues
                 Crucible re-verifies the fixes
                 Loops up to 3 times (configurable)
                 Stops on PASS or max iterations

Prompts without @crucible → nothing happens, zero overhead.
```

## Install

```bash
claude plugin install /path/to/crucible
```

Once installed, just add `@crucible` to any prompt to activate verification. The skill `/crucible-verify` and the adversary agent `@crucible:adversary` are also available for manual use.

To install for a specific scope:

```bash
claude plugin install /path/to/crucible --scope project   # team-wide via version control
claude plugin install /path/to/crucible --scope user       # personal (default)
```

## Enable / Disable

Check if Crucible is installed:

```bash
claude plugin list
```

Disable Crucible (hooks stop firing, plugin stays installed):

```bash
claude plugin disable crucible
```

Re-enable it:

```bash
claude plugin enable crucible
```

Uninstall completely:

```bash
claude plugin uninstall crucible
```

## Usage

### Automatic mode (default)

Crucible only activates when your prompt contains `@crucible`:

```
Build a URL shortener with SQLite storage @crucible
```

1. **You submit a prompt with `@crucible`** — Crucible captures your task and spawns Phase 1 planning in the background. Prompts without the trigger are ignored.
2. **Claude finishes** — the Stop hook captures the diff and runs Phase 2 verification. A spinner shows "Crucible: verifying your changes..." while it works.
3. **Findings delivered** — the session rewakes with the Crucible report. Claude reads the findings and fixes any issues.
4. **Re-verification** — Crucible re-verifies the fixes. This loops up to 3 times or until all findings are resolved.

### Configuration

```bash
export CRUCIBLE_MAX_ITERATIONS=5   # default is 3
export CRUCIBLE_TRIGGER="verify"   # default is @crucible
```

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

Previous iteration reports are preserved as `.crucible/report-1.md`, `.crucible/report-2.md`, etc.

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

The adversary agents have their own budget caps: $0.50 for Phase 1 (planning), $2.00 for Phase 2 (execution) per iteration.

## Troubleshooting

**Adversary not spawning:** Check that Crucible is installed and enabled: `claude plugin list`. The hooks fire automatically when the plugin is active.

**No diff captured:** The diff parser requires a git repository with at least one commit. It checks committed changes (`git diff HEAD~1 HEAD`), uncommitted changes (`git diff HEAD`), staged changes (`git diff --cached`), and untracked files (via `git add -N`), in that order.

**Large diffs causing timeouts:** Diffs over 50K characters are truncated. Use `/crucible-verify --focus <area>` to narrow the scope.

**Loop not stopping:** The verify-fix loop stops on PASS or after `CRUCIBLE_MAX_ITERATIONS` (default 3). To reset mid-session, delete `.crucible/iteration`.

**Stale state from a previous session:** Delete the `.crucible/` directory to start fresh.

## Architecture

```
crucible/
├── .claude-plugin/
│   └── plugin.json                 # Plugin manifest
├── hooks/
│   └── hooks.json                  # Lifecycle hook definitions
├── agents/
│   └── adversary.md                # Adversary system prompt
├── skills/
│   └── crucible-verify/
│       └── SKILL.md                # Manual /crucible-verify trigger
├── scripts/
│   ├── crucible-hooks.sh           # Hook dispatcher (phases + loop logic)
│   └── parse-diff.sh               # Diff parser (committed/uncommitted/untracked)
├── eval/
│   └── score.py                    # 5-dimension eval harness
├── tests/
│   ├── test_plugin_structure.py    # Structural validation tests
│   └── e2e/                        # End-to-end test scenarios
├── README.md
└── CLAUDE.md
```

## Zero Dependencies

No npm, no pip, no TypeScript, no SDK, no MCP server. Everything is shell scripts, markdown, and JSON configuration. Claude Code provides all the infrastructure.
