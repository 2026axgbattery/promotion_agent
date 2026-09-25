"""여러 페이지(실적 업로드/분석 결과/이력 조회)가 함께 쓰는 렌더링 헬퍼.

Streamlit의 `st.navigation` 기반 다중 페이지 구조에서는 각 페이지 스크립트가
독립적으로 실행되므로, 공통 표시 로직(디자인 시스템 CSS 주입, 표 컬럼 서식,
KPI·총평·편차 원인 구분·기간 비교·이력 조회 렌더링)을 여기 모아두고 각 페이지가
가져다 쓴다.
"""

from __future__ import annotations

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from app import db

_DESIGN_SYSTEM_CSS_PATH = Path(__file__).resolve().parents[1] / "sebang-design-system" / "sebang.css"

# design.md 1.2절의 "SEBANG" 단독 워드마크(공식 CI 벡터 `SEBANG_CI_251021.ai`에서 추출,
# 잉크 색 #1F3742 실측 확인)를 그대로 쓴다 — 로고를 텍스트로 다시 그리지 않는다(design.md
# 7절 금지 사항 2번).
_SEBANG_WORDMARK_SVG = """
<svg viewBox="0 0 595.276 231.696" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="SEBANG">
  <path fill="currentColor" d="M 124.988281 126.054688 C 123.054688 122.753906 119.492188 120.503906 114.375 119.367188 L 84.269531 112.652344 C 81.96875 112.136719 80.734375 111.574219 80.273438 110.824219 C 80.003906 110.386719 79.96875 109.835938 80.148438 109.148438 L 81.5625 105.273438 L 131.269531 105.273438 L 138.089844 84.414062 L 84.535156 84.414062 C 76.113281 84.414062 70.261719 85.457031 66.125 87.707031 C 61.179688 90.398438 57.871094 94.660156 56.019531 100.742188 L 53.300781 109.199219 C 51.847656 113.941406 52.394531 119.035156 54.789062 123.179688 C 57.144531 127.242188 60.996094 129.984375 65.910156 131.109375 L 94.691406 137.535156 C 96.339844 137.882812 97.414062 138.433594 97.878906 139.167969 C 98.167969 139.613281 98.226562 140.140625 98.089844 140.726562 L 96.664062 145.066406 L 46.699219 145.066406 L 39.976562 165.894531 L 91.207031 165.894531 C 102.574219 165.894531 108.519531 165.3125 113.71875 161.8125 C 119.089844 158.203125 121.214844 152.398438 123.253906 145.734375 L 125.683594 137.570312 C 127.023438 133.136719 126.78125 129.152344 124.988281 126.054688 "/>
  <path fill="currentColor" d="M 347.71875 154.867188 L 326.140625 154.867188 L 331.789062 140.066406 C 332.9375 137.015625 333.984375 135.929688 337.53125 135.929688 L 353.6875 135.929688 Z M 380.507812 119.90625 C 378.179688 116.730469 374.046875 115.117188 368.21875 115.117188 L 332.945312 115.117188 C 320.570312 115.117188 312.644531 120.042969 308.710938 130.207031 L 282.8125 196.617188 L 310.128906 196.617188 L 318.355469 175.246094 L 341.074219 175.246094 L 334.207031 196.617188 L 360.980469 196.617188 L 381.488281 132.738281 C 383.140625 127.484375 382.808594 123.039062 380.507812 119.90625 "/>
  <path fill="currentColor" d="M 509.464844 136.003906 L 548.054688 136.003906 L 554.925781 115.117188 L 503.15625 115.117188 C 491.136719 115.117188 484.535156 119.425781 481.058594 129.535156 L 464.992188 179.796875 C 463.464844 184.363281 463.847656 188.574219 466.070312 191.671875 C 468.382812 194.882812 472.429688 196.585938 477.765625 196.585938 L 513.4375 196.585938 C 521.953125 196.585938 525.527344 196.0625 529.375 194.261719 C 534.035156 192.085938 536.683594 188.644531 538.820312 181.988281 L 546.675781 157.476562 C 547.824219 153.910156 547.648438 151.046875 546.140625 148.980469 C 544.597656 146.859375 541.757812 145.734375 537.917969 145.734375 L 512.539062 145.734375 L 506.097656 165.859375 L 517.222656 165.859375 L 514.71875 173.722656 C 514.128906 175.375 513.625 175.683594 511.53125 175.683594 L 493.078125 175.683594 L 504.855469 139.027344 C 505.691406 136.457031 507.015625 136.003906 509.464844 136.003906 "/>
  <path fill="currentColor" d="M 447.175781 115.117188 L 434.335938 155.144531 L 424.21875 120.222656 C 423.285156 116.882812 420.730469 115.117188 416.828125 115.117188 L 399.117188 115.117188 L 373.203125 195.882812 L 372.984375 196.582031 L 399.742188 196.582031 L 412.410156 157.117188 L 422.769531 191.714844 C 423.328125 193.535156 424.980469 196.582031 429.792969 196.582031 L 447.804688 196.582031 L 473.941406 115.117188 Z M 447.175781 115.117188 "/>
  <path fill="currentColor" d="M 255.085938 172.742188 C 254.132812 175.535156 252.683594 175.675781 250.398438 175.675781 L 230.8125 175.675781 L 233.957031 165.878906 L 257.300781 165.878906 Z M 294.84375 119.371094 C 292.828125 116.625 289 115.117188 284.054688 115.117188 L 169.433594 115.117188 L 171.898438 107.378906 C 172.519531 105.367188 173.898438 105.269531 176.292969 105.269531 L 215.359375 105.269531 L 222.046875 84.414062 L 175.734375 84.414062 C 167.316406 84.414062 161.460938 85.457031 157.324219 87.707031 C 152.382812 90.398438 149.066406 94.664062 147.210938 100.746094 L 126.296875 165.878906 L 196.300781 165.878906 L 202.992188 145.0625 L 159.882812 145.0625 L 163.023438 135.230469 L 267.136719 135.230469 L 264.605469 143.070312 C 264.179688 144.363281 263.558594 145.0625 261.535156 145.0625 L 213.859375 145.082031 L 197.34375 196.617188 L 251.054688 196.617188 C 261.484375 196.617188 266.25 195.878906 270.664062 193.582031 C 274.40625 191.644531 276.871094 188.230469 278.664062 182.527344 L 282.601562 170.21875 C 283.867188 166.453125 284.804688 162.164062 282.1875 158.976562 L 279.359375 155.8125 L 283.808594 152.714844 C 288.523438 149.699219 289.851562 147.917969 291.671875 142.113281 L 295.675781 129.585938 C 296.992188 125.433594 296.699219 121.898438 294.84375 119.371094 "/>
</svg>
""".strip()


