# 📝 writeJP — 일본어 필사 봇 설계 계획서 (v3)

매일 일본어 뉴스에서 10문장을 뽑아 Discord로 전송하고,
문장에 나온 JLPT 단어를 단어장으로 함께 보내는 학습 봇.

> v2 → v3 변경 요약은 맨 아래 "부록 A"에 있다.

## 확정 사항
- 메신저: Discord Webhook
- 스케줄러: GitHub Actions (매일 KST 08:00)
- 단어 데이터: JLPT N1~N5 공개 CSV(약 8,300단어)를 빌드 스크립트로 받아 `data/jlpt_vocab.csv` 한 파일로 보관
- 설정: `config.json` 직접 수정 (Discord Bot 슬래시 커맨드는 추후)
- 비용: 0원 (외부 유료 API 없음)

---

## 1. 아키텍처

```
config.json ─┐
             ▼
     ┌───────────────┐
     │ News Fetcher  │  RSS → 기사 URL → 본문 추출 (소스별 파서)
     └──────┬────────┘
            ▼
     ┌───────────────┐
     │Sentence Picker│  문장 분리 → 필터 → 10문장 (문장별 출처 추적)
     └──────┬────────┘
            ▼
     ┌───────────────┐      ┌──────────────┐
     │Vocab Analyzer │◄─────│ Dict Lookup  │  data/jlpt_vocab.csv
     │ (fugashi)     │      │ (메모리 dict) │
     └──────┬────────┘      └──────────────┘
            ▼
     ┌───────────────┐
     │Discord Sender │  Embed 2개 (뉴스 / 단어장)
     └──────┬────────┘
            ▼
     State 저장 (data/sent_articles.json) → 워크플로가 레포에 커밋
```

실행은 GitHub Actions가 `main.py`를 호출한다. 실패하면 Discord로 실패 알림을 보낸다.

---

## 2. 모듈 설계

### 2-1. News Fetcher
2026-10 기준으로 각 소스를 직접 확인한 결과를 반영했다.

| 난이도 | 소스 | 상태 |
|---|---|---|
| `beginner` | Yahoo! Japan News RSS + **짧은 문장(≤60자) 필터** + N5·N4 단어장 | NHK Web Easy API는 JWT 필수(401). 대체로 검토한 NHK 일반 뉴스 RSS는 오래된 링크(404)를 주고 본문도 요약뿐이라 제외 |
| `intermediate` | Yahoo! Japan News RSS (분야별) | 동작 확인 |
| `advanced` | 朝日新聞 RSS | 동작 확인 (유료 기사는 본문 일부만 노출, 간헐적 타임아웃 → 1회 재시도) |

핵심 동작:
1. RSS에서 기사 링크 수집 후 이미 보낸 URL 제외.
2. **Yahoo RSS 링크는 `/pickup/` 요약 페이지**다. 그 안의 `/articles/…` 링크를 한 번 더 따라가야 본문(`div.article_body`)이 나온다.
3. 본문 추출은 소스별 선택자 → 실패하면 `<p>` 폴백.
4. 기사 하나가 실패해도 다음 기사로 넘어간다. 전부 실패하면 종료 코드 1.
5. 요청 간 1초 간격, 타임아웃 10초.

### 2-2. Sentence Picker
- `。！？` 기준 분리, 줄바꿈도 경계로 취급.
- 길이: **15~120자** (v2의 5~100자는 필사 용도로 너무 짧은 문장이 섞여 조정). beginner는 최대 60자.
- 제외: 광고·네비·날짜·출처·URL·설문·관련기사·구독/수신료 안내 문구, 제목형(종결 부호 없음), 따옴표가 중간에 끊긴 문장.
- `【ワシントン時事】` 같은 통신사 머리말은 떼어낸다.
- **문장마다 출처 기사를 기록**한다. Yahoo 본문은 짧아 기사 여러 개에서 모으는 경우가 많으므로, 사용한 기사 전부를 Embed에 표시한다. (v2는 첫 기사 하나만 표시해 출처가 틀렸다.)
- 같은 기사의 문장은 원문 순서를 유지한다.

