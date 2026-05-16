#!/usr/bin/env python3
"""Story-to-DART Auditor CLI.

Skillathon 제출용 DART 공시 기반 스토리 검증 도구.
"""

from __future__ import annotations

import json
import os
import re
import csv
import sqlite3
import urllib.parse
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree

import typer
from jinja2 import Template
from rich.console import Console
from rich.table import Table


app = typer.Typer(help="한국 기업의 최신 DART 공시로 실적, 경쟁사, 시장 스토리를 검증합니다.")
console = Console()

SKILL_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = SKILL_DIR.parents[1]
DEFAULT_DB = PROJECT_DIR / "data" / "research_cards.sqlite"
DEFAULT_REPORT_DIR = PROJECT_DIR / "outputs" / "reports"
DEFAULT_TABLE_DIR = PROJECT_DIR / "outputs" / "tables"
DEFAULT_CACHE_DIR = PROJECT_DIR / "data" / "cache"
TEMPLATE_PATH = SKILL_DIR / "assets" / "one_pager_template.html"
DISCLAIMER = "본 자료는 투자 추천이 아니며, 매수/매도 권유, 목표주가 제시, 투자 수익 보장을 목적으로 하지 않습니다."
OPENDART_BASE = "https://opendart.fss.or.kr/api"
COMPANY_ALIASES = {
    "엔씨소프트": "NC",
    "엔씨": "NC",
    "NC소프트": "NC",
}


FIXTURE = {
    "크래프톤": {
        "signals": {
            "global": "PUBG/Battlegrounds 기반 글로벌 IP 매출 의존도가 높고 해외 이용자 기반이 크다는 공시형 서술이 반복된다.",
            "ai": "AI 및 딥러닝 기반 제작 효율화, NPC/게임 제작 기술 고도화를 장기 R&D 방향으로 제시한다.",
            "growth": "장기 성장성은 글로벌 IP 확장과 신작 성과에 의존하므로 공시만으로 확정할 수 없다.",
        },
        "evidence": [
            {"id": "E01", "topic": "global", "text": "글로벌 IP 기반 매출과 해외 시장 노출이 핵심 사업 설명에 포함됨.", "level": "Fact"},
            {"id": "E02", "topic": "ai", "text": "AI/딥러닝 연구개발 방향이 사업 전략 문맥에서 언급됨.", "level": "Fact"},
            {"id": "E03", "topic": "growth", "text": "장기 성장성은 미래 신작 성과와 시장 반응에 따라 달라지는 추론 영역.", "level": "Inference"},
        ],
    },
    "넷마블": {
        "snapshot": "다수 IP와 모바일 포트폴리오 중심. 자체 IP와 라이선스 IP 혼재.",
        "story_signal": "IP 포트폴리오 다각화",
        "evidence_level": "Fixture",
    },
    "엔씨소프트": {
        "snapshot": "MMORPG 중심 레거시 IP 비중이 높고 장르 전환 과제가 존재.",
        "story_signal": "IP 재활성화와 장르 확장",
        "evidence_level": "Fixture",
    },
    "카카오게임즈": {
        "snapshot": "퍼블리싱과 투자 포트폴리오 성격이 강하며 자체 개발사와 연결된 구조.",
        "story_signal": "퍼블리싱/투자 포트폴리오",
        "evidence_level": "Fixture",
    },
}


@dataclass
class Finding:
    claim: str
    classification: str
    evidence: str
    rationale: str

    @property
    def class_css(self) -> str:
        return self.classification.replace(" ", "-")


class DartApiError(RuntimeError):
    """OpenDART API 호출 실패."""


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z가-힣_-]+", "-", text).strip("-")
    return cleaned[:60] or "audit"


def split_peers(peers: str) -> list[str]:
    return [p.strip() for p in peers.split(",") if p.strip()]


def http_get_bytes(path: str, params: dict[str, object], timeout: int = 20) -> bytes:
    query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    url = f"{OPENDART_BASE}/{path}?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "Story-to-DART-Auditor/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def http_get_json(path: str, params: dict[str, object]) -> dict[str, object]:
    raw = http_get_bytes(path, params)
    data = json.loads(raw.decode("utf-8"))
    status = str(data.get("status", "000"))
    if status not in {"000", "013"}:
        raise DartApiError(f"OpenDART {path} failed: {status} {data.get('message')}")
    return data


def parse_amount(value: object) -> Optional[int]:
    if value is None:
        return None
    text = str(value).replace(",", "").strip()
    if not text or text in {"-", "null"}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def format_krw(value: Optional[int]) -> str:
    if value is None:
        return "미확인"
    billion = value / 100_000_000
    if abs(billion) >= 1:
        return f"{billion:,.0f}억원"
    return f"{value:,}원"


