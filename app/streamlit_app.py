"""Streamlit 앱 진입점 — 페이지 내비게이션만 정의한다.

실제 화면은 `app/views/`의 각 페이지 스크립트에 있다: 업로드 → 분석 결과 → 이력
조회 순서로, 사이드바에서 클릭해 이동한다. 업로드 결과는 `st.session_state`에 담아
페이지 간에 공유한다(`app/ui_common.py` 참고).

실행: streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="프로모션 효과 시뮬레이션 에이전트", layout="wide")

pages = st.navigation(
    [
        st.Page("views/upload.py", title="실적 업로드", icon="📤", default=True),
        st.Page("views/analysis.py", title="분석 결과", icon="📊"),
        st.Page("views/history.py", title="이력 조회", icon="🕘"),
    ]
)
pages.run()