### 2-3. Dict Lookup
- `data/jlpt_vocab.csv`: `word,reading,meaning,level`
- 출처: stephenmk/yomichan-jlpt-vocab (JMdict 기반, Waller 목록). `scripts/build_vocab.py`가 내려받아 병합한다.
- 한 단어가 여러 레벨에 있으면 어려운 쪽(N1에 가까운 쪽)을 채택.
- 표제어는 한자 표기가 있으면 한자, 없으면 가나.
- **같은 표기라도 읽기가 다르면 별개 항목**이다(`認める`: みとめる N3 / したためる N1). 표기만으로 합치면 희귀한 읽기가 이겨서 오표기가 생긴다.
- **한국어 뜻**: 공개 한국어 데이터가 없어서(JMdict의 한국어 뜻은 131건) 8,289개 전부를 표기·읽기·영어 뜻을 보고 직접 번역해 `data/meaning_ko.csv`(`word,reading,meaning_ko`)에 저장했다. `build_vocab.py`를 다시 돌려도 이 파일은 지워지지 않는다. 번역이 없는 항목은 영어 뜻으로 대체한다.
- 전체 레벨을 로딩한 뒤 분석기가 읽기를 대조하고, 그다음에 레벨로 거른다(레벨을 먼저 거르면 N3 단어가 N1의 희귀 읽기로 둔갑한다).

### 2-4. Vocab Analyzer
- `fugashi` + `ipadic`로 형태소 분석, 명사/동사/형용사의 **기본형과 읽기** 추출. 사전 항목은 (기본형, 읽기)가 모두 일치할 때만 채택한다. (`11月`의 `月`처럼 읽기가 달라지는 노이즈도 일부 걸러진다.)
- 노이즈 방지: 한자가 없는 단어는 3자 이상일 때만 후보로 인정(`ある`, `する` 등 제외).
- 난이도별 기본 단어 레벨: beginner → N5·N4, intermediate → N3·N2, advanced → N2·N1. `config.json`의 `vocab_levels`로 덮어쓸 수 있다.
- 결과는 레벨 순(어려운 것 먼저), 레벨별 최대 15개.

### 2-5. Discord Sender
- Embed 1: 오늘의 뉴스 (날짜·난이도·분야·출처 목록·문장 목록).
- Embed 2: 단어장 (레벨별 묶음). 단어가 없으면 생략.
- Discord 제한(Embed 설명 4096자, 전체 6000자)을 넘기면 **줄 단위로** 잘라낸다.
- 429(rate limit)는 `retry_after`만큼 기다려 한 번 재시도.

### 2-6. State (중복 방지) — v3 신규
GitHub Actions 러너는 매번 새로 만들어지므로 로컬 파일은 저장되지 않는다.
- `data/sent_articles.json`을 **레포에 커밋**하고, 워크플로가 실행 후 변경분을 푸시한다 (`permissions: contents: write`).
- 최근 300개 URL만 유지하고 순서를 보존한다.
- 전송이 성공한 뒤에만 기록한다.

### 2-7. Scheduler / 알림
- `cron: '0 23 * * *'` (UTC 23:00 = KST 08:00), `workflow_dispatch`로 수동 실행 + 난이도/분야 입력.
- 수동 실행 입력은 파일을 고쳐 쓰지 않고 **환경변수**(`WRITEJP_DIFFICULTY`, `WRITEJP_CATEGORIES`)로 전달한다.
- 잡이 실패하면 Discord Webhook으로 실패 알림 메시지를 보낸다.
- 같은 워크플로가 겹쳐 실행되지 않도록 `concurrency` 그룹을 둔다.

### 2-8. 설정 (`config.json`)
```json
{
  "difficulty": "intermediate",
  "categories": ["business", "world"],
  "sentence_count": 10,
  "vocab_levels": null
}
```
- `vocab_levels`가 `null`이면 난이도에 따라 자동 결정.
- `send_time_kst`는 **삭제**했다. 실제 시각은 워크플로의 cron이 정하므로 설정값이 아무 효과가 없었다.
- Webhook URL은 설정 파일에 두지 않는다 (환경변수 `DISCORD_WEBHOOK_URL` / GitHub Secrets).

---

## 3. 파일 구조

```
writeJP/
├── main.py                  # 진입점 (--dry-run 지원)
├── config.json
├── requirements.txt
├── requirements-dev.txt     # pytest
├── PLAN.md  README.md
├── modules/
│   ├── config.py            # 설정 로딩 + 난이도별 기본값
│   ├── state.py             # 전송 기록
│   ├── news_fetcher.py
│   ├── sentence_picker.py
│   ├── dict_lookup.py
│   ├── vocab_analyzer.py
│   └── discord_sender.py
├── scripts/build_vocab.py   # N1~N5 CSV 내려받아 병합
├── tests/                   # pytest 단위 테스트 (네트워크 없음)
├── data/
│   ├── jlpt_vocab.csv
│   └── sent_articles.json
└── .github/workflows/daily_news.yml
```

