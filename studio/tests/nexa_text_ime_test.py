# -*- coding: utf-8 -*-
"""nexa-text.js 한글 조합(IME) 시험(헤드리스 Chrome, PG-032) - 이벤트 흉내가 아니라 CDP 입력(Input.imeSetComposition · Input.insertText ·
Input.dispatchKeyEvent)으로 브라우저가 실제로 조합 이벤트와 DOM 변경을 만들게 한다. 서버 없이 tests/nexa_text_page.html 을 파일로 연다.
    python studio/tests/nexa_text_ime_test.py
단계 = {pre: 준비 JS, cdp: [명령…], js: 판정(참이면 통과, 글이면 실패 사유 - 모델·DOM 덤프)} - smoke.js 의 cdp 단계."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import tmpfiles  # noqa: E402
import testlock  # noqa: E402,F401 - run_all 의 누수 검사·고정 포트와 겹치지 않게(이 시험도 Chrome·임시 폴더를 쓴다)


def comp(*texts):
    """한 글자씩 조합 중인 글(마지막이 확정 전 상태) - imeSetComposition 여러 번"""
    return [{"method": "Input.imeSetComposition", "params": {"text": t, "selectionStart": len(t), "selectionEnd": len(t)}, "wait": 30} for t in texts]


def commit(t):
    return [{"method": "Input.insertText", "params": {"text": t}, "wait": 60}]


def key(k, code, vk, text=None):
    down = {"type": "keyDown" if text else "rawKeyDown", "key": k, "code": code, "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk}
    if text:
        down["text"] = text
    return [{"method": "Input.dispatchKeyEvent", "params": down, "wait": 20},
            {"method": "Input.dispatchKeyEvent", "params": {"type": "keyUp", "key": k, "code": code, "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk}, "wait": 60}]


HANGUL = comp("ㅎ", "하", "한") + commit("한") + comp("ㄱ", "그", "글") + commit("글")
DUMP = "JSON.stringify({model:DOC.blocks.filter(b=>b.runs).map(b=>[b.id,b.runs]),dom:[...document.querySelectorAll('#ed [data-id]')].map(e=>e.dataset.id+'='+e.textContent),caret:caret(),log:LOG})"
WAIT = "await new Promise(r=>setTimeout(r,120)); "
R = "reset(); "
STEPS = [
    ("(a) 문단 끝에서 '한글' - 모델에 한 번만(중복·누락 없음) · DOM 같음 · 커서 뒤",
     R + "sel('b1',4);", HANGUL, WAIT + "return txt('b1')==='가나다라한글' && dom('b1')==='가나다라한글' && caret()==='b1:6' || " + DUMP),
    ("(b) 굵은 글 안에서 조합 - 굵게 이어짐",
     R + "sel('b2',8);", HANGUL, WAIT + "const r=blk('b2').runs; return txt('b2')==='Hello bi한글g world' && r.some(x=>x.b && x.t==='bi한글g') || " + DUMP),
    ("(b) 빈 문단에서 조합",
     R + "sel('b3',0);", HANGUL, WAIT + "return txt('b3')==='한글' && dom('b3')==='한글' && caret()==='b3:2' || " + DUMP),
    ("(b) 굵은 문단의 끝에서 조합",
     R + "sel('b2',15);", HANGUL, WAIT + "return txt('b2')==='Hello big world한글' && caret()==='b2:17' || " + DUMP),
    ("(b) 고른 글 위에서 조합 - 고른 글이 조합 글로 바뀜",
     R + "sel('b1',1,'b1',3);", HANGUL, WAIT + "return txt('b1')==='가한글라' && caret()==='b1:3' || " + DUMP),
    # 실제 IME 는 조합 중 화살표를 누르면 조합 글을 먼저 확정하고 커서를 옮긴다 - 헤드리스에는 IME 가 없어 확정(insertText)을 직접 보낸 뒤 화살표
    ("(c) 조합 중 ←(화살표) - 조합 글이 한 번만 확정되고 커서는 그 글 앞으로 · 이어 친 글은 그 자리에",
     R + "sel('b1',4);", comp("ㅎ", "하", "한") + commit("한") + key("ArrowLeft", "ArrowLeft", 37) + comp("ㄱ") + commit("ㄱ"),
     WAIT + "return txt('b1')==='가나다라ㄱ한' && dom('b1')==='가나다라ㄱ한' && caret()==='b1:5' || " + DUMP),
    ("(c) 조합 중 Backspace(조합 글을 다 지움) - 아무것도 남지 않음",
     R + "sel('b1',4);", comp("ㅎ", "하", "ㅎ", ""), WAIT + "return txt('b1')==='가나다라' && dom('b1')==='가나다라' || " + DUMP),
    ("(d) 조합 확정 직후 Enter - 조합 글 뒤에서 문단이 나뉨",
     R + "sel('b1',2);", comp("ㅎ", "하", "한") + commit("한") + key("Enter", "Enter", 13, "\r"), WAIT + "return txt('b1')==='가나한' && DOC.blocks[1] && T_text(DOC.blocks[1])==='다라' || " + DUMP),
]


def main():
    page = (HERE / "nexa_text_page.html").resolve().as_uri()
    steps = [{"name": n, "pre": pre + " document.querySelector('#ed').focus(); return true;", "cdp": c, "js": js.replace("T_text(", "((b)=>b.runs.map(x=>x.t).join(''))(")} for n, pre, c, js in STEPS]
    scn = {"base": page.rsplit("/", 1)[0], "pages": [{"url": "/nexa_text_page.html", "wait": 300, "steps": steps}]}
    with tmpfiles.temp_dir("nx-ime-") as d:
        f = Path(d) / "nexa_text_ime_scn.json"
        f.write_text(json.dumps(scn, ensure_ascii=False), "utf-8")
        r = subprocess.run(["node", str(HERE / "smoke.js"), str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(r.stdout)
    if r.returncode:
        print(r.stderr[-1500:])
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
