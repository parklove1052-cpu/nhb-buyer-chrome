from datetime import datetime

import salesintel as s


def row(key, found_at="2026-09-20T10:00:00", name="A"):
    return {"key": key, "found_at": found_at, "query": "q", "name": name, "category": "", "address": "",
            "phone": "", "website": "", "rating": "", "maps_url": ""}


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


if __name__ == "__main__":
    test_place_key(); test_merge_skips_duplicates(); test_report_counts_last_7_days()
    print("OK")
