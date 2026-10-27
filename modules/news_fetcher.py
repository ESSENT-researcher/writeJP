"""
news_fetcher.py
난이도에 맞는 소스의 RSS에서 기사 링크를 모으고 본문 텍스트를 추출한다.
"""

import re
import time
from datetime import datetime, timedelta, timezone
from itertools import zip_longest
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────
# 소스 정의
# ─────────────────────────────────────────
YAHOO_RSS = {
    "world":         "https://news.yahoo.co.jp/rss/topics/world.xml",
    "business":      "https://news.yahoo.co.jp/rss/topics/business.xml",
    "domestic":      "https://news.yahoo.co.jp/rss/topics/domestic.xml",
    "science":       "https://news.yahoo.co.jp/rss/topics/science.xml",
}
ASAHI_RSS = "https://www.asahi.com/rss/asahi/newsheadlines.rdf"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
TIMEOUT        = 10
REQUEST_DELAY  = 1.0   # 서버 부하 방지 (초)
MIN_TEXT_CHARS = 100
MIN_CANDIDATES = 3     # 새 기사 후보가 이보다 적으면 시간 범위를 넓혀 다시 찾는다
WIDEN_FACTOR   = 3

# 불필요한 태그
NOISE_TAGS = ["script", "style", "nav", "footer", "header", "aside",
              "form", "button", "noscript"]


# ─────────────────────────────────────────
# HTTP / RSS
# ─────────────────────────────────────────
def _get(url: str, attempts: int = 2) -> requests.Response:
    """GET 요청. 타임아웃/연결 오류는 한 번 더 시도한다."""
    for attempt in range(attempts):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp
        except (requests.Timeout, requests.ConnectionError):
            if attempt == attempts - 1:
                raise
            time.sleep(REQUEST_DELAY)


def _parse_rss(url: str) -> list[dict]:
    """RSS를 requests로 받아 feedparser로 파싱한다. 실패하면 빈 목록."""
    try:
        feed = feedparser.parse(_get(url).content)
    except Exception as e:
        print(f"⚠️  RSS 실패: {url} — {e}")
        return []

    items = []
    for entry in feed.entries:
        link = entry.get("link", "")
        # 사이트 루트·토픽 목록 링크는 기사가 아니다
        if link and re.search(r"/(pickup/\d+|articles/)", link):
            items.append({
                "title":     entry.get("title", ""),
                "url":       link,
                "published": _published(entry),
            })
    return items


def _published(entry) -> datetime | None:
    """RSS 항목의 발행 시각(UTC). 없으면 None."""
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    return datetime(*parsed[:6], tzinfo=timezone.utc) if parsed else None


