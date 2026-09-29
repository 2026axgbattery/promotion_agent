"""분석 결과 대시보드의 카드·차트 HTML 빌더.

`.docs/21_분석결과_대시보드_UI_개편_계획서.md` 참고. 차트는 `st.html(...,
unsafe_allow_javascript=True)`로 그린다 — iframe이 아니라 페이지 DOM에 바로 들어가서 세방고딕
폰트·스크롤 컨테이너를 그대로 쓰고, `IntersectionObserver`로 "화면에 들어오는 순간" 막대가
차오르고 숫자가 올라가게 할 수 있다.

보안: 대리점명·프로모션명은 업로드 파일에서 온 값이라 HTML에 넣을 때 전부 `html.escape`하고,
툴팁은 JS에서 `textContent`로만 채운다(`innerHTML` 문자열 결합 금지 — dataviz 규칙).

색: 식별색은 SEBANG Green(DC 지원)·Orange(프로모션 지원) 두 개만 쓴다 — 검증 스크립트
(`dataviz/scripts/validate_palette.js "#0097A9,#EB3300"`) 전 항목 PASS. 텍스트는 항상 텍스트
토큰(ink 계열)이고, 계열 색은 옆의 막대·스와치만 입는다.
"""

from __future__ import annotations

import html
import itertools
import math
import re

import pandas as pd

GREEN = "#0097A9"
ORANGE = "#EB3300"
_DC_TYPES = {"매출DC", "성장DC"}
_uid = itertools.count(1)

