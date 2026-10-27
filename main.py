"""
main.py
writeJP — 일본어 필사 봇 진입점.

    python3 main.py             # 수집 → 선별 → 단어 분석 → Discord 전송 → 기록 저장
    python3 main.py --dry-run   # 전송/기록 저장 없이 결과만 출력
"""

import argparse
import os
import sys

from dotenv import load_dotenv

from modules.config          import load_config
from modules.dict_lookup     import load_vocab_db
from modules.discord_sender  import send_to_discord
from modules.news_fetcher    import fetch_articles
from modules.sentence_picker import pick_sentences
from modules.state           import load_sent_articles, save_sent_articles
from modules.vocab_analyzer  import analyze_vocab


def print_preview(sentences: list[str], sources: list[dict], vocab_list: list[dict]) -> None:
    print("\n📰 출처")
    for s in sources:
        print(f"  - [{s['source']}] {s['title']}\n    {s['url']}")
    print(f"\n📝 필사 문장 ({len(sentences)}개)")
    for i, s in enumerate(sentences, 1):
        print(f"  {i:02d}. {s}")
    print(f"\n📚 단어장 ({len(vocab_list)}개)")
    for v in vocab_list:
        print(f"  [{v['level']}] {v['word']}（{v['reading']}）— {v['meaning']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="writeJP 일본어 필사 봇")
    parser.add_argument("--dry-run", action="store_true",
                        help="Discord 전송과 전송 기록 저장을 하지 않는다")
    args = parser.parse_args()

    load_dotenv()
    print("🇯🇵 writeJP 시작" + (" (dry-run)" if args.dry_run else ""))

    config = load_config()
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not webhook_url and not args.dry_run:
        print("❌ DISCORD_WEBHOOK_URL 환경변수가 없습니다 (.env 또는 GitHub Secrets).")
        return 1

    articles = fetch_articles(config["difficulty"], config["categories"],
                              sent=set(load_sent_articles()),
                              max_age_hours=config["max_age_hours"])
    if not articles:
        print("❌ 뉴스를 가져오지 못했습니다.")
        return 1

    picked = pick_sentences(articles, config["sentence_count"], config["difficulty"])
    if not picked:
        print("❌ 필사 문장을 선별하지 못했습니다.")
        return 1

    vocab_db   = load_vocab_db()
    vocab_list = analyze_vocab(picked["sentences"], vocab_db, config["vocab_levels"])

    if args.dry_run:
        print_preview(picked["sentences"], picked["sources"], vocab_list)
        return 0

    ok = send_to_discord(
        webhook_url = webhook_url,
        sentences   = picked["sentences"],
        sources     = picked["sources"],
        difficulty  = config["difficulty"],
        categories  = config["categories"],
        vocab_list  = vocab_list,
    )
    if not ok:
        return 1

    # 전송에 성공한 뒤에만 기록한다 (실패하면 내일 다시 같은 기사를 시도)
    save_sent_articles([s["feed_url"] for s in picked["sources"]])
    print("🎉 완료!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
