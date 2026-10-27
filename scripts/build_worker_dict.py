"""JLPT 단어장과 JMdict를 합쳐 Cloudflare Worker용 worker/dict.json을 만든다.

항목 형식: [표기들, 읽기들, 한국어 뜻, 레벨(JLPT가 아니면 "")]
"""
import csv
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = Path(__file__).resolve().parent.parent / "worker" / "dict.json"


def load_jlpt():
    ko = {}
    with open(DATA / "meaning_ko.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            ko[(row["word"], row["reading"])] = row["meaning_ko"]
    entries = []
    with open(DATA / "jlpt_vocab.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            key = (row["word"], row["reading"])
            entries.append([[row["word"]], [row["reading"]], ko.get(key) or row["meaning"], row["level"]])
    return entries


def main():
    entries = load_jlpt()
    seen = {(e[0][0], e[1][0]) for e in entries}
    added = 0
    with open(DATA / "jmdict.jsonl", encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            pairs = {(k, r) for k in e["k"] or [""] for r in e["r"]}
            if pairs & seen:
                continue
            entries.append([e["k"], e["r"], e["ko"], ""])
            added += 1
    OUT.write_text(json.dumps(entries, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"✅ {OUT}: JLPT {len(entries) - added}개 + JMdict {added}개 ({OUT.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    main()
