# -*- coding: utf-8 -*-
"""페이지 템플릿 - 새 페이지 문서의 쪽 설정 · 스타일 · 예시 본문. docs/dev/page-editor/design.md 7절.

    names()                 템플릿 이름 목록(기본 순서)
    info()                  [{name, label, desc, group, page, blocks(개수)}] - 고르는 화면용
    load(name)              템플릿 dict {name, label, desc, group, page, styles, blocks} - 없으면 None
    python studio/page_templates.py            목록 찍기

엔진 템플릿은 이 파일 안에 있다(로고·전용 글꼴 없음 - 색·글꼴은 토큰 이름만 쓴다). 작업 공간 전용 템플릿은
`<작업 공간>/page_templates/<이름>.json` 에 같은 꼴로 두면 함께 나온다(같은 이름이면 작업 공간 것이 이긴다).
본문은 자리 표시 글이다 - 만들 때 제목({title})과 날짜({date})만 채운다.
"""
import copy
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

GROUPS = {"general": "일반 문서", "study": "학습 자료"}


def p(text="", style=None, **kw):
    b = {"type": "p", "runs": [{"t": text}] if isinstance(text, str) and text else (text or [])}
    if style:
        b["style"] = style
    b.update(kw)
    return b


def li(text, kind="bullet", level=0, style=None, **kw):
    b = {"type": "p", "list": {"kind": kind, "level": level, **kw}, "runs": ([{"t": text}] if text else []) if isinstance(text, str) else (text or [])}
    if style:
        b["style"] = style
    return b


def table(cols, head, rows):
    cell = lambda t: {"blocks": [p(t)]}  # noqa: E731
    return {"type": "table", "cols": cols, "rows": [{"head": True, "cells": [cell(t) for t in head]}] + [{"cells": [cell(t) for t in r]} for r in rows]}


BREAK = {"type": "break", "kind": "page"}
B = lambda t: {"t": t, "b": True}  # noqa: E731
M = lambda t: {"t": t, "c": "muted"}  # noqa: E731

T = {}

T["blank"] = {"label": "빈 문서", "desc": "제목과 빈 문단만", "group": "general",
              "blocks": [p("{title}", "title"), p()]}

T["report"] = {"label": "보고서", "desc": "요약 · 배경 · 내용 · 결론 · 다음 할 일", "group": "general",
               "page": {"number": {"show": True, "pos": "footer-center"}},
               "blocks": [p("{title}", "title"), p([M("작성일 {date} · 작성자 ")], align="center"),
                          p("요약", "h1"), p("이 보고서가 말하려는 것을 세 문장 안으로 적습니다."),
                          p("배경", "h1"), p("왜 이 일을 하게 됐는지, 지금 상황이 어떤지 적습니다."),
                          p("내용", "h1"), p("첫째 항목", "h2"), p("사실과 근거를 적습니다."), p("둘째 항목", "h2"), p("사실과 근거를 적습니다."),
                          table([30, 25, 45], ["항목", "수치", "비고"], [["", "", ""], ["", "", ""]]),
                          p("결론", "h1"), p("판단과 권고를 적습니다."),
                          p("다음 할 일", "h1"), li("할 일 · 담당 · 기한", "check"), li("할 일 · 담당 · 기한", "check")]}

T["proposal"] = {"label": "기획서 · 제안서", "desc": "목적 · 문제 · 제안 · 효과 · 일정 · 예산", "group": "general",
                 "page": {"number": {"show": True, "pos": "footer-center"}},
                 "blocks": [p("{title}", "title"), p([M("{date}")], align="center"),
                            p("한 줄 요약", "h1"), p("무엇을, 누구를 위해, 왜 하는지 한 문장으로 적습니다.", "quote"),
                            p("문제", "h1"), p("지금 무엇이 불편하거나 모자란지 적습니다."),
                            p("제안", "h1"), li("핵심 기능 또는 활동", "number"), li("핵심 기능 또는 활동", "number"), li("핵심 기능 또는 활동", "number"),
                            p("기대 효과", "h1"), li("정량 효과(수치)"), li("정성 효과"),
                            p("일정", "h1"), table([25, 45, 30], ["단계", "내용", "기간"], [["1단계", "", ""], ["2단계", "", ""], ["3단계", "", ""]]),
                            p("예산", "h1"), table([40, 30, 30], ["항목", "금액", "비고"], [["", "", ""], ["합계", "", ""]]),
                            p("결정이 필요한 것", "h1"), li("결정할 것과 선택지", "check")]}

