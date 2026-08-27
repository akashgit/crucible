# Crucible — Build Instructions

## What This Is

Crucible is a Claude Code plugin that provides adversarial verification. It spawns an independent agent that plans verification while the primary agent works, then executes that plan against the actual changes with evidence-backed findings.

## Architecture

```
crucible/
├── plugin.json                     # Plugin manifest
├── hooks/
│   └── hooks.json                  # Lifecycle hook definitions
├── agents/
│   └── adversary.md                # Adversary system prompt (THE core product)
├── skills/
│   └── crucible-verify/
│       └── SKILL.md                # Manual /crucible-verify trigger
├── scripts/
│   └── parse-diff.sh               # Diff parser for feeding adversary
├── eval/
│   └── score.py                    # 5-dimension eval harness
├── tests/
│   ├── test_plugin_structure.py    # Structural validation tests
│   └── e2e/                        # End-to-end test scenarios
├── README.md                       # Installation and usage
└── CLAUDE.md                       # This file
```

## Design: Two-Phase Adversary

1. **Phase 1 (Planning)** — runs concurrently with the primary agent. Reads the user's original task, builds a verification plan BEFORE seeing any code. Writes plan to `.crucible/verification-plan.md`.

2. **Phase 2 (Execution)** — runs after primary signals done. Reads the diff, executes the pre-built verification plan, runs what was built, classifies findings by severity, argues back with evidence.

## Zero Dependencies

No npm, no pip packages, no TypeScript, no SDK, no MCP server. Pure shell scripts + markdown + JSON config. Claude Code provides everything: subprocess spawning, tool access (Read, Bash, Edit), cost control via `--max-cost`.

## What NOT to Add

- No MCP server for cost tracking — use Claude Code's `--max-cost`
- No TypeScript build pipeline — everything is shell + markdown
- No SDK integration — Claude Code's native tools are sufficient
- No model selection logic — use whatever model the session runs
- No API key strategy — use Claude Code's existing auth
- No fixed specialist fleet — the adversary decides what to check
- No external dependencies of any kind
