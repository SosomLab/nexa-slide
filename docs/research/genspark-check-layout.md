# Genspark `check_slide_layout` 출력 원문과 판정 기준 추정 (2026-10-01)

> 출처: 에이전트 대화 기록의 "슬라이드 레이아웃 확인 → 보기" 펼침 9건 중 내용이 있는 8건(원문 그대로). 크레딧 사용 없이 대화 기록에서 읽음.
> 판정 기준은 공개 문서가 없어 **출력 좌표로 역산한 추정**이다(검산 근거를 함께 적음).

## 1. 원문

### (1) 1~4장 첫 검사 — WARNING 3
```
Layout check — deck oracle-sql-tuning-ch00, canvas 1920×1080, 4 slide(s): 0 error(s), 3 warning(s)

ERROR findings are mechanically verified defects (held-out precision >=80%). Fix them unless your design context clearly indicates the effect is intentional. WARNING findings are likely-but-unconfirmed. Verify with capture_slide_screenshot region capture before acting.

cover.html (rendered 1920×1080, 7 elements; 0 error(s), 0 warning(s))

no verified layout issues detected

tuning-order.html (rendered 1920×1080, 25 elements; 0 error(s), 0 warning(s))

no verified layout issues detected

seven-stage-journey.html (rendered 1920×1080, 94 elements; 0 error(s), 3 warning(s))

WARNINGS — verify with a capture_slide_screenshot region capture of the reported rect before fixing:

[t2.cutoff.spill] el[10041] (textbox, at 680,548 300×17) "[opt: 공유 커서 없음 = 하드 파싱]" — text clipped (rect 298,230 568×742, ~114px cut): "[opt: 공유 커서 없음 = 하드 파싱]"
[t1.overlap.text-text] el[2] (textbox, at 120,110 1680×105) "0.2.1 요청 한 번의 여정 — 7단계 응답시간 = ①~⑦의 합(각 단계의 대기 포함) — 느린 원인은 D" ∩ el[4] (textbox, at 318,210 520×20) "WAS 프로세스" → 106×5 at (318,210)
[t1.overlap.text-text] el[62] (textbox, at 60,924 300×19) "[ loop — 남은 행이 있는 동안 ]" ∩ el[91] (textbox, at 200,930 240×19) "렌더링(그리드·차트)" → 43×13 at (200,930)
cost-by-stage.html (rendered 1920×1080, 6 elements; 0 error(s), 0 warning(s))

no verified layout issues detected
```

### (2) 5~8장 첫 검사 — ERROR 1 + WARNING 1 (유일한 ERROR 사례)
```
Layout check — deck oracle-sql-tuning-ch00, canvas 1920×1080, 4 slide(s): 1 error(s), 1 warning(s)

ERROR findings are mechanically verified defects (held-out precision >=80%). ...

workload-pair.html (rendered 1920×1080, 12 elements; 0 error(s), 0 warning(s))

no verified layout issues detected

same-plan-different-slope.html (rendered 1920×1080, 18 elements; 0 error(s), 0 warning(s))

no verified layout issues detected

viewing-execution-plan.html (rendered 1920×1080, 7 elements; 1 error(s), 1 warning(s))

ERRORS — fix unless your design context clearly indicates it's intentional:

[t1.cutoff.ancestor-clip] el[6] (textbox, at 100,252 850×224) "1 SELECT /*+ GATHER_PLAN_STATISTICS */ 2 d.item_cd, SUM(d.qt" — text clipped (rect 220,1052 597×56, ~171px cut): "작은 차이도 행이 많아지면 계획을 바꾼다 → | ch12 | ¹"

WARNINGS — verify with a capture_slide_screenshot region capture of the reported rect before fixing:

[t1.overlap.text-over-shape] el[5] (shape, at 90,258 860×30) ∩ el[6] (textbox, at 100,252 850×224) "1 SELECT /*+ GATHER_PLAN_STATISTICS */ 2 d.item_cd, SUM(d.qt" → 61×13 at (162,258)
reading-execution-plan.html (rendered 1920×1080, 7 elements; 0 error(s), 0 warning(s))

no verified layout issues detected
```

