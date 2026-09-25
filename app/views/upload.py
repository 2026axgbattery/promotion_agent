"""페이지: 실적 업로드.

"DC율"·"프로모션 기준"·"DATA" 3개 시트로 구성된 월 마감 워크북 하나를 업로드하면
`app/workbook_ingest.py`가 대리점 단위 결과로 변환한다. 결과는 세션 상태에 저장해
"분석 결과" 페이지에서 이어서 확인한다(다시 업로드할 필요 없음).
"""

from __future__ import annotations

import streamlit as st

from app import ui_common
from app.workbook_ingest import ColumnNotFoundError, build_sales_like_table

ui_common.inject_design_system_css()
ui_common.render_brand_header()

st.title("월 마감 실적 워크북 업로드")
st.caption('"DC율"·"프로모션 기준"·"DATA" 시트가 포함된 월 마감 워크북 하나를 올리면 대리점 단위 결과를 계산합니다.')

col_file, col_period = st.columns([3, 1])
with col_file:
    workbook_file = st.file_uploader("월 마감 워크북 (.xlsx)", type=["xlsx"], key="workbook_file")
with col_period:
    period_input = st.text_input("기준연월", value="2026-08", help="예: 2026-08 — 워크북 안에서 자동으로 읽어오지 않아 직접 입력합니다.")

if workbook_file is not None:
    try:
        ingest_result = build_sales_like_table(workbook_file, period_input)
    except ColumnNotFoundError as exc:
        st.error(f"워크북을 읽을 수 없습니다: {exc}")
    else:
        st.session_state["ingest_result"] = ingest_result
        st.session_state["기준연월"] = period_input
        st.success(f"{period_input} 워크북을 분석했습니다.")
        st.page_link("views/analysis.py", label="분석 결과 보기 →", icon="📊")
else:
    st.info("워크북을 올리면 결과가 표시됩니다.")
    if "ingest_result" in st.session_state:
        st.page_link("views/analysis.py", label=f"이전에 올린 {st.session_state.get('기준연월', '')} 분석 결과 다시 보기 →", icon="📊")