def load_corp_codes(api_key: str, cache_dir: Path = DEFAULT_CACHE_DIR) -> list[dict[str, str]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "corp_codes.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    raw = http_get_bytes("corpCode.xml", {"crtfc_key": api_key})
    with zipfile.ZipFile(BytesIO(raw)) as zf:
        xml_name = zf.namelist()[0]
        xml_raw = zf.read(xml_name)
    root = ElementTree.fromstring(xml_raw)
    rows: list[dict[str, str]] = []
    for item in root.findall("list"):
        row = {child.tag: (child.text or "").strip() for child in item}
        rows.append(row)
    cache_path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows


def resolve_corp(company: str, api_key: str) -> dict[str, str]:
    rows = load_corp_codes(api_key)
    lookup = COMPANY_ALIASES.get(company, company)
    exact = [r for r in rows if r.get("corp_name") == lookup]
    if not exact:
        compact = lookup.replace(" ", "")
        exact = [r for r in rows if r.get("corp_name", "").replace(" ", "") == compact]
    if not exact:
        exact = [r for r in rows if lookup in r.get("corp_name", "")]
    if not exact:
        raise DartApiError(f"회사명을 corp_code로 찾지 못했습니다: {company}")
    exact.sort(key=lambda r: (0 if r.get("stock_code") else 1, len(r.get("corp_name", ""))))
    return exact[0]


def fetch_filings(corp_code: str, api_key: str, years_back: int = 2) -> list[dict[str, str]]:
    today = datetime.now()
    bgn_de = f"{today.year - years_back}0101"
    end_de = today.strftime("%Y%m%d")
    data = http_get_json(
        "list.json",
        {
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bgn_de": bgn_de,
            "end_de": end_de,
            "pblntf_ty": "A",
            "page_no": 1,
            "page_count": 20,
        },
    )
    return list(data.get("list") or [])


def fetch_recent_disclosures(corp_code: str, api_key: str, years_back: int = 1, page_count: int = 30) -> list[dict[str, str]]:
    today = datetime.now()
    bgn_de = f"{today.year - years_back}0101"
    end_de = today.strftime("%Y%m%d")
    data = http_get_json(
        "list.json",
        {
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bgn_de": bgn_de,
            "end_de": end_de,
            "page_no": 1,
            "page_count": page_count,
        },
    )
    return list(data.get("list") or [])


def report_code_from_name(report_name: str) -> Optional[str]:
    parsed = report_year_month_from_name(report_name)
    if parsed:
        _, month = parsed
        if month == 3:
            return "11013"
        if month == 6:
            return "11012"
        if month == 9:
            return "11014"
        if month == 12:
            return "11011"
    if "사업보고서" in report_name:
        return "11011"
    if "반기보고서" in report_name:
        return "11012"
    if "3분기보고서" in report_name:
        return "11014"
    if "분기보고서" in report_name:
        return "11013"
    return None


def report_year_month_from_name(report_name: str) -> Optional[tuple[int, int]]:
    period_match = re.search(r"\((\d{4})\.(\d{2})\)", report_name)
    if not period_match:
        return None
    return int(period_match.group(1)), int(period_match.group(2))


def business_year_from_filing(filing: dict[str, str]) -> int:
    report_name = filing.get("report_nm", "")
    parsed = report_year_month_from_name(report_name)
    if parsed:
        return parsed[0]
    rcept_year = int((filing.get("rcept_dt") or str(datetime.now().year))[:4])
    if "사업보고서" in report_name:
        return rcept_year - 1
    return rcept_year


def fetch_financials_for_period(corp_code: str, api_key: str, fs_div: str, year: int, report_code: str, report_name: str) -> dict[str, object]:
    data = http_get_json(
        "fnlttSinglAcnt.json",
        {
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bsns_year": year,
            "reprt_code": report_code,
            "fs_div": fs_div,
        },
    )
    rows = list(data.get("list") or [])
    return {"year": year, "report_code": report_code, "report_name": report_name, "rows": rows, "fs_div": fs_div}


def fetch_latest_financials(corp_code: str, api_key: str, fs_div: str, filings: Optional[list[dict[str, str]]] = None) -> dict[str, object]:
    periodic = filings or fetch_filings(corp_code, api_key)
    for filing in periodic:
        report_name = filing.get("report_nm", "")
        report_code = report_code_from_name(report_name)
        if not report_code:
            continue
        year = business_year_from_filing(filing)
        financials = fetch_financials_for_period(corp_code, api_key, fs_div, year, report_code, report_name)
        if financials.get("rows"):
            financials["source_filing"] = filing
            return financials
    return fetch_financials_annual_first(corp_code, api_key, fs_div)


def fetch_financials_annual_first(corp_code: str, api_key: str, fs_div: str) -> dict[str, object]:
    current_year = datetime.now().year
    for year in range(current_year, current_year - 6, -1):
        if year == current_year:
            report_order = [("11013", "1분기보고서")]
        else:
            report_order = [("11011", "사업보고서"), ("11014", "3분기보고서"), ("11012", "반기보고서"), ("11013", "1분기보고서")]
        for report_code, report_name in report_order:
            data = http_get_json(
                "fnlttSinglAcnt.json",
                {
                    "crtfc_key": api_key,
                    "corp_code": corp_code,
                    "bsns_year": year,
                    "reprt_code": report_code,
                    "fs_div": fs_div,
                },
            )
            rows = list(data.get("list") or [])
            if rows:
                return {"year": year, "report_code": report_code, "report_name": report_name, "rows": rows, "fs_div": fs_div}
    return {"year": None, "report_code": None, "report_name": "미확인", "rows": [], "fs_div": fs_div}


def account_value(rows: list[dict[str, object]], names: list[str], amount_field: str = "thstrm_amount") -> Optional[int]:
    for row in rows:
        account = str(row.get("account_nm", ""))
        if any(name in account for name in names):
            value = parse_amount(row.get(amount_field))
            if value is None and amount_field != "thstrm_amount":
                value = parse_amount(row.get("thstrm_amount"))
            if value is not None:
                return value
    return None


def extract_metric_values(financials: dict[str, object], amount_field: str = "thstrm_amount") -> dict[str, Optional[int]]:
    rows = list(financials.get("rows") or [])
    return {
        "revenue": account_value(rows, ["매출액", "영업수익", "수익(매출액)"], amount_field),
        "operating_profit": account_value(rows, ["영업이익"], amount_field),
        "net_income": account_value(rows, ["당기순이익", "분기순이익", "반기순이익"], amount_field),
        "assets": account_value(rows, ["자산총계"]),
    }


def financial_summary(financials: dict[str, object]) -> dict[str, str]:
    metrics = extract_metric_values(financials)
    revenue = metrics["revenue"]
    op = metrics["operating_profit"]
    net = metrics["net_income"]
    assets = metrics["assets"]
    margin = "미확인"
    if revenue and op is not None:
        margin = f"{op / revenue * 100:.1f}%"
    return {
        "period": f"{financials.get('year') or '미확인'} {financials.get('report_name')}",
        "fs_div": str(financials.get("fs_div") or "CFS"),
        "revenue": format_krw(revenue),
        "operating_profit": format_krw(op),
        "net_income": format_krw(net),
        "assets": format_krw(assets),
        "op_margin": margin,
    }


REPORT_CODE_BY_QUARTER = {
    1: "11013",
    2: "11012",
    3: "11014",
    4: "11011",
}


def quarter_from_report(financials: dict[str, object]) -> Optional[int]:
    report_name = str(financials.get("report_name") or "")
    parsed = report_year_month_from_name(report_name)
    if parsed:
        month = parsed[1]
        return {3: 1, 6: 2, 9: 3, 12: 4}.get(month)
    code = str(financials.get("report_code") or "")
    return {"11013": 1, "11012": 2, "11014": 3, "11011": 4}.get(code)


def period_label(year: Optional[int], quarter: Optional[int]) -> str:
    if not year or not quarter:
        return "미확인"
    return f"{str(year)[-2:]}.{quarter}Q"


def parse_period_option(value: Optional[str]) -> Optional[tuple[int, int]]:
    if not value:
        return None
    normalized = value.strip().upper().replace(" ", "")
    match = re.fullmatch(r"(\d{2}|\d{4})[.\-]?Q?([1-4])Q?", normalized)
    if not match:
        raise typer.BadParameter("--period 형식은 26.1Q, 2026Q1, 2026.1Q 중 하나로 입력하세요.")
    year = int(match.group(1))
    if year < 100:
        year += 2000
    quarter = int(match.group(2))
    return year, quarter


def previous_quarter(year: int, quarter: int) -> tuple[int, int]:
    if quarter == 1:
        return year - 1, 4
    return year, quarter - 1


def subtract_metric_values(current: dict[str, Optional[int]], prior: dict[str, Optional[int]]) -> dict[str, Optional[int]]:
    result: dict[str, Optional[int]] = {}
    for key in ["revenue", "operating_profit", "net_income"]:
        cur = current.get(key)
        prev = prior.get(key)
        result[key] = cur - prev if cur is not None and prev is not None else None
    result["assets"] = current.get("assets")
    return result


def fetch_cumulative_metrics(corp_code: str, api_key: str, fs_div: str, year: int, quarter: int) -> Optional[dict[str, Optional[int]]]:
    code = REPORT_CODE_BY_QUARTER[quarter]
    report_name = {1: "1분기보고서", 2: "반기보고서", 3: "3분기보고서", 4: "사업보고서"}[quarter]
    financials = fetch_financials_for_period(corp_code, api_key, fs_div, year, code, report_name)
    if not financials.get("rows"):
        return None
    amount_field = "thstrm_add_amount" if quarter in {2, 3} else "thstrm_amount"
    return extract_metric_values(financials, amount_field=amount_field)


def fetch_quarter_metrics(corp_code: str, api_key: str, fs_div: str, year: int, quarter: int) -> Optional[dict[str, Optional[int]]]:
    code = REPORT_CODE_BY_QUARTER[quarter]
    report_name = {1: "1분기보고서", 2: "반기보고서", 3: "3분기보고서", 4: "사업보고서"}[quarter]
    financials = fetch_financials_for_period(corp_code, api_key, fs_div, year, code, report_name)
    if not financials.get("rows"):
        return None
    if quarter in {1, 2, 3}:
        return extract_metric_values(financials)
    annual = extract_metric_values(financials)
    q3_cumulative = fetch_cumulative_metrics(corp_code, api_key, fs_div, year, 3)
    if not q3_cumulative:
        return annual
    return subtract_metric_values(annual, q3_cumulative)


def find_filing_for_period(filings: list[dict[str, str]], year: int, quarter: int) -> Optional[dict[str, str]]:
    target_month = {1: 3, 2: 6, 3: 9, 4: 12}[quarter]
    for filing in filings:
        parsed = report_year_month_from_name(filing.get("report_nm", ""))
        if parsed == (year, target_month):
            return filing
    return None


def fetch_financials_for_quarter(corp_code: str, api_key: str, fs_div: str, year: int, quarter: int) -> dict[str, object]:
    code = REPORT_CODE_BY_QUARTER[quarter]
    report_name = {1: "1분기보고서", 2: "반기보고서", 3: "3분기보고서", 4: "사업보고서"}[quarter]
    financials = fetch_financials_for_period(corp_code, api_key, fs_div, year, code, report_name)
    financials["year"] = year
    financials["report_code"] = code
    financials["report_name"] = f"{report_name} ({year}.{quarter * 3:02d})"
    return financials


def pct_change(current: Optional[int], prior: Optional[int]) -> str:
    if current is None or prior is None:
        return "미확인"
    if prior == 0:
        return "n/a"
    return f"{(current - prior) / abs(prior) * 100:+.1f}%"


def margin_from_values(revenue: Optional[int], op: Optional[int]) -> str:
    if not revenue or op is None:
        return "미확인"
    return f"{op / revenue * 100:.1f}%"


def trend_comment(period: str, metrics: dict[str, Optional[int]], qoq: dict[str, str], yoy: dict[str, str], basis: str) -> str:
    revenue_qoq = qoq.get("revenue", "미확인")
    revenue_yoy = yoy.get("revenue", "미확인")
    op_qoq = qoq.get("operating_profit", "미확인")
    op_yoy = yoy.get("operating_profit", "미확인")
    basis_label = "분기 실적" if basis == "quarter" else "누계 실적"
    if basis == "cumulative":
        return f"{period} {basis_label} 기준. 매출 YoY {revenue_yoy}; 영업이익 YoY {op_yoy}. QoQ는 누계 기준이라 해석 제외."
    if "미확인" in {revenue_qoq, revenue_yoy, op_qoq, op_yoy}:
        return f"{period} 기준 추세 일부 미확인. DART 단일회사 주요계정 제공 범위 확인 필요."
    op = metrics.get("operating_profit")
    if op is not None and op < 0:
        return f"{period} {basis_label} 영업손실 구간. 매출 QoQ {revenue_qoq}, YoY {revenue_yoy}; 영업이익 QoQ {op_qoq}, YoY {op_yoy}."
    return f"{period} {basis_label} 기준. 매출 QoQ {revenue_qoq}, YoY {revenue_yoy}; 영업이익 QoQ {op_qoq}, YoY {op_yoy}."


def build_period_trend(corp_code: str, api_key: str, fs_div: str, financials: dict[str, object], basis: str) -> dict[str, str]:
    year_value = financials.get("year")
    quarter = quarter_from_report(financials)
    if not isinstance(year_value, int) or quarter is None:
        return {
            "period": "미확인",
            "revenue_qoq": "미확인",
            "revenue_yoy": "미확인",
            "op_qoq": "미확인",
            "op_yoy": "미확인",
            "trend_comment": "실적 기준 기간을 확인하지 못했습니다.",
        }
    if basis == "cumulative":
        current = fetch_cumulative_metrics(corp_code, api_key, fs_div, year_value, quarter) or extract_metric_values(financials)
        prior_q = None
        prior_y = fetch_cumulative_metrics(corp_code, api_key, fs_div, year_value - 1, quarter)
    else:
        current = fetch_quarter_metrics(corp_code, api_key, fs_div, year_value, quarter) or extract_metric_values(financials)
        prev_year, prev_quarter = previous_quarter(year_value, quarter)
        prior_q = fetch_quarter_metrics(corp_code, api_key, fs_div, prev_year, prev_quarter)
        prior_y = fetch_quarter_metrics(corp_code, api_key, fs_div, year_value - 1, quarter)
    qoq = {
        "revenue": pct_change(current.get("revenue"), prior_q.get("revenue") if prior_q else None),
        "operating_profit": pct_change(current.get("operating_profit"), prior_q.get("operating_profit") if prior_q else None),
    }
    yoy = {
        "revenue": pct_change(current.get("revenue"), prior_y.get("revenue") if prior_y else None),
        "operating_profit": pct_change(current.get("operating_profit"), prior_y.get("operating_profit") if prior_y else None),
    }
    period = period_label(year_value, quarter)
    return {
        "period": period,
        "revenue": format_krw(current.get("revenue")),
        "operating_profit": format_krw(current.get("operating_profit")),
        "op_margin": margin_from_values(current.get("revenue"), current.get("operating_profit")),
        "net_income": format_krw(current.get("net_income")),
        "revenue_qoq": qoq["revenue"],
        "revenue_yoy": yoy["revenue"],
        "op_qoq": qoq["operating_profit"],
        "op_yoy": yoy["operating_profit"],
        "trend_comment": trend_comment(period, current, qoq, yoy, basis),
    }


def fetch_document_text(rcept_no: str, api_key: str) -> str:
    raw = http_get_bytes("document.xml", {"crtfc_key": api_key, "rcept_no": rcept_no}, timeout=30)
    with zipfile.ZipFile(BytesIO(raw)) as zf:
        chunks = []
        for name in zf.namelist():
            try:
                data = zf.read(name).decode("utf-8", errors="ignore")
            except UnicodeDecodeError:
                data = zf.read(name).decode("euc-kr", errors="ignore")
            chunks.append(data)
    text = re.sub(r"<[^>]+>", " ", "\n".join(chunks))
    return re.sub(r"\s+", " ", text)


def pick_business_report(filings: list[dict[str, str]]) -> Optional[dict[str, str]]:
    for filing in filings:
        name = filing.get("report_nm", "")
        if "사업보고서" in name:
            return filing
    return filings[0] if filings else None


def snippet_for_terms(text: str, terms: list[str], width: int = 90) -> Optional[str]:
    lower_text = text.lower()
    for term in terms:
        idx = lower_text.find(term.lower())
        if idx >= 0:
            start = max(0, idx - width // 2)
            end = min(len(text), idx + width)
            return text[start:end].strip()
    return None


def read_ir_file(path: Path) -> dict[str, object]:
    """IR 자료 텍스트를 읽고 스토리 검증용 보조 스니펫을 만든다."""
    if not path.exists():
        raise typer.BadParameter(f"IR file not found: {path}")
    text = ""
    if path.suffix.lower() == ".pdf":
        try:
            import PyPDF2  # type: ignore

            reader = PyPDF2.PdfReader(str(path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise typer.BadParameter(f"PDF IR extraction failed: {exc}") from exc
    else:
        text = path.read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"\s+", " ", text)
    term_map = {
        "global": ["글로벌", "해외", "북미", "유럽", "PUBG", "배틀그라운드", "IP"],
        "ai": ["AI", "인공지능", "딥러닝", "머신러닝", "자동화"],
        "growth": ["성장", "신작", "매출", "영업이익"],
    }
    snippets = {key: snippet for key, terms in term_map.items() if (snippet := snippet_for_terms(text, terms))}
    return {"path": str(path), "snippets": snippets}


def decompose_story(story: str) -> list[str]:
    claims: list[str] = []
    if any(k in story for k in ["글로벌", "해외", "IP"]):
        claims.append("글로벌 IP가 성장 스토리의 핵심 근거다")
    if any(k in story for k in ["AI", "인공지능", "자동화"]):
        claims.append("AI 전환이 사업 경쟁력과 제작 효율을 높인다")
    if any(k in story for k in ["장기", "성장"]):
        claims.append("장기 성장성이 높다")
    if not claims:
        claims.append(story)
    return claims


def classify_claim(company: str, claim: str, live_evidence: Optional[dict[str, object]] = None) -> Finding:
    if live_evidence:
        snippets = dict(live_evidence.get("snippets") or {})
        ir_snippets = dict(live_evidence.get("ir_snippets") or {})
        finance = dict(live_evidence.get("financial_summary") or {})
        filing_label = str(live_evidence.get("filing_label") or "DART 공시")
        if ("글로벌" in claim or "IP" in claim) and snippets.get("global"):
            return Finding(
                claim,
                "Fact",
                f"{filing_label}: {snippets['global']}",
                "DART 사업보고서 본문에서 글로벌/IP 관련 서술을 직접 확인했다.",
            )
        if "AI" in claim and snippets.get("ai"):
            return Finding(
                claim,
                "Fact",
                f"{filing_label}: {snippets['ai']}",
                "DART 사업보고서 본문에서 AI/R&D 관련 서술을 직접 확인했다.",
            )
        if ("글로벌" in claim or "IP" in claim) and ir_snippets.get("global"):
            return Finding(
                claim,
                "Fact",
                f"IR 자료: {ir_snippets['global']}",
                "IR 자료에서 글로벌/IP 관련 서술을 확인했다. DART 공시와 함께 보는 보조 evidence다.",
            )
        if "AI" in claim and ir_snippets.get("ai"):
            return Finding(
                claim,
                "Fact",
                f"IR 자료: {ir_snippets['ai']}",
                "IR 자료에서 AI 관련 서술을 확인했다. DART 공시와 함께 보는 보조 evidence다.",
            )
        if "성장" in claim:
            revenue = finance.get("revenue", "미확인")
            op_margin = finance.get("op_margin", "미확인")
            if revenue != "미확인" or op_margin != "미확인":
                return Finding(
                    claim,
                    "Inference",
                    f"DART 재무 snapshot: 매출 {revenue}, 영업이익률 {op_margin}",
                    "성장성은 공시 재무와 전략 서술에서 도출되는 추론이며, 미래 성과 자체는 공시로 확정할 수 없다.",
                )
            return Finding(
                claim,
                "Missing Evidence",
                "DART 재무 snapshot에서 성장성 판단에 필요한 매출/수익성 지표를 확보하지 못했다.",
                "장기 성장성은 직접 fact가 아니므로 추가 evidence가 필요하다.",
            )

    company_data = FIXTURE.get(company, {})
    evidence = company_data.get("evidence", [])

    if "글로벌" in claim or "IP" in claim:
        item = next((e for e in evidence if e["topic"] == "global"), None)
        if item:
            return Finding(claim, "Fact", f"{item['id']}: {item['text']}", "공시형 fixture evidence가 claim의 핵심어를 직접 지지한다.")
    if "AI" in claim:
        item = next((e for e in evidence if e["topic"] == "ai"), None)
        if item:
            return Finding(claim, "Fact", f"{item['id']}: {item['text']}", "AI 전환 자체는 전략/R&D 방향으로 확인된다.")
    if "성장" in claim:
        item = next((e for e in evidence if e["topic"] == "growth"), None)
        if item:
            return Finding(claim, "Inference", f"{item['id']}: {item['text']}", "장기 성장성은 확인된 전략 방향에서 파생되는 추론이며 확정 fact가 아니다.")
    return Finding(claim, "Missing Evidence", "No matching fixture or DART evidence", "현재 evidence set에서 직접 검증할 수 없다.")


def score_findings(findings: list[Finding], peer_count: int) -> tuple[int, str, list[dict[str, object]]]:
    score = 40
    breakdown: list[dict[str, object]] = [{"component": "Base", "points": 40, "rationale": "중립 기준점"}]
    weights = {"Fact": 10, "Inference": 5, "Story": 0, "Missing Evidence": -12, "Contradicted": -20}
    for finding in findings:
        points = weights.get(finding.classification, 0)
        score += points
        breakdown.append({"component": finding.classification, "points": points, "rationale": finding.claim})
    if peer_count >= 3:
        score += 8
        breakdown.append({"component": "Peer Coverage", "points": 8, "rationale": "비교군 3개 이상 제공"})
    score += 6
    breakdown.append({"component": "Audit Completeness", "points": 6, "rationale": "red flags와 watchlist 포함"})
    score = max(0, min(100, score))
    if score >= 80:
        verdict = "Strongly evidenced"
    elif score >= 60:
        verdict = "Directionally supported"
    elif score >= 40:
        verdict = "Mixed evidence"
    else:
        verdict = "Weakly supported"
    return score, verdict, breakdown


def build_peer_snapshot(peer_names: list[str], api_key: Optional[str] = None, fs_div: str = "CFS") -> list[dict[str, str]]:
    rows = []
    for peer in peer_names:
        if api_key:
            try:
                corp = resolve_corp(peer, api_key)
                filings = fetch_filings(corp["corp_code"], api_key)
                financials = fetch_latest_financials(corp["corp_code"], api_key, fs_div, filings)
                summary = financial_summary(financials)
                rows.append(
                    {
                        "company": peer,
                        "disclosure_signal": f"{summary['period']} {summary['fs_div']} / 매출 {summary['revenue']} / 영업이익률 {summary['op_margin']}",
                        "story_signal": "DART live financial snapshot",
                        "evidence_level": "DART Live",
                    }
                )
                continue
            except Exception as exc:
                data = FIXTURE.get(peer, {})
                rows.append(
                    {
                        "company": peer,
                        "disclosure_signal": data.get("snapshot", f"DART 조회 실패: {exc}"),
                        "story_signal": data.get("story_signal", "Missing Evidence"),
                        "evidence_level": "Fallback after DART failure",
                    }
                )
                continue
        data = FIXTURE.get(peer, {})
        rows.append(
            {
                "company": peer,
                "disclosure_signal": data.get("snapshot", "fixture evidence 없음"),
                "story_signal": data.get("story_signal", "Missing Evidence"),
                "evidence_level": data.get("evidence_level", "Missing Evidence"),
            }
        )
    return rows


def collect_live_evidence(company: str, api_key: str, fs_div: str) -> dict[str, object]:
    corp = resolve_corp(company, api_key)
    filings = fetch_filings(corp["corp_code"], api_key)
    financials = fetch_latest_financials(corp["corp_code"], api_key, fs_div, filings)
    summary = financial_summary(financials)
    selected = pick_business_report(filings)
    snippets: dict[str, str] = {}
    document_error = None
    if selected and selected.get("rcept_no"):
        try:
            text = fetch_document_text(selected["rcept_no"], api_key)
            term_map = {
                "global": ["글로벌", "해외", "북미", "유럽", "PUBG", "배틀그라운드", "IP"],
                "ai": ["AI", "인공지능", "딥러닝", "머신러닝", "자동화"],
                "growth": ["성장", "신작", "매출", "영업이익"],
            }
            for key, terms in term_map.items():
                snippet = snippet_for_terms(text, terms)
                if snippet:
                    snippets[key] = snippet
        except Exception as exc:
            document_error = str(exc)
    filing_label = "DART 공시"
    if selected:
        filing_label = f"DART {selected.get('report_nm', '정기공시')} {selected.get('rcept_dt', '')} rcept_no={selected.get('rcept_no', '')}"
    return {
        "corp": corp,
        "filings": filings[:8],
        "financials": financials,
        "financial_summary": summary,
        "selected_filing": selected,
        "filing_label": filing_label,
        "snippets": snippets,
        "document_error": document_error,
    }


def build_result(
    company: str,
    story: str,
    peers: str,
    industry: str,
    purpose: str,
    mode: str,
    live_evidence: Optional[dict[str, object]] = None,
    api_key: Optional[str] = None,
    fs_div: str = "CFS",
) -> dict[str, object]:
    peer_names = split_peers(peers)
    claims = decompose_story(story)
    findings = [classify_claim(company, claim, live_evidence) for claim in claims]
    score, verdict, breakdown = score_findings(findings, len(peer_names))
    live_note = "live DART 조회 결과 기준" if live_evidence else "fixture mode 결과"
    red_flags = [
        "장기 성장성은 공시 데이터만으로 확정할 수 없으며 신작 성과, 지역별 매출, 비용 구조 확인이 필요하다.",
        "AI 전환은 전략 방향 fact일 수 있으나 재무성과 기여도는 별도 evidence가 필요하다.",
        f"{live_note}이며, IR 자료/컨퍼런스콜/세부 주석은 별도 확인하면 정확도가 올라간다.",
    ]
    if live_evidence and live_evidence.get("document_error"):
        red_flags.append(f"사업보고서 원문 스니펫 일부 조회 실패: {live_evidence['document_error']}")
    watchlist = [
        "다음 사업보고서: 지역별 매출, 주요 IP 매출 의존도, R&D/AI 관련 투자 서술 변화",
        "분기보고서: 신작 출시 전후 매출 성장률과 영업비용 변동",
        "주석: 무형자산, 개발비, 지급수수료, 라이선스 관련 계정 변화",
    ]
    script = (
        f"{company}의 '{story}' 스토리는 현재 evidence 기준 {score}점으로 {verdict}입니다. "
        "글로벌 IP와 AI 전환 자체는 확인 가능한 근거가 있으나, 장기 성장성은 미래 성과에 대한 추론이므로 "
        "다음 공시에서 매출 지역, 신작 효과, R&D 비용 변화를 추가 확인해야 합니다."
    )
    return {
        "company": company,
        "story": story,
        "peers_input": peers,
        "industry": industry,
        "purpose": purpose,
        "mode": mode,
        "generated_at": now_iso(),
        "score": score,
        "verdict": verdict,
        "score_breakdown": breakdown,
        "findings": [asdict(f) | {"class_css": f.class_css} for f in findings],
        "peers": build_peer_snapshot(peer_names, api_key=api_key, fs_div=fs_div),
        "dart_company": live_evidence.get("corp") if live_evidence else None,
        "recent_filings": live_evidence.get("filings", []) if live_evidence else [],
        "financial_summary": live_evidence.get("financial_summary") if live_evidence else None,
        "ir_file": live_evidence.get("ir_file") if live_evidence else None,
        "ir_snippets": live_evidence.get("ir_snippets", {}) if live_evidence else {},
        "red_flags": red_flags,
        "watchlist": watchlist,
        "script_30s": script,
        "disclaimer": DISCLAIMER,
    }


def ensure_schema(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            create table if not exists research_cards (
              id integer primary key autoincrement,
              created_at text not null,
              company text not null,
              story text not null,
              peers text not null,
              industry text not null,
              purpose text,
              score integer not null,
              verdict text not null,
              report_path text,
              request_json text not null,
              result_json text not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists research_card_events (
              id integer primary key autoincrement,
              card_id integer not null,
              created_at text not null,
              event_type text not null,
              payload_json text not null,
              foreign key(card_id) references research_cards(id)
            )
            """
        )


def save_card(db_path: Path, request: dict[str, object], result: dict[str, object], report_path: Optional[Path]) -> int:
    ensure_schema(db_path)
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            """
            insert into research_cards
              (created_at, company, story, peers, industry, purpose, score, verdict, report_path, request_json, result_json)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result["generated_at"],
                result["company"],
                result["story"],
                result["peers_input"],
                result["industry"],
                result["purpose"],
                result["score"],
                result["verdict"],
                str(report_path) if report_path else None,
                json.dumps(request, ensure_ascii=False),
                json.dumps(result, ensure_ascii=False),
            ),
        )
        card_id = int(cur.lastrowid)
        conn.execute(
            "insert into research_card_events (card_id, created_at, event_type, payload_json) values (?, ?, ?, ?)",
            (card_id, now_iso(), "created", json.dumps({"mode": result["mode"], "report_path": str(report_path) if report_path else None}, ensure_ascii=False)),
        )
    return card_id


def render_html(result: dict[str, object], report_dir: Path = DEFAULT_REPORT_DIR) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    template = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))
    html = template.render(title=f"{result['company']} Story-to-DART Auditor", **result)
    if DISCLAIMER not in html:
        raise RuntimeError("Missing required disclaimer")
    banned = ["목표주가 제시:", "매수 추천", "매도 추천", "수익 보장:"]
    for phrase in banned:
        if phrase in html:
            raise RuntimeError(f"Unsafe investment language detected: {phrase}")
    filename = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{slugify(str(result['company']))}.html"
    path = report_dir / filename
    path.write_text(html, encoding="utf-8")
    return path


def export_optional_formats(html_path: Path, outputs: set[str]) -> list[str]:
    """PDF/PNG export는 optional이다. Playwright가 있으면 생성하고, 없으면 안내만 남긴다."""
    requested = {"pdf", "png"} & outputs
    if not requested:
        return []
    notes: list[str] = []
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception:
        return [f"PDF/PNG export skipped: Playwright is not installed. HTML is ready at {html_path}"]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1600})
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        if "pdf" in requested:
            pdf_path = html_path.with_suffix(".pdf")
            page.pdf(path=str(pdf_path), format="A4", print_background=True)
            notes.append(f"PDF exported: {pdf_path}")
        if "png" in requested:
            png_path = html_path.with_suffix(".png")
            page.screenshot(path=str(png_path), full_page=True)
            notes.append(f"PNG exported: {png_path}")
        browser.close()
    return notes


