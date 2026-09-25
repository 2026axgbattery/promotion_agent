"""DuckDB 연결·스키마 로딩.

`.docs/08_기술스택.md`(DuckDB 확정 근거), `.docs/02_PRD.md` 7절(데이터 모델),
`.docs/19_최종백데이터_전환_계획서.md`(제품마스터·AGM기준선 시드 제거 근거) 참고.

DuckDB는 서버 프로세스가 없는 임베디드 DB라서, 이 파일의 함수들은 모두 "파일 경로 하나"를
받아 그 자리에서 연결·조회한다(단일 프로세스 배포 전제와 일치).

과거에는 `product_master`·`store_agm_baseline`·`promotion_master` 테이블에 참조용
시드를 채워 넣었으나, DC율/프로모션 기준/DATA 워크북 경로로 완전히 전환하면서(모든
제품·대리점·프로모션 규칙 정보가 매번 업로드되는 워크북 안에 그대로 들어있음) 이
테이블들은 죽은 스키마가 되어 제거했다. 이제 DB에는 기준연월별 **분석 결과**
(sales_record/applied_support)만 저장한다.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

APP_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = APP_DIR / "data" / "promotion_history.duckdb"

_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS sales_record (
    기준연월 VARCHAR,
    대리점코드 VARCHAR,
    대리점명 VARCHAR,
    판매수량 DOUBLE,
    매출액 DOUBLE,
    전월매출 DOUBLE,
    매출증감율 DOUBLE,
    전년동월매출 DOUBLE,
    전년동월매출증감율 DOUBLE,
    영업이익 DOUBLE,
    영업이익율 DOUBLE,
    매출DC율 DOUBLE,
    성장DC율 DOUBLE,
    DC율 DOUBLE,
    DC지원금액 DOUBLE,
    프로모션지원금액 DOUBLE,
    총지원금액 DOUBLE,
    원가율 DOUBLE
);

CREATE TABLE IF NOT EXISTS applied_support (
    -- 어떤 지원인지는 `지원유형`(예: "매출DC", "성장DC", 프로모션명)으로 구분한다.
    기준연월 VARCHAR,
    대리점코드 VARCHAR,
    대리점명 VARCHAR,
    제품코드 VARCHAR,
    지원유형 VARCHAR,
    지원단가 DOUBLE,
    지원금액 DOUBLE
);
"""


def get_connection(db_path: str | Path | None = None) -> duckdb.DuckDBPyConnection:
    # db_path=None을 기본값으로 두고 여기서 DEFAULT_DB_PATH를 참조해야, 테스트에서
    # `db.DEFAULT_DB_PATH`를 monkeypatch했을 때 실제로 반영된다(함수 시그니처의
    # 기본값으로 박아두면 모듈 임포트 시점 값으로 고정돼 나중에 바꿔도 소용없다).
    db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db_path))


def ensure_schema(con: duckdb.DuckDBPyConnection) -> None:
    """`CREATE TABLE IF NOT EXISTS`라서 이미 존재하는 테이블의 컬럼은 바꾸지 않는다 —
    sales_record·applied_support는 기준연월별 실제 분석 결과를 담고 있어(세션이
    끝나도 유지돼야 함) 매번 통째로 재생성하면 안 되기 때문이다.

    개발 중 이 DDL(컬럼 구성)을 바꿨는데 기존 `app/data/promotion_history.duckdb`가
    이미 있으면, 새 컬럼이 추가되지 않아 "Binder Error: column not found" 같은 오류가
    난다. 아직 마이그레이션 기능이 없으므로, 그럴 땐 그 파일을 지우고 다시 만든다
    (지워도 되는 로컬 개발용 캐시일 뿐 — 실제 운영에서는 마이그레이션이 필요하다).
    """
    con.execute(_SCHEMA_DDL)


def init_db(db_path: str | Path | None = None) -> duckdb.DuckDBPyConnection:
    """스키마 생성을 수행하고 연결을 반환한다(앱 시작 시 호출)."""
    con = get_connection(db_path)
    ensure_schema(con)
    return con


def replace_period_data(
    con: duckdb.DuckDBPyConnection,
    *,
    기준연월: str,
    sales_df: pd.DataFrame,
    applied_support_df: pd.DataFrame,
) -> None:
    """분석 실행 결과를 기준연월 키로 저장한다. 같은 기준연월이 이미 있으면 지우고
    다시 넣는다(PRD 6.8절 "같은 기준연월 재분석 시 덮어쓰기").
    """
    def _insert(table: str, df: pd.DataFrame, alias: str) -> None:
        if df.empty:
            return
        columns = ", ".join(f'"{c}"' for c in df.columns)
        con.register(alias, df)
        con.execute(f"INSERT INTO {table} ({columns}) SELECT {columns} FROM {alias}")
        con.unregister(alias)

    con.execute("DELETE FROM sales_record WHERE 기준연월 = ?", [기준연월])
    con.execute("DELETE FROM applied_support WHERE 기준연월 = ?", [기준연월])
    _insert("sales_record", sales_df, "_sales_df")
    _insert("applied_support", applied_support_df, "_applied_support_df")


def saved_periods(con: duckdb.DuckDBPyConnection) -> list[str]:
    """DB에 저장된(분석이 실행된) 기준연월 목록을 최신순으로 반환한다."""
    rows = con.execute(
        "SELECT DISTINCT 기준연월 FROM sales_record ORDER BY 기준연월 DESC"
    ).fetchall()
    return [r[0] for r in rows]


def period_summary(con: duckdb.DuckDBPyConnection, 기준연월: str) -> dict | None:
    """해당 기준연월에 저장된 sales_record를 전사 합계로 요약한다(프로모션 효과
    비교 화면용). 영업이익율·DC율은 단순 평균이 아니라 합산된 금액에서 다시 계산해
    매출액 가중 평균과 같은 결과가 되게 한다. 저장된 데이터가 없으면 None."""
    row = con.execute(
        """
        SELECT
            COUNT(DISTINCT 대리점코드) AS 대리점수,
            SUM(매출액) AS 매출액,
            SUM(영업이익) AS 영업이익,
            SUM(DC지원금액) AS DC지원금액,
            SUM(프로모션지원금액) AS 프로모션지원금액,
            SUM(총지원금액) AS 총지원금액
        FROM sales_record WHERE 기준연월 = ?
        """,
        [기준연월],
    ).fetchone()
    if row is None or row[0] == 0:
        return None
    대리점수, 매출액, 영업이익, dc지원금액, 프로모션지원금액, 총지원금액 = row
    return {
        "기준연월": 기준연월,
        "대리점수": 대리점수,
        "매출액": 매출액,
        "영업이익": 영업이익,
        "영업이익율": (영업이익 / 매출액 * 100) if 매출액 else None,
        "DC지원금액": dc지원금액,
        "DC율": (dc지원금액 / 매출액 * 100) if 매출액 else None,
        "프로모션지원금액": 프로모션지원금액,
        "총지원금액": 총지원금액,
    }
