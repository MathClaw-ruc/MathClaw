---
name: memory
description: Structured daily and weekly learning memory with dual graph snapshots.
always: true
---

# Memory

## Structure

- `memory/daily_memory/YYYY.M.D/YYYY_M_D.md` - Human-readable daily summary for one day.
- `memory/daily_memory/YYYY.M.D/YYYY_M_D.json` - Structured daily payload for code and downstream features.
- `memory/weekly_memory/YYYY_M_D_to_YYYY_M_D/YYYY_M_D_to_YYYY_M_D.md` - Weekly study plan generated from the last 7 daily summaries.
- `memory/graphs/knowledge_graph.json` - Knowledge-point graph.
- `memory/graphs/error_graph.json` - Error-pattern graph.
- `memory/MEMORY.md` - Auto-generated compatibility snapshot loaded into prompt context.
- `memory/HISTORY.md` - Append-only audit log of consolidation events.

## Read Order

Prefer these sources in order:

- Daily `.json` when you need structured fields such as `date`, `high_risk_knowledge_points`, `high_frequency_error_types`, `learning_status_summary`, and `tomorrow_study_suggestions`.
- Daily `.md` when you need a human-facing summary.
- Graph JSON files when you need relationships, ranking, or historical nodes.
- Weekly `.md` when you need the next-week learning plan.
- `HISTORY.md` only when you need an audit trail of what was archived.

## Graph Semantics

Knowledge graph:
- Nodes are knowledge points.
- Important fields include `time_points`, `risk`, `mastery`, `importance`, `last_seen`, and `display_size`.
- Relations include prerequisite, similar, contains, and related links.

Error graph:
- Nodes are error patterns.
- Important fields include `error_count`, `severity`, `repeated`, `last_seen`, and `display_size`.
- Relations include corresponding knowledge point, similar error, and correction suggestions.

## Dynamic Adjustment Rules

- Low-frequency, low-risk, long-inactive nodes can be archived.
- Similar concepts should be merged upstream before adding too many nodes.
- Example items only keep recent representative samples; older examples are dropped automatically.
- Frontend views should size nodes by importance or severity, not raw node count.

## Update Policy

- Do not manually edit `MEMORY.md` unless you are intentionally adjusting the compatibility snapshot.
- Prefer updating the structured daily JSON or graph JSON when building new features.
- If both Markdown and JSON exist for the same day, trust the JSON as the machine-readable source.

## Auto-consolidation

Archived conversations are automatically summarized into daily memory, graph snapshots, and weekly plans when enough recent data exists. You usually do not need to manage this manually.
