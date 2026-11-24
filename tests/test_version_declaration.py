"""The version's declaration as the upload reads it (contract v25): printed
from the plugin's root, as `meridian-declaration` prints it in the built
image, it carries the interface -- its pages and the tools their routes
make -- and each section of docs/ by its digest and size; and the texts the
upload sends beside it are the files, byte for byte. A version registers
exactly this, so the port is fixed, never read from the environment.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from meridian.declaration import main

from fred import declaration as version

ROOT = Path(__file__).resolve().parents[1]
NAMED = "fred.declaration:DECLARATION"
SECTIONS = ["overview", "setup", "troubleshooting", "terms", "pages"]


def printed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], *flags: str
) -> object:
    monkeypatch.chdir(ROOT)
    assert main([*flags, NAMED]) == 0
    return json.loads(capsys.readouterr().out)


def test_the_declaration_carries_its_pages_tools_and_documentation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    declared = printed(monkeypatch, capsys)
    assert isinstance(declared, dict)
    assert [page["title"] for page in declared["interface"]["pages"]] == ["Connection", "Datasets"]
    assert declared["tools"], "the tools its typed routes make"
    sections = declared["documentation"]
    assert [section["name"] for section in sections] == SECTIONS
    for section in sections:
        held = (ROOT / "docs" / f"{section['name']}.md").read_bytes()
        assert section["digest"] == f"sha256:{hashlib.sha256(held).hexdigest()}"
        assert section["bytes"] == len(held)


def test_the_texts_uploaded_are_the_files(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    texts = printed(monkeypatch, capsys, "--documentation")
    assert texts == [
        {"section": name, "markdown": (ROOT / "docs" / f"{name}.md").read_text("utf-8")}
        for name in SECTIONS
    ]


def test_the_key_is_declared_a_required_secret(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The upload declares FRED's API key required and secret, so a deployment
    asks for it at setup and names it missing until it is set."""
    declared = printed(monkeypatch, capsys)
    assert isinstance(declared, dict)
    (key,) = [s for s in declared["settings"] if s["name"] == "fred_api_key"]
    assert key["required"] is True and key["secret"] is True


def test_the_port_is_fixed() -> None:
    interface = version.DECLARATION.interface
    assert interface is not None
    assert interface.port == version.PORT == 8000