def filter_recent(items: list[dict], max_age_hours: float, now: datetime | None = None) -> list[dict]:
    """
    발행 시각이 max_age_hours 이내인 기사만 남기고 최신순으로 정렬한다.
    발행 시각을 알 수 없는 기사는 최신인지 확인할 수 없으므로 제외한다.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=max_age_hours)
    recent = [i for i in items if i.get("published") and cutoff <= i["published"] <= now + timedelta(hours=1)]
    undated = sum(1 for i in items if not i.get("published"))
    if undated:
        print(f"⚠️  발행 시각이 없는 기사 {undated}개 제외")
    return sorted(recent, key=lambda i: i["published"], reverse=True)


# ─────────────────────────────────────────
# 본문 추출
# ─────────────────────────────────────────
def _soup(url: str) -> BeautifulSoup:
    soup = BeautifulSoup(_get(url).content, "html.parser")
    for tag in soup(NOISE_TAGS):
        tag.decompose()
    return soup


def _paragraph_text(soup: BeautifulSoup) -> str:
    paragraphs = (p.get_text(strip=True) for p in soup.find_all("p"))
    return "\n".join(p for p in paragraphs if p)


def extract_article(url: str) -> tuple[str, str]:
    """
    기사 URL에서 (본문 텍스트, 최종 기사 URL)을 추출한다. 실패하면 ("", url).

    Yahoo RSS 링크는 /pickup/ 요약 페이지라서, 그 안의 /articles/ 링크를 한 번 따라간다.
    """
    try:
        soup = _soup(url)

        if "news.yahoo.co.jp/pickup/" in url:
            link = soup.find("a", href=re.compile(r"news\.yahoo\.co\.jp/articles/[0-9a-f]+$"))
            if not link:
                return "", url
            url = urljoin(url, link["href"])
            soup = _soup(url)

        if "news.yahoo.co.jp/articles/" in url:
            body = soup.find("div", class_=re.compile(r"article_body"))
            if body:
                return body.get_text(separator="\n", strip=True), url

        return _paragraph_text(soup), url

    except Exception as e:
        print(f"⚠️  본문 추출 실패: {url} — {e}")
        return "", url


# ─────────────────────────────────────────
# 소스별 기사 목록
# ─────────────────────────────────────────
def _interleave(lists: list[list[dict]]) -> list[dict]:
    """분야별 목록을 번갈아 섞는다 (한 분야만 몰리지 않도록)."""
    merged = []
    for group in zip_longest(*lists):
        merged.extend(item for item in group if item)
    return merged


def list_candidates(difficulty: str, categories: list[str], max_age_hours: float = 24) -> list[dict]:
    """
    난이도에 맞는 소스에서 기사 후보 목록을 만든다.
    advanced는 朝日新聞, 그 외(beginner/intermediate)는 Yahoo! 분야별 RSS.
    발행 후 max_age_hours 이내의 기사만, 최신순으로 반환한다.
    """
    if difficulty == "advanced":
        source = "朝日新聞"
        items = filter_recent(_parse_rss(ASAHI_RSS), max_age_hours)
        return [{**i, "source": source} for i in items]

    per_category = []
    for category in categories:
        rss_url = YAHOO_RSS.get(category)
        if not rss_url:
            print(f"⚠️  알 수 없는 카테고리: {category}")
            continue
        source = f"Yahoo!ニュース ({category})"
        items = filter_recent(_parse_rss(rss_url), max_age_hours)
        per_category.append([{**i, "source": source} for i in items])
    return _interleave(per_category)


# ─────────────────────────────────────────
# 공개 인터페이스
# ─────────────────────────────────────────
def fetch_articles(
    difficulty: str,
    categories: list[str],
    sent: set[str],
    max_articles: int = 6,
    max_age_hours: float = 24,
) -> list[dict]:
    """
    아직 보내지 않은 기사의 본문까지 가져온다.

    Args:
        sent: 이미 전송한 기사 URL 집합
        max_articles: 본문 추출에 성공한 기사를 이 개수까지만 모은다
        max_age_hours: 발행 후 이 시간 이내의 기사만 쓴다

    Returns:
        [{"title", "url"(RSS 링크, 중복 판별 키), "link"(표시용 최종 URL),
          "source", "text"}, ...]
    """
    print(f"📡 뉴스 수집 시작 (난이도: {difficulty}, 분야: {categories}, 최근 {max_age_hours:g}시간)")

    def unsent(hours: float) -> list[dict]:
        return [c for c in list_candidates(difficulty, categories, hours) if c["url"] not in sent]

    candidates = unsent(max_age_hours)
    if len(candidates) < MIN_CANDIDATES:
        wider = max_age_hours * WIDEN_FACTOR
        print(f"ℹ️  최근 {max_age_hours:g}시간 기사가 {len(candidates)}개뿐이라 {wider:g}시간으로 넓혀 다시 찾습니다")
        candidates = unsent(wider)
    if not candidates:
        print("⚠️  조건에 맞는 새 기사가 없습니다.")
        return []

    result = []
    for article in candidates:
        if len(result) >= max_articles:
            break
        print(f"  📄 본문 추출 중: {article['title'][:30]}")
        text, final_url = extract_article(article["url"])
        time.sleep(REQUEST_DELAY)
        if len(text) < MIN_TEXT_CHARS:
            print("  ⏭️  본문이 너무 짧아 건너뜀")
            continue
        result.append({**article, "link": final_url, "text": text})

    print(f"✅ {len(result)}개 기사 수집 완료")
    return result