def load_card(db_path: Path, card_id: int) -> dict[str, object]:
    ensure_schema(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("select * from research_cards where id = ?", (card_id,)).fetchone()
    if not row:
        raise typer.BadParameter(f"Research Card not found: {card_id}")
    data = dict(row)
    data["result"] = json.loads(data["result_json"])
    data["request"] = json.loads(data["request_json"])
    return data


def detect_special_situations(disclosures: list[dict[str, str]]) -> str:
    keywords = [
        "정정",
        "주요사항",
        "소송",
        "유상증자",
        "무상증자",
        "합병",
        "분할",
        "영업정지",
        "투자판단",
        "횡령",
        "배임",
        "불성실",
        "감사의견",
        "최대주주",
    ]
    hits = []
    for item in disclosures:
        name = item.get("report_nm", "")
        if any(keyword in name for keyword in keywords):
            hits.append(f"{item.get('rcept_dt', '')} {name}")
    return " / ".join(hits[:3]) if hits else "특이 공시 미탐지"


def build_season_row(company: str, api_key: str, fs_div: str, ir_dir: Optional[Path], target_period: Optional[tuple[int, int]], basis: str) -> dict[str, str]:
    corp = resolve_corp(company, api_key)
    periodic = fetch_filings(corp["corp_code"], api_key)
    recent = fetch_recent_disclosures(corp["corp_code"], api_key)
    selected: Optional[dict[str, str]]
    if target_period:
        year, quarter = target_period
        financials = fetch_financials_for_quarter(corp["corp_code"], api_key, fs_div, year, quarter)
        if not financials.get("rows"):
            raise DartApiError(f"{company} {period_label(year, quarter)} 재무 주요계정 데이터가 없습니다.")
        selected = find_filing_for_period(periodic, year, quarter)
    else:
        financials = fetch_latest_financials(corp["corp_code"], api_key, fs_div, periodic)
        selected = financials.get("source_filing") if isinstance(financials.get("source_filing"), dict) else pick_business_report(periodic)
    summary = financial_summary(financials)
    trend = build_period_trend(corp["corp_code"], api_key, fs_div, financials, basis)
    rcept_no = ""
    rcept_dt = ""
    report_nm = str(financials.get("report_name") or "미확인")
    if isinstance(selected, dict):
        rcept_no = selected.get("rcept_no", "")
        rcept_dt = selected.get("rcept_dt", "")
        report_nm = selected.get("report_nm", report_nm)
    ir_note = "IR 미입력"
    if ir_dir and ir_dir.exists():
        candidates = sorted([p for p in ir_dir.iterdir() if company in p.name and p.is_file()])
        if candidates:
            try:
                ir_data = read_ir_file(candidates[0])
                snippets = dict(ir_data.get("snippets") or {})
                ir_note = " / ".join(f"{k}: {v[:80]}" for k, v in snippets.items()) or f"IR 파일 확인: {candidates[0].name}"
            except Exception as exc:
                ir_note = f"IR 읽기 실패: {exc}"
    return {
        "updated_at": now_iso(),
        "company": company,
        "corp_code": corp.get("corp_code", ""),
        "stock_code": corp.get("stock_code", ""),
        "period": trend["period"],
        "latest_report": report_nm,
        "rcept_dt": rcept_dt,
        "rcept_no": rcept_no,
        "fs_div": summary["fs_div"],
        "basis": "분기" if basis == "quarter" else "누계",
        "revenue": trend["revenue"],
        "operating_profit": trend["operating_profit"],
        "op_margin": trend["op_margin"],
        "net_income": trend["net_income"],
        "revenue_qoq": trend["revenue_qoq"],
        "revenue_yoy": trend["revenue_yoy"],
        "op_qoq": trend["op_qoq"],
        "op_yoy": trend["op_yoy"],
        "trend_comment": trend["trend_comment"],
        "assets": summary["assets"],
        "special_situations": detect_special_situations(recent),
        "ir_note": ir_note,
    }


SEASON_COLUMNS = [
    "updated_at",
    "company",
    "corp_code",
    "stock_code",
    "period",
    "latest_report",
    "rcept_dt",
    "rcept_no",
    "fs_div",
    "basis",
    "revenue",
    "operating_profit",
    "op_margin",
    "net_income",
    "revenue_qoq",
    "revenue_yoy",
    "op_qoq",
    "op_yoy",
    "trend_comment",
    "assets",
    "special_situations",
    "ir_note",
]


def write_season_table(rows: list[dict[str, str]], table_path: Path, append: bool) -> None:
    table_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = table_path.suffix.lower()
    if suffix == ".csv":
        exists = table_path.exists() and table_path.stat().st_size > 0
        with table_path.open("a" if append else "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=SEASON_COLUMNS)
            if not append or not exists:
                writer.writeheader()
            writer.writerows(rows)
        return

    header = "| " + " | ".join(SEASON_COLUMNS) + " |\n"
    divider = "| " + " | ".join(["---"] * len(SEASON_COLUMNS)) + " |\n"
    body = "".join("| " + " | ".join(str(row.get(col, "")).replace("\n", " ") for col in SEASON_COLUMNS) + " |\n" for row in rows)
    if append and table_path.exists() and table_path.stat().st_size > 0:
        with table_path.open("a", encoding="utf-8") as f:
            f.write(body)
    else:
        table_path.write_text("# Earnings Season DART Table\n\n" + header + divider + body, encoding="utf-8")


@app.command()
def audit(
    company: str = typer.Option(..., help="분석할 한국 회사명"),
    story: Optional[str] = typer.Option(None, help="검증할 시장 스토리나 전략 가설. 비워두면 기본 실적 점검 스토리를 사용합니다."),
    peers: str = typer.Option("", help="쉼표로 구분한 비교 회사명"),
    industry: str = typer.Option("general", help="산업 렌즈. 예: game, platform, ecommerce"),
    purpose: str = typer.Option("", help="보고 목적 또는 회의 맥락"),
    output: str = typer.Option("html,db", help="생성할 결과물. 예: html,db 또는 html,pdf,png,db"),
    fallback: bool = typer.Option(False, help="DART 조회 실패 시 데모 fixture 사용 허용"),
    force_fallback: bool = typer.Option(False, help="DART 조회를 건너뛰고 데모 fixture만 사용"),
    ir_file: Optional[Path] = typer.Option(None, help="추가로 읽을 IR 자료/PDF/메모 파일"),
    fs_div: str = typer.Option("CFS", help="재무제표 구분: CFS(연결) 또는 OFS(별도)"),
    db_path: Path = typer.Option(DEFAULT_DB, help="SQLite DB 경로"),
) -> None:
    """회사 실적과 시장 스토리를 최신 DART 공시로 검증합니다."""
    resolved_story = story or "최근 실적과 공시 기준으로 이 회사가 좋아지고 있는지, 특수 상황은 무엇인지 확인"
    api_key = os.environ.get("DART_API_KEY", "").strip()
    live_evidence: Optional[dict[str, object]] = None
    mode = "fallback_fixture"
    dart_error = None
    if not force_fallback:
        if not api_key:
            dart_error = "DART_API_KEY 환경변수가 없습니다."
        else:
            try:
                live_evidence = collect_live_evidence(company, api_key, fs_div.upper())
                mode = "dart_live"
            except Exception as exc:
                dart_error = str(exc)
    if not live_evidence and not (fallback or force_fallback):
        console.print(f"[red]DART live 조회 실패:[/red] {dart_error}")
        console.print("오프라인/데모 실행은 --fallback 또는 --force-fallback을 붙이세요.")
        raise typer.Exit(2)
    if not live_evidence and dart_error:
        console.print(f"[yellow]DART live 조회 실패. fallback fixture로 진행:[/yellow] {dart_error}")
    if ir_file:
        ir_evidence = read_ir_file(ir_file)
        if live_evidence is None:
            live_evidence = {"filings": [], "financial_summary": None, "snippets": {}, "corp": None, "filing_label": "IR 자료"}
        live_evidence["ir_file"] = ir_evidence["path"]
        live_evidence["ir_snippets"] = ir_evidence["snippets"]
        console.print(f"[green]IR supplemental evidence:[/green] {ir_file}")

    request = {
        "company": company,
        "story": resolved_story,
        "peers": peers,
        "industry": industry,
        "purpose": purpose,
        "output": output,
        "fallback": fallback,
        "force_fallback": force_fallback,
        "ir_file": str(ir_file) if ir_file else None,
        "fs_div": fs_div.upper(),
    }
    result = build_result(company, resolved_story, peers, industry, purpose, mode, live_evidence=live_evidence, api_key=api_key if live_evidence else None, fs_div=fs_div.upper())
    outputs = {item.strip() for item in output.split(",") if item.strip()}
    report_path: Optional[Path] = None
    if {"html", "pdf", "png"} & outputs:
        report_path = render_html(result)
        console.print(f"[green]HTML one-pager:[/green] {report_path}")
        for note in export_optional_formats(report_path, outputs):
            console.print(f"[yellow]{note}[/yellow]" if "skipped" in note else f"[green]{note}[/green]")
    card_id: Optional[int] = None
    if "db" in outputs:
        card_id = save_card(db_path, request, result, report_path)
        console.print(f"[green]Research Card saved:[/green] #{card_id} -> {db_path}")
    console.print(f"Story Verification Score: [bold]{result['score']}[/bold] ({result['verdict']})")


@app.command()
def season(
    companies: str = typer.Option(..., help="쉼표로 구분한 업데이트 대상 회사명"),
    table_path: Optional[Path] = typer.Option(None, "--table", help="생성하거나 이어 쓸 Markdown/CSV 테이블 경로"),
    append: bool = typer.Option(True, help="기존 테이블이 있으면 행을 추가"),
    ir_dir: Optional[Path] = typer.Option(None, help="회사명으로 저장된 IR 파일 폴더"),
    fs_div: str = typer.Option("CFS", help="재무제표 구분: CFS(연결) 또는 OFS(별도)"),
    period: Optional[str] = typer.Option(None, "--period", help="특정 실적 기간. 예: 26.1Q, 2026Q1, 25.4Q"),
    basis: str = typer.Option("quarter", "--basis", help="실적 기준: quarter(분기 실적) 또는 cumulative(누계 실적)"),
) -> None:
    """최신 분기/반기/사업보고서 기준으로 경쟁사 실적 테이블을 생성하거나 업데이트합니다."""
    api_key = os.environ.get("DART_API_KEY", "").strip()
    if not api_key:
        console.print("[red]DART_API_KEY 환경변수가 필요합니다.[/red]")
        raise typer.Exit(2)
    names = split_peers(companies)
    if not names:
        raise typer.BadParameter("--companies must include at least one company")
    normalized_basis = basis.strip().lower()
    if normalized_basis not in {"quarter", "cumulative"}:
        raise typer.BadParameter("--basis는 quarter 또는 cumulative만 지원합니다.")
    target_period = parse_period_option(period)
    rows: list[dict[str, str]] = []
    for name in names:
        try:
            console.print(f"[cyan]Updating[/cyan] {name}")
            rows.append(build_season_row(name, api_key, fs_div.upper(), ir_dir, target_period, normalized_basis))
        except Exception as exc:
            rows.append(
                {
                    "updated_at": now_iso(),
                    "company": name,
                    "corp_code": "",
                    "stock_code": "",
                    "period": "조회 실패",
                    "latest_report": "조회 실패",
                    "rcept_dt": "",
                    "rcept_no": "",
                    "fs_div": fs_div.upper(),
                    "basis": "분기" if normalized_basis == "quarter" else "누계",
                    "revenue": "미확인",
                    "operating_profit": "미확인",
                    "op_margin": "미확인",
                    "net_income": "미확인",
                    "revenue_qoq": "미확인",
                    "revenue_yoy": "미확인",
                    "op_qoq": "미확인",
                    "op_yoy": "미확인",
                    "trend_comment": f"추세 계산 실패: {exc}",
                    "assets": "미확인",
                    "special_situations": f"오류: {exc}",
                    "ir_note": "미확인",
                }
            )
    if table_path is None:
        DEFAULT_TABLE_DIR.mkdir(parents=True, exist_ok=True)
        table_path = DEFAULT_TABLE_DIR / f"earnings-season-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    write_season_table(rows, table_path, append=append)

    table = Table(title="Earnings Season Update")
    for col in ["company", "period", "basis", "latest_report", "revenue", "revenue_qoq", "revenue_yoy", "operating_profit", "op_qoq", "op_yoy", "op_margin", "trend_comment", "special_situations"]:
        table.add_column(col)
    for row in rows:
        table.add_row(*(row.get(col, "") for col in ["company", "period", "basis", "latest_report", "revenue", "revenue_qoq", "revenue_yoy", "operating_profit", "op_qoq", "op_yoy", "op_margin", "trend_comment", "special_situations"]))
    console.print(table)
    console.print(f"[green]Table updated:[/green] {table_path}")


@app.command()
def company(
    company_name: str = typer.Argument(..., help="분석할 회사명"),
    peers: str = typer.Option("", help="쉼표로 구분한 비교 회사명"),
    industry: str = typer.Option("general", help="산업 렌즈"),
    purpose: str = typer.Option("회사명 기반 빠른 실적 점검", help="보고 목적"),
    output: str = typer.Option("html,db", help="생성할 결과물. 예: html,db 또는 html,pdf,png,db"),
    fallback: bool = typer.Option(False, help="DART 조회 실패 시 데모 fixture 사용 허용"),
    fs_div: str = typer.Option("CFS", help="재무제표 구분: CFS(연결) 또는 OFS(별도)"),
) -> None:
    """회사명만 넣는 빠른 점검용 단축 명령입니다. 내부적으로 audit을 실행합니다."""
    quick_story = "최근 실적과 공시 기준으로 이 회사가 좋아지고 있는지, 특수 상황은 무엇인지 확인"
    audit(
        company=company_name,
        story=quick_story,
        peers=peers,
        industry=industry,
        purpose=purpose,
        output=output,
        fallback=fallback,
        force_fallback=False,
        ir_file=None,
        fs_div=fs_div,
        db_path=DEFAULT_DB,
    )


@app.command("list")
def list_cards(
    company: Optional[str] = typer.Option(None, help="Filter by company"),
    industry: Optional[str] = typer.Option(None, help="Filter by industry"),
    limit: int = typer.Option(20, help="Max rows"),
    db_path: Path = typer.Option(DEFAULT_DB, help="SQLite DB path"),
) -> None:
    """List saved Research Cards."""
    ensure_schema(db_path)
    query = "select id, created_at, company, industry, score, verdict, purpose, report_path from research_cards"
    clauses: list[str] = []
    params: list[object] = []
    if company:
        clauses.append("company = ?")
        params.append(company)
    if industry:
        clauses.append("industry = ?")
        params.append(industry)
    if clauses:
        query += " where " + " and ".join(clauses)
    query += " order by id desc limit ?"
    params.append(limit)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    table = Table(title="Research Cards")
    for col in ["id", "created_at", "company", "industry", "score", "verdict", "purpose"]:
        table.add_column(col)
    for row in rows:
        table.add_row(*(str(x) for x in row[:7]))
    console.print(table)


@app.command()
def show(card_id: int, json_output: bool = typer.Option(False, "--json", help="Print JSON"), db_path: Path = typer.Option(DEFAULT_DB, help="SQLite DB path")) -> None:
    """Show a Research Card."""
    card = load_card(db_path, card_id)
    if json_output:
        console.print(json.dumps(card["result"], ensure_ascii=False, indent=2))
        return
    result = card["result"]
    console.print(f"[bold]#{card_id} {result['company']}[/bold] - {result['score']} ({result['verdict']})")
    console.print(f"Story: {result['story']}")
    console.print(f"Report: {card.get('report_path')}")
    table = Table(title="Findings")
    table.add_column("Classification")
    table.add_column("Claim")
    table.add_column("Rationale")
    for finding in result["findings"]:
        table.add_row(finding["classification"], finding["claim"], finding["rationale"])
    console.print(table)


@app.command()
def history(
    company: Optional[str] = typer.Option(None, help="Company filter"),
    story_contains: Optional[str] = typer.Option(None, help="Story keyword filter"),
    limit: int = typer.Option(20, help="Max rows"),
    db_path: Path = typer.Option(DEFAULT_DB, help="SQLite DB path"),
) -> None:
    """Show score history."""
    ensure_schema(db_path)
    query = "select id, created_at, company, score, verdict, story from research_cards"
    clauses: list[str] = []
    params: list[object] = []
    if company:
        clauses.append("company = ?")
        params.append(company)
    if story_contains:
        clauses.append("story like ?")
        params.append(f"%{story_contains}%")
    if clauses:
        query += " where " + " and ".join(clauses)
    query += " order by id desc limit ?"
    params.append(limit)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    table = Table(title="Audit History")
    for col in ["id", "created_at", "company", "score", "verdict", "story"]:
        table.add_column(col)
    for row in rows:
        table.add_row(*(escape(str(x)) for x in row))
    console.print(table)


@app.command()
def render(card_id: int, db_path: Path = typer.Option(DEFAULT_DB, help="SQLite DB path")) -> None:
    """Re-render a Research Card to HTML."""
    card = load_card(db_path, card_id)
    path = render_html(card["result"])
    with sqlite3.connect(db_path) as conn:
        conn.execute("update research_cards set report_path = ? where id = ?", (str(path), card_id))
        conn.execute(
            "insert into research_card_events (card_id, created_at, event_type, payload_json) values (?, ?, ?, ?)",
            (card_id, now_iso(), "rendered", json.dumps({"report_path": str(path)}, ensure_ascii=False)),
        )
    console.print(f"[green]Rendered:[/green] {path}")


if __name__ == "__main__":
    app()
