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

from app import dashboard, db

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


@st.cache_data
def _load_design_system_css() -> str:
    """`sebang-design-system/sebang.css`는 색상·간격 CSS 변수(`--sebang-ink` 등)를
    담고 있다(`design.md` UI 규칙) — 브랜드 헤더 등 직접 그리는 HTML에서 이 변수를
    쓴다. 기본 폰트는 이제 `.streamlit/config.toml`의 `[theme.fontFaces]`로 등록해
    Streamlit 전체(캔버스로 그려지는 st.dataframe 포함)에 적용되므로, 여기서 CSS로
    다시 강제하지 않는다 — 예전엔 `.stApp *`에 강제 적용했다가 아이콘 리가처가
    깨지는 부작용이 있었다."""
    return f"<style>{_DESIGN_SYSTEM_CSS_PATH.read_text(encoding='utf-8')}</style>"


def inject_design_system_css() -> None:
    """페이지마다 독립 실행되므로, 각 페이지 스크립트 맨 앞에서 호출해야 한다. 대시보드
    카드·차트 스타일(`app/dashboard.py`)도 함께 넣는다 — st.metric 값 글씨가 좁은 칸에서
    잘리지 않게 줄이는 규칙(사용자 확인)도 그 안에 들어 있다."""
    st.markdown(_load_design_system_css(), unsafe_allow_html=True)
    st.html(dashboard.DASHBOARD_CSS)


