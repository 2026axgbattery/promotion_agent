from __future__ import annotations

import pandas as pd
import pytest

from app import db


@pytest.fixture
def con(tmp_path):
    connection = db.init_db(tmp_path / "test_promotion_history.duckdb")
    yield connection
    connection.close()


class TestInitDb:
    def test_schema_tables_exist(self, con):
        tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
        assert {"sales_record", "applied_support"} <= tables


class TestReplacePeriodData:
    def test_insert_and_query(self, con):
        sales_df = pd.DataFrame(
            [
                {
                    "기준연월": "2026-10",
                    "대리점코드": "DG-014",
                    "대리점명": "대구달서대리점",
                    "판매수량": 33.0,
                    "전월매출": 1800000.0,
                    "매출액": 1817359.0,
                    "매출증감율": 4.1,
                    "DC율": 6.5,
                    "원가율": 70.0,
                    "영업이익": 120000.0,
                    "영업이익율": 11.2,
                    "DC지원금액": 126341.0,
                    "프로모션지원금액": 176700.0,
                    "총지원금액": 303041.0,
                }
            ]
        )
        support_df = pd.DataFrame(
            [
                {
                    "기준연월": "2026-10",
                    "대리점코드": "DG-014",
                    "제품코드": "PCC12366",
                    "지원유형": "10+1_GB",
                    "지원단가": 58900.0,
                    "지원금액": 176700.0,
                }
            ]
        )
        db.replace_period_data(con, 기준연월="2026-10", sales_df=sales_df, applied_support_df=support_df)

        assert db.saved_periods(con) == ["2026-10"]
        stored = con.execute("SELECT * FROM sales_record WHERE 기준연월 = '2026-10'").fetchdf()
        assert len(stored) == 1
        assert stored.loc[0, "대리점코드"] == "DG-014"

    def test_reanalysis_overwrites_previous(self, con):
        first = pd.DataFrame(
            [{"기준연월": "2026-10", "대리점코드": "A", "판매수량": 1.0}]
        )
        second = pd.DataFrame(
            [
                {"기준연월": "2026-10", "대리점코드": "B", "판매수량": 2.0},
                {"기준연월": "2026-10", "대리점코드": "C", "판매수량": 3.0},
            ]
        )
        empty_support = pd.DataFrame(
            columns=["기준연월", "대리점코드", "제품코드", "지원유형", "지원단가", "지원금액"]
        )

        db.replace_period_data(con, 기준연월="2026-10", sales_df=first, applied_support_df=empty_support)
        db.replace_period_data(con, 기준연월="2026-10", sales_df=second, applied_support_df=empty_support)

        stored = con.execute("SELECT 대리점코드 FROM sales_record WHERE 기준연월 = '2026-10'").fetchdf()
        assert sorted(stored["대리점코드"].tolist()) == ["B", "C"]


class TestPeriodSummary:
    def _sales_df(self, 기준연월: str, rows: list[dict]) -> pd.DataFrame:
        return pd.DataFrame([{"기준연월": 기준연월, **row} for row in rows])

    def test_summary_aggregates_across_stores(self, con):
        sales_df = self._sales_df(
            "2026-10",
            [
                {"대리점코드": "A", "매출액": 1000.0, "영업이익": 100.0, "DC지원금액": 50.0, "프로모션지원금액": 20.0, "총지원금액": 70.0},
                {"대리점코드": "B", "매출액": 2000.0, "영업이익": 300.0, "DC지원금액": 100.0, "프로모션지원금액": 40.0, "총지원금액": 140.0},
            ],
        )
        empty_support = pd.DataFrame(
            columns=["기준연월", "대리점코드", "제품코드", "지원유형", "지원단가", "지원금액"]
        )
        db.replace_period_data(con, 기준연월="2026-10", sales_df=sales_df, applied_support_df=empty_support)

        summary = db.period_summary(con, "2026-10")
        assert summary["대리점수"] == 2
        assert summary["매출액"] == pytest.approx(3000.0)
        assert summary["영업이익"] == pytest.approx(400.0)
        assert summary["영업이익율"] == pytest.approx(400 / 3000 * 100)
        assert summary["DC지원금액"] == pytest.approx(150.0)
        assert summary["총지원금액"] == pytest.approx(210.0)

    def test_summary_missing_period_returns_none(self, con):
        assert db.period_summary(con, "2099-01") is None
