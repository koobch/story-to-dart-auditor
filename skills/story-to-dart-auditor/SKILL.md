---
name: story-to-dart-auditor
description: "Automate earnings-season competitor review and market-story verification for Korean companies using OpenDART disclosures. Use when Codex is asked to analyze a company by name only, update a competitor earnings table, check latest quarterly/semiannual/annual filings, review IR/DART evidence, validate a market story or strategic hypothesis, classify claims into Fact/Inference/Story/Missing Evidence/Contradicted, produce an HTML/PDF/PNG one-pager, or save/list/show SQLite Research Cards. Primary users are strategy planners, business development, marketers, PMs, researchers, and non-developer operators; individual investors are a secondary non-recommendation use case."
---

# Story-to-DART Auditor

## Overview

Use this skill to turn earnings-season disclosure work into a repeatable audit. The primary use case is a strategy/planning professional who otherwise has to open IR decks and DART filings one by one; the secondary use case is a non-professional investor who wants a safer, non-recommendation company performance check.

## Quick Start

Use one of two modes.

### Mode A: Company-only quick check

Use when the user only gives a company name or asks "이 회사가 좋아지고 있는지 봐줘".

```bash
dart-audit company "크래프톤" --peers "넷마블,엔씨소프트,카카오게임즈" --industry game
```

### Mode B: Context-rich story audit

Use when the user provides a story, thesis, theme, peer group, or meeting purpose.

```bash
dart-audit audit --company "크래프톤" --story "글로벌 IP와 AI 전환으로 장기 성장성이 높다는 주장" --peers "넷마블,엔씨소프트,카카오게임즈" --industry game --purpose "전략기획 회의용 경쟁사 벤치마킹" --output html,pdf,png,db
```

For 실적 시즌 경쟁사 테이블 업데이트, run:

```bash
dart-audit season \
  --companies "크래프톤,넷마블,엔씨소프트,카카오게임즈" \
  --table outputs/tables/game-competitors.md
```

This creates or appends a table with latest DART periodic filing, revenue, operating profit, operating margin, net income, special situations, and optional IR notes.

For a single story audit, run the bundled CLI from this skill folder:

```bash
python3 scripts/dart_audit.py audit \
  --company "크래프톤" \
  --story "글로벌 IP와 AI 전환으로 장기 성장성이 높다는 주장" \
  --peers "넷마블,엔씨소프트,카카오게임즈" \
  --industry game \
  --purpose "전략기획 회의용" \
  --output html,db
```

If a `dart-audit` wrapper is available in the current project PATH, use:

```bash
dart-audit audit --company "크래프톤" --story "글로벌 IP와 AI 전환으로 장기 성장성이 높다는 주장" --peers "넷마블,엔씨소프트,카카오게임즈" --industry game --purpose "전략기획 회의용" --output html,db
```

Add `--fallback` when live DART fails and a demo-quality fixture result is acceptable. Add `--force-fallback` only for offline demos.

If the user has an IR deck or earnings memo, add `--ir-file path/to/file.pdf`. PDF, text, markdown, and HTML-like text files are supported as supplemental evidence.

If the user has a folder of IR files, name files with company names and add `--ir-dir path/to/ir-folder` to `season`.

## Workflow

1. Capture the input:
   - Company name
   - Or multiple competitor names for earnings-season table updates
   - Market story or strategic hypothesis
   - Peer group
   - Industry lens
   - Purpose/audience

2. Decompose the story:
   - Break the narrative into atomic claims.
   - Identify the evidence needed for each claim.
   - Keep claim text close to the user's wording.

3. Collect evidence:
   - Use live OpenDART by default when `DART_API_KEY` is present.
   - Resolve company name to `corp_code`, pull recent periodic filings, use the latest available periodic report (quarterly, semiannual, or annual), fetch financial statement major accounts, and search the filing body for story evidence.
   - If `--ir-file` is provided, scan the local IR deck or memo for matching story signals and include it as supplemental evidence.
   - Use fallback fixtures only when `--fallback` is set and DART fails, or when `--force-fallback` is explicitly requested.
   - Never fabricate numbers, filing dates, or source labels.

4. Classify every claim:
   - `Fact`: directly supported by evidence.
   - `Inference`: derived from facts with a stated logic chain.
   - `Story`: plausible narrative but not filing-proven.
   - `Missing Evidence`: no sufficient evidence found.
   - `Contradicted`: evidence conflicts with the claim.

5. Generate outputs:
   - Story Verification Score.
   - Claim classification table.
   - Peer snapshot.
   - Red flags.
   - Next Filing Watchlist.
   - 30-second report script.
   - HTML one-pager.
   - SQLite Research Card.

## Safety Rules

Always enforce these constraints:

- Do not provide buy/sell recommendations.
- Do not provide target prices.
- Do not promise or imply investment returns.
- Do not present fixture/demo data as live DART data.
- Do not invent numbers or sources.
- Include this disclaimer in every report: "본 자료는 투자 추천이 아니며, 매수/매도 권유, 목표주가 제시, 투자 수익 보장을 목적으로 하지 않습니다."

## CLI Commands

- `audit`: Run a story audit and generate requested outputs.
- `company`: Run a company-name-only quick check.
- `season`: Build or append an earnings-season competitor table from latest DART quarterly, semiannual, or annual filings.
- `list`: List saved Research Cards.
- `show`: Show one Research Card.
- `history`: Show audit history by company or keyword.
- `render`: Re-render an existing Research Card to HTML.

## Resources

- `scripts/dart_audit.py`: Typer-based CLI with fallback fixture demo, HTML generation, and SQLite storage.
- OpenDART live endpoints used by the script: `corpCode.xml`, `list.json`, `fnlttSinglAcnt.json`, `document.xml`.
- `references/audit-policy.md`: classification, scoring, and safety policy.
- `assets/one_pager_template.html`: self-contained HTML one-pager template.

## Output Interpretation

Treat the score as "how well this story is evidenced by available disclosures", not as investment attractiveness.

- 80-100: strongly supported by available evidence.
- 60-79: directionally supported with notable gaps.
- 40-59: mixed or weakly evidenced.
- 0-39: mostly unsupported, contradicted, or missing evidence.