DASHBOARD_CSS = """
<style>
/* SEBANG Gothic의 em dash(U+2014)·en dash(U+2013) 글리프는 윤곽선이 비어 있어 빈칸으로 보인다
   (fontTools로 확인). 같은 패밀리 이름에 unicode-range를 좁힌 face를 나중에 선언하면 그 글자만
   시스템 한글 폰트로 대신 그린다 — 표(캔버스)·캡션 등 앱 전체에 적용된다. */
@font-face{ font-family:"SEBANG Gothic"; font-weight:400; unicode-range:U+2013-2014, U+2212;
  src:local("Malgun Gothic"), local("Apple SD Gothic Neo"), local("Noto Sans KR"), local("Segoe UI"), local("Arial"); }
@font-face{ font-family:"SEBANG Gothic"; font-weight:700; unicode-range:U+2013-2014, U+2212;
  src:local("Malgun Gothic Bold"), local("Malgun Gothic"), local("Apple SD Gothic Neo"), local("Noto Sans KR"), local("Segoe UI"), local("Arial"); }
:root{
  --sb-ink:#1F3742; --sb-ink-400:#4C5F68; --sb-ink-300:#79878E; --sb-ink-50:#EDEFF0;
  --sb-line:#ECECEB; --sb-line-strong:#D9D9D8; --sb-page:#F6F6F5; --sb-surface:#FFFFFF;
  --sb-green:#0097A9; --sb-green-50:#EBF7F8; --sb-green-100:#CCEAEE; --sb-green-700:#006A76;
  --sb-orange:#EB3300; --sb-orange-50:#FDEFEB; --sb-orange-700:#A42400; --sb-gray-400:#B5BBBD;
  --sb-shadow:0 2px 8px rgba(31,55,66,0.08);
  --sb-ease:cubic-bezier(0.4,0,0.2,1);
}
[data-testid="stAppViewContainer"], [data-testid="stMain"]{ background:var(--sb-page); }
[data-testid="stHeader"]{ background:transparent; }
[class*="st-key-sbcard"]{
  background:var(--sb-surface); border:1px solid var(--sb-line); border-radius:8px;
  box-shadow:var(--sb-shadow); padding:20px 24px;
}
/* 카드 안의 Streamlit 기본 소제목을 HTML 카드 제목(.sb-card h3)과 같은 크기로 맞춘다 */
[class*="st-key-sbcard"] h3{ font-size:1.0625rem !important; line-height:1.4 !important; font-weight:700 !important; padding:0 0 2px !important; }
[class*="st-key-sbcard"] [data-testid="stCaptionContainer"]{ color:var(--sb-ink-400); }
div[data-testid="stMetricValue"]{ font-size:clamp(1rem,2.4vw,1.5rem); white-space:normal; overflow-wrap:break-word; line-height:1.25; }
div[data-testid="stMetricLabel"]{ white-space:normal; overflow-wrap:break-word; }

.sb-root{ position:relative; color:var(--sb-ink); font-family:"SEBANG Gothic","Pretendard","Noto Sans KR",sans-serif; }
.sb-root *{ box-sizing:border-box; }
.sb-card{ background:var(--sb-surface); border:1px solid var(--sb-line); border-radius:8px; box-shadow:var(--sb-shadow); padding:22px 24px; height:100%; }
.sb-card h3{ margin:0 0 4px; font-size:1.0625rem; font-weight:700; line-height:1.4; color:var(--sb-ink); }
.sb-desc{ margin:0 0 18px; font-size:0.8125rem; line-height:1.5; color:var(--sb-ink-400); }
.sb-row-head{ display:flex; justify-content:space-between; align-items:flex-start; gap:12px; }

/* 페이지 헤더 */
.sb-page-head{ display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; gap:12px; margin:4px 0 8px; }
.sb-page-head h1{ margin:0; font-size:1.875rem; font-weight:700; line-height:1.25; color:var(--sb-ink); }
.sb-page-head p{ margin:6px 0 0; font-size:0.9375rem; color:var(--sb-ink-400); }
.sb-chips{ display:flex; gap:8px; flex-wrap:wrap; }
.sb-chip{ display:inline-flex; align-items:center; gap:6px; padding:4px 10px; border-radius:999px; background:var(--sb-surface); border:1px solid var(--sb-line-strong); font-size:0.75rem; color:var(--sb-ink-400); white-space:nowrap; }
.sb-chip b{ color:var(--sb-ink); font-weight:700; }

/* 섹션 제목 */
.sb-section{ margin:28px 0 4px; }
.sb-section h2{ margin:0; font-size:1.25rem; font-weight:700; color:var(--sb-ink); }
.sb-section p{ margin:4px 0 0; font-size:0.8125rem; color:var(--sb-ink-400); }

/* KPI 카드 */
.sb-kpis{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:16px; }
@media (max-width:1100px){ .sb-kpis{ grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media (max-width:560px){ .sb-kpis{ grid-template-columns:1fr; } }
.sb-kpi-label{ font-size:0.8125rem; color:var(--sb-ink-400); }
.sb-help{ display:inline-flex; width:16px; height:16px; border-radius:999px; background:var(--sb-ink-50); color:var(--sb-ink-400); font-size:0.6875rem; align-items:center; justify-content:center; cursor:help; }
.sb-kpi-value{ margin-top:8px; font-size:1.75rem; font-weight:700; line-height:1.2; color:var(--sb-ink); white-space:nowrap; }
.sb-kpi-value small{ font-size:0.9375rem; font-weight:400; color:var(--sb-ink-400); margin-left:4px; }
.sb-delta{ display:inline-flex; align-items:center; gap:4px; margin-top:6px; font-size:0.8125rem; font-weight:700; }
.sb-delta span{ font-weight:400; color:var(--sb-ink-400); }
.sb-delta.up{ color:var(--sb-green-700); } .sb-delta.down{ color:var(--sb-orange-700); } .sb-delta.flat{ color:var(--sb-ink-400); }
.sb-kpi-sub{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:16px; padding-top:14px; border-top:1px solid var(--sb-line); }
.sb-sub-l{ display:block; font-size:0.6875rem; letter-spacing:0.04em; color:var(--sb-ink-400); }
.sb-sub-v{ display:block; margin-top:2px; font-size:0.9375rem; color:var(--sb-ink); white-space:nowrap; }

/* 막대/게이지 공통 */
.sb-track{ position:relative; height:8px; border-radius:4px; background:var(--sb-ink-50); overflow:hidden; }
.sb-fill{ height:100%; width:var(--w); border-radius:0 4px 4px 0; transition:width 700ms var(--sb-ease); transition-delay:var(--d,0ms); }
.sb-fill.green{ background:var(--sb-green); } .sb-fill.orange{ background:var(--sb-orange); }
.sb-track.green-track{ background:var(--sb-green-50); }
.sb-split{ display:flex; gap:2px; height:8px; margin-top:14px; }
.sb-split > div{ height:100%; }
.sb-split > div:first-child{ border-radius:4px 0 0 4px; } .sb-split > div:last-child{ border-radius:0 4px 4px 0; }
.sb-split > div:only-child{ border-radius:4px; }
.sb-split .green{ background:var(--sb-green); } .sb-split .orange{ background:var(--sb-orange); }
.sb-split > div:hover, .sb-split > div:focus-visible{ filter:brightness(1.12); outline:none; }
.sb-legend{ display:flex; gap:16px; flex-wrap:wrap; font-size:0.75rem; color:var(--sb-ink-400); }
.sb-legend i{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:6px; vertical-align:-1px; }

/* 지원유형 비중 */
.sb-share-row{ padding:10px 0; }
.sb-share-top{ display:flex; justify-content:space-between; align-items:baseline; gap:8px; margin-bottom:8px; font-size:0.875rem; }
.sb-share-name{ color:var(--sb-ink); min-width:0; overflow-wrap:anywhere; }
.sb-share-num{ color:var(--sb-ink-400); font-variant-numeric:tabular-nums; white-space:nowrap; }
.sb-share-num b{ color:var(--sb-ink); font-weight:700; margin-left:8px; }
.sb-tag{ display:inline-block; margin-left:6px; padding:1px 6px; border-radius:4px; font-size:0.6875rem; background:var(--sb-ink-50); color:var(--sb-ink-400); vertical-align:1px; }

/* 목록형(프로모션 시행 내용) */
.sb-list{ display:flex; flex-direction:column; }
.sb-item{ display:flex; gap:14px; padding:14px 0; border-top:1px solid var(--sb-line); }
.sb-item:first-child{ border-top:none; padding-top:2px; }
.sb-avatar{ flex:0 0 40px; height:40px; border-radius:999px; background:var(--sb-ink-50); color:var(--sb-ink); display:flex; align-items:center; justify-content:center; font-size:0.75rem; font-weight:700; }
.sb-item-body{ min-width:0; flex:1; }
.sb-item-title{ font-size:0.9375rem; font-weight:700; color:var(--sb-ink); }
.sb-item-title .sb-tag{ font-weight:400; }
.sb-item-lines{ margin:4px 0 0; padding:0; list-style:none; }
.sb-item-lines li{ font-size:0.8125rem; line-height:1.6; color:var(--sb-ink-400); overflow-wrap:anywhere; }

/* 순위 누적 막대 */
.sb-rank{ margin-top:14px; }
.sb-rank-row{ display:grid; grid-template-columns:minmax(120px,190px) 1fr 72px; align-items:center; gap:12px; padding:7px 0; }
.sb-rank-name{ font-size:0.8125rem; color:var(--sb-ink); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.sb-rank-name em{ font-style:normal; display:inline-block; width:20px; color:var(--sb-ink-300); font-variant-numeric:tabular-nums; }
.sb-rank-bar{ height:14px; }
.sb-stack{ display:flex; gap:2px; height:100%; width:var(--w); transition:width 800ms var(--sb-ease); transition-delay:var(--d,0ms); }
.sb-seg{ height:100%; min-width:2px; outline:none; }
.sb-seg:last-child{ border-radius:0 4px 4px 0; }
.sb-seg.green{ background:var(--sb-green); } .sb-seg.orange{ background:var(--sb-orange); }
.sb-seg:hover, .sb-seg:focus-visible{ filter:brightness(1.12); box-shadow:0 0 0 2px var(--sb-surface), 0 0 0 3px var(--sb-ink-300); }
.sb-rank-val{ font-size:0.8125rem; font-weight:700; text-align:right; color:var(--sb-ink); font-variant-numeric:tabular-nums; white-space:nowrap; }

/* 효과 평가 */
.sb-figs{ display:flex; flex-direction:column; gap:0; }
.sb-fig{ padding:14px 0; border-top:1px solid var(--sb-line); }
.sb-fig:first-child{ border-top:none; padding-top:0; }
.sb-fig-l{ font-size:0.8125rem; color:var(--sb-ink-400); }
.sb-fig-v{ margin-top:4px; font-size:1.5rem; font-weight:700; color:var(--sb-ink); }
.sb-fig-note{ margin-top:2px; font-size:0.75rem; color:var(--sb-ink-400); }

/* 문턱값 근접도 */
.sb-search{ width:100%; margin-bottom:14px; padding:8px 12px; border:1px solid var(--sb-line-strong); border-radius:8px; background:var(--sb-page); color:var(--sb-ink); font:inherit; font-size:0.8125rem; }
.sb-search::placeholder{ color:var(--sb-ink-300); }
.sb-search:focus{ outline:none; border-color:var(--sb-green); background:var(--sb-surface); }
.sb-more{ display:contents; }
.sb-more[hidden]{ display:none; }
.sb-more-toggle{ display:block; width:100%; margin-top:8px; padding:9px 12px; border:1px dashed var(--sb-line-strong); border-radius:8px; background:transparent; color:var(--sb-ink-400); font:inherit; font-size:0.8125rem; font-weight:700; cursor:pointer; }
.sb-more-toggle:hover, .sb-more-toggle:focus-visible{ border-color:var(--sb-green); color:var(--sb-green-700); outline:none; }
.sb-prox-row[hidden]{ display:none; }
.sb-stats{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:14px; }
.sb-stat{ flex:1 1 90px; padding:10px 12px; border-radius:8px; background:var(--sb-page); }
.sb-stat-v{ display:block; font-size:1.25rem; font-weight:700; line-height:1.3; color:var(--sb-ink); }
.sb-stat > span:last-child{ font-size:0.75rem; color:var(--sb-ink-400); }
.sb-prox-row{ padding:10px 0; border-top:1px solid var(--sb-line); }
.sb-prox-top{ display:flex; justify-content:space-between; gap:8px; margin-bottom:8px; font-size:0.8125rem; }
.sb-prox-top b{ color:var(--sb-ink); white-space:nowrap; }
.sb-prox-name{ color:var(--sb-ink); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.sb-prox-note{ margin-top:6px; font-size:0.75rem; color:var(--sb-ink-400); }

/* 그룹 카드 */
.sb-groups{ display:flex; flex-direction:column; gap:12px; }
.sb-group{ border:1px solid var(--sb-line); border-radius:8px; padding:14px 16px; }
.sb-group-top{ display:flex; justify-content:space-between; align-items:baseline; }
.sb-group-top b{ font-size:0.9375rem; }
.sb-group-top span{ font-size:0.8125rem; color:var(--sb-ink-400); }
.sb-group-grid{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:10px; }

/* 장단점 카드 */
.sb-insights{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; }
@media (max-width:1100px){ .sb-insights{ grid-template-columns:1fr; } }
.sb-ins-row{ display:flex; gap:10px; margin-top:14px; font-size:0.8125rem; line-height:1.6; color:var(--sb-ink); }
.sb-ins-ico{ flex:0 0 22px; height:22px; border-radius:999px; display:flex; align-items:center; justify-content:center; font-size:0.75rem; font-weight:700; }
.sb-ins-ico.pro{ background:var(--sb-green-50); color:var(--sb-green-700); }
.sb-ins-ico.con{ background:var(--sb-orange-50); color:var(--sb-orange-700); }
.sb-ins-ico.data{ background:var(--sb-ink-50); color:var(--sb-ink); }
.sb-ins-row b{ display:block; font-size:0.75rem; color:var(--sb-ink-400); font-weight:700; }

/* 업로드 화면 */
.sb-steps{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin-top:16px; }
@media (max-width:900px){ .sb-steps{ grid-template-columns:1fr; } }
.sb-step{ padding:14px 16px; border-radius:8px; background:var(--sb-page); }
.sb-step b{ display:block; font-size:0.875rem; color:var(--sb-ink); }
.sb-step span{ font-size:0.8125rem; color:var(--sb-ink-400); }

/* 툴팁 */
.sb-tip{ position:absolute; z-index:10; pointer-events:none; padding:8px 10px; border-radius:6px; background:var(--sb-ink); color:#FFFFFF; box-shadow:0 4px 16px rgba(31,55,66,0.2); white-space:nowrap; }
.sb-tip-v{ display:block; font-size:0.875rem; font-weight:700; }
.sb-tip-l{ display:block; font-size:0.75rem; color:#D2D7D9; }

/* 스크롤 등장 애니메이션 — JS가 .sb-armed를 붙였을 때만 숨긴다(JS가 안 돌면 처음부터 최종 상태) */
.sb-reveal{ transition:opacity 300ms var(--sb-ease), transform 300ms var(--sb-ease); }
.sb-armed .sb-reveal:not(.is-visible){ opacity:0; transform:translateY(12px); }
.sb-armed .sb-reveal:not(.is-visible) .sb-fill, .sb-armed .sb-reveal:not(.is-visible) .sb-stack{ width:0 !important; }
@media (prefers-reduced-motion: reduce){ .sb-reveal, .sb-fill, .sb-stack{ transition:none !important; } }
</style>
"""

