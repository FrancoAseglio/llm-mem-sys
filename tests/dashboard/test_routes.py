"""The results pages through FastAPI's test client.

Needs the optional dashboard group (fastapi); skipped when it is not installed, as in CI.
"""

from datetime import UTC, datetime

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from dashboard.app import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_home_explains_the_dashboard(client):
    page = client.get("/")
    assert page.status_code == 200
    assert "Behind the totals" in page.text
    assert "/results?run=O_full&amp;mode=baseline&amp;mode=hybrid" in page.text
    assert "57 questions" in page.text


def test_every_starting_point_opens_a_non_empty_list(client):
    from dashboard.routes import home

    points = home.starting_points()
    assert len(points) == len(home.STARTING_POINTS)
    for p in points:
        assert p["count"] > 0
        assert client.get(p["href"]).status_code == 200


def test_list_shows_the_default_run(client):
    page = client.get("/results")
    assert page.status_code == 200
    assert "57</b> questions" in page.text
    assert "Which city do I live in now?" in page.text
    assert 'name="set"' not in page.text  # one set only: no set menu


def test_list_filters_by_type_and_keeps_filters_in_links(client):
    page = client.get("/results", params={"qtype": "past"})
    assert (
        "Showing 7 of 57 questions of run N_full (set N): value before a change."
        in (page.text)
    )
    assert "/results/N_full/1?qtype=past" in page.text


def test_mode_boxes_hide_columns_and_stay_in_links(client):
    page = client.get("/results", params={"mode": ["baseline", "hybrid"]})
    assert "57</b> questions" in page.text  # the questions do not change
    assert 'data-mode="smart" title="smart (facts only)" hidden' in page.text
    assert 'data-mode="hybrid" title="hybrid (final design)" >' in page.text
    assert 'value="smart" >' in page.text and 'value="hybrid" checked>' in page.text
    assert "/results/N_full/0?mode=baseline&amp;mode=hybrid" in page.text


def test_short_runs_get_a_set_menu_and_no_type_menu(client):
    page = client.get("/results", params={"run": "A_to_J_change_rule_1b"})
    assert 'name="set"' in page.text
    assert 'name="qtype"' not in page.text


def test_unknown_filters_fall_back(client):
    page = client.get("/results", params={"run": "nope", "set": "Z", "mode": "?"})
    assert page.status_code == 200
    assert "57</b> questions" in page.text


def test_question_shows_every_mode_side_by_side(client):
    page = client.get("/results/N_full/3")
    assert page.status_code == 200
    assert "Where do I work now?" in page.text
    for mode in ("baseline", "smart", "hybrid", "full"):
        assert f'class="card mode-{mode}"' in page.text
    assert "Works at: Clinica Albereda" in page.text
    assert "(95 messages), not listed" in page.text


def test_question_pager_follows_the_filtered_list(client):
    page = client.get("/results/N_full/1", params={"qtype": "past"})
    assert "(1 of 7)" in page.text
    assert 'id="next" href="/results/N_full/2?qtype=past"' in page.text
    assert 'id="prev"' not in page.text


def test_question_hides_the_unticked_modes(client):
    page = client.get("/results/N_full/3", params={"mode": ["hybrid"]})
    assert 'class="card mode-hybrid" data-mode="hybrid" >' in page.text
    assert 'class="card mode-smart" data-mode="smart" hidden' in page.text
    assert (
        "/results?run=N_full&amp;mode=hybrid" in page.text
    )  # back to the same columns


def test_unknown_question_is_404(client):
    assert client.get("/results/N_full/999").status_code == 404
    assert client.get("/results/nope/0").status_code == 404


# ---- Inspector: the memory functions are replaced, so no database or model is needed ----


