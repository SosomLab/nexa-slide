# 임시 파일 정리 - 점검 결과와 예방 설계 (2026-11-03)

## 1. 무슨 일이 있었나

- `studio/tests/smoke.js` 가 실행마다 OS 임시 폴더(`%TEMP%`)에 헤드리스 Chrome 프로필 `nx-smoke-*`(약 1,000개 항목)를 만들고 지우지 않았다.
- 2,000회 가까이 쌓이자 로그온 때 Temp 전체를 훑는 작업이 4~5분 걸려, PIN 입력 뒤 바탕화면이 늦게 떴다.
- 818453f(2026-11-03)에서 고쳤다: Chrome 을 끝낸 직후 `finally` 에서 프로필을 지운다(파일을 쥐고 있을 수 있어 10회 × 200ms 다시 시도).

## 2. 수정 확인 (2026-11-03)

- 빈 시나리오로 `smoke.js` 를 돌려 실행 전후 `nx-smoke-*` 가 0 → 0 인 것을 봤다. 쌓였던 폴더도 없고 Temp 는 54개 항목.
- 정상 종료·시나리오 예외는 `finally` 가 덮는다.
- **남은 구멍**: 시간 초과·Ctrl+C 로 node 가 강제로 끝나면 `finally` 가 돌지 않아 그 한 번 분량이 남는다(3절 ② 가 덮는다).

## 3. 같은 종류의 누수 - `mkdtemp` 뒤 정리가 없는 곳

| 위치 | 남는 것 | 언제 |
|---|---|---|
| `studio/export_xlsx.py` `source_project` | `nexa-vba-*/vbaProject.bin` | 매크로 시트를 .xlsm 으로 내보낼 때마다(**운영 코드**) |
| `studio/sheet_import.py` (도형 내보내기) | `nexa-shapes-*`(도형 PNG) | Excel 이 있는 PC 에서 엑셀을 가져올 때마다(**운영 코드**) |
| `tests/autostart_test.py` | `nexa-autostart-*` | 시험마다 - 2026-11-03 실행으로 실제로 남는 것을 봤다 |
| `tests/engine_tidy_test.py` | `nexa-engine-tidy-*` | 시험마다 |
| `tests/sheet_roundtrip_test.py` · `sheet_font_test.py` | `nexa-sheet-rt-*` · `nexa-sheet-font-*` | 시험마다 |
| `tests/template_rec_test.py` · `py_shims_test.py` | `nexa-tplrec-*` · `nexa-pyshim-user-*` | 시험마다(사용자 설정 격리 폴더) |
| `tests/vba_safety_test.py` | `vbasafe-*`(접두사 규칙 밖) | 시험마다 |
| `tests/xlsm_crosscheck.py` | `nexa-xcheck-*` | 수동 실행, `--keep` 없을 때 |

`<임시 폴더>/nexa-slide-tests/`(약 2,600개 항목)는 실행마다 같은 폴더를 다시 쓰므로 늘어나지 않는다 - 누수 아님.

## 4. 예방 설계

**① 임시 폴더는 한 가지 방법으로만**
- `common.py` 에 `temp_dir(prefix)` context manager 를 둔다. 이름은 늘 `nexa-<prefix>-`.
- 블록이 끝나면 지운다(Windows 에서 파일을 쥐고 있으면 다시 시도, 끝내 실패하면 경고만).
- 3절의 곳을 모두 이것으로 바꾼다. 값을 돌려주는 함수(`source_project`)는 호출부(`export`)가 `with` 로 감싼다.
- `smoke.js` 는 Node 라 그대로 두되 접두사 규칙(`nx-smoke-`)을 지킨다.

**② 비정상 종료로 남은 것 쓸어내기**
- `run_all.py` 시작 때와 허브 `service.py start` 때 Temp 의 `nexa-*`·`nx-smoke-*` 중 **하루 넘게 지난 것**을 지운다.
- 지우지 못하는 것(사용 중)은 건너뛴다. `nexa-slide-tests`·`nexa-slide-tests.lock` 은 빼고 지운다.

**③ 누수 시험 - 재발 방지의 핵심**
- `run_all.py` 가 각 시험 전후 Temp 의 `nexa-*`·`nx-*` 목록을 비교해, 새로 남은 것이 있으면 그 시험 이름과 함께 FAIL 로 처리한다.
- 배포는 0.25.10 부터 시험을 기본으로 건너뛴다 - 이 시험은 `run_all` 과 배포 [시험도 돌리기]·`--tests` 에서 걸린다. 엔진 요청 처리의 검증 단계에서 `run_all` 을 돌릴 때 함께 확인된다.

**④ 눈에 보이게**
- `engine_tidy.py` 범주에 "Temp 의 nexa 잔여물"을 더한다(보고 → 고른 범주만 지움, 기존 흐름 그대로).
- 허브 상태에 Temp 항목 수를 보이고 500개를 넘으면 경고한다 - 이번처럼 로그온이 느려진 뒤에야 알게 되는 것을 막는다.

**⑤ 규칙으로 적기**
- CLAUDE.md: "임시 파일·폴더는 `common.temp_dir` 만 - 직접 `mkdtemp` 금지(누수 시험이 잡는다)."
- `docs/dev/tests.md` "시험을 더하려면" 에 같은 줄.

## 5. 진행

- [x] smoke.js 프로필 삭제(818453f) · 확인
- [x] 점검(3절) · 설계(4절) - 이 문서
- [ ] ① `common.temp_dir` · 3절 9곳 바꾸기
- [ ] ② 오래된 잔여물 쓸어내기
- [ ] ③ 누수 시험
- [ ] ④ engine_tidy 범주 · 허브 경고
- [ ] ⑤ CLAUDE.md · tests.md 규칙
