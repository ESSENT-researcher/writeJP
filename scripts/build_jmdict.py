"""
build_jmdict.py
JMdict에서 우선순위 태그가 붙은 항목(상용어)을 추려 한국어 뜻을 붙인 오프라인 사전을 만든다.
(슬래시 명령어 봇이 사전에 없는 단어를 조회할 때 쓴다.)

출처: JMdict (c) EDRDG — CC BY-SA 4.0 (https://www.edrdg.org/edrdg/licence.html)
이 스크립트로 만든 data/jmdict.jsonl은 같은 라이선스(CC BY-SA 4.0)를 따르며 출처를 표기해야 한다.

단계:
    python3 scripts/build_jmdict.py extract --out WORKDIR/tier.jsonl
        JMdict를 내려받아 우선순위 항목을 빈도순으로 추출한다 (번역 대상 목록, 영어 뜻 포함)
    python3 scripts/build_jmdict.py merge --tier WORKDIR/tier.jsonl
        data/jmdict_ko.csv(id → 한국어 뜻)를 합쳐 data/jmdict.jsonl을 만든다
"""

import argparse
import csv
import gzip
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

import requests

JMDICT_URL = "http://ftp.edrdg.org/pub/Nihongo/JMdict.gz"
OUT_PATH = "data/jmdict.jsonl"
KO_PATH = "data/jmdict_ko.csv"            # id,meaning_ko  (번역 결과)
JLPT_KO_PATH = "data/meaning_ko.csv"      # word,reading,meaning_ko  (JLPT 단어 번역 — 재사용)

_NF = re.compile(r"^nf(\d\d)$")
NO_NF_RANK = 49                            # nf 순위는 없지만 다른 우선순위 태그가 있는 항목
MAX_GLOSSES_PER_SENSE = 3
MAX_SENSES = 3


def _pos_code(pos_texts: list[str]) -> str:
    """JMdict의 긴 품사 설명을 번역에 도움이 되는 짧은 코드로 줄인다."""
    joined = " ".join(pos_texts).lower()
    for needle, code in (("verb", "v"), ("adjective (keiyoushi)", "adj-i"), ("adjectival nouns", "adj-na"),
                         ("adverb", "adv"), ("expression", "exp"), ("noun", "n")):
        if needle in joined:
            return code
    return ""


def parse_entries(fileobj):
    """JMdict XML(file-like)에서 항목을 하나씩 yield한다. 우선순위 태그가 없는 항목도 포함."""
    for _, el in ET.iterparse(fileobj):
        if el.tag != "entry":
            continue
        priorities = [p.text for p in el.iter() if p.tag in ("ke_pri", "re_pri") and p.text]
        nf = [int(m.group(1)) for p in priorities if (m := _NF.match(p))]

        senses = []
        pos = []
        for sense in el.findall("sense"):
            pos += [p.text for p in sense.findall("pos") if p.text]
            glosses = [g.text for g in sense.findall("gloss")
                       if g.text and g.get("{http://www.w3.org/XML/1998/namespace}lang", "eng") == "eng"]
            if glosses:
                senses.append(glosses[:MAX_GLOSSES_PER_SENSE])

        yield {
            "id": int(el.findtext("ent_seq")),
            "k": [k.findtext("keb") for k in el.findall("k_ele")],
            "r": [r.findtext("reb") for r in el.findall("r_ele")],
            "pos": _pos_code(pos),
            "en": senses[:MAX_SENSES],
            "rank": (min(nf) if nf else NO_NF_RANK) if priorities else None,
        }
        el.clear()


def english_summary(senses: list[list[str]], limit: int = 70) -> str:
    """첫 뜻 위주로 영어 뜻을 한 줄로 줄인다 (번역 입력용 / 사전의 영어 대체 표시용)."""
    text = " / ".join(", ".join(s) for s in senses)
    return text if len(text) <= limit else text[: limit - 1].rstrip(", /") + "…"


def load_jlpt_korean(path: str = JLPT_KO_PATH) -> dict[tuple[str, str], str]:
    try:
        with open(path, encoding="utf-8", newline="") as f:
            return {(r["word"], r["reading"]): r["meaning_ko"] for r in csv.DictReader(f)}
    except FileNotFoundError:
        return {}


def reuse_jlpt_translation(entry: dict, jlpt_ko: dict) -> str | None:
    """이미 번역한 JLPT 단어와 (표기, 읽기)가 같으면 그 번역을 재사용한다."""
    for reading in entry["r"]:
        for word in entry["k"] or [reading]:
            if (word, reading) in jlpt_ko:
                return jlpt_ko[(word, reading)]
    return None


def download(path: str) -> str:
    if not os.path.exists(path):
        print("📥 JMdict 내려받는 중...")
        resp = requests.get(JMDICT_URL, timeout=120)
        resp.raise_for_status()
        with open(path, "wb") as f:
            f.write(resp.content)
    return path


def cmd_extract(args) -> int:
    gz = download(args.cache)
    jlpt_ko = load_jlpt_korean()
    tier, reused = [], 0
    with gzip.open(gz, "rb") as f:
        for entry in parse_entries(f):
            if entry["rank"] is not None and entry["en"]:
                tier.append(entry)
    tier.sort(key=lambda e: (e["rank"], e["id"]))      # 빈도 높은 것부터
    with open(args.out, "w", encoding="utf-8") as f:
        for entry in tier:
            ko = reuse_jlpt_translation(entry, jlpt_ko)
            reused += ko is not None
            f.write(json.dumps({**entry, "ko": ko}, ensure_ascii=False) + "\n")
    print(f"✅ 우선순위 항목 {len(tier)}개 추출 (JLPT 번역 재사용 {reused}개, 직접 번역 필요 {len(tier) - reused}개): {args.out}")
    return 0


def cmd_merge(args) -> int:
    with open(KO_PATH, encoding="utf-8", newline="") as f:
        translated = {int(r["id"]): r["meaning_ko"] for r in csv.DictReader(f)}
    rows = []
    with open(args.tier, encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            ko = entry["ko"] or translated.get(entry["id"])
            rows.append({
                "id": entry["id"], "k": entry["k"], "r": entry["r"],
                "ko": ko or "", "en": english_summary(entry["en"]),
            })
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    done = sum(1 for r in rows if r["ko"])
    print(f"✅ {OUT_PATH}: {len(rows)}개 (한국어 뜻 {done}개, 영어만 {len(rows) - done}개)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("extract")
    p.add_argument("--out", required=True)
    p.add_argument("--cache", default="JMdict.gz", help="내려받은 JMdict.gz 위치 (없으면 내려받는다)")
    p.set_defaults(func=cmd_extract)
    p = sub.add_parser("merge")
    p.add_argument("--tier", required=True)
    p.set_defaults(func=cmd_merge)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
