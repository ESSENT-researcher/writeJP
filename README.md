# writeJP 🇯🇵

매일 일본어 뉴스에서 필사용 문장 8개를 뽑아 Discord로 보내고, 문장에 나온 JLPT 단어를 단어장으로 함께 보내는 봇.
설계는 [PLAN.md](PLAN.md) 참고.

## 설정
`config.json`

| 키 | 설명 |
|---|---|
| `difficulty` | `beginner` / `intermediate` / `advanced` |
| `categories` | `world`(국제), `business`(경제), `domestic`(사회), `science`(과학). advanced(朝日)는 분야 구분이 없어 무시 |
| `rotate_categories` | `true`면 날짜(JST)에 따라 `categories`를 **하루에 하나씩 순서대로** 돌려 쓴다 (기본: 경제 → 국제 → 과학). `false`면 모든 분야를 섞어서 사용 |
| `sentence_count` | 목표 문장 수 (현재 8) |
| `furigana` | `true`면 문장의 한자에 후리가나를 `漢字(かんじ)` 형태로 표기 |
| `translate` | `true`면 각 문장 밑에 한국어 번역을 붙인다. Claude API를 쓰며 `ANTHROPIC_API_KEY`가 없으면 번역만 생략된다 |
| `max_age_hours` | 발행 후 이 시간 이내의 기사만 사용 (기본 24). 최신 기사부터 고른다 |
| `vocab_levels` | `null`이면 난이도에 따라 자동 (beginner N5·N4 / intermediate N3·N2 / advanced N2·N1) |

분야를 직접 고를 필요는 없다. Actions 수동 실행에서 분야를 입력하면 그 실행에만 순환 없이 입력한 분야를 쓴다.

실행 시각은 `.github/workflows/daily_news.yml`의 cron이 정한다 (현재 KST 08:00).

## 로컬 실행
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

python3 main.py --dry-run     # Discord 전송 없이 결과만 출력
cp .env.example .env          # DISCORD_WEBHOOK_URL 입력 후
python3 main.py               # 실제 전송
pytest                        # 단위 테스트
```

## GitHub Actions 배포
1. 레포 Settings → Secrets and variables → Actions → `DISCORD_WEBHOOK_URL` 등록. 한국어 번역을 쓰려면 `ANTHROPIC_API_KEY`도 등록 (없어도 나머지는 정상 동작)
2. Actions 탭에서 `Daily Japanese News` → Run workflow로 수동 테스트
3. 전송 기록(`data/sent_articles.json`)은 실행 후 자동 커밋된다. 실패하면 Discord로 알림이 온다.

## 단어 데이터 갱신
`python3 scripts/build_vocab.py` — JLPT N1~N5 공개 CSV를 받아 `data/jlpt_vocab.csv`(영어 뜻)를 다시 만든다.
한국어 뜻은 `data/meaning_ko.csv`(표기, 읽기, 한국어 뜻)에 따로 저장돼 있어 다시 만들어도 유지된다. 번역이 없는 항목은 영어 뜻이 표시된다. 오역은 이 파일에서 직접 고치면 된다.

## 사전 데이터 (JMdict)
`python3 scripts/build_jmdict.py extract` / `merge` — JMdict에서 우선순위 태그가 붙은 흔한 단어 30,169개를 골라 `data/jmdict.jsonl`(표기, 읽기, 한국어 뜻, 영어 뜻)로 만든다. 한국어 뜻은 `data/jmdict_ko.csv`(id, 한국어 뜻)에 저장돼 있다.

JMdict는 [Electronic Dictionary Research and Development Group](https://www.edrdg.org/)의 자산이며 [CC BY-SA 4.0](https://www.edrdg.org/edrdg/licence.html) 라이선스로 배포된다. 이 저장소의 `data/jmdict.jsonl`, `data/jmdict_ko.csv`도 같은 조건(저작자 표시, 동일 조건 변경 허락)을 따른다.
