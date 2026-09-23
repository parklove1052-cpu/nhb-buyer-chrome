from datetime import datetime
from fnmatch import fnmatchcase
from unittest.mock import Mock

import salesintel as s


def row(key, found_at="2026-09-20T10:00:00", name="A"):
    return {"key": key, "found_at": found_at, "query": "q", "name": name, "category": "", "address": "",
            "phone": "", "website": "", "rating": "", "url": "", "source": "maps"}


def test_place_key():
    url = "https://www.google.com/maps/place/X/data=!4m7!3m6!1s0x38ae8b:0x1a2b!8m2"
    assert s.place_key(url, "X") == "0x38ae8b:0x1a2b"
    assert s.place_key("", " Foo  Bar ", "Tashkent") == "name:foo bar tashkent"


def test_merge_skips_duplicates():
    added = s.merge([row("a")], [row("a"), row("b"), row("b")])
    assert [r["key"] for r in added] == ["b"]


def test_report_counts_last_7_days():
    rows = [row("a", "2026-09-01T00:00:00", "Old"), row("b", "2026-09-20T00:00:00", "New")]
    body = s.build_report(rows, {"country": "Uzbekistan", "product": "P"}, now=datetime(2026, 9, 23))
    assert "전체 후보: 2곳 / 최근 7일 새 후보: 1곳" in body and "New" in body and "Old" not in body


def test_report_handles_bad_dates():
    rows = [row("bad", "bad-date"), row("empty", ""), row("null", None),
            row("aware", "2026-09-20T10:00:00+00:00", "Valid")]
    missing = row("missing")
    del missing["found_at"]
    rows.append(missing)
    body = s.build_report(rows, {"country": "U", "product": "P"}, now=datetime(2026, 9, 23))
    assert "전체 후보: 5곳 / 최근 7일 새 후보: 1곳" in body and "Valid" in body


def test_linkedin_login_returns_to_search():
    for landing in ("https://www.linkedin.com/feed/", "https://www.linkedin.com/feed",
                    "https://www.linkedin.com/search/results/companies/?keywords=test"):
        page = Mock()
        page.url = "https://www.linkedin.com/login"
        page.evaluate.return_value = []

        def wait_for_url(pattern, **kwargs):
            matches = fnmatchcase(landing, pattern) if isinstance(pattern, str) else pattern.search(landing)
            if not matches:
                raise TimeoutError("Login completed at a different URL")

        page.wait_for_url.side_effect = wait_for_url
        s.search_linkedin(page, "test", 2, False)
        assert page.goto.call_count == 2, landing
        page.wait_for_selector.assert_called_once()


if __name__ == "__main__":
    test_place_key(); test_merge_skips_duplicates(); test_report_counts_last_7_days()
    test_report_handles_bad_dates()
    test_linkedin_login_returns_to_search()
    print("OK")
