"""Tests for corpus health checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import List

import pytest

from exeuresis.config import CorpusConfig


def _write_valid_tei(path: Path, body: str = "Sample text") -> None:
    path.write_text(
        """<?xml version='1.0' encoding='UTF-8'?>
<TEI xmlns='http://www.tei-c.org/ns/1.0'>
  <text>
    <body>
      <p>{body}</p>
    </body>
  </text>
</TEI>
""".format(body=body),
        encoding="utf-8",
    )


def _write_invalid_tei(path: Path) -> None:
    path.write_text("<TEI xmlns='http://www.tei-c.org/ns/1.0'></TEI>", encoding="utf-8")


@dataclass
class DummyAuthor:
    tlg_id: str


@dataclass
class DummyWork:
    tlg_id: str
    work_id: str
    file_path: Path


class DummyCatalog:
    """Simple catalog stub backed by explicit works list."""

    def __init__(self, data_dir: Path, works: List[DummyWork] | None = None):
        self.data_dir = Path(data_dir)
        self._works = works or []

    def list_authors(self) -> List[DummyAuthor]:
        authors = {work.tlg_id for work in self._works}
        return [DummyAuthor(tlg_id=a) for a in sorted(authors)]

    def list_works(self, tlg_id: str) -> List[DummyWork]:
        return [work for work in self._works if work.tlg_id == tlg_id]


@pytest.fixture
def sample_corpus(tmp_path, monkeypatch):
    """Create a temporary corpus with nine valid works."""

    works = []
    for idx in range(9):
        author_id = "tlg{:04d}".format(idx // 3 + 1)
        work_id = f"{author_id}.tlg{idx:03d}"
        file_path = tmp_path / f"work_{idx}.xml"
        _write_valid_tei(file_path, body=f"Work {idx}")
        works.append(DummyWork(tlg_id=author_id, work_id=work_id, file_path=file_path))

    def _catalog_factory(*, data_dir=None, corpus_name=None):
        return DummyCatalog(data_dir, works=works)

    monkeypatch.setattr("exeuresis.corpus_health.PerseusCatalog", _catalog_factory)

    return CorpusConfig(name="test", path=tmp_path, description="Test corpus")


def test_quick_mode_defaults_to_five_samples(sample_corpus):
    from exeuresis.corpus_health import CorpusHealthStatus, check_corpus

    result = check_corpus(sample_corpus)

    assert result.status is CorpusHealthStatus.OK
    assert result.total_files == 9
    assert result.checked_files == 5  # default sample size
    assert result.failed_files == []


def test_quick_mode_respects_sample_percent(sample_corpus):
    from exeuresis.corpus_health import check_corpus

    result = check_corpus(sample_corpus, mode="quick", sample_percent=100)
    assert result.checked_files == result.total_files


def test_quick_mode_seed_is_deterministic(sample_corpus):
    from exeuresis.corpus_health import check_corpus

    result_one = check_corpus(sample_corpus, mode="quick", seed=42)
    result_two = check_corpus(sample_corpus, mode="quick", seed=42)

    assert result_one.sampled_paths == result_two.sampled_paths


def test_full_mode_checks_every_file(sample_corpus):
    from exeuresis.corpus_health import CorpusHealthStatus, check_corpus

    result = check_corpus(sample_corpus, mode="full")

    assert result.status is CorpusHealthStatus.OK
    assert result.checked_files == result.total_files == 9


def test_parse_failures_raise_warning(tmp_path, monkeypatch):
    from exeuresis.corpus_health import CorpusHealthStatus, check_corpus

    good = tmp_path / "good.xml"
    bad = tmp_path / "bad.xml"
    _write_valid_tei(good, body="good")
    _write_invalid_tei(bad)

    works = [
        DummyWork("tlg0001", "tlg0001.tlg001", good),
        DummyWork("tlg0001", "tlg0001.tlg002", bad),
    ]

    def _catalog_factory(*, data_dir=None, corpus_name=None):
        return DummyCatalog(data_dir, works=works)

    monkeypatch.setattr("exeuresis.corpus_health.PerseusCatalog", _catalog_factory)

    corpus = CorpusConfig(name="test", path=tmp_path)

    result = check_corpus(corpus, mode="full")

    assert result.status is CorpusHealthStatus.WARNING
    assert len(result.failed_files) == 1
    assert result.failed_files[0].path == bad


def test_missing_corpus_path_is_error(tmp_path):
    from exeuresis.corpus_health import CorpusHealthStatus, check_corpus

    missing = tmp_path / "missing"
    corpus = CorpusConfig(name="missing", path=missing)

    result = check_corpus(corpus)

    assert result.status is CorpusHealthStatus.ERROR
    assert "not found" in result.message.lower()
