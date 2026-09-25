"""페이지: 분석 결과.

"실적 업로드" 페이지에서 분석한 결과(세션 상태)를 이어서 보여준다. 이 페이지 자체는
업로드를 받지 않는다 — 업로드 없이 열리면 실적 업로드 페이지로 안내한다.
"""

from __future__ import annotations

import streamlit as st

from app import ui_common

ui_common.inject_design_system_css()
ui_common.render_brand_header()

st.title("대리점 단위 분석 결과")

result = st.session_state.get("ingest_result")
기준연월 = st.session_state.get("기준연월")

if result is None:
    st.info("아직 분석한 워크북이 없습니다. 먼저 '실적 업로드' 페이지에서 워크북을 올려주세요.")
    st.page_link("views/upload.py", label="실적 업로드 페이지로 이동 →", icon="📤")
else:
    ui_common.render_analysis(result, 기준연월)
