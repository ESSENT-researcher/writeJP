import io

from scripts.build_jmdict import english_summary, parse_entries, reuse_jlpt_translation

SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE JMdict [
<!ENTITY n "noun (common) (futsuumeishi)">
<!ENTITY vs "noun or participle which takes the aux. verb suru">
]>
<JMdict>
<entry>
<ent_seq>1</ent_seq>
<k_ele><keb>提訴</keb><ke_pri>news1</ke_pri><ke_pri>nf20</ke_pri></k_ele>
<r_ele><reb>ていそ</reb></r_ele>
<sense><pos>&n;</pos><pos>&vs;</pos><gloss>filing a lawsuit</gloss><gloss>presenting a case</gloss></sense>
<sense><gloss xml:lang="fre">procès</gloss></sense>
</entry>
<entry>
<ent_seq>2</ent_seq>
<k_ele><keb>稀</keb></k_ele>
<r_ele><reb>まれ</reb></r_ele>
<sense><pos>&n;</pos><gloss>rare</gloss></sense>
</entry>
<entry>
<ent_seq>3</ent_seq>
<r_ele><reb>あなた</reb><re_pri>ichi1</re_pri></r_ele>
<sense><pos>&n;</pos><gloss>you</gloss></sense>
</entry>
</JMdict>
""".encode("utf-8")


def _entries():
    return {e["id"]: e for e in parse_entries(io.BytesIO(SAMPLE))}


def test_parses_forms_priority_and_english_only_glosses():
    entry = _entries()[1]
    assert entry["k"] == ["提訴"] and entry["r"] == ["ていそ"]
    assert entry["rank"] == 20                       # nf20
    assert entry["en"] == [["filing a lawsuit", "presenting a case"]]   # 프랑스어 뜻은 제외
    assert entry["pos"] == "v"                       # 'noun ... aux. verb suru' → 동사 계열로 표시


def test_entries_without_priority_tags_have_no_rank():
    entries = _entries()
    assert entries[2]["rank"] is None
    assert entries[3]["rank"] == 49 and entries[3]["k"] == []   # 우선순위는 있지만 nf 순위는 없음


def test_english_summary_is_one_line_and_truncated():
    assert english_summary([["a", "b"], ["c"]]) == "a, b / c"
    assert english_summary([["x" * 200]]).endswith("…")


def test_reuses_jlpt_translation_by_word_and_reading():
    entry = {"k": ["提訴"], "r": ["ていそ"]}
    assert reuse_jlpt_translation(entry, {("提訴", "ていそ"): "제소"}) == "제소"
    assert reuse_jlpt_translation(entry, {("提訴", "べつ"): "제소"}) is None
    kana_only = {"k": [], "r": ["あなた"]}
    assert reuse_jlpt_translation(kana_only, {("あなた", "あなた"): "당신"}) == "당신"
