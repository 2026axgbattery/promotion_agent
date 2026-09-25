# SEBANG Design System 사용법

압축 풀면 아래 구조입니다.

```
sebang-design-system/
├── design.md      ← 규칙 문서 (사람이 읽는 참고용, 자동 적용 안 됨)
├── sebang.css     ← 폰트+토큰 CSS (링크하는 순간 바로 적용됨)
└── fonts/
    ├── SebangGothic-Regular.woff2   ← 직접 @font-face 걸고 싶을 때 참조용 원본
    └── SebangGothic-Bold.woff2
```

## 가장 빠른 방법 (권장)
프로젝트 아무 곳에나 `sebang.css`만 복사하고, HTML `<head>`에 한 줄만 추가하세요.

```html
<link rel="stylesheet" href="./sebang.css">
```

이 순간 바로:
- `body` 기본 서체가 **SEBANG Gothic**으로 바뀝니다 (폰트 데이터가 파일 안에 내장돼 있어 `fonts/` 폴더가 없어도 동작합니다)
- `var(--sebang-ink)`, `var(--color-accent-primary)` 같은 CSS 변수를 프로젝트 어디서든 바로 쓸 수 있습니다

## 주의할 점
`sebang.css`를 링크하지 않고 `design.md`나 `fonts/` 폴더만 프로젝트에 "넣어두기만" 하면 아무것도 적용되지 않습니다. 웹은 이런 파일을 자동으로 스캔해서 반영하지 않고, 코드에서 명시적으로 불러와야만 동작합니다. 즉:
- `design.md`만 있으면 → 사람(또는 AI)이 읽고 그 규칙대로 코드를 짜야 적용됩니다.
- `sebang.css`를 `<link>`로 걸면 → 폰트/색상 변수가 즉시 실제로 적용됩니다.
- `fonts/*.woff2`는 `sebang.css`를 안 쓰고 직접 `@font-face`를 작성하고 싶을 때만 필요합니다 (design.md 3.1절에 예시 있음).

## 다크 모드를 쓰는 프로젝트라면
`<html data-theme="dark">`를 토글하면 `sebang.css`에 이미 들어있는 다크 모드 색상 토큰이 자동으로 전환됩니다.
