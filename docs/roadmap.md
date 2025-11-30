## exeuresis Roadmap

This document outlines likely and useful future directions for `exeuresis`. Items are grouped into milestones; within a milestone, bullets are not strictly ordered.

---

### Completed Features

- ✅ **Corpus health checks** (Milestone 1)
  - Added `list-corpora --details` to show health status for each corpus
  - Implemented `check-corpus` subcommand with `--quick` and `--full` modes
  - Quick mode samples a percentage of files; full mode checks all files
  - Reports parse failures, metadata issues, and overall health status

- ✅ **Structured output formats (JSON/JSONL)** (Milestone 1)
  - Added `--format {text,json,jsonl}` flag for `extract` command
  - `text`: default behavior (backward compatible)
  - `json`: outputs JSON array with metadata wrapper (work_id, title, timestamp)
  - `jsonl`: outputs newline-delimited JSON (one segment per line)
  - Works with both single extraction and anthology modes
  - Segment schema: `{speaker, label, text, stephanus[], said_id, is_paragraph_start, book}`

- ✅ **Richer catalog exploration** (Milestone 1)
  - Added `--columns` flag to select which fields to display
  - Added `--filter` flag for exact (`=`) or contains (`~`) matching (repeatable for AND logic)
  - Added `--limit` and `--offset` for pagination
  - All flags work with both `list-authors` and `list-works` commands
  - Backward compatible: default behavior unchanged

---

### Milestone 1 – Diagnostics & Data Formats (Near‑Term, High ROI)

All items completed!

---

### Milestone 2 – Extensibility & Library Use (Medium Term)

- **Pluggable corpus layouts**
  - Allow each configured corpus to declare a `layout` in config (e.g. `perseus`, `simple-tei`).
  - Introduce a small `CorpusLayout` abstraction used by the catalog to resolve work IDs to paths and to iterate works.
  - Move the current Perseus-specific logic into a `PerseusLayout` implementation.
  - Provide at least one simple generic layout (e.g. glob over `**/*.xml`, work ID derived from filename).

- **Public Python API surface**
  - Add an `exeuresis.api` module exposing a minimal, stable API for programmatic use, for example:
    - `extract(work_id, *, style="A", corpus=None, ranges=None) -> list[Segment]`.
    - `search(query, *, corpus=None) -> list[SearchResult]`.
  - Implement these as thin wrappers around existing modules (catalog, work_resolver, extractor, formatter) without leaking internal details.
  - Add focused tests to pin down API behavior.

- **Streaming output mode**
  - Add a `--stream` flag for `extract` / anthology to emit text or JSONL incrementally instead of buffering all segments in memory.
  - Adjust formatter/CLI wiring so that at least text and JSONL formats can operate on iterators or generators of segments.

---

### Milestone 3 – Ergonomics & Advanced Extensibility (Longer Term)

- **CLI ergonomics and shell completion**
  - Provide a `completions` subcommand (e.g. `exeuresis.cli completions [bash|zsh|fish]`) that prints shell completion scripts.
  - Improve error messages to suggest helpful commands and flags, such as:
    - When a corpus is missing or misconfigured, suggest `list-corpora` and relevant configuration hints.
    - When a style is invalid, remind which styles are available and any constraints (for example, style `S` only for Plato).

- **Plugin / extension hooks**
  - Define small extension points for advanced users, such as:
    - Post-processing plugins that transform the list of extracted segments.
    - Custom output writers that can be selected from config.
  - Load plugins via simple import strings declared in configuration, keeping the core behavior unchanged when no plugins are configured.

---

This roadmap is intentionally high level and non-binding; individual items can be refined, re‑prioritized, or dropped as the project evolves.
