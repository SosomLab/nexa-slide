# -*- coding: utf-8 -*-
"""엔진 요청 검증 ④(studio/engine_regress.py) - 0.22.24.
격리된 사용자 설정 폴더와 엔진 **복제본**(git clone --shared, 저장소 밖)에서: (a) 변경 없음 → 0 · (b) 템플릿 토큰 하나를 바꾸면 그 덱의 모든 장이 unexpected → 1
· (c) --allow 덱 → 0, --allow 덱:장 하나 → 여전히 1 · (d) 깨진 덱 JSON → failed·2 · (e) 원본 작업 공간 파일 mtime 불변 · (f) --json 구조 · (g) 사본이 지워진다.
python-pptx 가 필요하다(없으면 SKIP)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8", errors="replace")
STUDIO = Path(__file__).resolve().parents[1]
ENGINE = STUDIO.parent
WORK = Path(os.environ.get("NEXA_TEST_DIR") or Path(tempfile.gettempdir()) / "nexa-slide-tests")
ROOT = WORK / "regress"


def _onerr(fn, p, exc):  # git 개체 파일은 읽기 전용이라 Windows 의 rmtree 가 멈춘다
    try:
        os.chmod(p, 0o700)
        fn(p)
    except OSError:
        pass


if ROOT.exists():
    shutil.rmtree(ROOT, onerror=_onerr)
    if ROOT.exists():
        sys.exit(f"이전 시험 폴더를 지우지 못했다: {ROOT}")
USER, PROJ, CLONE = ROOT / "user", ROOT / "projects", ROOT / "engine"
for _d in (USER, PROJ):
    _d.mkdir(parents=True, exist_ok=True)
ENV = {**os.environ, "NEXA_SLIDE_USER_DIR": str(USER), "NEXA_SLIDE_PROJECTS": str(PROJ), "PYTHONIOENCODING": "utf-8"}
ENV.pop("NEXA_SLIDE_WORKSPACE", None)
FAILS = []

try:
    import pptx  # noqa: F401
except ImportError:
    print("SKIP python-pptx 없음")
    sys.exit(0)


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL"), name, "" if cond else extra)
    if not cond:
        FAILS.append(name)


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace")


def regress(*args, timeout=600):
    cmd = [sys.executable, str(CLONE / "studio" / "engine_regress.py"), "--base", "HEAD", "--no-example", "--max-seconds", "300", *args]
    return subprocess.run(cmd, cwd=str(CLONE), env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)


# 엔진 복제본 - 지금 작업 트리의 studio/ 를 덮어쓰고 커밋해 working tree == HEAD 로 만든다(시험 대상 = 작업 트리 코드, 기준 HEAD 와 비교하면 "변경 없음")
r = git("clone", "-q", "--shared", str(ENGINE), str(CLONE), cwd=WORK)
check("엔진 복제", r.returncode == 0 and (CLONE / "studio").is_dir(), r.stderr[-300:])
if FAILS:
    sys.exit(1)
shutil.rmtree(CLONE / "studio")
shutil.copytree(STUDIO, CLONE / "studio", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
git("add", "-A", cwd=CLONE)
r = git("-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-q", "--allow-empty", "-m", "test: working tree", cwd=CLONE)
check("복제본에 작업 트리 커밋", r.returncode == 0 and (CLONE / "studio" / "engine_regress.py").is_file(), r.stderr[-300:])
# 작업 공간: example 사본을 저장소 밖에 두고 settings.json recent 에 등록
WS = PROJ / "regress-ws"
shutil.copytree(ENGINE / "example", WS)
(USER / "settings.json").write_text(json.dumps({"recent": [{"path": str(WS), "title": "regress", "opened": "2026-10-17T00:00:00"},
                                                           {"path": str(PROJ / "missing"), "title": "none", "opened": "2026-10-17T00:00:00"}]},
                                               ensure_ascii=False), encoding="utf-8")
before = {p: p.stat().st_mtime_ns for p in WS.rglob("*") if p.is_file()}

# (a) 변경 없음
t0 = time.time()
r = regress()
print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:])
check("(a) 변경 없음 → 종료 0", r.returncode == 0, r.stdout[-600:] + r.stderr[-300:])
check("(a) 등록된 작업 공간 1 · 없는 경로는 건너뜀 보고", "작업 공간 1 " in r.stdout and "skipped" in r.stdout and "동일 1" in r.stdout, r.stdout[-600:])
print(f"     ({round(time.time() - t0, 1)}초)")

# (b) 템플릿 토큰 하나를 바꾼다 → 모든 장이 예상 밖
tok = CLONE / "studio" / "templates" / "lecture" / "tokens.json"
orig = tok.read_text(encoding="utf-8")
assert '"primary": "#A91F24"' in orig, "lecture 토큰 primary 를 찾지 못했다 - 시험 갱신 필요"
tok.write_text(orig.replace('"primary": "#A91F24"', '"primary": "#A91F25"'), encoding="utf-8")
r = regress("--json")
try:
    res = json.loads(r.stdout)
except ValueError:
    res = {}
    check("(b) --json 출력", False, r.stdout[-300:] + r.stderr[-300:])
decks = [d for w in res.get("workspaces", []) for d in w.get("decks", [])]
demo = next((d for d in decks if d["deck"] == "demo"), {})
check("(b) 토큰 변경 → 종료 1", r.returncode == 1, r.stderr[-300:])
slides_b = demo.get("slides", {})
check("(b) demo 덱 unexpected · primary 를 쓰는 장들이 장별로 보고(1장 포함, 3장 이상)", demo.get("status") == "unexpected" and "1" in slides_b and len(slides_b) >= 3,
      json.dumps(demo, ensure_ascii=False)[:400])
check("(b) 기타 부품(presentation.xml 등)은 차이 없음", not demo.get("other"))
check("(b) 장 항목에 부품·첫 차이 줄", bool(demo.get("slides", {}).get("1", {}).get("parts", [{}])[0].get("lines")))
check("(b) counts.unexpected == 1", res.get("counts", {}).get("unexpected") == 1)
# (c) --allow
r = regress("--allow", "demo")
check("(c) --allow demo → 종료 0 · 의도한 변경 1", r.returncode == 0 and "의도한 변경 1" in r.stdout, r.stdout[-400:])
r = regress("--allow", "demo:1")
check("(c) --allow demo:1 만 → 나머지 장이 예상 밖 → 종료 1", r.returncode == 1 and "장 2 [예상 밖]" in r.stdout and "장 1 [의도]" in r.stdout, r.stdout[-600:])
tok.write_text(orig, encoding="utf-8")

# (d) 깨진 덱 → failed · 2 (조용히 통과하지 않는다)
bad = WS / "decks" / "broken.json"
bad.write_text("{ not json", encoding="utf-8")
r = regress()
check("(d) 깨진 덱 → 실패 보고 · 종료 2", r.returncode == 2 and "broken: failed" in r.stdout and "동일 1" in r.stdout, r.stdout[-600:])
bad.unlink()

# (e) 원본 mtime 불변 (broken.json 은 시험이 넣었다 지운 것)
after = {p: p.stat().st_mtime_ns for p in WS.rglob("*") if p.is_file()}
check("(e) 원본 작업 공간 파일이 바뀌지 않았다", after == before, str([str(p) for p in after if after.get(p) != before.get(p)][:5]))
# (g) 사본 정리 · 기준 엔진 재사용 폴더
scratch = USER / "hub" / "engine" / "scratch"
check("(g) regress-* 사본이 지워졌다", not list(scratch.glob("regress-*")), str(list(scratch.glob("regress-*"))[:3]))
check("(g) 기준 엔진 engine-<해시>/ 는 남아 재사용", bool(list(scratch.glob("engine-*/studio/export_pptx.py"))))
r = regress("--keep")
check("(g) --keep 이면 사본이 남는다", r.returncode == 0 and bool(list(scratch.glob("regress-*"))))

print("\n실패:", ", ".join(FAILS) if FAILS else "없음")
sys.exit(1 if FAILS else 0)