T["minutes"] = {"label": "회의록", "desc": "일시 · 참석 · 안건 · 결정 · 할 일", "group": "general",
                "blocks": [p("{title}", "title"),
                           table([20, 80], ["항목", "내용"], [["일시", "{date}"], ["장소", ""], ["참석", ""], ["작성", ""]]),
                           p("안건", "h1"), li("안건 1", "number"), li("안건 2", "number"),
                           p("논의", "h1"), p("안건 1", "h2"), li("나온 의견"), li("나온 의견"), p("안건 2", "h2"), li("나온 의견"),
                           p("결정", "h1"), li("결정한 것", "number"),
                           p("할 일", "h1"), table([50, 25, 25], ["할 일", "담당", "기한"], [["", "", ""], ["", "", ""]]),
                           p("다음 회의", "h1"), p("일시 · 장소 · 준비할 것")]}

T["letter"] = {"label": "공문 · 레터", "desc": "수신 · 제목 · 본문 · 붙임 · 발신", "group": "general",
               "page": {"margin": {"t": 30, "r": 25, "b": 25, "l": 25}},
               "blocks": [p([B("기관 · 회사 이름")], align="center", style="h2"), p([M("주소 · 전화 · 전자 우편")], align="center"), p(),
                          p([B("수신  "), {"t": ""}]), p([B("참조  "), {"t": ""}]), p([B("제목  "), {"t": "{title}"}]), p(),
                          li("관련 근거나 앞선 문서를 적습니다.", "number"), li("알리거나 요청하는 내용을 적습니다.", "number"), li("기한과 회신 방법을 적습니다.", "number"), p(),
                          p([B("붙임  "), {"t": "1. 문서 이름 1부.  끝."}]), p(), p(),
                          p([B("발신인 이름")], align="center", style="h2"), p([M("{date}")], align="center")]}

T["manual"] = {"label": "매뉴얼 · 안내서", "desc": "개요 · 준비 · 단계별 절차 · 문제 해결", "group": "general",
               "page": {"number": {"show": True, "pos": "footer-right"}},
               "blocks": [p("{title}", "title"), p([M("판 1.0 · {date}")], align="center"),
                          p("개요", "h1"), p("이 문서가 누구를 위한 것이고 무엇을 할 수 있게 하는지 적습니다."),
                          p("준비할 것", "h1"), li("필요한 것", "check"), li("필요한 것", "check"),
                          p("절차", "h1"), p("1. 첫 단계 이름", "h2"), li("할 일을 한 문장으로", "number"), li("할 일을 한 문장으로", "number"),
                          p("주의: 잘못하기 쉬운 점을 적습니다.", "quote"),
                          p("2. 둘째 단계 이름", "h2"), li("할 일을 한 문장으로", "number"), li("할 일을 한 문장으로", "number"),
                          p("문제 해결", "h1"), table([40, 60], ["증상", "해결"], [["", ""], ["", ""]]),
                          p("문의", "h1"), p("담당 · 연락처")]}

T["resume"] = {"label": "이력서", "desc": "인적 사항 · 경력 · 학력 · 기술 · 자기소개", "group": "general",
               "page": {"margin": {"t": 20, "r": 20, "b": 20, "l": 20}},
               "styles": {"h1": {"name": "제목 1", "based": "body", "font": "title", "size": 13, "bold": True, "color": "accent", "before": 12, "after": 4, "next": "body"}},
               "blocks": [p("이름", "title", align="left"), p([M("직무 · 전화 · 전자 우편 · 주소")]),
                          p("경력", "h1"), table([25, 30, 45], ["기간", "회사 · 직무", "한 일과 성과"], [["", "", ""], ["", "", ""]]),
                          p("학력", "h1"), table([25, 75], ["기간", "학교 · 전공"], [["", ""]]),
                          p("기술 · 자격", "h1"), li("기술 또는 자격 · 수준"), li("기술 또는 자격 · 수준"),
                          p("자기소개", "h1"), p("지원하는 일과 이어지는 경험을 세 문단 안으로 적습니다.")]}

