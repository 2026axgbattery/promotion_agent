"""워크북 인입(`workbook_ingest`) 결과를 DuckDB(`db.replace_period_data`)에 실제로
저장하는 연결 지점을 검증한다 — Streamlit 화면의 "DuckDB에 저장" 버튼이 하는 일과 동일하다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app import db
from app.workbook_ingest import build_sales_like_table

SALES_COLUMNS = [
    "기준연월", "대리점코드", "대리점명", "판매수량", "전월매출", "매출액", "매출증감율",
    "매출DC율", "성장DC율", "DC율", "원가율", "영업이익", "영업이익율",
    "DC지원금액", "프로모션지원금액", "총지원금액",
]


@pytest.fixture(scope="module")
def workbook_path():
    path = Path(__file__).resolve().parents[2] / "업로드 실적(8월).xlsx"
    if not path.exists():
        pytest.skip("업로드 실적(8월).xlsx가 없습니다")
    return path


@pytest.fixture(scope="module")
def ingest_result(workbook_path):
    return build_sales_like_table(workbook_path, "2026-08")


@pytest.fixture
def con(tmp_path):
    connection = db.init_db(tmp_path / "test_ingest_to_db.duckdb")
    yield connection
    connection.close()


class TestIngestToDb:
    def test_save_populates_both_tables(self, con, ingest_result):
        db.replace_period_data(
            con,
            기준연월="2026-08",
            sales_df=ingest_result.sales_like[SALES_COLUMNS],
            applied_support_df=ingest_result.applied_support,
        )

        assert db.saved_periods(con) == ["2026-08"]
        sales_count = con.execute("SELECT COUNT(*) FROM sales_record").fetchone()[0]
        support_count = con.execute("SELECT COUNT(*) FROM applied_support").fetchone()[0]
        assert sales_count == len(ingest_result.sales_like)
        assert support_count == len(ingest_result.applied_support)

    def test_saved_totals_match_source(self, con, ingest_result):
        db.replace_period_data(
            con,
            기준연월="2026-08",
            sales_df=ingest_result.sales_like[SALES_COLUMNS],
            applied_support_df=ingest_result.applied_support,
        )
        saved_total = con.execute(
            "SELECT SUM(총지원금액) FROM sales_record WHERE 기준연월 = '2026-08'"
        ).fetchone()[0]
        expected_total = ingest_result.sales_like["총지원금액"].sum()
        assert saved_total == pytest.approx(expected_total, abs=1.0)

    def test_reanalysis_overwrites(self, con, ingest_result):
        db.replace_period_data(
            con,
            기준연월="2026-08",
            sales_df=ingest_result.sales_like[SALES_COLUMNS],
            applied_support_df=ingest_result.applied_support,
        )
        db.replace_period_data(
            con,
            기준연월="2026-08",
            sales_df=ingest_result.sales_like[SALES_COLUMNS],
            applied_support_df=ingest_result.applied_support,
        )
        sales_count = con.execute(
            "SELECT COUNT(*) FROM sales_record WHERE 기준연월 = '2026-08'"
        ).fetchone()[0]
        assert sales_count == len(ingest_result.sales_like)
