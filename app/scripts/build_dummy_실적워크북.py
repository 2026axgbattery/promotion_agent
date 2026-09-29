"""제출용 더미 실적 워크북 생성 스크립트.

`.docs/22_더미_실적워크북_생성_계획서.md` 참고. "업로드 실적(8월).xlsx"의 시트 구조·병합
셀·"프로모션 기준" 시트의 제품/산식 설계는 그대로 두고, 대리점 실명과 대리점별 실적
수치(DC율, 매출, 영업이익, 원가, AGM Lv 문턱값 등)만 랜덤으로 바꿔 새 파일로 저장한다.
원본 파일은 건드리지 않는다.

실행: ./.venv/Scripts/python.exe app/scripts/build_dummy_실적워크북.py
출력: <프로젝트 루트>/업로드 실적(8월)_더미.xlsx
"""

from __future__ import annotations

import random
from pathlib import Path

import openpyxl

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SOURCE_PATH = ROOT_DIR / "업로드 실적(8월).xlsx"
OUTPUT_PATH = ROOT_DIR / "업로드 실적(8월)_더미.xlsx"

random.seed(20260929)

_NAME_PREFIX = [
    "한빛", "대영", "삼진", "동양", "현진", "세일", "우진", "대한", "미래", "청솔",
    "은성", "경인", "중앙", "동부", "서부", "남부", "북부", "신성", "일신", "대성",
    "고려", "한성", "부영", "태양", "금강", "청호", "송림", "신라", "가온", "다솜",
    "해오름", "온새미", "든든", "새길", "밝은", "푸른", "맑은", "큰별", "하늘", "이든",
    "정우", "상현", "재원", "동현", "지성", "우성", "형진", "민서", "가람", "누리",
]
_NAME_SUFFIX = ["전지", "배터리", "상사", "상회", "유통", "모터스", "산업", "테크", "파워", "에너지"]
_NAME_STYLE = ["{p}{s}", "(주){p}{s}", "{p}{s}(주)", "주식회사 {p}{s}"]


def _fake_dealer_names(n: int) -> list[str]:
    combos = [(p, s) for p in _NAME_PREFIX for s in _NAME_SUFFIX]
    random.shuffle(combos)
    names = []
    for i, (p, s) in enumerate(combos[:n]):
        style = _NAME_STYLE[i % len(_NAME_STYLE)]
        names.append(style.format(p=p, s=s))
    return names


def _fake_dealer_codes(n: int) -> list[str]:
    """실제 코드와 같은 7자리 "21xxxxx" 형태를 유지하되 중복 없이 새로 뽑는다."""
    pool = random.sample(range(1000, 999999), n)
    return [f"21{code:05d}" for code in pool]


