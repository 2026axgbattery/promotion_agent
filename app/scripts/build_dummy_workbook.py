"""`data_sample.xlsx`(실제 양식이지만 값이 비어있는 자료)를 바탕으로, 앱 업로드
테스트에 바로 쓸 수 있도록 모든 값이 채워진 더미 워크북을 만든다.

`data_sample.xlsx`의 총괄표 시트는 영업이익·전월매출·원가 관련 값이 비어 있어
영업이익율·매출증감율·원가율을 계산해볼 수 없었다. 이 스크립트는:
- 거래처코드·거래처명은 원본 그대로 유지하고,
- 판매수량·매출액·DC율·프로모션 지원금액·전월매출·영업이익을 서로 앞뒤가 맞도록
  (즉 매출액 - 원가 - 총지원금액 = 영업이익이 성립하도록) 새로 만들어 채우며,
- 원가(`app/workbook_ingest.py`가 있으면 읽어 원가율을 계산하는 신규 컬럼)를
  총괄표에 추가한다.

실행: python app/scripts/build_dummy_workbook.py
출력: <프로젝트 루트>/dummy_실적워크북.xlsx
"""

from __future__ import annotations

import random
from pathlib import Path

import openpyxl

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SOURCE_PATH = ROOT_DIR / "data_sample.xlsx"
OUTPUT_PATH = ROOT_DIR / "dummy_실적워크북.xlsx"

STORE_ROWS = range(4, 62)  # 총괄표 데이터 구간(4행~61행), 62행은 합계
COST_RATIO_RANGE = (0.65, 0.80)  # 원가율 65~80% 사이에서 무작위
GROWTH_RANGE = (-0.15, 0.30)  # 전월 대비 매출 증감율 -15%~+30%
DC_SALE_CHOICES = [0.01, 0.05, 0.065, 0.08, 0.085, 0.10]
DC_GROWTH_CHOICES = [0.0, 0.0, 0.01, 0.02, 0.03]
ZERO_REVENUE_STORES = {"2100785", "2101134", "2100008"}  # 원본에서도 매출 0이던 대리점(안성상사·(주)제일비엔티·흥신상사)


def _random_promo_amount(매출액: float, rng: random.Random, chance: float, max_ratio: float) -> int:
    if rng.random() > chance:
        return 0
    return round(매출액 * rng.uniform(0.0, max_ratio))


def build_dummy_workbook(seed: int = 42) -> Path:
    rng = random.Random(seed)
    wb = openpyxl.load_workbook(SOURCE_PATH, data_only=True)
    ws = wb["총괄표"]

    ws.merge_cells("T2:T3")
    ws["T2"] = "원가"

    total_원가 = 0.0
    for row in STORE_ROWS:
        store_code = ws.cell(row=row, column=1).value
        if store_code is None:
            continue
        store_code = str(store_code)

        if store_code in ZERO_REVENUE_STORES:
            판매수량 = 0
            매출액 = 0.0
            전월매출 = 0.0
            매출DC율 = 0.0
            성장DC율 = 0.0
            프로모션합계 = 0
            원가 = 0.0
            영업이익 = 0.0
            서브금액 = {"10+1": 0, "대형제품": 0, "특화제품": 0, "기타": 0, "추가": 0, "그외": 0}
        else:
            판매수량 = rng.randint(20, 3000)
            단가 = rng.uniform(80_000, 180_000)
            매출액 = round(판매수량 * 단가)
            매출DC율 = rng.choice(DC_SALE_CHOICES)
            성장DC율 = rng.choice(DC_GROWTH_CHOICES)
            서브금액 = {
                "10+1": _random_promo_amount(매출액, rng, chance=0.5, max_ratio=0.03),
                "대형제품": _random_promo_amount(매출액, rng, chance=0.15, max_ratio=0.01),
                "특화제품": _random_promo_amount(매출액, rng, chance=0.1, max_ratio=0.01),
                "기타": _random_promo_amount(매출액, rng, chance=0.1, max_ratio=0.005),
                "추가": _random_promo_amount(매출액, rng, chance=0.15, max_ratio=0.005),
                "그외": _random_promo_amount(매출액, rng, chance=0.3, max_ratio=0.01),
            }
            프로모션합계 = sum(서브금액.values())
            원가율 = rng.uniform(*COST_RATIO_RANGE)
            원가 = round(매출액 * 원가율)
            성장률 = rng.uniform(*GROWTH_RANGE)
            전월매출 = round(매출액 / (1 + 성장률))
            DC지원금액 = (매출DC율 + 성장DC율) * 매출액
            영업이익 = round(매출액 - 원가 - DC지원금액 - 프로모션합계)

        ws.cell(row=row, column=3, value=판매수량)  # C: 판매수량
        ws.cell(row=row, column=5, value=매출액)  # E: 실 매출액
        ws.cell(row=row, column=6, value=전월매출)  # F: 전월 매출
        ws.cell(row=row, column=8, value=영업이익)  # H: 영업이익
        ws.cell(row=row, column=9, value=매출DC율)  # I: 매출DC
        ws.cell(row=row, column=10, value=성장DC율)  # J: 성장DC
        ws.cell(row=row, column=11, value=서브금액["10+1"])  # K
        ws.cell(row=row, column=12, value=서브금액["대형제품"])  # L
        ws.cell(row=row, column=13, value=서브금액["특화제품"])  # M
        ws.cell(row=row, column=14, value=서브금액["기타"])  # N
        ws.cell(row=row, column=15, value=서브금액["추가"])  # O
        ws.cell(row=row, column=16, value=서브금액["그외"])  # P
        ws.cell(row=row, column=17, value=프로모션합계)  # Q
        ws.cell(row=row, column=20, value=원가)  # T (신규)

        total_원가 += 원가

    ws.cell(row=62, column=20, value=round(total_원가))

    wb.save(OUTPUT_PATH)
    return OUTPUT_PATH


if __name__ == "__main__":
    path = build_dummy_workbook()
    print(f"더미 워크북을 만들었습니다: {path}")