---

## 4. 라이브러리
`feedparser`, `beautifulsoup4`, `requests`, `fugashi`, `ipadic`, `python-dotenv` (개발: `pytest`)

---

## 5. 구현 순서
- [x] Phase 0: 소스·데이터 실측 (NHK Easy 401, Yahoo pickup 구조, 단어 데이터 확보 가능 여부)
- [x] Phase 1: 프로젝트 뼈대, 설정, State
- [x] Phase 2: 단어 데이터 빌드 스크립트 + Dict Lookup
- [x] Phase 3: News Fetcher
- [x] Phase 4: Sentence Picker
- [x] Phase 5: Vocab Analyzer
- [x] Phase 6: Discord Sender
- [x] Phase 7: main.py 연결 + `--dry-run`
- [x] Phase 8: 단위 테스트 (27개)
- [x] Phase 9: GitHub Actions 작성 (상태 커밋, 실패 알림)
- [x] Phase 10: dry-run으로 intermediate/advanced/beginner 실제 뉴스 검증, 가짜 Webhook으로 전송 경로 검증
- [ ] **남은 일**: GitHub에 push → Secrets(`DISCORD_WEBHOOK_URL`) 등록 → Actions에서 수동 실행해 실제 Discord 수신 확인

## 알려진 한계
- 한국어 뜻은 기계적으로 번역한 것이라 전수 검수하지 않았다. 표본 25개는 이상이 없었지만, 희귀 항목이나 다의어는 오역이 있을 수 있다. 틀린 것은 `data/meaning_ko.csv`에서 직접 고치면 된다.
- 사전의 영어 뜻 자체가 다의어의 첫 번째 뜻이라, 문장 속 쓰임과 다른 뜻이 붙을 수 있다 (예: `対` → "쌍, 대(對)").
- 외래어 고유명사가 일반 단어로 잡힌다 (`トランプ` → "트럼프(카드)").
- beginner는 "입문자용 뉴스"가 아니라 "일반 뉴스의 짧은 문장 + 쉬운 단어 위주"다. 쉬운 일본어 뉴스 소스를 찾으면 교체한다.
- Yahoo 기사 본문은 짧아서(약 800자) 보통 기사 2~3개에서 문장을 모은다.

## 6. 미래 기능
- Discord Bot 슬래시 커맨드로 설정 변경
- 번역 검수, 뉴스 전용 어려운 단어(JLPT 밖) 단어장 확장
- 필사 완료 체크(리액션), 주간 복습, 오답 노트
- beginner용 쉬운 일본어 뉴스 소스 (NHK Web Easy 접근 방법이 생기면 교체)

---

## 부록 A. v2 → v3 변경 이유
| 변경 | 이유 |
|---|---|
| State를 레포에 커밋 | Actions 러너는 일회성이라 v2 방식은 중복 방지가 동작하지 않음 |
| beginner 소스를 Yahoo + 짧은 문장 필터로 교체 | NHK Easy API가 JWT 필수로 변경, NHK 일반 RSS도 부적합 |
| Yahoo `/pickup/` → `/articles/` 추적 | RSS 링크가 요약 페이지라 본문이 없음 |
| 출처를 기사 여러 개로 표시 | 문장이 여러 기사에서 모이는데 출처는 첫 기사만 표시했음 |
| 사전을 N1~N5 약 8,300단어로 확장 | 소규모 목록으로는 매칭이 거의 안 됨 |
| 한국어 뜻을 직접 번역해 CSV로 보관 | 공개 데이터가 없고, 영어 뜻은 학습용으로 부적합 |
| (표기, 읽기) 단위로 사전 구성 + 읽기 대조 | `認める（したためる）`처럼 희귀한 읽기가 단어장에 나오는 버그 |
| 난이도 → 단어 레벨 자동 연동 | beginner인데 단어장이 N1/N2인 불일치 |
| 문장 길이 15~120자 | 5자 문장은 필사 가치가 없음 |
| `send_time_kst`, Webhook URL 설정 제거 | 효과 없는 설정 / 시크릿을 파일에 두지 않음 |
| 실패 알림, 단위 테스트, `--dry-run` 추가 | 조용한 실패 방지, 수동 네트워크 스크립트 대체 |
