import pytest

from app.services.chunking_service import PageText, chunk_pages, clean_text


def test_clean_text_dehyphenates_and_collapses():
    assert clean_text("secu-\nrity   policy\n\n\n\nnext") == "security policy\n\nnext"


def test_chunks_keep_page_numbers_and_size_bound():
    text = " ".join(f"Sentence number {i} about access control." for i in range(200))
    chunks = chunk_pages([PageText(1, text), PageText(2, "Short page two.")], 400, 60)
    assert {c.page for c in chunks} == {1, 2}
    assert all(len(c.text) <= 400 + 60 + 1 for c in chunks)
    assert chunks[-1].page == 2


def test_overlap_must_be_smaller_than_size():
    with pytest.raises(ValueError):
        chunk_pages([PageText(1, "x")], 100, 100)


def test_empty_pages_skipped():
    assert chunk_pages([PageText(1, "   \n ")], 400, 50) == []