### (3) 3장 재작성 후 — WARNING 5 (경계 사각형이 있던 판)
```
Layout check — deck oracle-sql-tuning-ch00, canvas 1920×1080, 1 slide(s): 0 error(s), 5 warning(s)

seven-stage-journey.html (rendered 1920×1080, 94 elements; 0 error(s), 5 warning(s))

WARNINGS — verify with a capture_slide_screenshot region capture of the reported rect before fixing:

[t2.cutoff.spill] el[10043] (textbox, at 740,624 178×19) "구문·의미 검사 →" — text clipped (rect 128,340 732×602, ~58px cut): "구문·의미 검사 →"
[t1.overlap.text-crosses-border] el[3] (shape, at 128,340 732×602) ∩ el[6] (textbox, at 148,325 170×30) "WAS 프로세스" → 94×4 at (186,340)
[t1.overlap.text-crosses-border] el[3] (shape, at 128,340 732×602) ∩ el[76] (textbox, at 430,932 280×19) "메모리 적재" → 63×4 at (538,938)
[t1.overlap.text-crosses-border] el[4] (shape, at 880,340 922×602) ∩ el[8] (textbox, at 900,325 240×30) "DBMS (Oracle 인스턴스)" → 177×4 at (932,340)
[t1.overlap.text-text] el[82] (textbox, at 160,985 280×19) "후처리(집계·가공)" ∩ el[87] (textbox, at 240,984 240×19) "HTTP 응답(JSON)" → 75×18 at (339,985)
```

### (4) 3·7장 재검사 — WARNING 3
```
seven-stage-journey.html (rendered 1920×1080, 93 elements; 0 error(s), 3 warning(s))
[t2.cutoff.spill] el[10041] (textbox, at 730,608 180×19) "구문·의미 검사" — text clipped (rect 128,330 732×612, ~50px cut): "구문·의미 검사"
[t1.overlap.text-crosses-border] el[61] (shape, at 60,880 1803×34) ∩ el[81] (textbox, at 160,872 280×19) "후처리(집계·가공)" → 101×5 at (339,880)
[t1.overlap.text-text] el[83] (textbox, at 60,980 34×34) "⑦" ∩ el[90] (textbox, at 80,978 280×19) "렌더링(그리드·차트)" → 6×13 at (80,984)
viewing-execution-plan.html (rendered 1920×1080, 15 elements; 0 error(s), 0 warning(s))
no verified layout issues detected
```

### (5) 그룹 사각형 제거 후 — WARNING 2
```
seven-stage-journey.html (rendered 1920×1080, 92 elements; 0 error(s), 2 warning(s))
[t1.overlap.text-text] el[46] (textbox, at 1330,610 170×21) "최적화²" ∩ el[60] (textbox, at 1140,626 300×19) "실행: 블록 읽기·조인·정렬" → 36×5 at (1395,626)
[t1.overlap.text-text] el[80] (textbox, at 160,975 200×19) "후처리(집계·가공)" ∩ el[89] (textbox, at 280,975 260×19) "렌더링(그리드·차트)" → 80×19 at (280,975)
```

### (6) 통과 시 꼬리말 (문제 0건일 때만 붙음)
```
Layout check — deck oracle-sql-tuning-ch00, canvas 1920×1080, 7 slide(s): 0 error(s), 0 warning(s)
... (파일마다) no verified layout issues detected
A clean layout check can never justify telling the user a reported problem is fixed — confirm with a region capture of the reported area.
```

## 2. 형식 정리

| 수준 | 형식 |
|---|---|
| 머리 | `Layout check — deck <deck>, canvas <W>×<H>, <N> slide(s): <e> error(s), <w> warning(s)` + 고정 안내문(ERROR/WARNING 정의) |
| 파일 | `<file> (rendered <W>×<H>, <k> elements; <e> error(s), <w> warning(s))` → 문제가 없으면 `no verified layout issues detected` |
| 묶음 | `ERRORS — fix unless your design context clearly indicates it's intentional:` / `WARNINGS — verify with a capture_slide_screenshot region capture of the reported rect before fixing:` |
| 겹침 항목 | `[<rule>] el[<i>] (<type>, at <x>,<y> <w>×<h>) "<text 60자>" ∩ el[<j>] (<type>, at …) "<text>" → <w>×<h> at (<x>,<y>)` ← 교차 사각형 |
| 잘림 항목 | `[<rule>] el[<i>] (<type>, at …) "<text>" — text clipped (rect <x>,<y> <w>×<h>, ~<n>px cut): "<잘린 텍스트>"` |
| 꼬리 | 0건일 때만 "깨끗한 결과로 사용자에게 고쳤다고 말하지 말라, 영역 캡처로 확인하라" |

