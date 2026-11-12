from evally.app.retrieval import DOCS_DIR, Retriever


def r():
    return Retriever.from_dir(DOCS_DIR)


def test_returns_question_finds_both_return_docs():
    hits = r().search("how many days do I have to return a book", k=3)
    assert {h.name for h in hits[:2]} == {"returns.md", "returns-2023.md"}


def test_shipping_question_in_top_two():
    # international-shipping.md also mentions express (to say it isn't offered),
    # so it can outrank shipping.md. The app sends the top 3, so both reach the model.
    assert "shipping.md" in [h.name for h in r().search("how much is express shipping")[:2]]


def test_price_match_question_top_hit():
    assert r().search("will you price match amazon")[0].name == "price-match.md"


def test_empty_query_returns_empty():
    assert r().search("   ") == []
