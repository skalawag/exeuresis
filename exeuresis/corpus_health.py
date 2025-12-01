"""Corpus health checking utilities."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

from lxml import etree

from exeuresis.catalog import PerseusCatalog
from exeuresis.config import CorpusConfig
from exeuresis.parser import TEIParser


class CorpusHealthStatus(Enum):
    """Simple status indicator for corpus checks."""

    OK = "OK"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class FileCheckResult:
    """Outcome for a single TEI file."""

    author_id: str
    work_id: str
    path: Path
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class CorpusHealthResult:
    """Summary of a corpus health check."""

    name: str
    path: Path
    status: CorpusHealthStatus
    message: str
    mode: str
    sample_percent: Optional[float]
    seed: Optional[int]
    total_authors: int
    total_works: int
    total_files: int
    checked_files: int
    sampled_paths: List[Path] = field(default_factory=list)
    failed_files: List[FileCheckResult] = field(default_factory=list)
    metadata_issues: List[str] = field(default_factory=list)


def sample_files(
    files: List[FileCheckResult],
    *,
    default_count: int = 5,
    sample_percent: Optional[float] = None,
    seed: Optional[int] = None,
) -> List[FileCheckResult]:
    """Select a subset of files for sampling."""

    if not files:
        return []

    if sample_percent is not None:
        if sample_percent <= 0:
            raise ValueError("sample_percent must be positive")
        ratio = min(sample_percent, 100.0) / 100.0
        count = max(1, math.ceil(len(files) * ratio))
    else:
        count = min(default_count, len(files))

    if count >= len(files):
        return list(files)

    rng = random.Random(seed)
    return rng.sample(files, count)


def check_corpus(
    corpus_config: CorpusConfig,
    *,
    mode: str = "quick",
    sample_percent: Optional[float] = None,
    seed: Optional[int] = None,
    default_sample_size: int = 5,
) -> CorpusHealthResult:
    """Run diagnostics for a configured corpus."""

    path = corpus_config.path
    if not path.exists():
        return CorpusHealthResult(
            name=corpus_config.name,
            path=path,
            status=CorpusHealthStatus.ERROR,
            message=f"Corpus directory not found: {path}",
            mode=mode,
            sample_percent=sample_percent,
            seed=seed,
            total_authors=0,
            total_works=0,
            total_files=0,
            checked_files=0,
            sampled_paths=[],
            failed_files=[],
            metadata_issues=[],
        )

    try:
        catalog = PerseusCatalog(data_dir=path)
    except Exception as exc:  # pragma: no cover - defensive
        return CorpusHealthResult(
            name=corpus_config.name,
            path=path,
            status=CorpusHealthStatus.ERROR,
            message=f"Failed to load catalog: {exc}",
            mode=mode,
            sample_percent=sample_percent,
            seed=seed,
            total_authors=0,
            total_works=0,
            total_files=0,
            checked_files=0,
            sampled_paths=[],
            failed_files=[],
            metadata_issues=[],
        )

    metadata_issues: List[str] = []
    file_entries: List[FileCheckResult] = []

    authors = catalog.list_authors()
    total_authors = len(authors)
    total_works = 0

    for author in authors:
        works = catalog.list_works(author.tlg_id)
        total_works += len(works)
        for work in works:
            file_path = getattr(work, "file_path", None)
            work_id = getattr(work, "work_id", getattr(work, "tlg_id", "unknown"))
            if not file_path:
                metadata_issues.append(f"{author.tlg_id}/{work_id}: missing TEI file path")
                continue

            file_path = Path(file_path)
            if not file_path.exists():
                metadata_issues.append(f"{author.tlg_id}/{work_id}: TEI file not found ({file_path})")
                continue

            file_entries.append(
                FileCheckResult(
                    author_id=getattr(author, "tlg_id", ""),
                    work_id=work_id,
                    path=file_path,
                )
            )

    total_files = len(file_entries)

    if total_files == 0:
        return CorpusHealthResult(
            name=corpus_config.name,
            path=path,
            status=CorpusHealthStatus.ERROR,
            message="No TEI files found for corpus",
            mode=mode,
            sample_percent=sample_percent,
            seed=seed,
            total_authors=total_authors,
            total_works=total_works,
            total_files=0,
            checked_files=0,
            sampled_paths=[],
            failed_files=[],
            metadata_issues=metadata_issues,
        )

    selected: List[FileCheckResult]
    if mode == "full":
        selected = list(file_entries)
    elif mode == "quick":
        selected = sample_files(
            file_entries,
            default_count=default_sample_size,
            sample_percent=sample_percent,
            seed=seed,
        )
    else:
        raise ValueError("mode must be 'quick' or 'full'")

    failed_files: List[FileCheckResult] = []
    sampled_paths = [entry.path for entry in selected]

    for entry in selected:
        try:
            TEIParser(entry.path)
        except etree.XMLSyntaxError as exc:
            failed_files.append(
                FileCheckResult(
                    author_id=entry.author_id,
                    work_id=entry.work_id,
                    path=entry.path,
                    error=str(exc),
                )
            )
        except Exception as exc:  # pragma: no cover - TEI validation errors
            failed_files.append(
                FileCheckResult(
                    author_id=entry.author_id,
                    work_id=entry.work_id,
                    path=entry.path,
                    error=str(exc),
                )
            )

    checked_files = len(selected)

    status = CorpusHealthStatus.OK
    message = "All checks passed"

    if failed_files:
        if checked_files == len(failed_files):
            status = CorpusHealthStatus.ERROR
            message = f"All {checked_files} checks failed"
        else:
            status = CorpusHealthStatus.WARNING
            message = (
                f"{len(failed_files)} of {checked_files} sampled files failed to parse"
            )
    elif metadata_issues:
        status = CorpusHealthStatus.WARNING
        message = f"{len(metadata_issues)} metadata issues detected"

    return CorpusHealthResult(
        name=corpus_config.name,
        path=path,
        status=status,
        message=message,
        mode=mode,
        sample_percent=sample_percent,
        seed=seed,
        total_authors=total_authors,
        total_works=total_works,
        total_files=total_files,
        checked_files=checked_files,
        sampled_paths=sampled_paths,
        failed_files=failed_files,
        metadata_issues=metadata_issues,
    )
