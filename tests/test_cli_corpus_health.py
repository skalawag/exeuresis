"""CLI tests for corpus health features."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from exeuresis.config import CorpusConfig
from exeuresis.corpus_health import CorpusHealthResult, CorpusHealthStatus, FileCheckResult


def _make_result(name="main", status=CorpusHealthStatus.OK):
    return CorpusHealthResult(
        name=name,
        path=Path("/tmp") / name,
        status=status,
        message="Healthy",
        mode="quick",
        sample_percent=None,
        seed=None,
        total_authors=2,
        total_works=4,
        total_files=4,
        checked_files=2,
        sampled_paths=[Path("/tmp") / f"{name}.xml"],
        failed_files=[],
        metadata_issues=[],
    )


def test_list_corpora_compact_output(monkeypatch, capsys):
    from exeuresis import cli

    corpora = {
        "main": CorpusConfig(name="main", path=Path("/tmp/main"), description="Primary"),
        "sandbox": CorpusConfig(name="sandbox", path=Path("/tmp/sandbox")),
    }

    monkeypatch.setattr("exeuresis.cli.get_corpora", lambda: corpora)
    monkeypatch.setattr("exeuresis.cli.get_default_corpus_name", lambda: "main")

    results = {
        "main": _make_result("main", CorpusHealthStatus.OK),
        "sandbox": _make_result("sandbox", CorpusHealthStatus.WARNING),
    }

    def fake_check(corpus_config, **kwargs):
        return results[corpus_config.name]

    monkeypatch.setattr("exeuresis.cli.check_corpus", fake_check)

    args = SimpleNamespace(details=False)
    cli.handle_list_corpora(args)

    output = capsys.readouterr().out
    assert "[OK]" in output
    assert "[WARNING]" in output
    assert "(default)" in output


def test_list_corpora_detailed_output(monkeypatch, capsys):
    from exeuresis import cli

    corpora = {
        "main": CorpusConfig(name="main", path=Path("/tmp/main"), description="Primary"),
    }

    monkeypatch.setattr("exeuresis.cli.get_corpora", lambda: corpora)
    monkeypatch.setattr("exeuresis.cli.get_default_corpus_name", lambda: "main")

    result = _make_result("main")
    monkeypatch.setattr("exeuresis.cli.check_corpus", lambda corpus_config, **_: result)

    args = SimpleNamespace(details=True)
    cli.handle_list_corpora(args)

    output = capsys.readouterr().out
    assert "Path:" in output
    assert "Authors:" in output
    assert "Works:" in output


def test_check_corpus_cli_invokes_health(monkeypatch, capsys):
    from exeuresis import cli

    corpora = {
        "main": CorpusConfig(name="main", path=Path("/tmp/main")),
    }

    monkeypatch.setattr("exeuresis.cli.get_corpora", lambda: corpora)
    monkeypatch.setattr("exeuresis.cli.get_default_corpus_name", lambda: "main")

    result = _make_result("main")
    called = {}

    def fake_check(corpus_config, **kwargs):
        called.update(kwargs)
        return result

    monkeypatch.setattr("exeuresis.cli.check_corpus", fake_check)

    args = SimpleNamespace(corpus=None, mode="full", sample_percent=None, seed=None)
    cli.handle_check_corpus(args)

    output = capsys.readouterr().out
    assert "Status: OK" in output
    assert called["mode"] == "full"


def test_check_corpus_cli_handles_missing_corpus(monkeypatch, capsys):
    from exeuresis import cli

    monkeypatch.setattr("exeuresis.cli.get_corpora", lambda: {})
    monkeypatch.setattr("exeuresis.cli.get_default_corpus_name", lambda: "main")

    args = SimpleNamespace(corpus="missing", mode="quick", sample_percent=None, seed=None)
    with pytest.raises(SystemExit):
        cli.handle_check_corpus(args)

    captured = capsys.readouterr()
    assert "corpus" in captured.err.lower()


def test_list_corpora_manual_paths(monkeypatch, capsys, tmp_path):
    from exeuresis import cli

    extra = tmp_path / "manual"
    extra.mkdir()

    monkeypatch.setattr("exeuresis.cli.get_corpora", lambda: {})
    monkeypatch.setattr("exeuresis.cli.get_default_corpus_name", lambda: "main")

    invoked_paths = []

    def fake_check(config, **kwargs):
        invoked_paths.append(config.path)
        return _make_result("manual")

    monkeypatch.setattr("exeuresis.cli.check_corpus", fake_check)

    args = SimpleNamespace(details=False, extra_corpora=[extra], corpus=None)
    cli.handle_list_corpora(args)

    assert invoked_paths == [extra]
    output = capsys.readouterr().out
    assert str(extra) in output


def test_check_corpus_falls_back_to_first_available(monkeypatch, capsys):
    from exeuresis import cli

    corpora = {
        "secondary": CorpusConfig(name="secondary", path=Path("/tmp/sec")),
    }
    monkeypatch.setattr("exeuresis.cli.get_corpora", lambda: corpora)
    monkeypatch.setattr("exeuresis.cli.get_default_corpus_name", lambda: "missing")

    result = _make_result("secondary")
    monkeypatch.setattr("exeuresis.cli.check_corpus", lambda config, **_: result)

    args = SimpleNamespace(corpus=None, mode="quick", sample_percent=None, seed=None)
    cli.handle_check_corpus(args)

    out = capsys.readouterr().out
    assert "secondary" in out


def test_check_corpus_accepts_path(monkeypatch, capsys, tmp_path):
    from exeuresis import cli

    target = tmp_path / "manual"
    target.mkdir()

    monkeypatch.setattr("exeuresis.cli.get_corpora", lambda: {})
    monkeypatch.setattr("exeuresis.cli.get_default_corpus_name", lambda: "default")

    captured_config = {}

    def fake_check(config, **kwargs):
        captured_config["path"] = config.path
        return _make_result("manual")

    monkeypatch.setattr("exeuresis.cli.check_corpus", fake_check)

    args = SimpleNamespace(corpus=str(target), mode="quick", sample_percent=None, seed=None)
    cli.handle_check_corpus(args)

    assert captured_config["path"] == target
