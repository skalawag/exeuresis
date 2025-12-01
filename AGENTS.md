# AGENT GUIDE

Goal: extract + format TEI XML via `exeuresis.cli`. Keep answers short, never touch `canonical-greekLit` (or other corpora) content.

## TL;DR commands

```bash
.venv/bin/python -m exeuresis.cli list-authors
.venv/bin/python -m exeuresis.cli list-works tlg0059
.venv/bin/python -m exeuresis.cli extract euthyphro --style A
.venv/bin/python -m exeuresis.cli extract tlg0059.tlg001 2a-3e --print
.venv/bin/python -m exeuresis.cli extract euthyphro --format json  # JSON output
.venv/bin/python -m exeuresis.cli extract euthyphro --format jsonl # JSONL output
.venv/bin/python -m pytest tests/ -v
```

## Architecture snapshot

XML → `parser` (TEI sanity) → `extractor` (segments w/ speaker, Stephanus) → `formatter` (styles A‑E,S) → file/stdout. `catalog` + `work_resolver` locate files/aliases, `range_filter` trims ranges, `anthology_*` handles multi-passages, `cli` wires flags, `exceptions` for user errors.

Segment schema (approx): `{speaker,label,text,stephanus[],said_id,is_paragraph_start,book}`.

## Key behaviors

- Styles: A full modern, B minimal punct, C no punct, D no punct/labels, E scriptio continua, S Stephanus layout (Plato only).
- Formats: `--format {text,json,jsonl}`. Text is default; JSON outputs array with metadata; JSONL outputs one segment per line.
- Multi-book: uppercase accented-stripped headers auto.
- Anthology: `--passages` per work, styles limited to A-D.
- Aliases: `.exeuresis/aliases.yaml` (project overrides home).
- Corpus path: configurable via `PERSEUS_CORPUS_PATH` env var, `.exeuresis/config.yaml` (project), or `~/.exeuresis/config.yaml` (user). Defaults to `./canonical-greekLit/data`.
- Multi-corpus: `corpora:` section in config with `default_corpus:`. Use `--corpus NAME` flag or `list-corpora` command.
- Logging: `--debug` for stack traces.

## Constraints / warnings

- **Do not** traverse entire `canonical-greekLit/data` (huge) unless instructed to do so. Access only specific paths.
- Never write to corpus dir; outputs go `./output/` unless `--print` or custom `-o`.
- Respect style validation (S only in authors that have Stephanus pagination). Use `InvalidStyleError` messaging.
- Book + section markers come from `<div subtype="book|section">` + `<milestone unit="section|stephpage">`.

## Typical workflow snippets

Search + extract alias:
```bash
.venv/bin/python -m exeuresis.cli search "Republic"
.venv/bin/python -m exeuresis.cli extract republic --style B --output out.txt
```

Range filter:
```bash
.venv/bin/python -m exeuresis.cli extract tlg0059.tlg001 2a-3e --print
```

Anthology:
```bash
.venv/bin/python -m exeuresis.cli extract euthyphro --passages 5a,7b tlg0059.tlg030 --passages 327a-328b -s A
```

Catalog exploration:
```bash
.venv/bin/python -m exeuresis.cli list-authors --filter name_en~Plat --limit 5
.venv/bin/python -m exeuresis.cli list-authors --columns tlg_id,name_en --limit 10
.venv/bin/python -m exeuresis.cli list-works --all --filter tlg_id=tlg0059 --columns work_id,title_en
.venv/bin/python -m exeuresis.cli list-works tlg0059 --filter title_en~Alc --limit 3
```

Testing / lint:
```bash
.venv/bin/python -m pytest tests/ -v
.venv/bin/python -m black exeuresis tests
.venv/bin/python -m ruff check exeuresis tests
```

## Notes for agents

- Prefer incremental TEI reads (use `Read` w/ offsets) to save tokens.
- Mention output style limits + alias behavior succinctly when relevant.
- When editing code, follow existing style; minimal comments.
- For doc replies, keep sentences short; token thrift beats polish.

## Feature Development 

- Use TDD workflow.
- Features are developed on git worktrees in .worktrees.
- Ask to merge worktrees to main, ask for permission to commit.