def render_brand_header() -> None:
    """사이드바에 SEBANG 워드마크 + "세방전지(주)" 조합 로고를 보여준다 — design.md
    1.3절 "헤더/사이드바 등 브랜드 노출 영역에는 항상 벡터 워드마크를 사용" 원칙.
    사이드바는 어두운 Ink 배경(`.streamlit/config.toml` [theme.sidebar])이라 design.md
    1.2·5절대로 흰색 워드마크를 쓴다."""
    with st.sidebar:
        st.markdown(
            f"""
            <div style="padding:4px 4px 12px; color:#FFFFFF;">
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
            {"지원유형": "프로모션 합계", "지원금액": promo_total},
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


def _effect_stats(sales_like: pd.DataFrame) -> dict | None:
    """프로모션 지원을 받은 대리점과 안 받은 대리점을 비교한다(HTML 목업 "이번 달 프로모션
    효과 평가(본사 관점)" 대응). DC 지원금액은 매출만 있으면 사실상 모든 대리점에 붙는
    값이라 "해당/미해당"을 가르는 기준으로 쓰면 안 된다 — 프로모션 지원금액 유무로만 나눈다.
    한쪽 그룹이 비면 비교할 수 없어 None."""
    yes = sales_like[sales_like["프로모션지원금액"] > 0]
    no = sales_like[sales_like["프로모션지원금액"] == 0]
    if yes.empty or no.empty:
        return None
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
        roi = (growth_gap / 100 * yes_stats["전월매출"]) / yes_stats["총지원금액"]
    return {"yes": yes_stats, "no": no_stats, "op_gap": op_gap, "growth_gap": growth_gap, "roi": roi}


def _render_deviation_comparison(sales_like: pd.DataFrame) -> None:
    """대리점을 2개 이상 선택해 DC 구성·지원금액·영업이익율·매출증감율을 비교하고,
    차이가 DC율 때문인지 지원 유무 때문인지 짧은 총평을 보여준다."""
    st.subheader("편차 원인 구분 — DC율 차이 vs 지원 조건 차이")
    st.caption("대리점을 골라 DC 구성과 지원 여부 중 무엇이 차이를 만들었는지 비교합니다.")
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


_CHART_FONT = "SEBANG Gothic, Pretendard, Noto Sans KR, sans-serif"
_SCATTER_GROWTH_LIMIT = 300


def _render_op_growth_scatter(sales_like: pd.DataFrame) -> None:
    """영업이익율×매출증감율 산점도 — 프로모션 해당 대리점만 Green, 나머지는 회색으로
    두는 강조(emphasis) 방식이다(dataviz: 하나를 강조하고 나머지는 회색). 점에 흰색
    2px 테두리(겹칠 때 구분), 0% 기준선은 가는 실선, 격자는 배경보다 한 단계만 진하게."""
    st.subheader("영업이익율 × 매출증감율 (프로모션 해당 여부)")
    st.caption("오른쪽 위일수록 매출도 늘고 이익률도 높은 대리점입니다 — 점에 마우스를 올리면 대리점명이 보입니다.")
    df = sales_like.dropna(subset=["영업이익율", "매출증감율"]).copy()
    if df.empty:
        st.write("영업이익율·매출증감율 데이터가 없어 표시할 수 없습니다.")
        return
    df["프로모션 해당"] = df["프로모션지원금액"].apply(lambda v: "해당" if v > 0 else "미해당")
    # 전월 매출이 거의 없던 대리점은 증감율이 수백~수천 %로 튀어 나머지 점을 한쪽으로 몰아
    # 버린다 — 차트에서는 빼고 어느 대리점이 빠졌는지 캡션으로 밝힌다(값은 상세 데이터 표에 있음).
    outliers = df[df["매출증감율"].abs() > _SCATTER_GROWTH_LIMIT]
    df = df.drop(outliers.index)
    points = (
        alt.Chart(df)
        .mark_circle(size=80, opacity=0.9, stroke="#FFFFFF", strokeWidth=2)
        .encode(
            x=alt.X("매출증감율:Q", title="매출증감율(%, 전월 대비)"),
            y=alt.Y("영업이익율:Q", title="영업이익율(%)"),
            color=alt.Color(
                "프로모션 해당:N",
                scale=alt.Scale(domain=["해당", "미해당"], range=["#0097A9", "#B5BBBD"]),
                legend=alt.Legend(title=None, orient="top", direction="horizontal"),
            ),
            order=alt.Order("프로모션 해당:N", sort="ascending"),
            tooltip=[
                alt.Tooltip("대리점명:N", title="대리점"),
                alt.Tooltip("매출증감율:Q", title="매출증감율(%)", format=".1f"),
                alt.Tooltip("영업이익율:Q", title="영업이익율(%)", format=".1f"),
                alt.Tooltip("총지원금액:Q", title="총지원금액", format=",.0f"),
            ],
        )
    )
    one_row = pd.DataFrame({"_": [0]})
    zero_x = alt.Chart(one_row).mark_rule(color="#A5AFB3", strokeWidth=1).encode(x=alt.datum(0))
    zero_y = alt.Chart(one_row).mark_rule(color="#A5AFB3", strokeWidth=1).encode(y=alt.datum(0))
    chart = (
        alt.layer(points, zero_x, zero_y)
        .properties(height=360)
        .configure(font=_CHART_FONT)
        .configure_axis(
            gridColor="#ECECEB", domainColor="#D9D9D8", tickColor="#D9D9D8",
            labelColor="#4C5F68", titleColor="#4C5F68", labelFontSize=11, titleFontSize=12, titleFontWeight="normal",
        )
        .configure_legend(labelColor="#4C5F68", labelFontSize=12, symbolType="circle")
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(chart, width="stretch")
    if not outliers.empty:
        names = ", ".join(f"{r['대리점명']}({r['매출증감율']:+,.0f}%)" for _, r in outliers.iterrows())
        st.caption(f"매출증감율이 ±{_SCATTER_GROWTH_LIMIT}%를 넘는 {len(outliers)}곳은 축이 과하게 늘어나 차트에서 뺐습니다: {names}")


_STORE_GROUP_ORDER = ["우수 (15%+)", "보통 (0~15%)", "저조 (0% 미만)"]


def _bucket_영업이익율(value: float) -> str:
    if value >= 15:
        return _STORE_GROUP_ORDER[0]
    if value >= 0:
        return _STORE_GROUP_ORDER[1]
    return _STORE_GROUP_ORDER[2]


def _store_group_summary(sales_like: pd.DataFrame) -> pd.DataFrame:
    """대리점을 영업이익율 구간(우수/보통/저조)으로 묶어 그룹별 평균을 낸다(PRD 6.7절).
    저조 그룹의 평균 총지원금액이 우수 그룹 못지않은데 영업이익율이 낮다면, 그 그룹엔
    이번 지원 설계가 잘 안 먹혔다는 뜻이다."""
    df = sales_like.dropna(subset=["영업이익율"]).copy()
    if df.empty:
        return pd.DataFrame(columns=["그룹", "대리점수", "영업이익율", "매출증감율", "총지원금액"])
    df["그룹"] = df["영업이익율"].apply(_bucket_영업이익율)
    summary = df.groupby("그룹", as_index=False).agg(
        대리점수=("대리점코드", "nunique"),
        영업이익율=("영업이익율", "mean"),
        매출증감율=("매출증감율", "mean"),
        총지원금액=("총지원금액", "mean"),
    )
    summary["그룹"] = pd.Categorical(summary["그룹"], categories=_STORE_GROUP_ORDER, ordered=True)
    return summary.sort_values("그룹").reset_index(drop=True)


def _html(markup: str) -> None:
    # 업로드 데이터에서 온 텍스트는 dashboard.py가 전부 이스케이프한다 — 여기서 실행되는
    # 스크립트는 dashboard.py에 고정된 코드(스크롤 등장·숫자 카운트·툴팁)뿐이다.
    st.html(markup, unsafe_allow_javascript=True)


def render_analysis(result, 기준연월: str) -> None:
    """분석 결과 대시보드(`.docs/21_분석결과_대시보드_UI_개편_계획서.md`).

    카드·차트가 먼저 오고, 엑셀과 같은 원본 표는 맨 아래 "상세 데이터" 탭으로 내렸다 —
    엑셀 시트를 그대로 옮긴 줄글·표 위주라 한눈에 안 들어온다는 사용자 피드백 반영. 모든
    차트 값은 상세 데이터 탭의 표로도 확인할 수 있다(dataviz: 표 보기 유지)."""
    sales_like = result.sales_like
    types = dashboard.insight_types(result.promotion_insight)

    _html(dashboard.page_header(기준연월, sales_like, len(types)))
    for w in result.warnings:
        st.info(w)
    _html(dashboard.kpi_row(sales_like))

    _html(dashboard.section("지원금액 구성", "어떤 지원이 얼마나 나갔는지, 그리고 이번 달 시행한 프로모션 조건"))
    left, right = st.columns([5, 7], gap="medium")
    with left:
        _html(dashboard.support_share(result.applied_support))
    with right:
        _html(dashboard.promotion_notice_cards(result.promotion_notice, types, 기준연월))

    _html(dashboard.section("대리점 성과", "어느 대리점에 지원이 몰렸는지, 프로모션을 받은 대리점이 실제로 나았는지"))
    left, right = st.columns([7, 5], gap="medium")
    with left:
        _html(dashboard.store_ranking(sales_like))
    with right:
        _html(dashboard.effect_summary(_effect_stats(sales_like)))

    _html(dashboard.section("교차 분석", "문턱값까지 얼마나 남았는지, 매출과 이익률이 어떻게 움직였는지"))
    threshold_cards = dashboard.threshold_cards(result.threshold_proximity)
    if threshold_cards:
        cols = st.columns(min(len(threshold_cards), 3), gap="medium")
        for i, card in enumerate(threshold_cards):
            with cols[i % len(cols)]:
                _html(card)
    else:
        st.info("구간별 문턱값이 있는 규칙(구간별단가/연동형)이 없어 근접도를 볼 수 없습니다.")
    left, right = st.columns([7, 5], gap="medium")
    with left:
        with st.container(key="sbcard-scatter"):
            _render_op_growth_scatter(sales_like)
    with right:
        _html(dashboard.store_group_cards(_store_group_summary(sales_like)))
    with st.container(key="sbcard-deviation"):
        _render_deviation_comparison(sales_like)

    _html(dashboard.section(
        "프로모션 장단점 분석",
        "산식유형별 구조적 장단점과 이번 달 데이터 신호 — 차기 설계를 대신 결정하는 게 아니라 판단에 참고할 의견입니다",
    ))
    _html(dashboard.insight_cards(result.promotion_insight))

    _html(dashboard.section("상세 데이터", "엑셀과 같은 원본 표 — 위 카드·차트의 모든 값을 표로 확인할 수 있습니다"))
    with st.container(key="sbcard-detail"):
        tab_store, tab_support, tab_group, tab_prox = st.tabs(
            ["대리점 단위 요약", "지원유형별 지원금액 내역", "제품군별 판매수량 · 지원금액", "문턱값 근접도 전체"]
        )
        with tab_store:
            st.caption("컬럼이 많아 가로로 스크롤됩니다 — 대리점명은 고정돼 있어 스크롤 중에도 어느 줄인지 알 수 있습니다.")
            main_table_config = column_config(sales_like)
            main_table_config["대리점명"] = st.column_config.TextColumn("대리점명", pinned=True, width=110)
            st.dataframe(sales_like, width="stretch", column_config=main_table_config)
        with tab_support:
            if result.applied_support.empty:
                st.write("지원 내역이 없습니다.")
            else:
                detail = result.applied_support.drop(columns=["제품코드", "지원단가"])
                st.dataframe(detail, width="stretch", column_config=column_config(detail))
                st.caption("유형별 소계")
                subtotal = _support_subtotal(result.applied_support)
                st.dataframe(subtotal, width="stretch", column_config=column_config(subtotal), hide_index=True)
        with tab_group:
            if result.product_group_support.empty:
                st.write("제품군별 요약을 계산할 수 없습니다.")
            else:
                st.caption("대리점 구분 없는 전사 합계")
                st.dataframe(
                    result.product_group_support, width="stretch",
                    column_config=column_config(result.product_group_support), hide_index=True,
                )
        with tab_prox:
            if result.threshold_proximity.empty:
                st.write("구간별 문턱값이 있는 규칙이 없습니다.")
            else:
                st.caption("\"다음구간까지\"가 작을수록 조금만 더 팔면 더 높은 지원단가 구간에 도달합니다.")
                st.dataframe(
                    result.threshold_proximity, width="stretch",
                    column_config=column_config(result.threshold_proximity), hide_index=True,
                )

    with st.container(key="sbcard-save"):
        st.subheader("저장")
        st.caption("이 기준연월의 대리점 단위 결과를 DuckDB에 저장하면 '이력 조회'에서 다시 볼 수 있습니다.")
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
                sales_df=sales_like[sales_cols],
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