# Streamlit 기본 st.metric 값 글씨(약 2.25rem)가 "핵심 지표"·"프로모션 효과" 카드처럼
# 좁은 컬럼에 큰 금액(예: "5,342,788")이 들어가면 폭을 넘어 잘려 보인다(사용자 확인) —
# 원화 표시가 없어 숫자 자릿수가 길어질수록 더 잘 생기는 문제다. 글씨는 작아져도 되니
# (사용자 확인) 잘리지 않고 다 보이도록, 값 글씨 크기를 줄이고 줄바꿈을 허용한다.
_METRIC_FONT_FIX_CSS = """
<style>
div[data-testid="stMetricValue"] {
    font-size: clamp(1rem, 2.4vw, 1.5rem);
    white-space: normal;
    overflow-wrap: break-word;
    line-height: 1.25;
}
div[data-testid="stMetricLabel"] {
    white-space: normal;
    overflow-wrap: break-word;
}
</style>
"""


@st.cache_data
def _load_design_system_css() -> str:
    """`sebang-design-system/sebang.css`는 색상·간격 CSS 변수(`--sebang-ink` 등)를
    담고 있다(`design.md` UI 규칙) — 브랜드 헤더 등 직접 그리는 HTML에서 이 변수를
    쓴다. 기본 폰트는 이제 `.streamlit/config.toml`의 `[theme.fontFaces]`로 등록해
    Streamlit 전체(캔버스로 그려지는 st.dataframe 포함)에 적용되므로, 여기서 CSS로
    다시 강제하지 않는다 — 예전엔 `.stApp *`에 강제 적용했다가 아이콘 리가처가
    깨지는 부작용이 있었다."""
    return f"<style>{_DESIGN_SYSTEM_CSS_PATH.read_text(encoding='utf-8')}</style>{_METRIC_FONT_FIX_CSS}"


