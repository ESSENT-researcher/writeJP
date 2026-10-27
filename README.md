# writeJP 🇯🇵

매일 일본어 뉴스에서 필사용 문장 10개를 뽑아 Discord로 보내고, 문장에 나온 JLPT 단어를 단어장으로 함께 보내는 봇.
설계는 [PLAN.md](PLAN.md) 참고.

## 설정
`config.json`

| 키 | 설명 |
|---|---|
| `difficulty` | `beginner` / `intermediate` / `advanced` |
| `categories` | `world, business, domestic, science, sports, entertainment` (advanced는 무시) |
| `sentence_count` | 목표 문장 수 |
| `max_age_hours` | 발행 후 이 시간 이내의 기사만 사용 (기본 24). 최신 기사부터 고른다 |
| `vocab_levels` | `null`이면 난이도에 따라 자동 (beginner N5·N4 / intermediate N3·N2 / advanced N2·N1) |

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
1. 레포 Settings → Secrets and variables → Actions → `DISCORD_WEBHOOK_URL` 등록
2. Actions 탭에서 `Daily Japanese News` → Run workflow로 수동 테스트
3. 전송 기록(`data/sent_articles.json`)은 실행 후 자동 커밋된다. 실패하면 Discord로 알림이 온다.

## 단어 데이터 갱신
`python3 scripts/build_vocab.py` — JLPT N1~N5 공개 CSV를 받아 `data/jlpt_vocab.csv`(영어 뜻)를 다시 만든다.
한국어 뜻은 `data/meaning_ko.csv`(표기, 읽기, 한국어 뜻)에 따로 저장돼 있어 다시 만들어도 유지된다. 번역이 없는 항목은 영어 뜻이 표시된다. 오역은 이 파일에서 직접 고치면 된다.
