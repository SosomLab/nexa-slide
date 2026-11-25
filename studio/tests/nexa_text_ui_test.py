# -*- coding: utf-8 -*-
"""nexa-text.js 입력 처리 시험(헤드리스 Chrome) - 서버 없이 tests/nexa_text_page.html 을 파일로 열어 입력 이벤트를 흉내 낸다.
    python studio/tests/nexa_text_ui_test.py
beforeinput 은 만든 이벤트(합성)라 브라우저가 DOM 을 고치지 않는다 - 편집기가 모델을 고치고 다시 그리는지를 본다.
한글 조합은 compositionstart → 글 노드를 직접 고침 → compositionend 로 흉내 낸다(실제 IME 는 PG-032 의 CDP 시험)."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import tmpfiles  # noqa: E402

R = "reset(); "
STEPS = [
    ("치기 - 가운데에 한 글자", R + "sel('b1',2); bi('insertText','X'); return txt('b1')==='가나X다라' && dom('b1')==='가나X다라' && caret()==='b1:3' || JSON.stringify([txt('b1'),dom('b1'),caret()])"),
    ("치기 - 굵은 글 안에서는 굵게", R + "sel('b2',8); bi('insertText','X'); const r=blk('b2').runs; return r.length===3 && r[1].t==='biXg' && r[1].b===true || JSON.stringify(r)"),
    ("치기 - 고른 글을 바꾼다", R + "sel('b2',6,'b2',9); bi('insertText','small'); return txt('b2')==='Hello small world' && blk('b2').runs[1].b===true && caret()==='b2:11' || JSON.stringify([blk('b2').runs,caret()])"),
    ("치기 - 빈 문단", R + "sel('b3',0); bi('insertText','가'); return txt('b3')==='가' && dom('b3')==='가' && caret()==='b3:1' || JSON.stringify([txt('b3'),dom('b3'),caret()])"),
    ("Enter - 가운데에서 나눈다(속성 물려받음)", R + "sel('b2',6); bi('insertParagraph'); return ids()==='b1,b2,n1,b3,b4,b5' && txt('b2')==='Hello ' && txt('n1')==='big world' && blk('n1').style==='h1' && caret()==='n1:0' || JSON.stringify([ids(),caret(),blk('n1')])"),
    ("Enter - 제목 끝에서는 본문 스타일", R + "sel('b2',15); bi('insertParagraph'); return txt('n1')==='' && !('style' in blk('n1')) && caret()==='n1:0' || JSON.stringify(blk('n1'))"),
    ("Backspace - 문단 맨 앞에서 앞 문단과 잇는다", R + "sel('b2',0); bi('deleteContentBackward'); return ids()==='b1,b3,b4,b5' && txt('b1')==='가나다라Hello big world' && caret()==='b1:4' || JSON.stringify([ids(),txt('b1'),caret()])"),
    ("Backspace - 한 글자", R + "sel('b1',2); bi('deleteContentBackward'); return txt('b1')==='가다라' && caret()==='b1:1' || JSON.stringify([txt('b1'),caret()])"),
    ("Delete - 문단 끝에서 뒤 문단을 끌어온다", R + "sel('b1',4); bi('deleteContentForward'); return ids()==='b1,b3,b4,b5' && txt('b1')==='가나다라Hello big world' && caret()==='b1:4' || JSON.stringify([ids(),txt('b1'),caret()])"),
    ("Backspace - 앞이 그림이면 그림을 지운다", R + "sel('b5',0); bi('deleteContentBackward'); return ids()==='b1,b2,b3,b5' && caret()==='b5:0' || JSON.stringify([ids(),caret()])"),
    ("지우기 - 여러 문단에 걸친 선택(가운데 그림 포함)", R + "sel('b1',2,'b5',2); bi('deleteContentBackward'); return ids()==='b1' && txt('b1')==='가나문단' && caret()==='b1:2' || JSON.stringify([ids(),txt('b1'),caret()])"),
    ("서식 - 선택에 굵게, 다시 누르면 끔", R + "sel('b1',1,'b1',3); ED.toggle('b'); const a=JSON.stringify(blk('b1').runs); const w=document.querySelector('[data-id=b1] span:nth-child(2)').style.fontWeight; sel('b1',1,'b1',3); ED.toggle('b'); return a==='[{\"t\":\"가\"},{\"t\":\"나다\",\"b\":true},{\"t\":\"라\"}]' && w==='700' && JSON.stringify(blk('b1').runs)==='[{\"t\":\"가나다라\"}]' || a+' '+w"),
    ("서식 - 여러 문단에 걸쳐 한 번에", R + "sel('b1',2,'b2',5); ED.toggle('i'); return blk('b1').runs[1].i===true && blk('b2').runs[0].i===true && blk('b2').runs[0].t==='Hello' || JSON.stringify([blk('b1').runs,blk('b2').runs])"),
    ("서식 - 선택이 비면 켜 두었다가 다음 글에", R + "sel('b1',4); ED.toggle('b'); const on=ED.state().marks.b; bi('insertText','굵'); bi('insertText','게'); return on===true && JSON.stringify(blk('b1').runs)==='[{\"t\":\"가나다라\"},{\"t\":\"굵게\",\"b\":true}]' || JSON.stringify([on,blk('b1').runs])"),
    ("서식 - 켜 둔 서식은 다른 곳으로 가면 버린다", R + "sel('b1',4); ED.toggle('b'); sel('b1',1); await new Promise(r=>setTimeout(r,60)); bi('insertText','X'); return JSON.stringify(blk('b1').runs)==='[{\"t\":\"가X나다라\"}]' || JSON.stringify(blk('b1').runs)"),
    ("서식 - 값 있는 서식(색)과 문단 속성", R + "sel('b1',0,'b1',2); ED.setMark('c','accent'); sel('b1',1,'b2',1); ED.blockAttrs({align:'center'}); return blk('b1').runs[0].c==='accent' && blk('b1').align==='center' && blk('b2').align==='center' && !blk('b3').align || JSON.stringify(DOC.blocks)"),
    ("단축키 - Ctrl+B", R + "sel('b1',0,'b1',1); document.querySelector('#ed').dispatchEvent(new KeyboardEvent('keydown',{key:'b',ctrlKey:true,bubbles:true,cancelable:true})); return blk('b1').runs[0].b===true || JSON.stringify(blk('b1').runs)"),
    ("한글 조합 - 조합이 끝나면 모델로 읽어 들인다(서식 잇기)", R + "sel('b2',9); const h=document.querySelector('#ed'); h.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true})); const tn=document.querySelector('[data-id=b2] span:nth-child(2)').firstChild; tn.data='big한'; getSelection().collapse(tn,4); bi('insertCompositionText','한'); h.dispatchEvent(new CompositionEvent('compositionend',{data:'한',bubbles:true})); const r=blk('b2').runs; return r[1].t==='big한' && r[1].b===true && caret()==='b2:10' && LOG[LOG.length-1]==='ime' || JSON.stringify([r,caret(),LOG])"),
    ("한글 조합 - 빈 문단에서(브라우저가 글 노드를 새로 만든 경우)", R + "sel('b3',0); const h=document.querySelector('#ed'); h.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true})); const el=document.querySelector('[data-id=b3]'); el.replaceChildren(document.createTextNode('한글')); getSelection().collapse(el.firstChild,2); h.dispatchEvent(new CompositionEvent('compositionend',{data:'한글',bubbles:true})); return txt('b3')==='한글' && dom('b3')==='한글' && el.isConnected===false && caret()==='b3:2' || JSON.stringify([txt('b3'),dom('b3'),caret()])"),
    ("한글 조합 - 조합 중 beforeinput 은 막지 않는다", R + "sel('b1',0); const h=document.querySelector('#ed'); h.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true})); const ok=bi('insertCompositionText','ㅎ'); h.dispatchEvent(new CompositionEvent('compositionend',{bubbles:true})); const ok2=bi('insertText','x'); return ok===true && ok2===false && txt('b1')==='x가나다라' || JSON.stringify([ok,ok2,txt('b1')])"),
    ("붙여넣기 - 여러 줄은 문단으로", R + "sel('b1',2); const dt=new DataTransfer(); dt.setData('text/plain','A\\r\\nB\\nC'); bi('insertFromPaste',null,dt); return ids()==='b1,n1,n2,b2,b3,b4,b5' && txt('b1')==='가나A' && txt('n1')==='B' && txt('n2')==='C다라' && caret()==='n2:1' || JSON.stringify([ids(),DOC.blocks.slice(0,3),caret()])"),
    ("줄바꿈(Shift+Enter) - 문단 안에 남는다", R + "sel('b1',4); bi('insertLineBreak'); return txt('b1')==='가나다라\\n' && ids()==='b1,b2,b3,b4,b5' && !!document.querySelector('[data-id=b1] br') && caret()==='b1:5' || JSON.stringify([txt('b1'),caret()])"),
    ("다시 그리기 - 바뀌지 않은 문단의 요소는 그대로 둔다", R + "const e2=document.querySelector('[data-id=b2]'), e1=document.querySelector('[data-id=b1]'); sel('b1',1); bi('insertText','X'); return document.querySelector('[data-id=b2]')===e2 && document.querySelector('[data-id=b1]')!==e1 || 'reuse'"),
    ("글이 아닌 블록은 편집할 수 없다", R + "const o=document.querySelector('[data-id=b4]'); return o.contentEditable==='false' && o.textContent==='[image]' || o.outerHTML"),
    ("저장 이유 - 실행 취소 묶음용", R + "sel('b1',0); bi('insertText','a'); bi('insertParagraph'); sel('n1',0,'n1',1); bi('deleteContentBackward'); return LOG.join(',')==='type,enter,delete' || LOG.join(',')"),
]


def main():
    page = (HERE / "nexa_text_page.html").resolve().as_uri()
    scn = {"base": page.rsplit("/", 1)[0], "pages": [{"url": "/nexa_text_page.html", "wait": 300, "steps": [{"name": n, "js": js} for n, js in STEPS]}]}
    with tmpfiles.temp_dir("nx-text-") as d:
        f = Path(d) / "nexa_text_scn.json"
        f.write_text(json.dumps(scn, ensure_ascii=False), "utf-8")
        r = subprocess.run(["node", str(HERE / "smoke.js"), str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(r.stdout)
    if r.returncode:
        print(r.stderr[-1500:])
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