def inject_design_system_css() -> None:
    """페이지마다 독립 실행되므로, 각 페이지 스크립트 맨 앞에서 호출해야 한다."""
    st.markdown(_load_design_system_css(), unsafe_allow_html=True)


def render_brand_header() -> None:
    """사이드바에 SEBANG 워드마크 + "세방전지(주)" 조합 로고를 보여준다 — design.md
    1.3절 "헤더/사이드바 등 브랜드 노출 영역에는 항상 벡터 워드마크를 사용" 원칙."""
    with st.sidebar:
        st.markdown(
            f"""
            <div style="padding:4px 4px 12px; color:#1F3742;">
              <div style="width:110px;">{_SEBANG_WORDMARK_SVG}</div>
              <div style="font-weight:700; font-size:0.8125rem; letter-spacing:0.02em; margin-top:4px;">
                세방전지(주)
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


_MONEY_COLUMNS = [
    "매출액", "영업이익", "매출원가", "DC지원금액", "프로모션지원금액", "총지원금액", "전월매출",
    "전년동월매출", "지원단가", "지원금액", "현재단가", "다음구간단가",
]
_PERCENT_COLUMNS = ["영업이익율", "매출DC율", "성장DC율", "DC율", "원가율", "매출증감율", "전년동월매출증감율"]
_COUNT_COLUMNS = ["판매수량", "대리점수", "현재수량", "다음구간까지"]


def column_config(df) -> dict:
    """금액·수량 컬럼은 천 단위 콤마(원화 기호 없이), 비율 컬럼은 %로 표시한다
    (PRD 6.4절 "지표를 나란히" 요구사항).

    컬럼 폭도 함께 고정한다 — 폭을 Streamlit이 자동으로 좁게 잡으면 "1,850,028,329"처럼
    자릿수 큰 금액이 셀 안에서 줄바꿈되거나 잘려, 같은 컬럼의 값들이 서로 다른 줄 높이로
    보여 가독성이 떨어진다는 피드백을 반영했다(대리점 단위 결과 표처럼 컬럼이 많을 때
    특히 두드러진다). 금액은 가장 큰 자릿수 기준으로 넉넉하게, 비율·수량은 좁게 잡는다."""
    config = {}
    for col in df.columns:
        if col in _MONEY_COLUMNS:
            config[col] = st.column_config.NumberColumn(col, format="%,.0f", width=130)
        elif col in _PERCENT_COLUMNS:
            config[col] = st.column_config.NumberColumn(col, format="%.1f%%", width=95)
        elif col in _COUNT_COLUMNS:
            config[col] = st.column_config.NumberColumn(col, format="%,.0f", width=95)
    return config


def format_metric_value(value: float | None, unit: str) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.0f}" if unit == "₩" else f"{value:.1f}%"


def format_delta(a: float | None, b: float | None, unit: str) -> str | None:
    if a is None or b is None:
        return None
    delta = a - b
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:,.0f}" if unit == "₩" else f"{sign}{delta:.1f}%p"


def _render_kpi_summary(sales_like) -> None:
    total_revenue = sales_like["매출액"].sum()
    total_profit = sales_like["영업이익"].sum()
    avg_op = (total_profit / total_revenue * 100) if total_revenue else float("nan")
    total_dc = sales_like["DC지원금액"].sum()
    total_promo = sales_like["프로모션지원금액"].sum()
    total_support = sales_like["총지원금액"].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("대리점 수", f"{sales_like['대리점코드'].nunique()}곳")
    c2.metric("평균 영업이익율", "N/A" if total_revenue == 0 else f"{avg_op:.1f}%")
    c3.metric("총 지원금액", f"{total_support:,.0f}")
    c4.metric("DC / 프로모션 지원금액", f"{total_dc:,.0f} / {total_promo:,.0f}")


def _render_promotion_notice(result, 기준연월: str) -> None:
    """워크북의 "프로모션 기준" 시트 내용을 보여준다(구조화된 표면 "▶ 프로모션명"
    블록으로, 아직 줄글이면 원문 그대로)."""
    st.subheader(f"{기준연월} 프로모션 시행 내용")
    if not result.promotion_notice:
        st.write("프로모션 기준 시트가 없어 표시할 내용이 없습니다.")
        return
    with st.container(border=True):
        for line in result.promotion_notice:
            st.write(line)


_DC_지원유형 = ["매출DC", "성장DC"]


def _support_subtotal(applied_support: pd.DataFrame) -> pd.DataFrame:
    """지원유형별 지원금액 소계 + DC 합계·프로모션 합계·총 지원금액을 만든다."""
    if applied_support.empty:
        return pd.DataFrame(columns=["지원유형", "지원금액"])

    by_type = applied_support.groupby("지원유형", as_index=False)["지원금액"].sum()
    dc_total = by_type.loc[by_type["지원유형"].isin(_DC_지원유형), "지원금액"].sum()
    promo_total = by_type.loc[~by_type["지원유형"].isin(_DC_지원유형), "지원금액"].sum()

    totals = pd.DataFrame(
        [
            {"지원유형": "DC 합계(매출DC+성장DC)", "지원금액": dc_total},
            {"지원유형": "프로모션 합계(10+1+대형제품+특화제품+기타+추가+그 외)", "지원금액": promo_total},
            {"지원유형": "총 지원금액", "지원금액": dc_total + promo_total},
        ]
    )
    return pd.concat([by_type, totals], ignore_index=True)


def _group_stats(df: pd.DataFrame) -> dict:
    """대리점 그룹(해당/미해당 등)의 매출액 가중 영업이익율·매출증감율을 계산한다.
    영업이익·전월매출이 전부 비어 있으면(이 워크북에 없는 경우) None으로 둔다 — pandas의
    `sum()`은 전부 NaN이어도 0을 돌려줘 착각하기 쉽다."""
    매출액 = df["매출액"].sum()
    총지원금액 = df["총지원금액"].sum()
    if df["영업이익"].isna().all():
        영업이익율 = None
    else:
        영업이익율 = (df["영업이익"].sum() / 매출액 * 100) if 매출액 else None
    if df["전월매출"].isna().all():
        매출증감율 = None
        전월매출 = None
    else:
        전월매출 = df["전월매출"].sum()
        매출증감율 = ((매출액 - 전월매출) / 전월매출 * 100) if 전월매출 else None
    return {
        "대리점수": len(df),
        "매출액": 매출액,
        "전월매출": 전월매출,
        "영업이익율": 영업이익율,
        "매출증감율": 매출증감율,
        "총지원금액": 총지원금액,
    }


def _render_promotion_effect_summary(sales_like: pd.DataFrame) -> None:
    """프로모션 지원을 받은 대리점과 안 받은 대리점을 비교해 이번 달 프로모션 효과를
    총평으로 보여준다(HTML 목업 "이번 달 프로모션 효과 평가(본사 관점)" 대응). DC
    지원금액은 매출만 있으면 사실상 모든 대리점에 붙는 값이라 "해당/미해당"을 가르는
    기준으로 쓰면 안 된다 — 프로모션 지원금액 유무로만 나눈다."""
    st.subheader("이번 달 프로모션 효과 평가 (본사 관점) — 총평")
    yes = sales_like[sales_like["프로모션지원금액"] > 0]
    no = sales_like[sales_like["프로모션지원금액"] == 0]
    if yes.empty or no.empty:
        st.info("이번 달은 대리점 전체가 프로모션 지원 대상이거나 전부 미대상이라 해당/미해당 비교를 할 수 없습니다.")
        return

    yes_stats, no_stats = _group_stats(yes), _group_stats(no)
    op_gap = (
        yes_stats["영업이익율"] - no_stats["영업이익율"]
        if yes_stats["영업이익율"] is not None and no_stats["영업이익율"] is not None
        else None
    )
    growth_gap = (
        yes_stats["매출증감율"] - no_stats["매출증감율"]
        if yes_stats["매출증감율"] is not None and no_stats["매출증감율"] is not None
        else None
    )
    # ROI(추정) = 미해당 그룹 수준의 자연 성장률을 넘어선 초과 성장분을 지원 덕분으로 보고,
    # 그 초과 성장분(원)을 해당 그룹 총지원금액으로 나눈 값이다 — 엄밀한 인과 추정이 아니라
    # 참고용 근사치다.
    roi = None
    if growth_gap is not None and yes_stats["전월매출"] and yes_stats["총지원금액"]:
        초과성장금액 = growth_gap / 100 * yes_stats["전월매출"]
        roi = 초과성장금액 / yes_stats["총지원금액"]

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "해당 vs 미해당 · 영업이익율",
        f"{op_gap:+.1f}%p" if op_gap is not None else "N/A",
        help=f"해당 {format_metric_value(yes_stats['영업이익율'], '%')} · 미해당 {format_metric_value(no_stats['영업이익율'], '%')}",
    )
    c2.metric(
        "해당 vs 미해당 · 매출증감율",
        f"{growth_gap:+.1f}%p" if growth_gap is not None else "N/A",
        help=f"해당 {format_metric_value(yes_stats['매출증감율'], '%')} · 미해당 {format_metric_value(no_stats['매출증감율'], '%')}",
    )
    c3.metric(
        "프로모션 ROI (추정)",
        f"{roi:.1f}x" if roi is not None else "N/A",
        help="지원금액 1원당, 미해당 그룹 대비 초과 매출 증가분(추정)",
    )
    st.caption(f"지원 해당 대리점 {yes_stats['대리점수']}곳 · 미해당 {no_stats['대리점수']}곳")


def _render_deviation_comparison(sales_like: pd.DataFrame) -> None:
    """대리점을 2개 이상 선택해 DC 구성·지원금액·영업이익율·매출증감율을 비교하고,
    차이가 DC율 때문인지 지원 유무 때문인지 짧은 총평을 보여준다."""
    st.subheader("편차 원인 구분 — DC율 차이 vs 지원 조건 차이")
    labels = sales_like["대리점명"].astype(str) + " (" + sales_like["대리점코드"].astype(str) + ")"
    label_to_index = dict(zip(labels, sales_like.index))
    default = labels.tolist()[:2]
    selected = st.multiselect("비교할 대리점 선택 (2개 이상)", labels.tolist(), default=default, key="deviation_compare")
    if len(selected) < 2:
        st.info("비교하려면 대리점을 2개 이상 선택하세요.")
        return

    subset = sales_like.loc[[label_to_index[label] for label in selected]]
    display_cols = [
        "대리점명", "매출DC율", "성장DC율", "DC지원금액", "프로모션지원금액", "총지원금액", "영업이익율", "매출증감율",
    ]
    st.dataframe(subset[display_cols], width="stretch", column_config=column_config(subset), hide_index=True)

    parts = []
    if not subset["영업이익율"].isna().all():
        max_row = subset.loc[subset["영업이익율"].idxmax()]
        min_row = subset.loc[subset["영업이익율"].idxmin()]
        parts.append(
            f"선택된 {len(subset)}개 대리점 중 영업이익율이 가장 높은 곳은 **{max_row['대리점명']}**"
            f"({max_row['영업이익율']:.1f}%), 가장 낮은 곳은 **{min_row['대리점명']}**({min_row['영업이익율']:.1f}%)입니다."
        )
    dc_조합 = set(zip(subset["매출DC율"].round(2), subset["성장DC율"].round(2)))
    if len(dc_조합) > 1:
        parts.append("선택된 대리점 간 **DC율 구성 자체가 다릅니다** — 매출 규모 구간과 성장 실적 차이에서 비롯됩니다(등급 차이가 아님).")
    if subset["총지원금액"].gt(0).nunique() > 1:
        parts.append("또한 일부 대리점만 이번 달 지원(DC 또는 프로모션)을 받아 총지원금액 차이가 발생했습니다.")
    st.info(" ".join(parts) if parts else "선택한 대리점들의 DC율·지원 여부가 서로 비슷합니다.")


def _render_promotion_insight(promotion_insight: list[str]) -> None:
    """산식유형별 구조적 장단점 + 이번 달 데이터 신호를 함께 보여준다. 차기 설계안을
    시스템이 대신 결정하는 게 아니라(PRD 3절 비목표), 팀장의 판단을 돕는 참고 의견일
    뿐이라는 점을 캡션으로 명시한다."""
    st.subheader("이 프로모션들의 장단점 (참고 의견)")
    st.caption("차기 설계를 대신 결정하는 게 아니라, 판단에 참고할 의견입니다 — 최종 결정은 팀장님 몫입니다.")
    if not promotion_insight:
        st.write("프로모션 기준 시트가 없어 장단점을 정리할 수 없습니다.")
        return
    for line in promotion_insight:
        st.write(line)


def _render_threshold_proximity(threshold_proximity: pd.DataFrame) -> None:
    """구간별단가(절대수량)·연동형(AGM Lv 등) 규칙의 "다음 구간까지 얼마나 남았는지"를
    보여준다 — 이 프로모션이 실제로 추가 구매를 유도하고 있는지 직접 보여주는 지표다
    (`.docs/16_교차검증_보완_계획서.md`·`19_최종백데이터_전환_계획서.md`). 다음 구간까지
    남은 수량이 적은 순으로 정렬돼 있어, 위쪽에 나오는 대상일수록 조금만 더 팔면
    다음 구간(더 높은 지원단가)에 도달한다."""
    st.subheader("프로모션 문턱값 근접도 (다음 구간까지 남은 수량)")
    if threshold_proximity.empty:
        st.write("구간별 문턱값이 있는 규칙(구간별단가/연동형)이 없어 근접도를 볼 수 없습니다.")
        return
    st.caption(
        "\"다음구간까지\"가 작을수록 조금만 더 팔면 더 높은 지원단가 구간에 도달한다는 뜻입니다 — "
        "문턱값을 낮추거나 기간을 늘리는 차기 설계 논의에 참고하세요."
    )
    st.dataframe(
        threshold_proximity, width="stretch", column_config=column_config(threshold_proximity), hide_index=True
    )


def _render_op_growth_scatter(sales_like: pd.DataFrame) -> None:
    """영업이익율×매출증감율 산점도 — 프로모션 해당/미해당을 색으로 구분해 "매출은
    늘었지만 이익률은 깎인" 손익-매출 트레이드오프 패턴을 시각적으로 보여준다."""
    st.subheader("영업이익율 × 매출증감율 (프로모션 해당 여부)")
    df = sales_like.dropna(subset=["영업이익율", "매출증감율"]).copy()
    if df.empty:
        st.write("영업이익율·매출증감율 데이터가 없어 표시할 수 없습니다.")
        return
    df["프로모션 해당"] = df["프로모션지원금액"].apply(lambda v: "해당" if v > 0 else "미해당")
    chart = (
        alt.Chart(df)
        .mark_circle(size=90, opacity=0.7)
        .encode(
            x=alt.X("매출증감율:Q", title="매출증감율(%)"),
            y=alt.Y("영업이익율:Q", title="영업이익율(%)"),
            color=alt.Color(
                "프로모션 해당:N",
                scale=alt.Scale(domain=["해당", "미해당"], range=["#0097A9", "#B5BBBD"]),
            ),
            tooltip=["대리점명", "매출증감율", "영업이익율", "총지원금액"],
        )
        .properties(height=380)
        # Altair/Vega는 SVG에 자체 폰트를 지정해 페이지 CSS를 상속하지 않는다 —
        # 전 항목을 세방고딕으로 맞추려면 차트에도 명시해야 한다.
        .configure(font="SEBANG Gothic, Pretendard, Noto Sans KR, sans-serif")
    )
    st.altair_chart(chart, width="stretch")


_STORE_GROUP_ORDER = ["우수 (15%+)", "보통 (0~15%)", "저조 (0% 미만)"]


def _bucket_영업이익율(value: float) -> str:
    if value >= 15:
        return _STORE_GROUP_ORDER[0]
    if value >= 0:
        return _STORE_GROUP_ORDER[1]
    return _STORE_GROUP_ORDER[2]


def _render_store_groups(sales_like: pd.DataFrame) -> None:
    """대리점을 영업이익율 구간(우수/보통/저조)으로 묶어 그룹별 효과를 비교한다
    (PRD 6.7절). 저조 그룹의 평균 총지원금액이 우수 그룹 못지않은데 영업이익율이
    낮다면, 그 그룹엔 이번 지원 설계가 잘 안 먹혔다는 뜻이다."""
    st.subheader("대리점 그룹별 효과 비교 (영업이익율 구간)")
    df = sales_like.dropna(subset=["영업이익율"]).copy()
    if df.empty:
        st.write("영업이익율 데이터가 없어 그룹별 비교를 할 수 없습니다.")
        return
    df["그룹"] = df["영업이익율"].apply(_bucket_영업이익율)
    summary = df.groupby("그룹", as_index=False).agg(
        대리점수=("대리점코드", "nunique"),
        평균영업이익율=("영업이익율", "mean"),
        평균매출증감율=("매출증감율", "mean"),
        평균총지원금액=("총지원금액", "mean"),
    )
    summary["그룹"] = pd.Categorical(summary["그룹"], categories=_STORE_GROUP_ORDER, ordered=True)
    summary = summary.sort_values("그룹").rename(
        columns={"평균영업이익율": "영업이익율", "평균매출증감율": "매출증감율", "평균총지원금액": "총지원금액"}
    )
    st.dataframe(
        summary,
        width="stretch",
        column_config=column_config(summary),
        hide_index=True,
    )


def render_analysis(result, 기준연월: str) -> None:
    """분석 결과 페이지 전체(프로모션 안내부터 DB 저장 버튼까지)를 렌더링한다.

    구획별로 `st.header` + `st.divider()`로 큰 덩어리를 나누고, 그 안의 각 표/차트는
    `st.container(border=True)`로 카드처럼 테두리를 둘러 구분한다 — 소제목만 죽 나열
    되어 있으면 어디서 한 주제가 끝나는지 구별이 안 된다는 사용자 피드백을 반영했다."""
    with st.container(border=True):
        _render_promotion_notice(result, 기준연월)

    st.divider()
    st.header("이번 달 요약")
    with st.container(border=True):
        st.subheader("핵심 지표")
        _render_kpi_summary(result.sales_like)
    with st.container(border=True):
        _render_promotion_effect_summary(result.sales_like)

    st.divider()
    st.header("대리점 단위 결과")
    with st.container(border=True):
        st.subheader("대리점 단위 요약")
        st.caption("컬럼이 많아 가로로 스크롤됩니다 — 대리점명은 고정돼 있어 스크롤 중에도 어느 줄인지 알 수 있습니다.")
        main_table_config = column_config(result.sales_like)
        main_table_config["대리점명"] = st.column_config.TextColumn("대리점명", pinned=True, width=110)
        st.dataframe(
            result.sales_like,
            width="stretch",
            column_config=main_table_config,
        )
    for w in result.warnings:
        st.info(w)

    st.divider()
    st.header("지원금액 내역")
    with st.container(border=True):
        st.subheader("지원유형별 지원금액 내역")
        if result.applied_support.empty:
            st.write("지원 내역이 없습니다.")
        else:
            detail = result.applied_support.drop(columns=["제품코드", "지원단가"])
            st.dataframe(
                detail,
                width="stretch",
                column_config=column_config(detail),
            )

            st.caption("유형별 소계")
            subtotal = _support_subtotal(result.applied_support)
            st.dataframe(
                subtotal,
                width="stretch",
                column_config=column_config(subtotal),
                hide_index=True,
            )

    with st.container(border=True):
        st.subheader("제품군별 판매수량 · 지원금액 (전사 합계, 대리점 구분 없음)")
        if result.product_group_support.empty:
            st.write("제품군별 요약을 계산할 수 없습니다(백데이터 시트 확인 필요).")
        else:
            st.dataframe(
                result.product_group_support,
                width="stretch",
                column_config=column_config(result.product_group_support),
            )

    st.divider()
    st.header("교차 분석")
    with st.container(border=True):
        _render_threshold_proximity(result.threshold_proximity)
    with st.container(border=True):
        _render_op_growth_scatter(result.sales_like)
    with st.container(border=True):
        _render_store_groups(result.sales_like)
    with st.container(border=True):
        _render_deviation_comparison(result.sales_like)

    st.divider()
    st.header("프로모션 장단점 분석")
    with st.container(border=True):
        _render_promotion_insight(result.promotion_insight)

    st.divider()
    st.header("저장")
    if st.button("DuckDB에 저장", type="primary"):
        con = db.init_db()
        sales_cols = [
            "기준연월", "대리점코드", "대리점명", "판매수량", "전월매출", "매출액", "매출증감율",
            "전년동월매출", "전년동월매출증감율",
            "매출DC율", "성장DC율", "DC율", "원가율", "영업이익", "영업이익율",
            "DC지원금액", "프로모션지원금액", "총지원금액",
        ]
        db.replace_period_data(
            con,
            기준연월=기준연월,
            sales_df=result.sales_like[sales_cols],
            applied_support_df=result.applied_support,
        )
        st.success(f"기준연월 {기준연월} 결과를 저장했습니다. 저장된 기준연월: {db.saved_periods(con)}")


# ---------------------------------------------------------------------------
# 프로모션 효과 비교 — DuckDB에 저장된 기준연월 중 두 개를 골라 전사 합계 지표를
# 나란히 비교한다. 업로드한 워크북과 무관하게, DB에 이미 저장된 이력만 있으면
# 바로 쓸 수 있다(전월 대비·저번 같은 프로모션 시행월 대비 등 자유롭게 선택).
# ---------------------------------------------------------------------------

_COMPARISON_METRICS = [
    ("매출액", "₩"),
    ("영업이익", "₩"),
    ("영업이익율", "%"),
    ("DC지원금액", "₩"),
    ("DC율", "%"),
    ("프로모션지원금액", "₩"),
    ("총지원금액", "₩"),
]


def render_period_comparison() -> None:
    st.header("프로모션 효과 비교 (기준연월 간)")
    st.caption("DuckDB에 저장된 기준연월 중 두 개를 골라 전사 합계 지표를 비교합니다 — 전월 대비, 저번 같은 프로모션 시행월 대비 등 자유롭게 선택하세요.")

    con = db.init_db()
    periods = db.saved_periods(con)
    if len(periods) < 2:
        st.info(f"비교하려면 최소 2개 기준연월의 분석 결과가 저장되어 있어야 합니다. 현재 저장된 기준연월: {periods or '없음'}")
        return

    with st.container(border=True):
        col_a, col_b = st.columns(2)
        with col_a:
            period_a = st.selectbox("이번 달(기준)", periods, index=0, key="cmp_period_a")
        with col_b:
            period_b = st.selectbox("비교 대상월", periods, index=1, key="cmp_period_b")

        if period_a == period_b:
            st.warning("서로 다른 두 기준연월을 선택하세요.")
            return

        summary_a = db.period_summary(con, period_a)
        summary_b = db.period_summary(con, period_b)

        cols = st.columns(len(_COMPARISON_METRICS))
        for col, (metric, unit) in zip(cols, _COMPARISON_METRICS):
            a_val = summary_a[metric]
            b_val = summary_b[metric]
            col.metric(
                f"{metric} ({period_a})",
                format_metric_value(a_val, unit),
                delta=format_delta(a_val, b_val, unit),
                help=f"{period_b} 대비 증감",
            )


# ---------------------------------------------------------------------------
# 이력 조회 — DuckDB에 저장된 기준연월들을 한눈에 훑어보고(개요 표), 하나를 골라
# 재업로드 없이 그 시점 대리점 단위 결과를 다시 불러온다.
# ---------------------------------------------------------------------------

_HISTORY_OVERVIEW_COLUMNS = [
    "기준연월", "대리점수", "매출액", "영업이익율", "DC지원금액", "프로모션지원금액", "총지원금액",
]


def render_history_view() -> None:
    st.header("이력 조회")
    st.caption("DuckDB에 저장된 기준연월을 골라 재업로드 없이 그때 저장된 대리점 단위 결과를 다시 조회합니다.")

    con = db.init_db()
    periods = db.saved_periods(con)
    if not periods:
        st.info("아직 저장된 분석 결과가 없습니다. 워크북을 분석하고 'DuckDB에 저장'을 눌러야 이력에 나타납니다.")
        return

    with st.container(border=True):
        st.subheader("기준연월별 개요")
        overview = pd.DataFrame([db.period_summary(con, p) for p in periods])[_HISTORY_OVERVIEW_COLUMNS]
        st.dataframe(overview, width="stretch", column_config=column_config(overview), hide_index=True)

    with st.container(border=True):
        st.subheader("기준연월 상세 조회")
        selected_period = st.selectbox("상세 조회할 기준연월", periods, key="history_period")
        summary = db.period_summary(con, selected_period)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("대리점 수", f"{summary['대리점수']}곳")
        c2.metric("평균 영업이익율", format_metric_value(summary["영업이익율"], "%"))
        c3.metric("총 지원금액", format_metric_value(summary["총지원금액"], "₩"))
        c4.metric(
            "DC / 프로모션 지원금액",
            f"{format_metric_value(summary['DC지원금액'], '₩')} / {format_metric_value(summary['프로모션지원금액'], '₩')}",
        )

        stored = con.execute(
            "SELECT * FROM sales_record WHERE 기준연월 = ? ORDER BY 대리점코드", [selected_period]
        ).fetchdf()
        st.dataframe(stored, width="stretch", column_config=column_config(stored))