_SCRIPT = """
<script>
(function(){
  function fmt(v, f){
    if (!isFinite(v)) return "–";
    if (f === "krw"){
      var a = Math.abs(v);
      if (a >= 1e8) return (v/1e8).toLocaleString("ko-KR",{minimumFractionDigits:1,maximumFractionDigits:1}) + "억";
      if (a >= 1e4) return Math.round(v/1e4).toLocaleString("ko-KR") + "만";
      return Math.round(v).toLocaleString("ko-KR");
    }
    if (f === "pct") return v.toLocaleString("ko-KR",{minimumFractionDigits:1,maximumFractionDigits:1}) + "%";
    if (f === "pp") return (v >= 0 ? "+" : "") + v.toLocaleString("ko-KR",{minimumFractionDigits:1,maximumFractionDigits:1}) + "%p";
    if (f === "x") return v.toLocaleString("ko-KR",{minimumFractionDigits:1,maximumFractionDigits:1}) + "x";
    return Math.round(v).toLocaleString("ko-KR");
  }
  function init(id){
    var root = document.getElementById(id);
    if (!root || root.dataset.sbInit) return;
    root.dataset.sbInit = "1";
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var targets = root.querySelectorAll(".sb-reveal");
    function run(scope){
      scope.classList.add("is-visible");
      scope.querySelectorAll("[data-countup]").forEach(function(el){
        var t = parseFloat(el.dataset.countup), f = el.dataset.format;
        if (reduce || !isFinite(t)) { el.textContent = fmt(t, f); return; }
        var start = performance.now(), dur = 900;
        function step(now){
          var p = Math.min(1, (now - start) / dur), e = 1 - Math.pow(1 - p, 3);
          el.textContent = fmt(t * e, f);
          if (p < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
      });
    }
    if (reduce || !("IntersectionObserver" in window)) {
      targets.forEach(run);
    } else {
      root.classList.add("sb-armed");
      targets.forEach(function(el){
        el.querySelectorAll("[data-countup]").forEach(function(c){ c.textContent = fmt(0, c.dataset.format); });
      });
      var io = new IntersectionObserver(function(entries){
        entries.forEach(function(e){ if (e.isIntersecting) { run(e.target); io.unobserve(e.target); } });
      }, { threshold: 0.15 });
      targets.forEach(function(el){ io.observe(el); });
    }
    // 문턱값 근접도 카드: "더 보기"로 숨겨둔 나머지 대리점을 펼치고, 검색창으로 특정
    // 대리점을 찾는다 — 일부만 보이고 나머지는 조용히 생략되는 것처럼 보인다는 피드백 반영.
    root.querySelectorAll("[data-toggle-more]").forEach(function(btn){
      var box = btn.previousElementSibling;
      btn.addEventListener("click", function(){
        var opening = box.hasAttribute("hidden");
        if (opening) { box.removeAttribute("hidden"); btn.textContent = btn.dataset.labelOpen; }
        else { box.setAttribute("hidden", ""); btn.textContent = btn.dataset.labelClosed; }
      });
    });
    root.querySelectorAll("[data-search-scope]").forEach(function(input){
      var card = input.closest(".sb-card");
      var box = card.querySelector(".sb-more");
      var toggle = card.querySelector("[data-toggle-more]");
      input.addEventListener("input", function(){
        var q = input.value.trim().toLowerCase();
        if (q && box && box.hasAttribute("hidden")) {
          box.removeAttribute("hidden");
          if (toggle) toggle.textContent = toggle.dataset.labelOpen;
        }
        card.querySelectorAll(".sb-prox-row").forEach(function(row){
          var name = (row.querySelector(".sb-prox-name") || {}).textContent || "";
          row.hidden = !!q && name.toLowerCase().indexOf(q) === -1;
        });
      });
    });

    var tip = root.querySelector(".sb-tip");
    if (!tip) return;
    var tv = tip.querySelector(".sb-tip-v"), tl = tip.querySelector(".sb-tip-l");
    function show(el, x, y){
      tv.textContent = el.dataset.tipValue || "";
      tl.textContent = el.dataset.tipLabel || "";
      tip.hidden = false;
      var rr = root.getBoundingClientRect(), tr = tip.getBoundingClientRect();
      var left = x - rr.left + 14, top = y - rr.top - tr.height - 10;
      if (left + tr.width > rr.width) left = x - rr.left - tr.width - 14;
      if (top < 0) top = y - rr.top + 18;
      tip.style.left = Math.max(0, left) + "px";
      tip.style.top = top + "px";
    }
    root.querySelectorAll("[data-tip-value]").forEach(function(el){
      el.addEventListener("pointermove", function(ev){ show(el, ev.clientX, ev.clientY); });
      el.addEventListener("pointerleave", function(){ tip.hidden = true; });
      el.addEventListener("focus", function(){ var r = el.getBoundingClientRect(); show(el, r.left + r.width / 2, r.top); });
      el.addEventListener("blur", function(){ tip.hidden = true; });
    });
  }
  init("__ID__");
})();
</script>
"""


