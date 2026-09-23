"""NHB 바이어 수집기: 크롬(Playwright)으로 구글 지도·링크드인을 검색해 data/leads.csv 에 모으고 주간 보고를 만든다.

사용법:  python salesintel.py collect | report | all
"""
import csv
import json
import random
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
LEADS = ROOT / "data" / "leads.csv"
FIELDS = ["key", "source", "found_at", "query", "name", "category", "address", "phone", "website", "rating", "url"]


def place_key(url, name, address=""):
    m = re.search(r"!1s(0x[0-9a-f]+:0x[0-9a-f]+)", url or "")
    return m.group(1) if m else "name:" + " ".join(f"{name} {address}".casefold().split())


def load_leads():
    if not LEADS.exists():
        return []
    with LEADS.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def merge(existing, found):
    """이미 있는 업체는 건너뛰고 새 업체만 돌려준다."""
    seen = {r["key"] for r in existing}
    added = []
    for r in found:
        if r["key"] not in seen:
            seen.add(r["key"])
            added.append(r)
    return added


def save_leads(rows):
    LEADS.parent.mkdir(exist_ok=True)
    # utf-8-sig: 엑셀에서 더블클릭해도 한글·키릴 문자가 안 깨진다
    with LEADS.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows)


def build_report(rows, config, now=None):
    now = now or datetime.now()
    start = now - timedelta(days=7)
    new = []
    for r in rows:
        try:
            found_at = datetime.fromisoformat(r["found_at"])
        except (KeyError, TypeError, ValueError):
            continue
        if found_at.tzinfo is not None:
            found_at = found_at.astimezone().replace(tzinfo=None)
        if found_at >= start:
            new.append(r)
    lines = [f"# {config['country']} 주간 바이어 보고 ({now:%Y-%m-%d})",
             f"캠페인 제품: {config['product']}",
             f"전체 후보: {len(rows)}곳 / 최근 7일 새 후보: {len(new)}곳", "", "## 새 후보"]
    lines += [f"- [{r.get('source', 'maps')}] {r['name']} | {r['category']} | {r['phone'] or '전화 없음'} | {r['website'] or '웹사이트 없음'}"
              for r in new] or ["- 없음"]
    lines += ["", "## 참고", "구글 지도·링크드인 검색 결과일 뿐 수입 실적이 아닙니다. 연락 전 수입 법인·취급 제품을 확인하세요."]
    return "\n".join(lines)


def text(page, selector, attr=None):
    el = page.locator(selector).first
    if not el.count():
        return ""
    return (el.get_attribute(attr) if attr else el.inner_text()) or ""


def search_maps(page, query, limit):
    page.goto(f"https://www.google.com/maps/search/{quote(query)}?hl=en", wait_until="domcontentloaded")
    try:
        page.wait_for_selector('div[role="feed"], h1', timeout=20000)
    except Exception:
        print(f"  [경고] 검색 결과가 안 떴습니다: {query}")
        return []
    links = {}
    feed = page.locator('div[role="feed"]')
    if feed.count():
        for _ in range(30):  # 목록을 내리며 limit 개가 찰 때까지
            for a in page.locator("a.hfpxzc").all():
                links.setdefault(a.get_attribute("href"), a.get_attribute("aria-label"))
            if len(links) >= limit or page.locator("text=You've reached the end of the list").count():
                break
            feed.evaluate("el => el.scrollBy(0, el.scrollHeight)")
            page.wait_for_timeout(1500)
    else:  # 결과가 1곳이면 바로 업체 페이지가 뜬다
        links[page.url] = text(page, "h1")

    found = []
    for url, name in list(links.items())[:limit]:
        page.goto(url, wait_until="domcontentloaded")
        try:
            page.wait_for_selector("h1", timeout=15000)
            page.wait_for_timeout(800)
        except Exception:
            continue
        name = text(page, "h1") or name or ""
        address = text(page, 'button[data-item-id="address"]', "aria-label").removeprefix("Address: ").strip()
        phone = text(page, 'button[data-item-id^="phone:tel:"]', "data-item-id").removeprefix("phone:tel:")
        found.append({
            "key": place_key(url, name, address), "source": "maps", "found_at": datetime.now().isoformat(timespec="seconds"),
            "query": query, "name": name.strip(), "category": text(page, "button.DkEaL").strip(),
            "address": address, "phone": phone, "website": text(page, 'a[data-item-id="authority"]', "href"),
            "rating": text(page, 'div.F7nice span[aria-hidden="true"]').strip(), "url": url,
        })
        print(f"  - {found[-1]['name']}")
    return found


