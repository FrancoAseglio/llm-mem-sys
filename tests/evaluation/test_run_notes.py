"""Which evaluation runs write episode notes and digests (evaluation/run.py)."""

from evaluation.run import writes_notes


def test_make_quick_writes_no_notes():
    # make quick: stored data, retrieval only, so no chat model at all
    assert not writes_notes(no_ingest=True, retrieval_only=True, summaries=True)


def test_every_other_run_writes_notes_as_before():
    assert writes_notes(
        no_ingest=False, retrieval_only=True, summaries=True
    )  # make set
    assert writes_notes(
        no_ingest=True, retrieval_only=False, summaries=True
    )  # make answers
    assert writes_notes(
        no_ingest=False, retrieval_only=False, summaries=True
    )  # make eval


def test_summaries_off_writes_none():
    assert not writes_notes(no_ingest=False, retrieval_only=False, summaries=False)
