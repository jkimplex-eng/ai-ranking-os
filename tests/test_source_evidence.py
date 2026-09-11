from product.source_evidence import source_evidence


def test_sources_are_separated_by_model_and_have_explicit_denominators():
    rows = [
        {
            "response_id": 1,
            "provider": "yandex",
            "model": "a",
            "query": "Q",
            "mentioned": True,
            "sources": ["example.org"],
            "source_urls": ["https://example.org/a"],
        },
        {
            "response_id": 2,
            "provider": "yandex",
            "model": "a",
            "query": "Q",
            "mentioned": False,
            "sources": [],
            "source_urls": [],
        },
        {
            "response_id": 3,
            "provider": "other",
            "model": "b",
            "query": "Q",
            "mentioned": False,
            "sources": ["example.org"],
            "source_urls": ["https://example.org/b"],
        },
    ]
    result = source_evidence({"query_matrix": rows, "sample": {"excluded_responses": 2}})
    assert result["successful_responses"] == 3
    assert result["excluded_responses"] == 2
    first = next(row for row in result["resources"] if row["provider"] == "yandex")
    other = next(row for row in result["resources"] if row["provider"] == "other")
    assert first["mentioned_with"] == first["with_source"] == 1
    assert first["mention_rate_without"] == 0
    assert other["mention_rate_without"] is None
    assert first["urls"] == ["https://example.org/a"]
    assert other["status"] == "INSUFFICIENT_COMPARISON"


def test_no_sources_does_not_invent_criteria():
    result = source_evidence({"query_matrix": [], "sample": {}})
    assert result["resources"] == []
    assert "не критерии" in result["limitation"]
