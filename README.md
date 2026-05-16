# 공시청문회 OS: Story-to-DART Auditor

실적 시즌마다 경쟁사 IR 자료와 DART 공시를 하나씩 열어보는 전략기획 업무를 자동화하는 Codex Skill입니다. 단순히 재무제표를 요약하는 도구가 아니라, 시장 스토리를 검증 가능한 주장으로 쪼개고 DART 숫자와 공시 서술로 확인하는 "스토리 검증기"입니다.

## Two Usage Modes

### 1. Company-only quick check

회사명만 넣고 최신 분기/반기/사업보고서 기준으로 빠르게 원페이퍼를 만듭니다.

```bash
dart-audit company "크래프톤" --peers "넷마블,엔씨소프트,카카오게임즈" --industry game
```

### 2. Context-rich story audit

스토리라인, 비교군, 목적을 넣고 Fact / Inference / Story / Missing Evidence / Contradicted로 검증합니다.

```bash
dart-audit audit \
  --company "크래프톤" \
  --story "글로벌 IP와 AI 전환으로 장기 성장성이 높다는 주장" \
  --peers "넷마블,엔씨소프트,카카오게임즈" \
  --industry game \
  --purpose "전략기획 회의용 경쟁사 벤치마킹" \
  --output html,pdf,png,db
```

PDF/PNG export is optional. If Playwright is not installed, the command still generates the HTML one-pager and DB record.

## Earnings Season Workflow

```bash
export PATH="$PWD/bin:$PATH"

dart-audit season \
  --companies "크래프톤,넷마블,엔씨소프트,카카오게임즈" \
  --table outputs/tables/game-competitors.md
```

The `season` command resolves company names through OpenDART, finds the latest available periodic filing (quarterly, semiannual, or annual), pulls major financial accounts, detects special situation disclosures, and creates/appends a table.

## Target Users

- Strategy planners
- Business development teams
- Marketers and PMs
- Researchers and non-developer operators
- Startup and SMB founders
- Individual investors as a secondary, non-recommendation use case

## Use Cases

- 경쟁사 실적 분석
- 벤치마킹 기업 분석
- 시장 테마 검증
- 투자 아이디어 1차 점검
- 회의 전 원페이퍼 생성
- 분기별 watchlist 업데이트
- "이 회사가 진짜 좋아지고 있는지" 확인

## Differentiation

Existing analyzers usually do:

```text
Company -> Financial statements -> Summary
```

Story-to-DART Auditor does:

```text
Market story -> Verifiable claims -> DART evidence -> Fact/Inference/Story/Missing Evidence -> One-pager -> SQLite history
```

The key difference:

- It analyzes the story, not just the company.
- It identifies what would break the story.
- It separates fact, inference, narrative, and missing evidence.
- It preserves results in reports and DB so the next quarter can continue from prior context.

## Outputs

- `outputs/tables/`: earnings-season competitor tables.
- `outputs/reports/`: HTML one-pagers.
- `data/research_cards.sqlite`: saved Research Cards.
- `skills/story-to-dart-auditor/`: installable Codex Skill.

## Safety

This is not an investment recommendation tool. Reports include a disclaimer and do not provide buy/sell recommendations, target prices, or guaranteed returns.