T["paper"] = {"label": "논문 · 리포트", "desc": "초록 · 서론 · 본론 · 결론 · 참고 문헌", "group": "general",
              "page": {"margin": {"t": 30, "r": 25, "b": 30, "l": 25}, "number": {"show": True, "pos": "footer-center"}},
              "styles": {"body": {"name": "본문", "font": "body", "size": 10.5, "line": 1.8, "after": 4, "first": 4, "align": "justify"},
                         "h1": {"name": "제목 1", "based": "body", "font": "title", "size": 14, "bold": True, "before": 14, "after": 6, "first": 0, "align": "left", "next": "body"},
                         "title": {"name": "문서 제목", "based": "h1", "size": 20, "align": "center", "after": 10}},
              "blocks": [p("{title}", "title"), p([M("이름 · 소속 · {date}")], align="center", first=0),
                         p("초록", "h1"), p("연구의 목적 · 방법 · 결과 · 의의를 한 문단으로 적습니다.", "quote"),
                         p("1. 서론", "h1"), p([{"t": "문제의식과 연구 질문을 적습니다"}, {"t": ".", "fn": "각주 - 출처나 덧붙이는 말을 여기에 적습니다([각주] 단추)."}]),
                         p("2. 본론", "h1"), p("2.1 소제목", "h2"), p("근거와 분석을 적습니다."), p("2.2 소제목", "h2"), p("근거와 분석을 적습니다."),
                         p("3. 결론", "h1"), p("찾은 것과 한계, 다음 연구를 적습니다."),
                         p("참고 문헌", "h1"), li("지은이(연도). 제목. 펴낸 곳.", "number", first=0), li("지은이(연도). 제목. 펴낸 곳.", "number", first=0)]}

def layout(cols, cells, border="inner-v"):
    """배치용 표 - 칸을 단처럼 쓴다(너비가 다른 2단). cells = 칸마다 블록 목록. Word 로는 테두리 없는 표로 나간다."""
    return {"type": "table", "cols": cols, "border": border, "rows": [{"cells": [{"blocks": bs} for bs in cells]}]}


R = lambda t, top: {"t": t, "ruby": top}  # noqa: E731 - 윗주(글 위의 문법 표시)

T["study-guide"] = {"label": "해설지(지문 분석)", "desc": "왼쪽 지문(윗주로 문법 표시) · 오른쪽 해석·어휘 - 지문 하나에 한 쪽", "group": "study",
                    "page": {"margin": {"t": 21, "r": 17, "b": 15, "l": 17},
                             "header": {"blocks": [{"type": "p", "runs": [{"t": "{date}", "c": "muted"}, {"t": "  {title}", "b": True}]}]}},
                    "styles": {"body": {"name": "본문", "font": "body", "size": 8, "line": 1.6, "after": 3},
                               "h1": {"name": "제목 1", "based": "body", "font": "title", "size": 10, "bold": True, "color": "accent", "before": 6, "after": 3, "next": "body"},
                               "title": {"name": "문서 제목", "based": "h1", "size": 12, "color": "ink", "align": "center", "before": 0, "after": 4},
                               "passage": {"name": "지문", "based": "body", "size": 9, "line": 2.6, "align": "justify"},
                               "note": {"name": "설명", "based": "body", "size": 7, "color": "muted"},
                               "word": {"name": "어휘", "based": "body", "size": 7, "line": 1.4, "after": 1, "fill": "#e6e6e6"},
                               "box": {"name": "해설 상자", "based": "body", "size": 7, "line": 1.4, "color": "accent", "align": "center", "fill": "#e6e6e6", "after": 4}},
                    "blocks": [
                        p([{"t": "1강 01  ", "c": "accent", "b": True}, {"t": "지문의 주제를 한 줄로 적습니다"}], "title"),
                        p("글의 흐름을 화살표로 적습니다: 원인 → 과정 → 결과(∴ 글쓴이의 주장)", "box"),
                        layout([67, 33], [
                            [li([R("Professor Kim", "S"), {"t": " "}, R("observed", "V"), {"t": " "}, R("that", "접속사"), {"t": " the first sentence of the passage goes here."}], "number", style="passage"),
                             li([{"t": "The second sentence goes here, and "}, {"t": "the key phrase", "hl": "#fff59d", "fn": "핵심 어구의 풀이를 각주로 적습니다."}, {"t": " is highlighted."}], "number", style="passage"),
                             li([{"t": "The third sentence of the passage goes here."}], "number", style="passage"),
                             p("주제문", "h1"), p([{"t": "The key phrase", "c": "accent", "u": True}, {"t": " 를 옮겨 적습니다."}]),
                             p("핵심 요약", "h1"), p("글 전체를 두세 문장으로 요약합니다.")],
                            [p([{"t": "observe", "b": True}, {"t": " 관찰하다 · 준수하다"}], "word"), p([{"t": "regardless of", "b": True}, {"t": " ~과 상관없이"}], "word"), p(),
                             li("첫째 문장의 해석을 적습니다.", "number"), li("둘째 문장의 해석을 적습니다.", "number"), li("셋째 문장의 해석을 적습니다.", "number"),
                             p("Words & Phrases", "h1"), li("observe 관찰하다", "check", style="word"), li("opportunity 기회", "check", style="word"), li("disaster 재해", "check", style="word")],
                        ]),
                        table([25, 25, 25, 25], ["어원 · 파생어", "", "", ""], [["", "", "", ""]])]}

