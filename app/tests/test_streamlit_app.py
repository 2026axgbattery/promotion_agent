"""Streamlit 앱(다중 페이지)이 예외 없이 렌더링되는지 확인하는 스모크 테스트.

`AppTest`는 실제 브라우저 없이 스크립트를 한 번 실행해보고 예외를 잡아준다. 이 앱은
`st.navigation`으로 3개 페이지(실적 업로드/분석 결과/이력 조회)를 나눴다 —
`AppTest.switch_page()`로 같은 세션 안에서 페이지를 옮겨 다니며 세션 상태
(`st.session_state`)가 페이지 간에 유지되는지도 함께 검증한다.

DuckDB는 파일 하나에 동시에 한 프로세스만 붙을 수 있어서, 개발자가 `streamlit run`으로
띄워둔 실제 앱과 기본 경로(`app/data/promotion_history.duckdb`)를 공유하면 파일 잠금
충돌이 난다 — 그래서 매 테스트마다 `db.DEFAULT_DB_PATH`를 임시 경로로 바꿔준다.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from app import db

APP_SCRIPT = Path(__file__).resolve().parents[1] / "streamlit_app.py"


@pytest.fixture(autouse=True)
def _isolated_db_path(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DEFAULT_DB_PATH", tmp_path / "test_promotion_history.duckdb")


def test_app_runs_without_exception():
    at = AppTest.from_file(str(APP_SCRIPT), default_timeout=30)
    at.run()
    assert not at.exception


def test_sidebar_shows_brand_logo():
    # design.md 1.3절: 브랜드 노출 영역(헤더/사이드바)엔 항상 SEBANG 워드마크를 쓴다.
    at = AppTest.from_file(str(APP_SCRIPT), default_timeout=30)
    at.run()
    assert not at.exception
    sidebar_markdown = " ".join(m.value or "" for m in at.sidebar.markdown)
    assert "세방전지" in sidebar_markdown
    assert "<svg" in sidebar_markdown


def test_app_shows_upload_prompt_when_no_files():
    at = AppTest.from_file(str(APP_SCRIPT), default_timeout=30)
    at.run()
    assert not at.exception
    info_texts = [i.value for i in at.info]
    assert any("워크북을 올리면" in text for text in info_texts)


def test_analysis_page_prompts_when_nothing_uploaded_yet():
    at = AppTest.from_file(str(APP_SCRIPT), default_timeout=30)
    at.run()
    at.switch_page("views/analysis.py")
    at.run()
    assert not at.exception
    info_texts = [i.value for i in at.info]
    assert any("아직 분석한 워크북이 없습니다" in text for text in info_texts)


def test_upload_then_analysis_page_renders_result_table():
    workbook_path = Path(__file__).resolve().parents[2] / "업로드 실적(8월).xlsx"
    if not workbook_path.exists():
        pytest.skip("업로드 실적(8월).xlsx가 없습니다")

    at = AppTest.from_file(str(APP_SCRIPT), default_timeout=60)
    at.run()
    at.file_uploader(key="workbook_file").upload(
        "업로드 실적(8월).xlsx", workbook_path.read_bytes(),
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    at.run()
    assert not at.exception

    at.switch_page("views/analysis.py")
    at.run()
    assert not at.exception
    assert len(at.dataframe) >= 1
    subheaders = [h.value for h in at.subheader]
    assert any("대리점 단위 요약" in text for text in subheaders)
    assert any("프로모션 시행 내용" in text for text in subheaders)
    assert any("제품군별" in text for text in subheaders)
    assert any("프로모션 효과 평가" in text for text in subheaders)
    assert any("편차 원인 구분" in text for text in subheaders)
    assert any("문턱값 근접도" in text for text in subheaders)
    assert any("장단점" in text for text in subheaders)
    assert any("영업이익율 × 매출증감율" in text for text in subheaders)
    assert any("대리점 그룹별 효과 비교" in text for text in subheaders)

    metric_labels = [m.label for m in at.metric]
    assert "대리점 수" in metric_labels
    assert "평균 영업이익율" in metric_labels
    assert "총 지원금액" in metric_labels


def test_history_page_prompts_when_fewer_than_two_periods_saved():
    at = AppTest.from_file(str(APP_SCRIPT), default_timeout=30)
    at.run()
    at.switch_page("views/history.py")
    at.run()
    assert not at.exception
    headers = [h.value for h in at.header]
    assert any("프로모션 효과 비교" in text for text in headers)
    assert any("이력 조회" in text for text in headers)
    info_texts = [i.value for i in at.info]
    assert any("최소 2개 기준연월" in text for text in info_texts)
    assert any("아직 저장된 분석 결과가 없습니다" in text for text in info_texts)


def _save_period(con, period: str, revenue: float) -> None:
    empty_support = pd.DataFrame(
        columns=["기준연월", "대리점코드", "제품코드", "지원유형", "지원단가", "지원금액"]
    )
    sales_df = pd.DataFrame(
        [{"기준연월": period, "대리점코드": "S1", "대리점명": "테스트대리점", "매출액": revenue,
          "영업이익": revenue * 0.1, "DC지원금액": revenue * 0.05, "프로모션지원금액": 0.0,
          "총지원금액": revenue * 0.05}]
    )
    db.replace_period_data(con, 기준연월=period, sales_df=sales_df, applied_support_df=empty_support)


def test_history_page_shows_comparison_and_detail_for_saved_periods(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DEFAULT_DB_PATH", tmp_path / "test_promotion_history.duckdb")
    con = db.init_db()
    _save_period(con, "2026-06", 1000.0)
    _save_period(con, "2026-07", 1500.0)
    con.close()

    at = AppTest.from_file(str(APP_SCRIPT), default_timeout=30)
    at.run()
    at.switch_page("views/history.py")
    at.run()
    assert not at.exception

    metric_labels = [m.label for m in at.metric]
    assert any("매출액 (2026-07)" in label for label in metric_labels)

    selectboxes = {sb.label: sb for sb in at.selectbox}
    assert "상세 조회할 기준연월" in selectboxes
    assert selectboxes["상세 조회할 기준연월"].value == "2026-07"
