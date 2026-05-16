# Story-to-DART Auditor

**A Codex Skill that turns earnings-season disclosure work into a repeatable story verification workflow.**

Every earnings season, strategy and research teams open multiple IR decks, DART filings, competitor reports, and notes just to answer a deceptively simple question:

> "Is this company actually getting better, or does the story only sound good?"

Story-to-DART Auditor automates the first pass. It pulls the latest DART periodic filings, builds competitor tables, checks market stories against disclosure evidence, separates fact from inference, and saves the result as a one-pager plus a SQLite research card.

It is built for non-developer operators who need decision-ready evidence, not another generic finance dashboard.

## What It Does

- Resolves Korean company names through OpenDART.
- Uses the latest available periodic filing: quarterly, semiannual, or annual.
- Pulls core financial metrics: revenue, operating profit, operating margin, net income, assets.
- Detects special situation disclosures such as corrections, major events, shareholder changes, and investment decision notices.
- Reads optional IR files or earnings notes as supplemental context.
- Decomposes a market story into verifiable claims.
- Classifies each claim as `Fact`, `Inference`, `Story`, `Missing Evidence`, or `Contradicted`.
- Generates an HTML one-pager and saves a SQLite research card for next-quarter follow-up.
- Supports optional PDF/PNG export when Playwright is installed.

## Why This Is Different

Most tools start from the company:

```text
Company -> Financial statements -> Summary
```

This skill starts from the work pattern:

```text
Earnings season question -> Latest filings -> Evidence table -> Story audit -> One-pager -> Research history
```

The key idea is simple: **business decisions are usually made around stories, but those stories should be tested against filings.**

Instead of only summarizing numbers, the skill asks:

- Which part of the story is directly supported by DART?
- Which part is only an inference?
- What evidence is missing?
- What would break the story next quarter?
- How does the company compare with peers?

## Primary Users

- Strategy planners
- Business development teams
- Marketers and PMs preparing market/competitor briefings
- Researchers and non-developer operators
- Startup and SMB founders tracking competitors
- Individual investors as a secondary, non-recommendation use case

## Core Workflows

### 1. Company-only quick check

Use this when you only know the company name and need a quick briefing.

```bash
dart-audit company "크래프톤" \
  --peers "넷마블,엔씨소프트,카카오게임즈" \
  --industry game
```

This creates a one-pager using the latest DART filing and peer snapshot.

### 2. Context-rich story audit

Use this when you have a thesis, market theme, or meeting context.

```bash
dart-audit audit \
  --company "크래프톤" \
  --story "글로벌 IP와 AI 전환으로 장기 성장성이 높다는 주장" \
  --peers "넷마블,엔씨소프트,카카오게임즈" \
  --industry game \
  --purpose "전략기획 회의용 경쟁사 벤치마킹" \
  --output html,pdf,png,db
```

If Playwright is not installed, PDF/PNG export is skipped gracefully and the HTML one-pager plus DB record are still created.

### 3. Earnings-season competitor table

Use this to update a competitor tracking table every quarter.

```bash
export PATH="$PWD/bin:$PATH"

dart-audit season \
  --companies "크래프톤,넷마블,엔씨소프트,카카오게임즈" \
  --table outputs/tables/game-competitors.md
```

The same table path can be reused to append new rows next quarter.

## Demo Setup

```bash
git clone https://github.com/koobch/story-to-dart-auditor.git
cd story-to-dart-auditor
export PATH="$PWD/bin:$PATH"
export DART_API_KEY="your-opendart-api-key"
```

Run the fastest live demo:

```bash
dart-audit season \
  --companies "크래프톤,넷마블,엔씨소프트,카카오게임즈" \
  --table outputs/tables/game-competitors.md
```

Offline or API-failure demo:

```bash
dart-audit audit \
  --company "크래프톤" \
  --story "글로벌 IP와 AI 전환으로 장기 성장성이 높다는 주장" \
  --peers "넷마블,엔씨소프트,카카오게임즈" \
  --industry game \
  --purpose "전략기획 회의용" \
  --output html,db \
  --fallback
```

## Outputs

- `outputs/tables/`: earnings-season competitor tables.
- `outputs/reports/`: HTML one-pagers.
- `data/research_cards.sqlite`: saved research cards and audit history.
- `skills/story-to-dart-auditor/`: installable Codex Skill.

Generated outputs and local DART caches are ignored by git.

## Skillathon Pitch

This project is meant to be shown as a practical Codex Skill, not just a CLI script.

The Skill captures a real non-developer workflow:

1. Open DART.
2. Search each competitor.
3. Find the latest quarterly/semiannual/annual report.
4. Pull key financials.
5. Check if there were unusual events.
6. Read IR material.
7. Compare peers.
8. Prepare a one-page meeting brief.
9. Repeat the same process next quarter.

Story-to-DART Auditor compresses that into a few commands and makes the output reusable.

## Safety

This is not an investment recommendation tool.

Reports include a disclaimer and do not provide:

- Buy/sell recommendations.
- Target prices.
- Guaranteed returns.

The output should be read as disclosure-backed research support, not financial advice.