def _e(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _is_num(v) -> bool:
    return v is not None and not (isinstance(v, float) and math.isnan(v)) and not pd.isna(v)


def fmt_krw(v) -> str:
    """금액 요약 표기(억/만). 원화 기호는 붙이지 않는다(사용자 확인)."""
    if not _is_num(v):
        return "–"
    a = abs(v)
    if a >= 1e8:
        return f"{v / 1e8:,.1f}억"
    if a >= 1e4:
        return f"{v / 1e4:,.0f}만"
    return f"{v:,.0f}"


def fmt_pct(v) -> str:
    return f"{v:,.1f}%" if _is_num(v) else "–"


def fmt_pp(v) -> str:
    return f"{v:+,.1f}%p" if _is_num(v) else "–"


def _countup(value, fmt: str, text: str) -> str:
    if not _is_num(value):
        return _e(text)
    return f'<span data-countup="{float(value)}" data-format="{fmt}">{_e(text)}</span>'


def wrap(inner: str, *, tooltip: bool = False) -> str:
    """카드 묶음 하나를 스크립트와 함께 감싼다(블록마다 독립적으로 초기화)."""
    root_id = f"sb-{next(_uid)}"
    tip = '<div class="sb-tip" role="tooltip" hidden><span class="sb-tip-v"></span><span class="sb-tip-l"></span></div>' if tooltip else ""
    return f'<div class="sb-root" id="{root_id}">{inner}{tip}</div>' + _SCRIPT.replace("__ID__", root_id)


def section(title: str, desc: str = "") -> str:
    d = f"<p>{_e(desc)}</p>" if desc else ""
    return f'<div class="sb-root sb-section"><h2>{_e(title)}</h2>{d}</div>'


def _delta(value, label: str, *, up_is_good: bool = True) -> str:
    if not _is_num(value):
        return f'<div class="sb-delta flat">– <span>{_e(label)} 비교 불가</span></div>'
    if abs(value) < 0.05:
        cls, arrow = "flat", "–"
    else:
        good = (value > 0) == up_is_good
        cls, arrow = ("up" if good else "down"), ("▲" if value > 0 else "▼")
    return f'<div class="sb-delta {cls}">{arrow} {abs(value):,.1f}% <span>{_e(label)}</span></div>'


def _growth(cur: float, prev) -> float | None:
    if not _is_num(prev) or not prev:
        return None
    return (cur - prev) / prev * 100


def page_header(기준연월: str, sales_like: pd.DataFrame, promo_count: int) -> str:
    m = re.match(r"^(\d{4})-(\d{1,2})$", str(기준연월 or ""))
    period_text = f"{m.group(1)}년 {int(m.group(2))}월" if m else str(기준연월)
    chips = (
        f'<span class="sb-chip">기준연월 <b>{_e(기준연월)}</b></span>'
        f'<span class="sb-chip">대리점 <b>{sales_like["대리점코드"].nunique()}곳</b></span>'
        f'<span class="sb-chip">시행 프로모션 <b>{promo_count}건</b></span>'
    )
    return (
        '<div class="sb-root"><div class="sb-page-head"><div>'
        f"<h1>{_e(period_text)} 프로모션 분석 대시보드</h1>"
        "<p>업로드한 월 마감 워크북 기준 · DC 지원과 프로모션 지원을 나눠서 봅니다</p>"
        f'</div><div class="sb-chips">{chips}</div></div></div>'
    )


def kpi_row(sales_like: pd.DataFrame) -> str:
    df = sales_like
    revenue = float(df["매출액"].sum())
    profit = float(df["영업이익"].sum())
    cost_rate = (df["원가율"] * df["매출액"]).sum() / revenue if revenue else float("nan")
    op_rate = profit / revenue * 100 if revenue else float("nan")
    dc = float(df["DC지원금액"].sum())
    promo = float(df["프로모션지원금액"].sum())
    total = dc + promo

    prev = df.loc[df["전월매출"].notna()]
    prev_sum = float(prev["전월매출"].sum()) if not prev.empty else None
    mom = _growth(float(prev["매출액"].sum()), prev_sum) if prev_sum else None
    yoy_df = df.loc[df["전년동월매출"].notna()]
    yoy_sum = float(yoy_df["전년동월매출"].sum()) if not yoy_df.empty else None
    yoy = _growth(float(yoy_df["매출액"].sum()), yoy_sum) if yoy_sum else None

    stores = df["대리점코드"].nunique()
    promo_stores = int((df["프로모션지원금액"] > 0).sum())
    promo_share = promo_stores / stores * 100 if stores else 0
    avg_promo = promo / promo_stores if promo_stores else float("nan")
    support_rate = total / revenue * 100 if revenue else float("nan")
    dc_share = dc / total * 100 if total else 0

    def sub(l1, v1, l2, v2):
        return (
            f'<div class="sb-kpi-sub"><div><span class="sb-sub-l">{_e(l1)}</span><span class="sb-sub-v">{_e(v1)}</span></div>'
            f'<div><span class="sb-sub-l">{_e(l2)}</span><span class="sb-sub-v">{_e(v2)}</span></div></div>'
        )

    def head(label, help_text):
        return f'<div class="sb-row-head"><span class="sb-kpi-label">{_e(label)}</span><span class="sb-help" title="{_e(help_text)}">?</span></div>'

    split = ""
    if total:
        segs = []
        if dc:
            segs.append(f'<div class="green" style="flex:{dc:.0f}" data-tip-value="{_e(fmt_krw(dc))} ({dc_share:.0f}%)" data-tip-label="DC 지원" tabindex="0"></div>')
        if promo:
            segs.append(f'<div class="orange" style="flex:{promo:.0f}" data-tip-value="{_e(fmt_krw(promo))} ({100 - dc_share:.0f}%)" data-tip-label="프로모션 지원" tabindex="0"></div>')
        split = f'<div class="sb-split">{"".join(segs)}</div>'

    tiles = [
        '<div class="sb-card sb-reveal">'
        + head("총 매출액", "DATA 시트 매출액 합계(프로모션 기준에 없는 제품코드 제외)")
        + f'<div class="sb-kpi-value">{_countup(revenue, "krw", fmt_krw(revenue))}</div>'
        + _delta(mom, "전월 대비")
        + sub("전월 매출", fmt_krw(prev_sum), "전년 동월 대비", "–" if yoy is None else f"{yoy:+.1f}%")
        + "</div>",
        '<div class="sb-card sb-reveal">'
        + head("총 지원금액", "DC 지원금액 + 프로모션 지원금액")
        + f'<div class="sb-kpi-value">{_countup(total, "krw", fmt_krw(total))}</div>'
        + split
        + '<div class="sb-legend" style="margin-top:8px"><span><i style="background:#0097A9"></i>DC</span><span><i style="background:#EB3300"></i>프로모션</span></div>'
        + sub("DC 지원", fmt_krw(dc), "프로모션 지원", fmt_krw(promo))
        + "</div>",
        '<div class="sb-card sb-reveal">'
        + head("평균 영업이익율", "본사 기준 영업이익 합계 ÷ 매출액 합계(매출액 가중)")
        + f'<div class="sb-kpi-value">{_countup(op_rate, "pct", fmt_pct(op_rate))}</div>'
        + '<div class="sb-delta flat"><span>본사(세방전지) 기준</span></div>'
        + sub("영업이익 합계", fmt_krw(profit), "원가율(가중)", fmt_pct(cost_rate))
        + "</div>",
        '<div class="sb-card sb-reveal">'
        + head("프로모션 지원 대리점", "이번 달 프로모션 지원금액이 1원이라도 있는 대리점")
        + f'<div class="sb-kpi-value">{_countup(promo_stores, "int", f"{promo_stores:,}")}<small>/ {stores:,}곳</small></div>'
        + f'<div class="sb-track green-track" style="margin-top:14px"><div class="sb-fill green" style="--w:{promo_share:.1f}%"></div></div>'
        + sub("1곳당 평균", fmt_krw(avg_promo), "매출 대비 지원율", fmt_pct(support_rate))
        + "</div>",
    ]
    return wrap(f'<div class="sb-kpis">{"".join(tiles)}</div>', tooltip=True)


def support_share(applied_support: pd.DataFrame) -> str:
    head = '<h3>지원유형별 지원금액</h3><p class="sb-desc">총 지원금액에서 각 유형이 차지하는 비중</p>'
    if applied_support.empty:
        return wrap(f'<div class="sb-card sb-reveal">{head}<p class="sb-desc">지원 내역이 없습니다.</p></div>')
    by_type = applied_support.groupby("지원유형")["지원금액"].sum().sort_values(ascending=False)
    total = float(by_type.sum()) or 1.0
    rows = []
    for i, (name, amount) in enumerate(by_type.items()):
        share = amount / total * 100
        is_dc = name in _DC_TYPES
        tag = "DC" if is_dc else "프로모션"
        color = "green" if is_dc else "orange"
        rows.append(
            '<div class="sb-share-row">'
            f'<div class="sb-share-top"><span class="sb-share-name">{_e(name)}<span class="sb-tag">{tag}</span></span>'
            f'<span class="sb-share-num">{_e(fmt_krw(amount))}<b>{share:.1f}%</b></span></div>'
            f'<div class="sb-track"><div class="sb-fill {color}" style="--w:{max(share, 0.6):.2f}%;--d:{i * 60}ms" '
            f'data-tip-value="{_e(f"{amount:,.0f}")} ({share:.1f}%)" data-tip-label="{_e(name)}" tabindex="0"></div></div>'
            "</div>"
        )
    legend = '<div class="sb-legend" style="margin-bottom:6px"><span><i style="background:#0097A9"></i>DC 지원</span><span><i style="background:#EB3300"></i>프로모션 지원</span></div>'
    return wrap(f'<div class="sb-card sb-reveal">{head}{legend}{"".join(rows)}</div>', tooltip=True)


_TITLE_RE = re.compile(r"^▶\s*(.+?)\s*\(([^()]*)\)\s*$")
_유형_약칭 = {"품목별고정단가": "고정", "구간별단가-절대수량": "구간", "연동형": "연동", "무상증정": "증정"}


def _parse_blocks(lines: list[str]) -> list[dict]:
    blocks: list[dict] = []
    for line in lines:
        if line.startswith("▶"):
            m = _TITLE_RE.match(line)
            name, meta = (m.group(1), m.group(2)) if m else (line.lstrip("▶ ").strip(), "")
            blocks.append({"name": name, "meta": meta, "lines": []})
        elif blocks:
            blocks[-1]["lines"].append(line.strip())
    return blocks


def insight_types(promotion_insight: list[str]) -> dict[str, str]:
    return {b["name"]: b["meta"] for b in _parse_blocks(promotion_insight)}


def promotion_notice_cards(promotion_notice: list[str], types: dict[str, str], 기준연월: str) -> str:
    head = f'<h3>{_e(기준연월)} 프로모션 시행 내용</h3><p class="sb-desc">"프로모션 기준" 시트에서 읽은 조건</p>'
    blocks = _parse_blocks(promotion_notice)
    if not blocks:
        return wrap(f'<div class="sb-card sb-reveal">{head}<p class="sb-desc">프로모션 기준 시트가 없어 표시할 내용이 없습니다.</p></div>')
    items = []
    for b in blocks:
        유형 = types.get(b["name"], "")
        badge = _유형_약칭.get(유형, "P")
        tags = (f'<span class="sb-tag">{_e(유형)}</span>' if 유형 else "") + (f'<span class="sb-tag">{_e(b["meta"])}</span>' if b["meta"] else "")
        lis = "".join(f"<li>{_e(l)}</li>" for l in b["lines"])
        items.append(
            f'<div class="sb-item"><div class="sb-avatar" aria-hidden="true">{_e(badge)}</div>'
            f'<div class="sb-item-body"><div class="sb-item-title">{_e(b["name"])}{tags}</div>'
            f'<ul class="sb-item-lines">{lis}</ul></div></div>'
        )
    return wrap(f'<div class="sb-card sb-reveal">{head}<div class="sb-list">{"".join(items)}</div></div>')


def store_ranking(sales_like: pd.DataFrame, top_n: int = 10) -> str:
    head = (
        f'<div class="sb-row-head"><div><h3>대리점별 지원금액 TOP {top_n}</h3>'
        '<p class="sb-desc" style="margin-bottom:10px">총 지원금액 순 · 막대에 마우스를 올리면 금액이 보입니다</p></div></div>'
        '<div class="sb-legend"><span><i style="background:#0097A9"></i>DC 지원</span><span><i style="background:#EB3300"></i>프로모션 지원</span></div>'
    )
    top = sales_like.sort_values("총지원금액", ascending=False).head(top_n)
    max_total = float(top["총지원금액"].max() or 0) if not top.empty else 0
    rows = []
    for rank, (_, r) in enumerate(top.iterrows(), start=1):
        name = r["대리점명"] or r["대리점코드"]
        total, dc, promo = float(r["총지원금액"]), float(r["DC지원금액"]), float(r["프로모션지원금액"])
        width = total / max_total * 100 if max_total else 0
        segs = []
        if dc > 0:
            segs.append(f'<div class="sb-seg green" style="flex:{dc:.0f}" tabindex="0" data-tip-value="{_e(f"{dc:,.0f}")}" data-tip-label="DC 지원 · {_e(name)}"></div>')
        if promo > 0:
            segs.append(f'<div class="sb-seg orange" style="flex:{promo:.0f}" tabindex="0" data-tip-value="{_e(f"{promo:,.0f}")}" data-tip-label="프로모션 지원 · {_e(name)}"></div>')
        rows.append(
            f'<div class="sb-rank-row"><div class="sb-rank-name" title="{_e(name)}"><em>{rank}</em>{_e(name)}</div>'
            f'<div class="sb-rank-bar"><div class="sb-stack" style="--w:{width:.2f}%;--d:{(rank - 1) * 50}ms">{"".join(segs)}</div></div>'
            f'<div class="sb-rank-val">{_e(fmt_krw(total))}</div></div>'
        )
    body = f'<div class="sb-rank">{"".join(rows)}</div>' if rows else '<p class="sb-desc">표시할 대리점이 없습니다.</p>'
    return wrap(f'<div class="sb-card sb-reveal">{head}{body}</div>', tooltip=True)


def effect_summary(stats: dict | None) -> str:
    head = '<h3>이번 달 프로모션 효과 평가</h3><p class="sb-desc">프로모션 지원을 받은 대리점 vs 받지 않은 대리점 (본사 관점)</p>'
    if stats is None:
        return wrap(
            f'<div class="sb-card sb-reveal">{head}<p class="sb-desc">이번 달은 대리점 전체가 프로모션 지원 대상이거나 전부 '
            "미대상이라 해당/미해당 비교를 할 수 없습니다.</p></div>"
        )
    yes, no = stats["yes"], stats["no"]

    def fig(label, value, fmt, text, note):
        return (
            f'<div class="sb-fig"><div class="sb-fig-l">{_e(label)}</div>'
            f'<div class="sb-fig-v">{_countup(value, fmt, text)}</div><div class="sb-fig-note">{_e(note)}</div></div>'
        )

    figs = [
        fig("영업이익율 차이 (해당 − 미해당)", stats["op_gap"], "pp", fmt_pp(stats["op_gap"]),
            f"해당 {fmt_pct(yes['영업이익율'])} · 미해당 {fmt_pct(no['영업이익율'])}"),
        fig("매출증감율 차이 (해당 − 미해당)", stats["growth_gap"], "pp", fmt_pp(stats["growth_gap"]),
            f"해당 {fmt_pct(yes['매출증감율'])} · 미해당 {fmt_pct(no['매출증감율'])}"),
        fig("프로모션 ROI (추정)", stats["roi"], "x", "–" if stats["roi"] is None else f"{stats['roi']:.1f}x",
            "지원금 1원당 미해당 대비 초과 매출 증가분(참고용 근사치)"),
    ]
    note = f'<div class="sb-chips" style="margin-top:6px"><span class="sb-chip">해당 <b>{yes["대리점수"]}곳</b></span><span class="sb-chip">미해당 <b>{no["대리점수"]}곳</b></span></div>'
    return wrap(f'<div class="sb-card sb-reveal">{head}<div class="sb-figs">{"".join(figs)}</div>{note}</div>')


def _prox_row(r, i: int) -> str:
    cur = float(r["현재수량"])
    left = r["다음구간까지"]
    maxed = left is None or pd.isna(left)
    if maxed:
        badge, progress, note = (
            "최고 구간 도달",
            100.0,
            f'현재 {cur:,.0f}대 · 현재 단가 {r["현재단가"]:,.0f}원 · 더 이상 오를 구간이 없습니다',
        )
        tip_value = "최고 구간"
    else:
        left = float(left)
        next_amt = cur + left
        progress = cur / next_amt * 100 if next_amt else 0
        badge = f"{left:,.0f}대 남음"
        note = f'현재 {cur:,.0f}대 · 현재 단가 {r["현재단가"]:,.0f}원 → 도달 시 대당 {r["다음구간단가"]:,.0f}원'
        tip_value = f"{progress:.0f}% 달성"
    return (
        '<div class="sb-prox-row">'
        f'<div class="sb-prox-top"><span class="sb-prox-name">{_e(r["대상"])}</span><b>{_e(badge)}</b></div>'
        f'<div class="sb-track green-track"><div class="sb-fill green" style="--w:{progress:.1f}%;--d:{min(i, 12) * 40}ms" tabindex="0" '
        f'data-tip-value="{_e(tip_value)}" data-tip-label="{_e(r["대상"])}"></div></div>'
        f'<div class="sb-prox-note">{_e(note)}</div>'
        "</div>"
    )


def threshold_cards(threshold_proximity: pd.DataFrame, top_n: int = 8) -> list[str]:
    """산식유형(구간별단가·연동형) 그룹마다 카드 하나 — 다음 구간에 가장 가까운 대리점부터
    (최고 구간에 이미 도달한 대리점은 맨 뒤에). 기본으로는 위 `top_n`곳만 보이지만, 전체
    대리점이 다 들어있어 "더 보기"로 펼치거나 검색창에 대리점명을 입력해 찾을 수 있다 —
    일부만 보이고 나머지는 조용히 생략되는 것처럼 보인다는 피드백을 반영했다."""
    if threshold_proximity.empty:
        return []
    cards = []
    for group, rows in threshold_proximity.groupby("산식유형", sort=False):
        remaining = rows["다음구간까지"]
        target = rows["현재수량"] + remaining
        near = int((remaining.notna() & (remaining <= (target * 0.1).clip(lower=1))).sum())
        maxed = int(remaining.isna().sum())
        below = int((remaining.notna() & (rows["현재단가"] == 0)).sum())
        stats = (
            '<div class="sb-stats">'
            f'<div class="sb-stat"><span class="sb-stat-v">{_countup(len(rows), "int", str(len(rows)))}</span><span>전체 대상</span></div>'
            f'<div class="sb-stat"><span class="sb-stat-v">{_countup(near, "int", str(near))}</span><span>10% 이내 근접</span></div>'
            f'<div class="sb-stat"><span class="sb-stat-v">{_countup(maxed, "int", str(maxed))}</span><span>최고 구간 도달</span></div>'
            f'<div class="sb-stat"><span class="sb-stat-v">{_countup(below, "int", str(below))}</span><span>최저 구간 미달</span></div></div>'
        )
        ordered = pd.concat([rows.loc[remaining.notna()].sort_values("다음구간까지"), rows.loc[remaining.isna()]])
        if ordered.empty:
            body = '<p class="sb-desc">대상 대리점이 없습니다.</p>'
        else:
            visible = "".join(_prox_row(r, i) for i, (_, r) in enumerate(ordered.head(top_n).iterrows()))
            rest = ordered.iloc[top_n:]
            more = ""
            if not rest.empty:
                rest_html = "".join(_prox_row(r, i) for i, (_, r) in enumerate(rest.iterrows()))
                more = (
                    f'<div class="sb-more" hidden>{rest_html}</div>'
                    f'<button type="button" class="sb-more-toggle" data-toggle-more '
                    f'data-label-closed="나머지 {len(rest)}곳 더 보기" data-label-open="접기">나머지 {len(rest)}곳 더 보기</button>'
                )
            body = visible + more
        search = (
            f'<input type="search" class="sb-search" data-search-scope placeholder="대리점 검색 (전체 {len(rows)}곳)" '
            f'aria-label="{_e(group)} 대리점 검색">'
        )
        head = f'<h3>{_e(group)}</h3><p class="sb-desc">다음 구간 문턱값에 가까운 순 · 막대는 다음 구간까지의 달성률</p>'
        cards.append(wrap(f'<div class="sb-card sb-reveal">{head}{search}{stats}{body}</div>', tooltip=True))
    return cards


def store_group_cards(summary: pd.DataFrame) -> str:
    head = '<h3>대리점 그룹별 효과 비교</h3><p class="sb-desc">본사 영업이익율 구간으로 묶은 그룹 평균</p>'
    if summary.empty:
        return wrap(f'<div class="sb-card sb-reveal">{head}<p class="sb-desc">영업이익율 데이터가 없어 그룹별 비교를 할 수 없습니다.</p></div>')
    total = int(summary["대리점수"].sum()) or 1
    groups = []
    for i, (_, r) in enumerate(summary.iterrows()):
        share = r["대리점수"] / total * 100
        groups.append(
            '<div class="sb-group">'
            f'<div class="sb-group-top"><b>{_e(r["그룹"])}</b><span>{int(r["대리점수"])}곳 · {share:.0f}%</span></div>'
            f'<div class="sb-track" style="margin-top:8px"><div class="sb-fill green" style="--w:{share:.1f}%;--d:{i * 80}ms"></div></div>'
            '<div class="sb-group-grid">'
            f'<div><span class="sb-sub-l">영업이익율</span><span class="sb-sub-v">{_e(fmt_pct(r["영업이익율"]))}</span></div>'
            f'<div><span class="sb-sub-l">매출증감율</span><span class="sb-sub-v">{_e(fmt_pct(r["매출증감율"]))}</span></div>'
            f'<div><span class="sb-sub-l">평균 총지원금액</span><span class="sb-sub-v">{_e(fmt_krw(r["총지원금액"]))}</span></div>'
            "</div></div>"
        )
    return wrap(f'<div class="sb-card sb-reveal">{head}<div class="sb-groups">{"".join(groups)}</div></div>')


def insight_cards(promotion_insight: list[str]) -> str:
    blocks = _parse_blocks(promotion_insight)
    if not blocks:
        return wrap('<div class="sb-card"><p class="sb-desc">프로모션 기준 시트가 없어 장단점을 정리할 수 없습니다.</p></div>')
    kinds = [("장점:", "pro", "✓", "장점"), ("단점:", "con", "!", "단점"), ("이번 달", "data", "i", "이번 달 데이터")]
    cards = []
    for b in blocks:
        rows = []
        for line in b["lines"]:
            for prefix, cls, icon, label in kinds:
                if line.startswith(prefix):
                    text = line[len(prefix):].lstrip(" (:").strip()
                    if prefix == "이번 달":
                        text = line.split(":", 1)[1].strip() if ":" in line else line
                        label = line.split(":", 1)[0].strip() if ":" in line else label
                    rows.append(
                        f'<div class="sb-ins-row"><span class="sb-ins-ico {cls}" aria-hidden="true">{icon}</span>'
                        f"<div><b>{_e(label)}</b>{_e(text)}</div></div>"
                    )
                    break
        meta = f'<span class="sb-tag">{_e(b["meta"])}</span>' if b["meta"] else ""
        cards.append(f'<div class="sb-card sb-reveal"><h3>{_e(b["name"])}{meta}</h3>{"".join(rows)}</div>')
    return wrap(f'<div class="sb-insights">{"".join(cards)}</div>')


def upload_intro() -> str:
    steps = [
        ("① DC율 시트", "대리점별 매출DC·성장DC와 매출액(이번 달·전월·전년 동월)"),
        ("② 프로모션 기준 시트", "제품코드별 기준가·산식유형·지원 조건/금액"),
        ("③ DATA 시트", "대리점×제품 매출액·매출수량·영업이익·매출원가"),
    ]
    items = "".join(f'<div class="sb-step"><b>{_e(t)}</b><span>{_e(d)}</span></div>' for t, d in steps)
    return (
        '<div class="sb-root"><div class="sb-page-head"><div><h1>월 마감 실적 워크북 업로드</h1>'
        "<p>워크북을 올리면 분석이 끝나는 대로 결과 대시보드로 바로 이동합니다</p></div></div>"
        f'<div class="sb-steps">{items}</div></div>'
    )
