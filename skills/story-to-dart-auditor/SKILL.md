---
name: story-to-dart-auditor
description: "한국 기업의 실적 시즌 경쟁사 분석과 시장 스토리 검증을 OpenDART 공시 기반으로 자동화한다. 회사명만으로 빠른 점검을 하거나, 회사명/스토리/비교군/산업 렌즈/회의 목적을 받아 최신 분기보고서·반기보고서·사업보고서, IR 자료, 재무 주요 계정, 특수 상황 공시를 확인한다. 결과는 Fact/Inference/Story/Missing Evidence/Contradicted로 분류하고 HTML/PDF/PNG 원페이퍼 및 SQLite Research Card로 저장한다. 전략기획, 사업개발, 마케팅, PM, 리서처, 비개발 실무자에게 우선 사용하며, 개인 투자자 용도는 투자 추천이 아닌 보조적 실적 점검으로 제한한다."
---

# Story-to-DART Auditor

## 언제 쓰나

사용자가 한국 기업의 실적, 경쟁사, DART 공시, IR 자료, 시장 스토리, 벤치마킹 가설을 확인해달라고 하면 이 스킬을 사용한다.

대표 요청:

- "크래프톤 최신 공시로 원페이퍼 만들어줘."
- "게임사 경쟁사 실적 테이블 업데이트해줘."
- "이 회사가 진짜 좋아지고 있는지 확인해줘."
- "글로벌 IP와 AI 전환 스토리가 DART 숫자로 확인되는지 봐줘."
- "이번 분기 경쟁사 특수 상황 공시가 있었는지 정리해줘."

## 사용자에게 설명할 기본 구조

기본 명령은 `audit`이다.

`company`는 별도 분석 체계가 아니라 회사명만 넣고 빠르게 실행하는 단축 명령이다. 사용자가 헷갈려 하면 `audit --company "회사명"`만 안내한다.

`peers`는 별도 명령이 아니라 비교군 옵션이다. 분석 대상 회사와 비교할 회사를 쉼표로 넣으면 된다.

## 추천 사용법

### 1. 실적 시즌 경쟁사 테이블

경쟁사 여러 곳을 한 번에 업데이트할 때 사용한다.

```bash
dart-audit season \
  --companies "크래프톤,넷마블,엔씨소프트,카카오게임즈" \
  --table outputs/tables/game-competitors.md
```

특정 분기 기준으로 비교하려면 `--period`를 사용한다.

```bash
dart-audit season \
  --companies "크래프톤,넷마블,엔씨소프트,카카오게임즈" \
  --period 25.4Q \
  --table outputs/tables/game-competitors-25-4q.md
```

기본값은 `--basis quarter`이며, 분기 실적을 보여준다. DART 보고서 누계 숫자를 그대로 보고 싶으면 `--basis cumulative`을 사용한다.

결과:

- 최신 분기/반기/사업보고서 확인
- 매출, 영업이익, 영업이익률, 순이익, 자산 추출
- 특정 분기 지정 시 회사별 기준 기간 통일
- QoQ, YoY 증감률과 추세 코멘트 생성
- 특수 상황 공시 탐지
- Markdown 또는 CSV 테이블 생성/추가

### 2. 회사명만 넣는 빠른 점검

```bash
dart-audit audit \
  --company "크래프톤" \
  --peers "넷마블,엔씨소프트,카카오게임즈" \
  --industry game
```

동일한 단축 명령:

```bash
dart-audit company "크래프톤" \
  --peers "넷마블,엔씨소프트,카카오게임즈" \
  --industry game
```

### 3. 스토리 검증 리포트

```bash
dart-audit audit \
  --company "크래프톤" \
  --story "글로벌 IP와 AI 전환으로 장기 성장성이 높다는 주장" \
  --peers "넷마블,엔씨소프트,카카오게임즈" \
  --industry game \
  --purpose "전략기획 회의용 경쟁사 벤치마킹" \
  --output html,db
```

### 4. IR 파일까지 같이 확인

```bash
dart-audit audit \
  --company "크래프톤" \
  --story "신작과 글로벌 IP 확장으로 성장성이 개선되고 있다는 주장" \
  --peers "넷마블,엔씨소프트,카카오게임즈" \
  --ir-file sample-ir-note.md \
  --output html,db
```

PDF, txt, md, HTML 계열 텍스트를 보조 근거로 읽을 수 있다.

## 실행 원칙

1. 회사명과 비교군을 확인한다.
2. `DART_API_KEY`가 있으면 live OpenDART를 우선 사용한다.
3. 최신 정기공시는 분기보고서, 반기보고서, 사업보고서 중 가장 최근 것을 사용한다.
4. DART 실패 시 사용자가 `--fallback`을 허용했을 때만 fixture를 사용한다.
5. 숫자, 날짜, 출처를 지어내지 않는다.
6. 스토리 검증 결과를 반드시 Fact, Inference, Story, Missing Evidence, Contradicted로 구분한다.
7. 리포트는 투자 추천이 아니라 공시 기반 업무 보조 자료로 작성한다.

## DART API 키 안내

live DART 조회에는 사용자별 OpenDART API 인증키가 필요하다.

- 키는 레포에 포함하지 않는다.
- 사용자는 OpenDART 사이트에서 직접 인증키를 발급받아야 한다.
- 로컬 환경변수 또는 프로젝트 루트 `.env` 파일에 `DART_API_KEY`로 설정한다.
- 키가 없으면 live 조회는 실패하므로, 데모 목적이면 `--force-fallback` 또는 `--fallback`을 안내한다.

```bash
export DART_API_KEY="발급받은_API_KEY"
```

## 결과물

`audit` 결과:

- Story Verification Score
- Claim classification table
- 분기 실적 기준 period, QoQ, YoY, trend comment
- Peer snapshot
- Red flags
- Next Filing Watchlist
- 30초 보고 스크립트
- HTML one-pager
- SQLite Research Card

`season` 결과:

- 경쟁사 실적 테이블
- 최신 공시명과 접수일
- 주요 재무지표
- QoQ, YoY, trend comment
- 특수 상황 공시 요약
- 선택적으로 IR 메모

## 저장된 결과 확인

```bash
dart-audit list
dart-audit show 1
dart-audit history --company "크래프톤"
dart-audit render 1
```

## 안전 규칙

항상 지켜야 한다.

- 매수/매도 추천 금지
- 목표주가 제시 금지
- 투자 수익 보장 금지
- fallback/demo 데이터를 live DART 데이터처럼 표현 금지
- 출처 없는 숫자나 공시명 생성 금지

모든 리포트에는 다음 disclaimer를 포함한다.

```text
본 자료는 투자 추천이 아니며, 매수/매도 권유, 목표주가 제시, 투자 수익 보장을 목적으로 하지 않습니다.
```

## 점수 해석

Story Verification Score는 투자 매력도가 아니라, 현재 접근 가능한 공시로 스토리가 얼마나 확인되는지를 의미한다.

- 80-100: 공시 근거가 강함
- 60-79: 방향성은 있으나 중요한 공백 존재
- 40-59: 근거가 혼재되거나 약함
- 0-39: 대부분 미확인, 반박, 또는 증거 부족