@pytest.fixture
def fake_memory(monkeypatch):
    from dashboard import data, memory

    when = datetime(2026, 1, 1, tzinfo=UTC)
    bergen = memory.Fact("user", "lives_in", "Bergen", "active", when, None, 0.8)
    oslo = memory.Fact("user", "lives_in", "Oslo", "superseded", when, when, 0.8)
    monkeypatch.setattr(
        memory,
        "status",
        lambda: [
            memory.Check("Postgres", True, "connected, 1 stored users"),
            memory.Check("Ollama", True, "running, llama3.1:8b and nomic-embed-text"),
        ],
    )
    monkeypatch.setattr(memory, "list_users", lambda: [memory.User("lena", 6, 1)])
    monkeypatch.setattr(
        memory,
        "user_memory",
        lambda user: memory.UserMemory(
            user, 6, 0, [bergen], [oslo], ["Lives in, oldest first: Oslo -> Bergen"]
        ),
    )
    line = '[2025-09-01] "I moved to Bergen!"'
    monkeypatch.setattr(
        memory,
        "prompt",
        lambda mode, user, q: memory.ModeMemory(
            mode, 1, [data.Line(line, "message")], f"system prompt for {mode}"
        ),
    )
    monkeypatch.setattr(memory, "answer", lambda mode, user, q: (f"{mode} says", 1.25))


def test_inspector_lists_users(client, fake_memory):
    page = client.get("/inspector")
    assert page.status_code == 200
    assert "lena (6 messages, 1 facts)" in page.text
    assert "Choose a user" in page.text


def test_inspector_shows_a_users_facts(client, fake_memory):
    page = client.get("/inspector", params={"user": "lena"})
    assert "Bergen" in page.text and "Oslo" in page.text
    assert "Lives in, oldest first: Oslo -&gt; Bergen" in page.text
    assert 'class="card' not in page.text  # no question yet


def test_inspector_shows_the_chosen_modes_prompts(client, fake_memory):
    params = {"user": "lena", "q": "Where do I live?", "mode": ["smart", "hybrid"]}
    page = client.get("/inspector", params=params)
    assert 'class="card mode-smart"' in page.text
    assert 'class="card mode-hybrid"' in page.text
    assert 'class="card mode-baseline"' not in page.text
    assert "system prompt for hybrid" in page.text
    assert (
        "/inspector/answer?user=lena&amp;q=Where+do+I+live%3F&amp;mode=smart"
        in page.text
    )


def test_inspector_answer_fragment(client, fake_memory):
    params = {"user": "lena", "q": "Where do I live?", "mode": "hybrid"}
    fragment = client.get("/inspector/answer", params=params)
    assert "hybrid says" in fragment.text
    assert "1.2 s" in fragment.text
    assert "<html" not in fragment.text


def test_inspector_reports_an_unknown_user(client, fake_memory):
    page = client.get("/inspector", params={"user": "nobody"})
    assert "No stored user called" in page.text


def test_inspector_shows_the_services(client, fake_memory):
    page = client.get("/inspector")
    assert "Postgres" in page.text and "running, llama3.1:8b" in page.text


def test_inspector_explains_a_missing_database(client, monkeypatch):
    from dashboard import memory

    monkeypatch.setattr(
        memory,
        "status",
        lambda: [
            memory.Check("Postgres", False, "Postgres is not reachable"),
            memory.Check("Ollama", True, "running"),
        ],
    )
    page = client.get("/inspector")
    assert page.status_code == 200
    assert "Postgres is not reachable" in page.text
    assert 'name="user"' not in page.text  # no users to choose from


def test_inspector_without_ollama_shows_memory_but_cannot_ask(
    client, fake_memory, monkeypatch
):
    from dashboard import memory

    message = "not running: start it with `brew services start ollama`"
    monkeypatch.setattr(
        memory,
        "status",
        lambda: [
            memory.Check("Postgres", True, "connected"),
            memory.Check("Ollama", False, message),
        ],
    )
    page = client.get("/inspector", params={"user": "lena", "q": "Where do I live?"})
    assert "<code>brew services start ollama</code>" in page.text
    assert "Bergen" in page.text  # the facts need only Postgres
    assert 'class="card' not in page.text  # no prompts without the embedding model
    assert "Questions need Ollama" in page.text


def test_every_page_has_the_footer(client, fake_memory):
    for url in ("/", "/results", "/results/N_full/0", "/inspector"):
        page = client.get(url)
        assert 'class="site-footer"' in page.text
        assert "brew services start ollama" in page.text
