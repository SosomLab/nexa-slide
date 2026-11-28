# -*- coding: utf-8 -*-
"""백업 파일 이름(ledger.backup_name) 시험 - 연달아 저장해도 이름이 겹치지 않는다(PG-118).
    python3 studio/tests/backup_name_test.py
시계 값만으로 지은 이름은 겹쳤다 - Windows 의 Python 3.12 이하는 datetime.now() 가 약 15.6ms 눈금이라 그 안의 두 저장이 같은 이름을 만들어
뒤 저장이 앞 백업을 덮어썼다(원장의 before.hash 와 백업 내용이 어긋남). 한 폴더에 300번(접미사 없음 · -build · -ext 를 섞어) 이름을 잡아 본다:
- 이름이 모두 다르다 · 시각 부분(접미사를 뺀 22자)도 모두 다르다 · 이름 순서 = 만든 순서 · 이름마다 자리(파일)가 잡혀 있다 · 형식 그대로"""
import os
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr): _s.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
os.environ.setdefault("NEXA_SLIDE_WORKSPACE", str(STUDIO.parent / "example"))  # ledger 를 불러오려면 작업 공간이 있어야 한다(쓰지는 않는다 - 이름은 임시 폴더에 잡는다)
sys.path.insert(0, str(STUDIO))
import ledger  # noqa: E402
import tmpfiles  # noqa: E402

FAILS = []


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def main():
    with tmpfiles.temp_dir("bn-test") as tmp:
        d = Path(tmp) / "hist"
        names = [ledger.backup_name(d, s) for _ in range(100) for s in ("", "-build", "-ext")]
        stems = [n[:22] for n in names]
        dup = sorted({n for n in names if names.count(n) > 1})[:3]
        dups = sorted({s for s in stems if stems.count(s) > 1})[:3]
        print(f"   python {sys.version.split()[0]} · 이름 {len(names)}개 · 서로 다른 시각 {len(set(stems))}개 · 예 {names[0]} · {names[1]} · {names[2]}")
        check("이름 300개가 모두 다르다", len(set(names)) == len(names), f"겹친 이름 {dup}")
        check("시각 부분도 모두 다르다(접미사가 달라도 같은 시각을 쓰지 않는다 - 시각이 곧 순서)", len(set(stems)) == len(stems), f"겹친 시각 {dups}")
        check("이름 순서 = 만든 순서(오래된 것부터 지우기가 맞게 돈다)", sorted(names) == names, str([(i, a, b) for i, (a, b) in enumerate(zip(names, sorted(names))) if a != b][:2]))
        miss = [n for n in names if not (d / n).is_file()]
        check("이름마다 자리(파일)가 잡혀 있다", not miss, str(miss[:3]))
        bad = [n for n in names if not re.fullmatch(r"\d{8}-\d{6}-\d{6}(-build|-ext)?\.json", n)]
        check("이름 형식 그대로(YYYYmmdd-HHMMSS-ffffff<접미사>.json)", not bad, str(bad[:3]))
    print("\n실패: 없음" if not FAILS else "\n실패: " + str(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
