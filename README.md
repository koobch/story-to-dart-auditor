# Story-to-DART Auditor

실적 시즌마다 경쟁사 IR 자료와 DART 공시를 하나씩 열어보는 전략기획 업무를 자동화하는 Codex Skill입니다.

## Primary Workflow

```bash
export PATH="$PWD/bin:$PATH"

dart-audit season \
  --companies "크래프톤,넷마블,엔씨소프트,카카오게임즈" \
  --table outputs/tables/game-competitors.md
```

The `season` command resolves company names through OpenDART, finds the latest available periodic filing (quarterly, semiannual, or annual), pulls major financial accounts, detects special situation disclosures, and creates/appends a table.

## Story Audit

```bash
dart-audit audit \
  --company "크래프톤" \
  --story "글로벌 IP와 AI 전환으로 장기 성장성이 높다는 주장" \
  --peers "넷마블,엔씨소프트,카카오게임즈" \
  --industry game \
  --purpose "전략기획 회의용" \
  --output html,db
```

## Outputs

- `outputs/tables/`: earnings-season competitor tables.
- `outputs/reports/`: HTML one-pagers.
- `data/research_cards.sqlite`: saved Research Cards.
- `skills/story-to-dart-auditor/`: installable Codex Skill.

## Safety

This is not an investment recommendation tool. Reports include a disclaimer and do not provide buy/sell recommendations, target prices, or guaranteed returns.

