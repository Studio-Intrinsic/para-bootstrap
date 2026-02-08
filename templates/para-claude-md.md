# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Personal knowledge management system using the **PARA method**. Not a software codebase — a collection of markdown notes organized by lifecycle stage.

## Filesystem Structure

All knowledge lives in `{{PARA_ROOT}}`:

- **Projects/** — Active goals with deadlines
- **Areas/** — Ongoing responsibilities (health, finances, etc.)
- **Resources/** — Evergreen/reference notes
- **Archives/** — Completed or inactive items moved from the other three folders
- **memory/**
  - `daily/YYYY-MM-DD.md` — Daily summaries, decisions, reflections
  - `facts/` — Atomic facts as individual `.md` files

## Atomic Fact Template (Always Use Exactly This)

```markdown
# Fact: [Clear, unique title e.g. Pricing Decision for Side Project]

**Created**: YYYY-MM-DD
**Last Accessed**:
**Superseded By**: (link to newer fact file if updated)
**Tags**: #pricing #product #idea

**Content**: [precise statement or knowledge]

**Source**: From conversation on [date] or user input [details]
```

## Daily Log Rules

- Append to `memory/daily/$(date +%Y-%m-%d).md`
- Sections: `## Summary`, `## Key Decisions`, `## New Facts Extracted`, `## Reflections`
- Create file if missing

## qmd Helpers

- To search: run shell command like `qmd query "your search"` or `qmd search keyword`
- When I ask to recall/search PARA: prefer `qmd query` first, then fall back to reading files directly
- Example: if I say "what do we know about pricing", run `qmd query "pricing ideas"` and summarize results

## Behavior

- When I say "update memory", "remember this", "extract facts", "daily reflection": extract 3-10 atomic facts -> write files -> append daily log
- When I say "recall [topic]", "search PARA for [thing]": search relevant files, summarize, quote sources
- Never delete/overwrite without asking me first
- Be concise, structured, use Markdown
