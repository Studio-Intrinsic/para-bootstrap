
### GLOBAL PARA MEMORY AUTOMATION

**Filesystem root**: always `{{PARA_ROOT}}`

**Atomic fact template** (use EXACTLY this format):

```
# Fact: [Clear, unique title]

**Created**: YYYY-MM-DD
**Last Accessed**:
**Superseded By**:
**Tags**: #tag1 #tag2

**Content**: [precise fact/decision/preference]

**Source**: From Claude Code session on [date] or user input
```

**Daily log**: append to `{{PARA_ROOT}}/memory/daily/YYYY-MM-DD.md` (create if missing)
Sections: `## Summary` · `## Decisions` · `## New Facts` · `## Reflections`

**Trigger phrases** — when user says any of these, extract 1-8 atomic facts + update daily log:
- "remember this", "extract facts", "update memory", "daily reflection"

**Recall** — when user says "recall [topic]" or "search PARA for [thing]":
- Prefer running `qmd query "..."` first, then fall back to reading files directly

**Safety**: never delete or overwrite files without explicit confirmation from the user.
