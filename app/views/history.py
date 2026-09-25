"""페이지: 이력 조회.

DuckDB에 저장된 기준연월 이력을 다룬다 — 두 기준연월 간 지표 비교와, 과거 저장된
대리점 단위 결과 다시 보기. 둘 다 현재 업로드한 워크북과 무관하게 DB 이력만으로
동작한다.
"""

from __future__ import annotations

import streamlit as st

from app import ui_common

ui_common.inject_design_system_css()
ui_common.render_brand_header()

st.title("이력 조회")

ui_common.render_period_comparison()
st.divider()
ui_common.render_history_view()