- 필드: 규칙 ID · 요소 번호 `el[i]` · 종류(textbox/shape) · 요소 경계 사각형 · 텍스트 앞 60자 · 교차 사각형 또는 잘림 정보. **수정 제안은 없음**(무엇을 고칠지는 에이전트가 판단)
- `<k> elements` = 그 장의 `data-object` 개수와 일치(94·93·92). `el[i]` = 그 목록의 순번(0부터). `el[10041]` 같은 1만대 번호는 data-object가 아닌 **내부 텍스트 노드용 별도 번호**로 보임(spill 규칙에서만 등장)
- 좌표는 1920×1080 슬라이드 px, 정수

## 3. 규칙별 판정 기준 (역산 추정)

| 규칙 | 등급(관측) | 의미 | 검산 근거 |
|---|---|---|---|
| `t1.overlap.text-text` | WARNING | 글상자 두 개의 경계 사각형이 겹침 | 교차 면적 최소 관측 **6×13=78px²**(⑦ 배지와 글자), 5px 높이도 보고 → 면적·비율 하한이 매우 낮음(사실상 >0) |
| `t1.overlap.text-crosses-border` | WARNING | 글상자가 **도형의 테두리 선을 가로지름**(슬라이드 경계 아님) | 교차 높이가 늘 **4~5px** = 도형 윗변 띠. el[3] shape(128,340 732×602)의 윗변 y=340을 글상자(325~355)가 걸침 → 94×4 at (186,340). 도형 안에 완전히 든 글자는 보고되지 않음 |
| `t1.overlap.text-over-shape` | WARNING | 글상자가 도형 **내부**와 겹침(배경 강조 띠 위 코드 등) | 강조 줄 배경(90,258 860×30)과 코드 블록 → 61×13 |
| `t2.cutoff.spill` | WARNING | 글상자가 자기를 담고 있는 도형 영역 **밖으로 삐져나감**(기하 비교, scrollHeight 아님) | cut = (글상자 오른쪽 끝) − (영역 오른쪽 끝): 680+300−(298+568)=**114** ✓, 730+180−(128+732)=**50** ✓, 740+178−(128+732)=**58** ✓ |
| `t1.cutoff.ancestor-clip` | **ERROR** | `overflow:hidden` 조상(슬라이드 컨테이너 1920×1080 포함)에 의해 글자가 **실제로 잘림** = 슬라이드 밖 검사 | 잘린 텍스트 rect y=1052 높이 56 → 1108 > 1080. 보고된 el[6]은 코드 글상자, 잘린 텍스트는 그 아래 콜아웃 → 렌더 후 텍스트 줄 단위로 측정하는 것으로 보임. "~171px cut" 산식은 미확정 |

- 접두 `t1`/`t2`는 등급이 아니라 **규칙 계층(tier)**로 보임: t1.overlap 규칙은 WARNING, t1.cutoff.ancestor-clip은 ERROR → 같은 t1 안에 두 등급이 섞임
- 관측되지 않은 규칙: 최소 글자 크기, 슬라이드 밖으로 나간 개체(잘리지 않은 경우), 대비, 원문 대조

## 4. ERROR와 WARNING
- 안내문 원문: "ERROR findings are mechanically verified defects (held-out precision >=80%). ... WARNING findings are likely-but-unconfirmed. Verify with capture_slide_screenshot region capture before acting."
- 뜻: ERROR 규칙은 **따로 떼어 둔 라벨 데이터(held-out set)에서 정밀도 80% 이상**(ERROR로 보고된 것 중 실제 결함 비율 ≥80%)이 검증된 규칙 → 바로 고침. WARNING은 그 기준에 못 미치는 규칙 → 영역 캡처(`capture_slide_screenshot`)로 눈으로 확인한 뒤 고침
- 실제 흐름: 에이전트가 WARNING마다 "Capturing slide N for visual review"로 캡처한 뒤 판단

## 5. 범위와 표시
- **호출할 때 장 목록을 지정**: 4장씩(1~4, 5~8), 2장(3·7), 1장(3), 7장, 전체 → 결과는 덱 머리 아래 파일별로 묶임
- 표시 위치: **에이전트 대화 안의 도구 실행 카드("슬라이드 레이아웃 확인" + 한 줄 설명 + "보기" 펼침)에만** 나옴
  - 검증 탭(`verify-panel`)은 콘텐츠 검증 전용 — 레이아웃 결과 없음("검증 기록이 없습니다")
  - 레일 배지(`rail-mark-badge`)는 사용자 주석 개수 — 레이아웃 결과와 무관
  - 결과 항목을 눌러 해당 요소로 이동하는 기능 **없음**(일반 텍스트)
- 사용자용 버튼 "레이아웃 수정"(`ai-edit-fix-layout`)은 같은 검사기를 쓰는 에이전트 작업으로 추정(크레딧 사용, 미실행)
