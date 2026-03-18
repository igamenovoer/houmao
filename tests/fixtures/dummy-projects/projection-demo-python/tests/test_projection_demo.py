from projection_demo import render_projection_summary, summarize_numbers


def test_summarize_numbers_returns_count_and_total() -> None:
    assert summarize_numbers([1, 2, 3]) == {
        "count": 3,
        "total": 6,
    }


def test_render_projection_summary_renders_compact_line() -> None:
    assert render_projection_summary("sample", [2, 4]) == "sample: count=2, total=6"
