"""페이지: 실적 업로드.

"DC율"·"프로모션 기준"·"DATA" 3개 시트로 구성된 월 마감 워크북 하나를 업로드하면
`app/workbook_ingest.py`가 대리점 단위 결과로 변환한다. 분석하는 동안 진행 단계
(`st.status` + `st.progress`)와 결과 화면 모양의 스켈레톤을 보여주고, 끝나면 "분석 결과"
페이지로 자동 이동한다(`.docs/21_분석결과_대시보드_UI_개편_계획서.md`).

같은 파일·같은 기준연월을 이미 분석했다면 이 페이지에 다시 들어와도 재분석·재이동하지
않는다 — 그래야 업로드 화면에 머물면서 파일을 바꾸거나 기준연월을 고칠 수 있다.
"""

from __future__ import annotations

import time

import streamlit as st

from app import dashboard, ui_common
from app.workbook_ingest import ColumnNotFoundError, build_sales_like_table

ui_common.inject_design_system_css()
ui_common.render_brand_header()

st.html(dashboard.upload_intro())

with st.container(key="sbcard-upload"):
    col_file, col_period = st.columns([3, 1])
    with col_file:
        workbook_file = st.file_uploader("월 마감 워크북 (.xlsx)", type=["xlsx"], key="workbook_file")
    with col_period:
        period_input = st.text_input(
            "기준연월", value="2026-08", help="예: 2026-08 — 워크북 안에서 자동으로 읽어오지 않아 직접 입력합니다."
        )


def _show_result_skeleton():
    """분석 결과 대시보드와 같은 배치(KPI 4개 → 2단 카드 → 넓은 카드)의 스켈레톤."""
    slot = st.empty()
    with slot.container():
        st.caption("분석 결과 화면을 준비하고 있어요")
        for col in st.columns(4):
            col.skeleton(height=150)
        left, right = st.columns([5, 7])
        left.skeleton(height=300)
        right.skeleton(height=300)
        st.skeleton(height=220)
    return slot


def _analyze(file, period: str):
    status = st.status("워크북을 분석하고 있습니다…", expanded=False)
    # 진행률 막대는 status 바깥에 둔다 — status가 접힌 채로 보이면 안쪽 막대가 가려진다.
    bar = st.progress(0.0, text="분석 준비 중")
    skeleton = _show_result_skeleton()

    def on_progress(label: str, fraction: float) -> None:
        bar.progress(fraction, text=label)
        status.update(label=f"{label}…")

    try:
        result = build_sales_like_table(file, period, progress=on_progress)
    except ColumnNotFoundError as exc:
        skeleton.empty()
        bar.empty()
        status.update(label="워크북을 읽을 수 없습니다", state="error", expanded=True)
        st.error(f"워크북을 읽을 수 없습니다: {exc}")
        return None
    bar.progress(1.0, text="분석 완료")
    status.update(label="분석 완료 — 결과 화면으로 이동합니다", state="complete", expanded=False)
    return result


if workbook_file is not None:
    fingerprint = (getattr(workbook_file, "file_id", None) or (workbook_file.name, workbook_file.size), period_input)
    if st.session_state.get("analyzed_fingerprint") != fingerprint:
        ingest_result = _analyze(workbook_file, period_input)
        if ingest_result is not None:
            st.session_state["ingest_result"] = ingest_result
            st.session_state["기준연월"] = period_input
            st.session_state["analyzed_fingerprint"] = fingerprint
            st.session_state["just_analyzed"] = True
            time.sleep(0.4)  # "분석 완료" 상태를 잠깐이라도 보여주고 넘어간다.
            st.switch_page("views/analysis.py")
    else:
        st.success(f"이 워크북({period_input})은 이미 분석했습니다. 다른 파일을 올리거나 기준연월을 바꾸면 다시 분석합니다.")
        st.page_link("views/analysis.py", label="분석 결과 보기 →", icon="📊")
else:
    st.info("워크북을 올리면 분석이 끝나는 대로 결과 화면으로 이동합니다.")
    if "ingest_result" in st.session_state:
        st.page_link(
            "views/analysis.py",
            label=f"이전에 올린 {st.session_state.get('기준연월', '')} 분석 결과 다시 보기 →",
            icon="📊",
        )
