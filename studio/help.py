# -*- coding: utf-8 -*-
"""실행기 하위 명령 목록 - python3 nexa.py help. AI 세션(엔진 문서를 읽지 못하는 웹 세션 포함)이 쓸 수 있는 명령을 한눈에."""
import sys

COMMANDS = [
    ("start | stop | restart | status | url", "편집기 서버 시작·중지·상태·주소"),
    ("draft_deck <덱> [--element <id>] [--slide <id>] [--range B2:D5]", "덱 사본(out/.studio/draft-<덱>.json)을 만들고 경로·줄 번호를 알려 준다 → 사본을 Edit 로 고친다(시트 문서면 --slide 탭 --range 범위)"),
    ("save_deck <덱> --from <사본> --request <요청 id> --note \"…\"", "사본을 덱으로 저장(변경 원장에 Claude 로, 백업·충돌 검사). 덱 파일을 직접 덮어쓰지 않는다"),
    ("layout_samples [--json]", "레이아웃 21종과 필드 예시(새 슬라이드를 만들 때 구조 참고)"),
    ("slide_types [낱말]", "내용 성격에 맞는 슬라이드 유형 고르기(레이아웃·필드 구조)"),
    ("build_deck <덱> --force", "content/<덱>.json → decks/<덱>.json 빌드"),
    ("check_layout <덱>", "레이아웃 검사(겹침·넘침·최소 글자·슬라이드 밖) - ERROR 0 목표"),
    ("scale_fonts <덱> --ratio 1.2 [--role body,title] [--dry-run]", "덱 전체 글자 크기를 비율로 키우고 상자 높이·세로 배치를 다시 잡는다(바닥을 넘치면 그 장만 비율을 낮춤)"),
    ("export_pptx <덱>", "PPTX 내보내기 → out/<덱>.pptx"),
    ("export_xlsx <시트 문서>", "시트 문서(kind sheet) xlsx 내보내기 → out/<id>.xlsx"),
    ("sheet_theme list|show <이름>|import <샘플.xlsx>… --name <이름>", "시트 테마(색·셀 스타일·표지/이력/개요/요약/목록 틀·로고) 목록·보기·샘플 엑셀에서 만들기 → assets/sheet-themes/<이름>/"),
    ("set_fonts <세트>", "글꼴 세트 고르기"),
    ("set_template [<이름>] [--json]", "템플릿(디자인) 목록 보기·고르기 - 바꾼 뒤 서버 재시작(사용자에게 안내) → build_deck --force"),
    ("deck list|create <id> [--title …] [--kind sheet]|rename <id> <새 id>|retitle <id> \"제목\"|delete <id>", "덱 관리 - 추가·이름(id)·제목·삭제(휴지통 decks/.trash/). 편집기 덱 탭의 ＋·오른쪽 클릭과 같다"),
    ("import_doc <파일> [--out <폴더>]", "첨부 Word(.docx)·Excel(.xlsx/.xlsm)·PDF 의 글·제목·목록·표·시트·차트 값·그림 → out/import/<이름>/content.md·.json, images/"),
    ("import_pptx <파일.pptx> [--out <폴더>]", "첨부 PPTX 의 글·표·차트·노트 → out/import/<이름>/slides.md·.json, 그림 → images/ (Read 로 못 여는 PPTX 를 꺼낼 때)"),
    ("watch_requests --stream", "수동 세션용 요청 감시(웹 세션 중에는 거절된다)"),
    ("help", "이 목록"),
]


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    print("python3 nexa.py <명령> …   (작업 공간 폴더에서, cwd 기준)")
    for cmd, desc in COMMANDS:
        print(f"  {cmd:62s} {desc}")
    print("요청 처리 규약: requests.json status working → draft_deck → Edit 사본 → save_deck --from --request → content 반영 → status done + reply")


if __name__ == "__main__":
    main()
