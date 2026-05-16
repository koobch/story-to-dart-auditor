# 공시청문회 OS: Story-to-DART Auditor

## One-liner

실적 시즌마다 IR 자료와 DART 공시를 하나씩 확인해야 하는 전략기획 업무를, 회사명·스토리·비교군만 입력하면 공시 기반 감사 리포트로 바꿔주는 Codex Skill입니다.

## Why this should win

- 비개발자 실무자가 실적 시즌에 실제로 하는 일을 다룹니다: IR/DART 확인, 실적 비교, 보고서용 팩트 분류를 자동화합니다.
- 단순 리서치 요약이 아니라 의사결정 전 안전장치입니다.
- 전략기획, 리서치, IR, 마케팅, 임원 보고에 바로 연결됩니다.
- OpenDART API를 직접 사용하되, 현장 네트워크/API 실패에 대비해 fallback fixture demo도 지원합니다.
- 개인 투자자는 보조적으로 기업 실적 분석의 출발점으로 쓸 수 있지만, 투자 추천은 하지 않습니다.

## Demo

```bash
cd /Users/noname/skillathon-story-to-dart-auditor
export PATH="$PWD/bin:$PATH"
dart-audit season --companies "크래프톤,넷마블,엔씨소프트,카카오게임즈" --table outputs/tables/game-competitors.md
dart-audit audit --company "크래프톤" --story "글로벌 IP와 AI 전환으로 장기 성장성이 높다는 주장" --peers "넷마블,엔씨소프트,카카오게임즈" --industry game --purpose "전략기획 회의용" --output html,db
dart-audit list
dart-audit show 1
dart-audit history --company "크래프톤"
dart-audit render 1
```

현장 네트워크나 DART API가 실패하면 같은 명령에 `--fallback`을 붙여 fixture demo로 전환할 수 있습니다.

## Outputs

- HTML one-pager: `outputs/reports/`
- SQLite Research Card: `data/research_cards.sqlite`
- Earnings-season competitor table: `outputs/tables/`
- Codex Skill: `skills/story-to-dart-auditor/SKILL.md`
- Live DART integration: `corpCode.xml`, `list.json`, `fnlttSinglAcnt.json`, `document.xml`

## Safety

Every report includes a disclaimer and bans buy/sell recommendations, target prices, and guaranteed return language.
