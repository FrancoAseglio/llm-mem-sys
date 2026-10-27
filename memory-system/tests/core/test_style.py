import pytest

from memory_system.core import style


@pytest.fixture(autouse=True)
def reset():
    style.set_enabled(None)
    yield
    style.set_enabled(None)


def test_plain_when_disabled():
    style.set_enabled(False)
    assert style.paint("hello", "red", "bold") == "hello"
    assert style.colour_marks("✓/✗") == "✓/✗"
    assert style.memory_line("Earlier: Job: nurse") == "Earlier: Job: nurse"


def test_codes_when_enabled():
    style.set_enabled(True)
    assert style.paint("hi", "red") == "\033[31mhi\033[0m"
    assert style.paint("hi", "bold", "cyan") == "\033[1;36mhi\033[0m"
    assert style.paint("hi") == "hi"
    assert style.paint("", "red") == ""


def test_marks_coloured_after_padding():
    style.set_enabled(True)
    cell = f"{'✓/✗':>10}"
    out = style.colour_marks(cell)
    assert "\033[32m✓\033[0m" in out and "\033[31m✗\033[0m" in out
    assert out.startswith("      ")  # padding untouched


def test_memory_line_kinds():
    style.set_enabled(True)
    assert "\033[35m" in style.memory_line("Earlier: City: Turin (until 2026-01-01)")
    assert "\033[34m" in style.memory_line("Note from 2026-01-01: moved")
    assert (
        style.memory_line("City: Milan (since 2026-01-01)")
        == "City: Milan (since 2026-01-01)"
    )


def test_env_switches(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert style.enabled() is False
    monkeypatch.delenv("NO_COLOR")
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert style.enabled() is True


def test_status_prints_plain_line_when_not_a_terminal(capsys):
    style.set_enabled(False)
    style.status("working")
    style.status_clear()
    assert capsys.readouterr().out == "working\n"