LINKEDIN_JS = r"""() => {
  const out = {};
  for (const a of document.querySelectorAll('main a[href*="/company/"]')) {
    const m = a.href.match(/linkedin\.com\/company\/([^/?#]+)/);
    const name = (a.innerText || '').trim().split('\n')[0];
    if (!m || !name || out[m[1]]) continue;
    const li = a.closest('li');
    out[m[1]] = {slug: m[1], name, info: li ? li.innerText : ''};
  }
  return Object.values(out);
}"""


def search_linkedin(page, query, limit, headless):
    """링크드인 회사 검색 1페이지. 로그인은 사람이 열린 창에서 직접 한다(비밀번호를 코드에 넣지 않음)."""
    page.goto("https://www.linkedin.com/search/results/companies/?keywords=" + quote(query), wait_until="domcontentloaded")
    if "/search/results/" not in page.url:  # 로그인 화면으로 튕김
        if headless:
            print("  [경고] 링크드인 로그인 필요: config.json 의 headless 를 false 로 두고 한 번 로그인하세요")
            return []
        print("  링크드인 로그인이 필요합니다. 열린 크롬 창에서 로그인해 주세요 (5분 대기)")
        try:
            page.wait_for_url(re.compile(r"^https://(?:www\.)?linkedin\.com/(?:feed|search/results/companies)(?:[/?#]|$)"), timeout=300000)
        except Exception:
            print("  [경고] 로그인 대기 시간 초과")
            return []
        page.goto("https://www.linkedin.com/search/results/companies/?keywords=" + quote(query), wait_until="domcontentloaded")
    try:
        page.wait_for_selector('main a[href*="/company/"]', timeout=20000)
    except Exception:
        print(f"  [경고] 링크드인 결과가 안 떴습니다: {query}")
        return []
    page.wait_for_timeout(2000)
    found = []
    for it in page.evaluate(LINKEDIN_JS)[:limit]:
        info = [x.strip() for x in it["info"].splitlines() if x.strip() and x.strip() != it["name"]]
        found.append({
            "key": "li:" + it["slug"], "source": "linkedin", "found_at": datetime.now().isoformat(timespec="seconds"),
            "query": query, "name": it["name"], "category": " | ".join(info[:3]), "address": "", "phone": "",
            "website": "", "rating": "", "url": f"https://www.linkedin.com/company/{it['slug']}/",
        })
        print(f"  - {it['name']}")
    return found


def open_browser(p, headless):
    profile = str(ROOT / "profile")  # 로그인 상태가 여기 저장돼 다음 실행에도 유지된다
    opts = dict(headless=headless, locale="en-US", viewport={"width": 1280, "height": 900})
    try:
        return p.chromium.launch_persistent_context(profile, channel="chrome", **opts)  # 설치된 크롬
    except Exception:
        return p.chromium.launch_persistent_context(profile, **opts)  # 없으면 Playwright 크롬


def collect(config):
    from playwright.sync_api import sync_playwright
    rows = load_leads()
    with sync_playwright() as p:
        ctx = open_browser(p, config.get("headless", False))
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        total = 0
        jobs = [("maps", q) for q in config.get("queries", [])] + [("linkedin", q) for q in config.get("linkedin_queries", [])]
        for source, q in jobs:
            print(f"검색[{source}]: {q}")
            if source == "maps":
                found = search_maps(page, q, config.get("max_per_query", 20))
            else:
                found = search_linkedin(page, q, config.get("linkedin_max_per_query", 10), config.get("headless", False))
                page.wait_for_timeout(random.randint(5000, 10000))  # 링크드인은 천천히: 계정 제한 예방
            added = merge(rows, found)
            rows += added
            save_leads(rows)  # 검색어마다 저장: 중간에 꺼져도 모은 건 남는다
            total += len(added)
        ctx.close()
    print(f"새 후보 {total}곳 추가 (전체 {len(rows)}곳) -> {LEADS}")


def report(config):
    body = build_report(load_leads(), config)
    out = ROOT / "reports" / f"report_{datetime.now():%Y-%m-%d}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print(f"보고서 -> {out}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    if cmd in ("collect", "all"):
        collect(cfg)
    if cmd in ("report", "all"):
        report(cfg)