T["worksheet"] = {"label": "문제지", "desc": "이름 칸 · 문항 · 보기 · 서술형 · 정답", "group": "study",
                  "page": {"margin": {"t": 20, "r": 18, "b": 18, "l": 18}, "number": {"show": True, "pos": "footer-center"}},
                  "blocks": [p("{title}", "title"), table([20, 30, 20, 30], ["학년 · 반", "", "이름", ""], []),
                             p("[1~2] 다음 글을 읽고 물음에 답하시오.", "h3"), p("지문을 여기에 적습니다.", "quote"),
                             li("글의 주제로 가장 알맞은 것은?", "number"),
                             li("① 보기", level=1), li("② 보기", level=1), li("③ 보기", level=1), li("④ 보기", level=1), li("⑤ 보기", level=1),
                             li("밑줄 친 부분의 뜻을 우리말로 쓰시오. (서술형)", "number"), p(), p(),
                             BREAK, p("정답과 해설", "h1"), table([12, 18, 70], ["번호", "정답", "해설"], [["1", "", ""], ["2", "", ""]])]}

T["vocab"] = {"label": "어휘 정리", "desc": "낱말 표 · 예문 · 확인 문제", "group": "study",
              "page": {"margin": {"t": 20, "r": 18, "b": 18, "l": 18}},
              "blocks": [p("{title}", "title"), p([M("단원 · 날짜 {date}")], align="center"),
                         p("오늘의 낱말", "h1"), table([8, 26, 26, 40], ["", "낱말", "뜻", "예문"], [["☐", "", "", ""], ["☐", "", "", ""], ["☐", "", "", ""], ["☐", "", "", ""], ["☐", "", "", ""]]),
                         p("뿌리가 같은 낱말", "h1"), li("낱말 - 뜻"), li("낱말 - 뜻"),
                         p("확인 문제", "h1"), li("빈칸에 알맞은 낱말을 쓰시오: ______", "number"), li("빈칸에 알맞은 낱말을 쓰시오: ______", "number")]}

ORDER = ["blank", "report", "proposal", "minutes", "letter", "manual", "resume", "paper", "study-guide", "worksheet", "vocab"]


def _workspace_dir():
    # common 은 작업 공간을 못 찾으면 프로세스를 끝낸다 - 이미 불려 있을 때(서버·CLI)만 본다. 작업 공간 없이 부르면(시험·허브) 엔진 템플릿만
    c = sys.modules.get("common")
    if not c or getattr(c, "HUB", True) or not getattr(c, "WORKSPACE", None):
        return None
    return c.WORKSPACE / "page_templates"


def _workspace():
    d = _workspace_dir()
    out = {}
    if d and d.is_dir():
        for f in sorted(d.glob("*.json")):
            try:
                t = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(t, dict) and isinstance(t.get("blocks"), list):
                    out[f.stem] = {**t, "workspace": True}
            except (OSError, ValueError):
                continue
    return out


def names():
    ws = _workspace()
    return [n for n in ORDER if n not in ws] + list(ws)


def _fill(obj, vals):
    if isinstance(obj, str):
        for k, v in vals.items():
            obj = obj.replace("{" + k + "}", v)
        return obj
    if isinstance(obj, list):
        return [_fill(x, vals) for x in obj]
    if isinstance(obj, dict):
        return {k: _fill(v, vals) for k, v in obj.items()}
    return obj


def load(name, title=None, date=None):
    """템플릿 dict - title·date 를 주면 본문의 {title}·{date} 자리를 채운다. 없는 이름이면 None."""
    src = _workspace().get(name) or T.get(name)
    if not src:
        return None
    t = {"name": name, **copy.deepcopy(src)}
    if title is not None:
        vals = {"title": title, "date": date or dt.date.today().isoformat()}
        t["blocks"] = _fill(t["blocks"], vals)
        if t.get("page"):
            t["page"] = _fill(t["page"], vals)  # 머리말·꼬리말 글의 자리도
    return t


def info():
    out = []
    for n in names():
        t = load(n)
        out.append({"name": n, "label": t.get("label") or n, "desc": t.get("desc") or "", "group": t.get("group") or "general",
                    "groupLabel": GROUPS.get(t.get("group") or "general", t.get("group")), "blocks": len(t.get("blocks") or []),
                    "workspace": bool(t.get("workspace")), "page": t.get("page") or {}})
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for x in info():
        print(f"{x['name']:12} {x['groupLabel']:6} {x['label']} - {x['desc']} ({x['blocks']}블록)")
