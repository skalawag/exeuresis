## exeuresis Roadmap

This document outlines likely and useful future directions for `exeuresis`. Items are grouped into milestones; within a milestone, bullets are not strictly ordered.

---

### Milestone 1 – Diagnostics & Data Formats (Near‑Term, High ROI)

- **Corpus health checks**
  - Extend `list-corpora` with a `--details` (or `--verbose`) option to show name, path, description, and a simple health status (OK / warning / error).
  - Add a `check-corpus` subcommand, e.g. `exeuresis.cli check-corpus [--corpus NAME] [--quick | --full]`.
    - Quick mode: verify corpus directory exists and is readable; sample a small number of TEI files and ensure they parse.
    - Full mode: walk a curated subset of works (not the whole tree), count parse failures, and highlight missing or malformed metadata.

- **Structured output formats (JSON/JSONL)**
  - Add a `--format` flag for `extract` (and anthology extraction): `--format {text,json,jsonl}`.
    - `text`: current default behavior.
    - `json`: a JSON array of segments.
    - `jsonl`: one JSON object per segment per line.
  - Reuse the existing segment schema; ensure it is serializable and stable enough for downstream tools (NLP, notebooks, pipelines).

- **Richer catalog exploration**
  - Extend `list-authors` and `list-works` with:
    - `--columns` to select which fields to show.
    - `--filter field=value` for simple exact / contains filtering.
    - `--limit` and `--offset` for pagination over large result sets.
  - Keep default behavior backwards compatible for existing scripts.

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