def build_dummy_workbook() -> Path:
    wb = openpyxl.load_workbook(SOURCE_PATH, data_only=True)
    dc_ws, promo_ws, data_ws = wb["DC율"], wb["프로모션 기준"], wb["DATA"]

    # --- 1) 대리점 식별자 매핑(코드+상호명)을 세 시트에 걸쳐 하나로 통일한다 ---
    # DATA 시트에는 DC율 시트에 없는 대리점 코드도 섞여 있다(원본 파일에도 있던 구조 —
    # DC율 미보고 대리점으로 추정). 이 코드들도 실명이 그대로 새어 나가지 않도록 DC율·
    # DATA·AGM Lv 표 전체를 훑어 나온 코드를 다 모아 매핑을 만든다.
    old_codes_seen: list[str] = []
    seen_set: set[str] = set()

    def _collect(code) -> None:
        if code is None:
            return
        code = str(code).strip()
        if code not in seen_set:
            seen_set.add(code)
            old_codes_seen.append(code)

    for r in range(4, dc_ws.max_row + 1):
        _collect(dc_ws.cell(row=r, column=1).value)
    for r in range(2, data_ws.max_row + 1):
        _collect(data_ws.cell(row=r, column=9).value)
    for r in range(3, promo_ws.max_row + 1):
        _collect(promo_ws.cell(row=r, column=24).value)
    old_codes = old_codes_seen
    new_codes = _fake_dealer_codes(len(old_codes))
    new_names = _fake_dealer_names(len(old_codes))
    code_map = dict(zip(old_codes, new_codes))
    name_map = dict(zip(old_codes, new_names))
    # 대리점별 "규모 배율" — DATA 금액·AGM Lv 문턱값에 공통으로 곱해 큰 대리점은 매출도
    # 크고 Lv 문턱값도 높다는 실제 패턴을 더미 데이터에도 유지한다.
    scale = {code: random.uniform(0.2, 4.0) for code in old_codes}

    # --- 2) DATA 시트: 금액/수량 25개 컬럼(18~42열)에 대리점별 배율 × 행별 잡음을 곱한다 ---
    money_cols = list(range(18, 43))
    revenue_by_new_code: dict[str, float] = {}
    for r in range(2, data_ws.max_row + 1):
        old_code = data_ws.cell(row=r, column=9).value
        if old_code is None:
            continue
        old_code = str(old_code).strip()
        if old_code not in code_map:
            continue  # 방어적 처리 — DC율에 없는 코드가 섞여 있으면 손대지 않고 건너뜀
        factor = scale[old_code] * random.uniform(0.85, 1.15)
        for c in money_cols:
            v = data_ws.cell(row=r, column=c).value
            if isinstance(v, (int, float)):
                new_v = v * factor
                data_ws.cell(row=r, column=c, value=round(new_v) if c == 19 else round(new_v, 0))
        new_code = code_map[old_code]
        data_ws.cell(row=r, column=9, value=new_code)
        data_ws.cell(row=r, column=10, value=name_map[old_code])
        revenue_by_new_code[new_code] = revenue_by_new_code.get(new_code, 0.0) + (
            data_ws.cell(row=r, column=18).value or 0
        )

    # --- 3) DC율 시트: 코드/상호명 치환 + DC율 소폭 재추첨 + 매출 이력은 DATA 합계로 재계산 ---
    _DC_RATE_CHOICES = [0.01, 0.05, 0.065, 0.08, 0.085, 0.10, 0.13]
    for r in range(4, dc_ws.max_row + 1):
        old_code = dc_ws.cell(row=r, column=1).value
        if old_code is None:
            continue
        old_code = str(old_code).strip()
        new_code = code_map[old_code]
        dc_ws.cell(row=r, column=1, value=new_code)
        dc_ws.cell(row=r, column=2, value=name_map[old_code])
        dc_ws.cell(row=r, column=3, value=random.choice(_DC_RATE_CHOICES))
        dc_ws.cell(row=r, column=4, value=random.choice([0.0, 0.01, 0.02, 0.03]))

        this_month = revenue_by_new_code.get(new_code, 0.0)
        prev_month = this_month * random.uniform(0.6, 1.6)
        prev_year = this_month * random.uniform(0.5, 1.9)
        dc_ws.cell(row=r, column=5, value=round(this_month))
        dc_ws.cell(row=r, column=6, value=round(prev_month))
        dc_ws.cell(row=r, column=7, value=(this_month - prev_month) / prev_month if prev_month else 0)
        dc_ws.cell(row=r, column=8, value=round(prev_year))
        dc_ws.cell(row=r, column=9, value=(this_month - prev_year) / prev_year if prev_year else 0)

    # --- 4) "프로모션 기준" 시트: 제품/산식 설계(A~S열)는 그대로, AGM Lv 표(X~AB열)만 치환 ---
    for r in range(3, promo_ws.max_row + 1):
        old_code = promo_ws.cell(row=r, column=24).value
        if old_code is None:
            continue
        old_code = str(old_code).strip()
        if old_code not in code_map:
            continue
        new_code = code_map[old_code]
        promo_ws.cell(row=r, column=24, value=new_code)
        promo_ws.cell(row=r, column=25, value=name_map[old_code])
        factor = scale[old_code]
        lv_values = []
        for col in (26, 27, 28):
            v = promo_ws.cell(row=r, column=col).value
            lv_values.append(round((v or 0) * factor / 10) * 10 if isinstance(v, (int, float)) else v)
        # 반올림 후에도 Lv.1<Lv.2<Lv.3 순서가 반드시 유지되도록 최소 10 간격을 강제한다.
        for i in range(1, 3):
            if isinstance(lv_values[i], (int, float)) and isinstance(lv_values[i - 1], (int, float)):
                lv_values[i] = max(lv_values[i], lv_values[i - 1] + 10)
        for col, v in zip((26, 27, 28), lv_values):
            promo_ws.cell(row=r, column=col, value=v)

    wb.save(OUTPUT_PATH)
    return OUTPUT_PATH


if __name__ == "__main__":
    path = build_dummy_workbook()
    print(f"작성 완료: {path}")
