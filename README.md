# Story-to-DART Auditor

실적 시즌에 반복되는 경쟁사 공시 확인, IR 자료 읽기, 숫자 정리, 특이사항 체크, 회의용 원페이퍼 작성을 Codex Skill로 줄이는 프로젝트입니다.

> [!IMPORTANT]
> 본 Skill 실행을 위해서는 DART API 발급이 필요합니다. [발급하기](#dart-api-키-발급)

Story-to-DART Auditor는 한국 기업의 최신 DART 정기공시를 기준으로 실적과 스토리를 함께 점검합니다. 단순 재무 요약기가 아니라, 사용자가 갖고 있는 시장 스토리나 경쟁사 벤치마킹 가설을 공시 근거로 검증하는 업무 보조 스킬입니다.

## 먼저 이것만 기억하면 됩니다

실무자는 명령 2개만 먼저 쓰면 됩니다.

```bash
# 1. 실적 시즌 경쟁사 테이블 업데이트
dart-audit season --companies "크래프톤,넷마블,엔씨소프트,카카오게임즈"

# 2. 특정 회사 원페이퍼 생성
dart-audit audit --company "크래프톤" --peers "넷마블,엔씨소프트,카카오게임즈"
```

`audit`이 기본 명령입니다. 회사명만 넣어도 실행되고, 스토리나 회의 목적을 더 넣으면 더 깊게 분석합니다.

`company` 명령도 있지만 필수로 외울 필요는 없습니다. `dart-audit company "크래프톤"`은 `audit --company "크래프톤"`을 짧게 쓴 단축 명령입니다.

`peers`는 별도 분석 모드가 아니라 비교군 옵션입니다. 분석 대상 회사와 비교할 회사를 쉼표로 넣으면 peer snapshot에 반영됩니다.

## Codex에서 이렇게 말하면 됩니다

CLI 명령을 직접 외우기 어렵다면 Codex에게 자연어로 요청하면 됩니다.

```text
크래프톤, 넷마블, 엔씨소프트, 카카오게임즈 최신 DART 공시로 경쟁사 실적 테이블 업데이트해줘.
```

```text
크래프톤이 글로벌 IP와 AI 전환으로 장기 성장성이 높다는 스토리를 DART 공시로 검증해서 HTML 원페이퍼와 DB 카드로 저장해줘.
```

```text
이번 분기 게임사 경쟁사 실적 비교표를 만들고, 특수 상황 공시가 있는지도 같이 체크해줘.
```

## 주요 사용 장면

- 실적 시즌 경쟁사 실적 정리
- 최신 분기/반기/사업보고서 기반 업데이트
- IR 자료와 DART 공시를 함께 본 회의용 요약
- 벤치마킹 기업의 특수 상황 확인
- 시장 테마나 성장 스토리의 공시 근거 점검
- 다음 분기에 다시 확인할 watchlist 저장

1차 사용자는 전략기획, 사업개발, 마케팅, PM, 리서처, 비개발 실무자입니다. 개인 투자자는 보조 사용 사례이며, 이 도구는 투자 추천을 하지 않습니다.

## 사용 흐름

### 1. 경쟁사 실적 테이블 만들기

실적 시즌에 가장 먼저 쓸 명령입니다.

```bash
export PATH="$PWD/bin:$PATH"

dart-audit season \
  --companies "크래프톤,넷마블,엔씨소프트,카카오게임즈" \
  --table outputs/tables/game-competitors.md
```

특정 분기 실적을 맞춰 보고 싶으면 `--period`를 사용합니다.

```bash
dart-audit season \
  --companies "크래프톤,넷마블,엔씨소프트,카카오게임즈" \
  --period 25.4Q \
  --table outputs/tables/game-competitors-25-4q.md
```

기본값은 분기 실적 기준입니다. DART 보고서의 누계 숫자를 그대로 보고 싶을 때만 `--basis cumulative`을 사용합니다.

```bash
dart-audit season \
  --companies "크래프톤,넷마블,엔씨소프트,카카오게임즈" \
  --period 25.4Q \
  --basis cumulative
```

하는 일:

- 회사명을 OpenDART `corp_code`로 매칭
- 최신 분기보고서, 반기보고서, 사업보고서 중 가장 최근 공시 선택
- `26.1Q`, `25.4Q`처럼 실적 기준 기간 표시
- `--period 25.4Q`처럼 특정 분기를 지정해 회사별 기준 기간 통일
- 매출, 영업이익, 영업이익률, 순이익, 자산 추출
- 매출과 영업이익의 QoQ, YoY 증감률 계산
- 추세 코멘트 자동 생성
- 정정, 주요사항보고, 지분 변동, 투자 결정 등 특수 상황 공시 탐지
- Markdown 또는 CSV 테이블 생성
- 같은 테이블 경로를 쓰면 다음 분기에도 이어서 업데이트

### 2. 회사명만 넣고 빠른 원페이퍼 만들기

스토리라인이 아직 없고, "이 회사 최근 어때?" 수준으로 볼 때 씁니다.

```bash
dart-audit audit \
  --company "크래프톤" \
  --peers "넷마블,엔씨소프트,카카오게임즈" \
  --industry game
```

같은 의미의 단축 명령:

```bash
dart-audit company "크래프톤" \
  --peers "넷마블,엔씨소프트,카카오게임즈" \
  --industry game
```

### 3. 스토리까지 넣고 검증하기

회의용 보고나 벤치마킹 분석처럼 맥락이 있을 때 씁니다.

```bash
dart-audit audit \
  --company "크래프톤" \
  --story "글로벌 IP와 AI 전환으로 장기 성장성이 높다는 주장" \
  --peers "넷마블,엔씨소프트,카카오게임즈" \
  --industry game \
  --purpose "전략기획 회의용 경쟁사 벤치마킹" \
  --output html,db
```

결과에는 다음 항목이 포함됩니다.

- 스토리 검증 점수(Story Verification Score)
- 사실(Fact) / 추론(Inference) / 스토리(Story) / 근거 부족(Missing Evidence) / 반박됨(Contradicted) 분류
- 비교군 스냅샷(Peer Snapshot)
- 위험 신호(Red Flags)
- 다음 공시 확인 목록(Next Filing Watchlist)
- 30초 보고 스크립트
- HTML 원페이퍼
- SQLite Research Card

### 4. IR 자료를 같이 읽히기

로컬에 IR 자료나 메모가 있으면 보조 근거로 넣을 수 있습니다.

```bash
dart-audit audit \
  --company "크래프톤" \
  --story "신작과 글로벌 IP 확장으로 성장성이 개선되고 있다는 주장" \
  --peers "넷마블,엔씨소프트,카카오게임즈" \
  --ir-file sample-ir-note.md \
  --output html,db
```

지원 형식은 PDF, txt, md, HTML 계열 텍스트입니다.

## 설치와 데모

```bash
git clone https://github.com/koobch/story-to-dart-auditor.git
cd story-to-dart-auditor
python3 -m pip install -r requirements.txt
export PATH="$PWD/bin:$PATH"
export DART_API_KEY="your-opendart-api-key"
```

## DART API 키 발급

실제 DART 공시를 조회하려면 OpenDART API 인증키가 필요합니다. 이 키는 레포에 포함되어 있지 않으며, 사용자별로 직접 발급받아야 합니다.

발급 절차:

1. OpenDART 사이트에 접속합니다: https://opendart.fss.or.kr
2. 회원가입 또는 로그인을 진행합니다.
3. 상단 메뉴에서 `인증키 신청/관리`로 이동합니다.
4. `인증키 신청`에서 오픈API 이용약관에 동의하고 신청을 완료합니다.
5. 신청 결과는 등록한 이메일로 발송됩니다.
6. 발급된 API Key를 복사해 로컬 환경변수로 설정합니다.

macOS 또는 Linux:

```bash
export DART_API_KEY="발급받은_API_KEY"
```

또는 프로젝트 루트에 `.env` 파일을 만들고 다음처럼 저장해도 됩니다.

```env
DART_API_KEY=발급받은_API_KEY
```

Windows PowerShell:

```powershell
$env:DART_API_KEY="발급받은_API_KEY"
```

설정 확인:

```bash
echo $DART_API_KEY
```

주의사항:

- 키가 없거나 현장 네트워크가 불안정한 경우 `--force-fallback`으로 데모를 실행할 수 있습니다.
- 이 프로젝트는 OpenDART API의 `crtfc_key` 파라미터에 `DART_API_KEY` 값을 넣어 호출합니다.

가장 빠른 라이브 데모:

```bash
dart-audit season \
  --companies "크래프톤,넷마블,엔씨소프트,카카오게임즈" \
  --table outputs/tables/game-competitors.md
```

DART API가 없거나 현장 네트워크가 불안정하면 fallback으로 데모를 돌릴 수 있습니다.

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

## 저장된 결과 확인

```bash
# 저장된 Research Card 목록
dart-audit list

# 특정 카드 상세 보기
dart-audit show 1

# 회사명 또는 스토리 키워드로 이력 보기
dart-audit history --company "크래프톤"

# 기존 카드를 HTML로 다시 렌더링
dart-audit render 1
```

## 결과물이 저장되는 위치

- `outputs/tables/`: 경쟁사 실적 테이블
- `outputs/reports/`: HTML 원페이퍼
- `data/research_cards.sqlite`: 누적 Research Card DB
- `skills/story-to-dart-auditor/`: Codex Skill 본체

경쟁사 실적 테이블에는 `period`, `basis`, `revenue_qoq`, `revenue_yoy`, `op_qoq`, `op_yoy`, `trend_comment`가 포함됩니다. 기본값인 `--basis quarter`에서는 1Q~3Q는 DART의 해당 분기 값을 사용하고, 4Q는 사업보고서 연간 값에서 3Q 누계를 차감해 계산합니다.

생성 결과물과 DART 캐시는 git에 올리지 않도록 제외되어 있습니다.

## 개선하고자 한 업무 문제

이 프로젝트는 "AI가 분석해줍니다"가 아니라, 실제 실무자가 매 분기 반복하는 워크플로우를 Codex Skill로 바꾼 사례입니다.

기존 업무:

```text
DART 접속 -> 회사 검색 -> 최신 정기공시 확인 -> 숫자 복사 -> 특수 상황 확인 -> IR 자료 읽기 -> 경쟁사 비교 -> 회의용 요약 작성 -> 다음 분기에 다시 반복
```

Skill 적용 후:

```text
회사 목록 입력 -> 최신 공시 자동 수집 -> 실적 테이블 생성 -> 스토리 검증 -> 원페이퍼 저장 -> 다음 분기 이력 연결
```

차별점은 세 가지입니다.

- 기업을 단순 요약하지 않고, "좋아지고 있다는 주장"을 검증 가능한 claim으로 쪼갭니다.
- 사실(Fact), 추론(Inference), 스토리(Story), 근거 부족(Missing Evidence), 반박됨(Contradicted)을 분리해 과장된 해석을 줄입니다.
- 결과를 HTML과 SQLite DB로 남겨 다음 분기에도 이어서 추적합니다.
