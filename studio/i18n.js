/* nexa-slide 표시 언어(i18n) - 사전 기반 런타임 번역. 한국어 원문이 키, 사전에 없으면 한국어 그대로.
   화면 파일을 t() 로 감싸지 않고 DOM 의 글(텍스트 노드·placeholder·title·aria-label·option)을 사전으로 바꾼다.
   MutationObserver 가 뒤에 생기는 글도 바꾸므로 동적 화면(innerHTML)도 즉시 반영되고, 언어를 바꾸면 원문으로 되돌린 뒤 다시 적용한다.
     I18N.lang()              "system" | "ko" | "en"   (저장: localStorage nexa-lang, 주소 ?lang= 도 받음)
     I18N.effective()         실제 적용 언어 "ko" | "en" - system 이면 브라우저 언어(navigator.language)
     I18N.set(lang)           바꾸고 즉시 반영 · I18N.t(str) 글 하나 번역(토스트·확인 창용) · I18N.options() 선택 목록
   변수가 든 문구는 PATTERNS(정규식)과 " · " 구분 조각 번역으로 처리한다. 긴 안내문은 사전에 있는 것만 바뀐다. */
(function () {
  const KEY = "nexa-lang";
  const EN = {
    // ---- 공통 · 메뉴
    "홈": "Home", "새 슬라이드 만들기": "New slides", "폴더·저장소 열기": "Open folder / repo", "튜토리얼": "Tutorial", "데모": "Demo", "템플릿": "Templates",
    "샘플 둘러보기": "Browse samples", "템플릿 검토": "Template review", "슬라이드 유형 검토": "Slide type review", "최근 작업": "Recent work", "최근 작업 찾기": "Find recent work",
    "기준 폴더 설정": "Settings", "계정": "Account", "계정 · 사용자 관리": "Account · Users", "로그아웃": "Log out", "로그인": "Log in", "기본 메뉴": "Main menu",
    "기본 메뉴 열기": "Open main menu", "메뉴 닫기": "Close menu", "nexa-slide 홈": "nexa-slide home", "이름·경로로 찾기": "Search by name or path",
    "찾는 작업이 없습니다": "No matching work", "아직 연 작업이 없습니다": "No recent work yet", "표시 언어": "Display language", "시스템": "System", "시스템 기본": "System default",
    "기본 메뉴 - 홈 · 새로 만들기 · 튜토리얼 · 데모 · 템플릿 · 샘플 · 최근 작업": "Main menu - home · new · tutorial · demo · templates · samples · recent work", "(폴더 없음)": "(folder missing)",
    "닫기": "Close", "취소": "Cancel", "저장": "Save", "삭제": "Delete", "추가": "Add", "열기": "Open", "시작": "Start", "확인": "OK", "복사": "Copy", "복사했습니다": "Copied",
    "바꾸기": "Change", "받기": "Download", "등록": "Register", "찾아보기": "Browse", "기본으로": "Reset to default", "없음": "None", "기본": "Default", "자동": "Auto",
    "오류": "Error", "경고": "Warning", "정상": "OK", "실패": "Failed", "처리 중": "Working", "처리 중...": "Working...", "대기": "Waiting", "완료": "Done", "초안": "Draft",
    "불러오는 중": "Loading", "불러오는 중…": "Loading…", "연결 중…": "Connecting…", "올리는 중…": "Uploading…", "저장 중…": "Saving…", "저장됨": "Saved", "저장 대기": "Pending save",
    "저장 실패": "Save failed", "저장 실패:": "Save failed:", "응답 없음": "No response", "설정을 저장했습니다": "Settings saved", "저장하지 못했습니다": "Could not save",
    "방금": "just now", "오늘": "today", "마지막": "last", "마지막 확인": "last seen", "이름": "Name", "경로": "Path", "종류": "Kind", "값": "Value", "모델": "Model", "에이전트": "Agent", "사용자 관리": "User management",
    // ---- 로그인 · 계정
    "nexa-slide 로그인": "nexa-slide login", "nexa-slide 계정": "nexa-slide account", "최초 관리자 설정": "Initial admin setup", "아이디": "User ID", "비밀번호": "Password",
    "비밀번호 (8자 이상)": "Password (8+ characters)", "비밀번호 다시": "Confirm password", "관리자 만들기": "Create admin", "두 비밀번호가 다릅니다": "Passwords do not match",
    "서버에 연결할 수 없습니다": "Cannot reach the server", "시작 페이지와 작업 공간은 로그인한 사용자만 쓸 수 있습니다.": "Only signed-in users can use the start page and workspaces.",
    "비밀번호를 잊었으면 이 PC 에서": "Forgot your password? On this PC run", "— 원격에서 초기화할 길은 없습니다.": "— there is no remote reset.",
    "비밀번호 변경": "Change password", "현재 비밀번호": "Current password", "새 비밀번호 (8자 이상)": "New password (8+ characters)", "새 비밀번호 다시": "Confirm new password",
    "바꾸면 다른 기기의 로그인은 모두 끊기고 이 기기만 남습니다.": "Changing it signs out every other device; only this one stays signed in.",
    "관리자가 정한 임시 비밀번호로 들어왔습니다 — 지금 새 비밀번호로 바꿔 주세요.": "You signed in with a temporary password set by an admin — please set a new one now.",
    "바꿨습니다": "Changed", "바꾸지 못했습니다": "Could not change", "바꾸지 못했습니다:": "Could not change:", "반영했습니다": "Applied", "관리자": "admin", "나": "me", "임시 비밀번호": "temporary password",
    "역할": "Role", "만든 날": "Created", "관리자 해제": "Remove admin", "관리자로": "Make admin", "비밀번호 초기화": "Reset password", "사용자 추가": "Add user", "일반 사용자로 변경": "change to regular user",
    "관리자로 지정": "make admin", "넣지 못했습니다": "Could not add",
    // ---- 시작 페이지
    "nexa-slide 시작": "nexa-slide start", "무엇을 만들까요?": "What will you make?", "제목": "Title", "시작용 내용": "Starter content", "목적": "Purpose", "대상(청중)": "Audience",
    "작성 방향": "Direction", "참고 자료": "Materials", "저장 위치": "Location", "저장 위치 고르기": "Choose location", "기본 위치": "Default location", "폴더·저장소 지정": "Choose folder / repo",
    "작업 공간 폴더": "Workspace folder", "하위 폴더 (비우면 그 폴더가 저장소 루트)": "Subfolder (empty = that folder is the repo root)", "포트": "Port",
    "Claude 세션에 초안 작성 요청 남기기": "Leave a draft request for the Claude session", "만들고 Studio 열기": "Create and open Studio", "또는 명령으로 만들기": "Or create with a command",
    "① 작업 공간 만들기 + 덱 빌드": "① Create workspace + build deck", "② 서버 시작 →": "② Start server →", "를 브라우저로 엽니다": "then open it in a browser",
    "만들 위치: 폴더를 고르세요": "Location: choose a folder", "저장할 폴더를 고르세요": "Choose a folder to save in", "만들지 못했습니다": "Could not create", "그 작업 공간 열기": "Open that workspace",
    "작업 공간을 만들고 서버를 띄우는 중...": "Creating the workspace and starting its server...", "작업 공간을 여는 중...": "Opening the workspace...", "작업 공간 서버를 띄우는 중...": "Starting the workspace server...",
    "폴더 경로": "Folder path", "폴더 경로를 적거나 고르세요": "Type or choose a folder path", "열 폴더 고르기": "Choose a folder to open", "열지 못했습니다": "Could not open",
    "이미 만든 작업 공간(nexa-slide.json 이 있는 폴더)을 엽니다. 작업 공간이 없는 폴더면 그 자리에 새로 만들 수 있습니다.": "Opens an existing workspace (a folder with nexa-slide.json). If the folder has none, you can create one there.",
    "덱": "decks", "서버 시작": "Start server", "서버 중지": "Stop server", "서버만 띄우기(페이지는 그대로)": "Start only the server (stay on this page)", "이 작업 공간 서버 끄기": "Stop this workspace server",
    "목록에서 빼기(폴더는 그대로)": "Remove from list (folder is kept)", "폴더 없음": "Folder missing", "작업 공간 아님": "Not a workspace", "중계": "relay",
    "세션 없음": "No session", "웹 세션": "Web session", "수동 세션": "Manual session", "터미널이 맡음": "handled by a terminal", "끊기": "Disconnect", "끊지 못했습니다": "Could not disconnect", "끊을 수동 세션이 없습니다": "No manual session to disconnect", "터미널 세션의 감시를 끊었습니다 - 이제 [세션 시작]으로 웹 세션을 띄울 수 있습니다": "Disconnected the terminal session's watcher - you can now start a web session with [Start session]", "터미널 세션으로 맡기기": "Hand off to a terminal session", "ⓘ 설정 안내": "ⓘ Setup guide", "설정 안내 — 저장소를 받은 뒤 할 일": "Setup guide — after cloning a repo", "설치 문서": "Install docs",
    "저장소를 받은 뒤 이 PC 에서 할 일 - 실제 경로가 채워진 명령과 복사": "What to do on this PC after cloning - commands with real paths, copyable", "이 작업 공간을 다른 PC 에서 받았을 때 할 일(명령·복사)": "What to do after cloning this workspace on another PC (commands · copy)",
    "명령은 이 PC 의 실제 경로로 채워져 있습니다. 어느 OS 든 ": "Commands are filled with this PC's real paths. On any OS run them with ", "(없으면 ": "(or ", ")로 실행합니다.": ").", "1. 엔진(제작 도구) 저장소 — ": "1. Engine (tool) repo — ", "처음 받을 때 한 번. 이 시작 페이지(허브)를 내주는 서버가 엔진입니다.": "Once, when first cloned. The server serving this start page (hub) is the engine.",
    "엔진 업데이트(받은 뒤 허브·작업 공간 서버 재시작):": "Update the engine (then restart the hub and workspace servers):", "2. 작업 공간(슬라이드) 저장소 — PC 마다 한 번": "2. Workspace (slides) repo — once per PC",
    "③ 이 작업 공간 서버 띄우기(시작 페이지의 [서버 시작]과 같음) · 상태 · 끄기:": "③ Start this workspace server (same as [Start server] on the start page) · status · stop:", "열려 있는 Claude Code 세션(터미널·VS Code)으로 맡기기": "Hand off to an open Claude Code session (terminal · VS Code)", "지금은": "Currently", "웹 엔진 세션": "web engine session", "터미널의 Claude Code 세션이 큐를 맡게 하는 방법(숨김 메뉴)": "How to let a terminal Claude Code session take the queue (hidden menu)", "명령을 복사했습니다": "Command copied", "명령": "Command", "수동 세션이 끝나면(그 터미널에서 Monitor 종료) 웹 세션을 시작할 수 있다": "Once the manual session ends (stop the Monitor in that terminal) a web session can be started", "세션 시작": "Start session", "세션 중지": "Stop session", "중지 중...": "Stopping...",
    "세션을 중지했습니다": "Session stopped", "중지하지 못했습니다": "Could not stop", "중지하지 못했습니다:": "Could not stop:", "시작 중...": "Starting...", "시작하지 못했습니다": "Could not start",
    "사용자 중지": "stopped by user", "유휴 중지": "stopped (idle)", "서버 종료": "server shutdown",
    "웹 세션 시작 —": "Start web session —", "웹 세션 시작": "Start web session", "웹 세션 시작…": "Start web session…", "웹 세션 진행": "Web session progress",
    "서버가 이 작업 공간에서 AI 를 턴마다 실행해 편집기 요청을 처리합니다. 쓰기 범위는 그 작업 공간 폴더뿐이며": "The server runs the AI one turn at a time in this workspace to handle editor requests. It can only write inside that workspace folder, and only",
    "서버가 이 작업 공간에서 AI 를 턴마다 실행해 편집기 요청을 처리합니다. 쓰기 범위는 이 작업 공간 폴더뿐이며": "The server runs the AI one turn at a time in this workspace to handle editor requests. It can only write inside this workspace folder, and only",
    "명령만 허용됩니다.": "commands are allowed.", "에이전트·로그인 상태를 확인하는 중…": "Checking agents and login…", "에이전트 상태를 읽지 못했습니다": "Could not read agent status",
    "모델 ID 직접 입력": "Type a model ID", "직접 입력…": "Custom…", "이 작업 공간 기본으로 저장": "Save as this workspace's default", "이 PC 만": "this PC only", "공유(nexa-slide.json)": "shared (nexa-slide.json)",
    "이 PC 만(nexa-slide.local.json)": "this PC only (nexa-slide.local.json)", "공유": "shared", "모델을 고르거나 입력하세요": "Choose or type a model",
    "서버를 확인하고 세션을 시작하는 중...": "Checking the server and starting the session...", "엔진 worktree 를 확인하고 세션을 시작하는 중...": "Checking the engine worktree and starting the session...",
    "허브 서버가 옛 판입니다 - 운영자가": "The hub server is an old build — the operator must run", "- 로그인 안 됨": "- not signed in", "- 미설치": "- not installed", "(미확인)": "(unverified)", "미설치": "not installed", "설치됨": "installed",
    "기본(claude)": "default (claude)", "기본(opus)": "default (opus)", "AI 세션 전역 기본": "AI session global defaults", "claude 모델 목록(쉼표)": "claude model list (comma-separated)", "codex 모델 목록(쉼표)": "codex model list (comma-separated)",
    "유휴 (분)": "Idle (min)", "턴 (분)": "Turn (min)", "동시 세션 (개)": "Concurrent sessions", "턴당 도구 반복": "Tool calls per turn", "예산 ($)": "Budget ($)", "웹 검색 허용(WebSearch·WebFetch) - 세션 시작 창에서 세션마다 켠다": "Allow web search (WebSearch · WebFetch) - enabled per session in the start dialog",
    "켜면 그 세션이 외부 웹을 검색·열람합니다. 슬라이드·요청 내용이 검색어·요청 URL 로 외부에 전달될 수 있습니다. 턴 로그에 요청한 URL 이 남습니다.": "When on, that session searches and reads the external web. Slide and request content may be sent outside as search terms or request URLs. Requested URLs are kept in the turn log.",
    "이 세션에 웹 검색 허용(WebSearch·WebFetch)": "Allow web search in this session (WebSearch · WebFetch)", "- 관리자만": "- admin only", "웹 허용": "web allowed", "서버 작업 보기": "Open server work", "데스크톱 알림 켜기": "Enable desktop notifications", "확인 명령": "Command to check", "이 세션은 아직 첫 턴 전이라 claude --resume 로 열리지 않습니다 - 요청을 하나 처리한 뒤에 다시 시도": "This session has not run its first turn yet, so claude --resume cannot open it - try again after it handles a request", "아직 첫 턴 전 - 대화 파일이 없어 claude --resume 로는 안 열린다(요청을 처리한 뒤부터)": "Before the first turn - no conversation file yet, so claude --resume cannot open it (after it handles a request)", "확인 명령(claude --resume) 복사": "Copy command (claude --resume)", "세션 ID 를": "Session ID", "확인 명령을": "Command", "git 기록 허용(add·commit·branch·switch·merge·stash·tag)": "Allow git commits (add · commit · branch · switch · merge · stash · tag)", "push 허용(git push·pull·fetch - git 기록을 함께 켬)": "Allow push (git push · pull · fetch - also enables git commits)",
    "저장소 루트 접근(작업 공간을 품은 저장소의 문서 읽기·쓰기)": "Repository root access (read/write docs in the repo containing the workspace)", "이 세션에 열린 권한": "Permissions granted to this session", "이 세션은 웹 검색(WebSearch·WebFetch)을 쓸 수 있다": "This session can use web search (WebSearch · WebFetch)",
    "이 세션이 외부 웹을 검색·열람합니다 - 슬라이드·요청 내용이 검색어·URL 로 외부에 전달될 수 있습니다(claude 만, 실행 중 세션은 다시 시작해야 바뀜).": "This session searches and reads the external web - slide and request content may be sent outside as search terms or URLs (claude only; a running session must be restarted to change this).",
    "이 세션이 외부 웹을 검색·열람합니다 - 슬라이드·요청 내용이 검색어·URL 로 외부에 전달될 수 있습니다(claude 만).": "This session searches and reads the external web - slide and request content may be sent outside as search terms or URLs (claude only).", "에이전트 상태 확인 중…": "Checking agents…",
    "제작 기준 폴더": "Projects root folder", "새로 만들 때 기본 위치입니다. 비우면 운영체제의 문서 폴더 아래": "Default location for new workspaces. Leave empty to use the OS Documents folder's",
    "를 씁니다.": "subfolder.", "기준 폴더 고르기": "Choose root folder", "작업 공간을 이 주소로 열기 -": "Open workspaces through this address -",
    "서버 작업": "Server work", "nexa-slide 엔진 개발": "nexa-slide engine development", "요청 추가": "Add request", "처리할 요청 없음": "No pending requests", "관리자에게 시작 요청": "Ask an admin to start", "관리자에게 시작 요청됨": "Admin asked to start", "관리자에게 세션 시작을 요청했습니다": "Asked an admin to start the session",
    "- 그림은 Ctrl+V 로 붙여 넣기, 파일은 끌어다 놓기": "- paste images with Ctrl+V, drop files", "- Enter = 큐에 넣기, Shift+Enter = 줄바꿈 · 그림은 Ctrl+V 로 붙여 넣기, 파일은 끌어다 놓기": "- Enter = add to queue, Shift+Enter = newline · paste images with Ctrl+V, drop files", "첨부를 올리는 중입니다": "Attachments are still uploading", "운영 트리(main)": "production tree (main)", "요청 제목": "Request title", "내용(무엇이 왜 필요한지 · 재현 방법)": "Details (what, why, how to reproduce)",
    "큐에 넣기": "Add to queue", "승인 대기": "Awaiting approval", "완료(적용 대기)": "Done (awaiting apply)", "거절": "Rejected", "적용됨": "Applied", "승인": "Approve", "목록에서 지우기": "Remove from list",
    "엔진 변경 요청이 없습니다. 작업 공간 세션이 엔진 한계를 만나면 여기로 넘기고, 직접 적을 수도 있습니다.": "No engine change requests. Workspace sessions hand off engine limits here, and you can add your own.",
    "엔진 상태를 읽지 못했습니다": "Could not read engine status", "엔진 세션": "Engine session", "엔진 개발 세션 진행": "Engine session progress", "진행": "Progress", "진행 보기": "Show progress",
    "엔진 요청 큐를 처리하는 개발 세션을 띄웁니다(엔진 worktree, 관리자)": "Start the development session that works the engine request queue (engine worktree, admin only)",
    "엔진 세션을 중지했습니다": "Engine session stopped", "main 에 병합·재시작한 뒤": "after merging into main and restarting", "세션": "session",
    "데모 열기": "Open demo", "▶ 데모 열기": "▶ Open demo", "데모를 준비하는 중... (처음 한 번 복사)": "Preparing the demo... (copied once)", "데모를 열지 못했습니다": "Could not open the demo",
    "데모 - 기능 훑어보기": "Demo - a quick tour", "데모는 내 작업과 섞이지 않습니다": "The demo stays separate from your work", "데모에서 해 볼 것": "Things to try in the demo",
    "미리 보기": "Preview", "이 템플릿으로 만들기": "Create with this template", "이 내용으로 시작": "Start with this content", "이 조합으로 만들기": "Create with this combination",
    "미리 보기를 만드는 중... (조합마다 처음 한 번은 빌드합니다)": "Building the preview... (built once per combination)", "미리 보기를 만들지 못했습니다": "Could not build the preview",
    "레이아웃 견본": "Layout samples", "레이아웃 견본(레이아웃마다 한 장)": "Layout samples (one slide per layout)", "빈 시작(표지 · 글머리 · 표 · 정리 · 끝 5장)": "Blank start (cover · bullets · table · summary · end — 5 slides)",
    "샘플 등록": "Register sample", "등록했습니다": "Registered", "등록한 샘플이 없습니다. 아래에서 참고할 사이트를 등록하세요.": "No samples yet. Register sites to reference below.",
    "튜토리얼 - 처음 만드는 슬라이드": "Tutorial - your first slides", "폴더 고르기": "Choose folder", "이 폴더": "This folder", "이 폴더 선택": "Select this folder", "위 폴더": "Parent folder",
    "하위 폴더가 없습니다": "No subfolders", "열 수 없는 폴더입니다": "Cannot open this folder", "저장소": "repo", "작업 공간": "workspace", "문서": "Documents", "제작 기준": "Projects root",
    "시작 정보를 읽지 못했습니다:": "Could not load start page info:", "명령을 만들지 못했습니다": "Could not build the command", "제목을 적으면 명령의 제목·폴더 이름이 채워집니다": "Enter a title to fill in the command's title and folder name",
    "저장할 폴더를 고르면 명령의 <폴더> 가 채워집니다": "Choose a folder to fill in <folder> in the command", "선택했습니다 - Ctrl+C 로 복사하세요": "Selected - press Ctrl+C to copy",
    "시작 페이지": "Start page", "작업 공간 서버": "Workspace server", "한 주소로 중계": "single-address relay",
    // ---- 편집기 머리줄 · 모드 · 칩
    "편집": "Edit", "선택": "Select", "그리기": "Draw", "✎ 편집": "✎ Edit", "◎ 선택": "◎ Select", "✐ 그리기": "✐ Draw", "⚠ 검사": "⚠ Check", "✨ 레이아웃 고치기": "✨ Fix layout", "✨ 다듬기": "✨ Polish",
    "✨ 세션에 고치기 요청": "✨ Ask session to fix", "＋ 추가 ▾": "＋ Add ▾", "＋ 새 슬라이드": "＋ New slide", "+ 새 슬라이드": "+ New slide", "▶ 발표": "▶ Present", "발표": "Present", "기록": "History", "변경": "Changes",
    "내보내기 ▾": "Export ▾", "내보내기": "Export", "더 보기": "More", "더보기 - 글꼴 세트·템플릿·단축키": "More - font set · template · shortcuts", "속성": "Properties", "요청": "Requests", "노트": "Notes", "개요": "Outline", "검사": "Check",
    "세션 확인 중": "Checking session", "세션 연결됨": "Session connected", "세션 연결 없음": "No session", "세션 처리 중": "Session working", "작업 중": "Busy", "대기 - 요청 바로 처리": "Idle - requests handled right away",
    "세션 연결됨 - 보낸 요청은 바로 전달된다": "Session connected - sent requests are delivered immediately", "세션 연결 없음 - 보낸 요청은 저장되고, 세션이 감시를 시작하면 전달된다": "No session - sent requests are stored and delivered once a session starts watching",
    "웹 세션 대기 중 - 보낸 요청은 바로 처리된다": "Web session idle - sent requests are handled right away", "Claude Code 세션의 요청 감시 연결 상태": "Connection state of the Claude Code session watching requests",
    "터미널의 Claude Code 세션이 요청 감시(watch_requests)로 맡고 있습니다. 웹 세션으로 바꾸려면 그 감시를 끝내세요.": "A terminal Claude Code session is watching requests (watch_requests). Stop that watcher to switch to a web session.",
    "서버가 Claude 를 띄워 편집기 요청을 처리합니다. 터미널 세션(Monitor)과 함께 쓸 수 없습니다.": "The server runs Claude to handle editor requests. It cannot be used alongside a terminal (Monitor) session.",
    "모델 바꾸기": "Change model", "모델 바꾸기…": "Change model…", "턴 로그": "Turn log", "턴 로그…": "Turn log…", "로그 없음": "No log", "웹 세션을 중지할까요? 실행 중인 턴이 있으면 바로 종료됩니다.": "Stop the web session? A running turn will be terminated.",
    "이 작업 공간의 웹 세션을 중지할까요? 실행 중인 턴이 있으면 바로 종료됩니다.": "Stop this workspace's web session? A running turn will be terminated.", "엔진 개발 세션을 중지할까요? 실행 중인 턴이 있으면 바로 종료됩니다.": "Stop the engine session? A running turn will be terminated.",
    "웹 세션을 중지했습니다": "Web session stopped", "시작 실패:": "Start failed:", "이 브라우저는 SSE 를 지원하지 않습니다": "This browser does not support SSE", "연결이 끊겨 다시 붙는 중…": "Connection lost - reconnecting…",
    "한도: 유휴": "Limits: idle", "(턴 끝난 뒤)": "(after this turn)",
    // ---- 편집기 본문
    "슬라이드": "Slide", "슬라이드 추가": "Add slide", "슬라이드 복제": "Duplicate slide", "슬라이드 이동": "Move slide", "아래에 새 슬라이드…": "New slide below…", "유형 바꾸기…": "Change type…", "빈 슬라이드": "Blank slide",
    "마지막 슬라이드는 지울 수 없습니다": "The last slide cannot be deleted", "슬라이드를 추가했습니다 - 예시 내용을 고쳐 쓰세요 (Ctrl+Z 로 되돌리기)": "Slide added - replace the sample content (Ctrl+Z to undo)",
    "유형을 바꿨습니다 - 제목·노트는 옮겼고 본문은 예시 내용입니다 (Ctrl+Z 로 되돌리기)": "Type changed - title and notes kept, body is sample content (Ctrl+Z to undo)", "유형을 불러오는 중…": "Loading types…", "찾는 유형이 없습니다.": "No matching type.",
    "찾기 - 결정, 추이, 사례…": "Search - decision, trend, case…", "유형으로": "By type", "레이아웃으로": "By layout", "새 슬라이드 실패": "New slide failed",
    "실행 취소 (Ctrl+Z)": "Undo (Ctrl+Z)", "다시 실행 (Ctrl+Y)": "Redo (Ctrl+Y)", "되돌리기": "Revert", "되돌렸습니다 (Ctrl+Z 로 취소 가능)": "Reverted (Ctrl+Z to undo)", "직전으로": "Revert to before",
    "굵게": "Bold", "굵게 (Ctrl+B)": "Bold (Ctrl+B)", "글자색": "Text color", "채우기": "Fill", "테두리": "Border", "선": "Line", "면": "Face", "글꼴": "Font", "적용 글꼴": "Applied font", "본문": "Body", "고정폭": "Monospace", "고정폭(코드)": "Monospace (code)",
    "크기(px)": "Size (px)", "크기 프리셋": "Size presets", "줄 높이": "Line height", "줄 간격·세로 정렬": "Line spacing · vertical align", "세로 정렬": "Vertical align", "정렬": "Align", "왼쪽": "Left", "가운데": "Center", "오른쪽": "Right", "양쪽": "Justify", "위": "Top", "아래": "Bottom", "세로": "Vertical",
    "복제": "Duplicate", "복제 (Ctrl+D)": "Duplicate (Ctrl+D)", "삭제 (Del)": "Delete (Del)", "삭제 (Delete)": "Delete (Delete)", "잠금": "Lock", "잠금 - 끌기·삭제 막기": "Lock - prevent drag and delete",
    "위치 조정 - 정렬·순서·크기·좌표": "Arrange - align · order · size · position", "슬라이드 기준 정렬": "Align to slide", "가로 가운데": "Center horizontally", "세로 가운데": "Center vertically", "가로 중앙": "Horizontal center", "세로 중앙": "Vertical center",
    "왼쪽 맞춤": "Align left", "오른쪽 맞춤": "Align right", "위쪽 맞춤": "Align top", "아래쪽 맞춤": "Align bottom", "왼쪽 정렬": "Align left", "오른쪽 정렬": "Align right", "위쪽 정렬": "Align top", "아래쪽 정렬": "Align bottom",
    "같은 너비": "Same width", "같은 높이": "Same height", "같은 크기": "Same size", "가로 같은 간격": "Distribute horizontally", "세로 같은 간격": "Distribute vertically", "분배 (3개 이상)": "Distribute (3+)", "크기 맞추기 (주 선택 기준)": "Match size (to primary selection)",
    "맨 앞으로": "Bring to front", "맨 뒤로": "Send to back", "앞으로 가져오기": "Bring forward", "뒤로 보내기": "Send backward", "맨 앞으로 가져오기": "Bring to front", "맨 뒤로 보내기": "Send to back", "맨 앞": "Front", "맨 뒤": "Back", "⇊ 맨 뒤": "⇊ Back", "↓ 뒤로": "↓ Backward", "↑ 앞으로": "↑ Forward", "⇈ 맨 앞": "⇈ Front", "⧉ 복제": "⧉ Duplicate", "💬 요청": "💬 Request", "🗑 삭제": "🗑 Delete", "동작": "Actions", "면·테두리": "Fill · border", "⇤ 왼쪽": "⇤ Left", "↔ 가운데": "↔ Center", "⇥ 오른쪽": "⇥ Right", "⤒ 위": "⤒ Top", "↕ 가운데": "↕ Middle", "⤓ 아래": "⤓ Bottom", "크기": "Size", "**굵게** · ==강조== · [[토큰|색]] · {page}": "**bold** · ==emphasis== · [[token|color]] · {page}", "인라인 강조 표기": "Inline emphasis syntax", "px (PPT = px × 0.75 pt)": "px (PPT = px × 0.75 pt)", "이 요소에 실제로 적용되는 글꼴 - 역할·세트·크기": "The font actually applied to this element - role, set, size", "순서": "Order",
    "잠기지 않은 상자 요소를 2개 이상 고르세요": "Select two or more unlocked box elements", "Shift/Ctrl+클릭 = 여러 개 고르기": "Shift/Ctrl+click = multi-select", "클릭 = 선택 · Ctrl+클릭 = 더하거나 빼기 · Shift+클릭 = 범위 선택": "Click = select · Ctrl+click = add/remove · Shift+click = select range", "여러 요소": "Multiple elements",
    "글자 편집": "Edit text", "이 요소에 요청 메모": "Request memo on this element", "이 요소에 요청": "Request on this element", "이 요소에 요청 메모(세션에 보냄)": "Request memo on this element (sent to the session)", "이 슬라이드에 요청 메모": "Request memo on this slide",
    "잘라내기": "Cut", "붙여넣기": "Paste", "요소 추가": "Add element", "글자": "Text", "상자": "Box", "원": "Ellipse", "화살표": "Arrow", "그림": "Image", "표": "Table", "코드": "Code", "글머리": "Bullets", "글머리 목록": "Bullet list", "글머리 종류": "Bullet style", "글 앞의 번호·기호가 우선": "typed number/symbol wins", "항목": "Items", "하위 항목": "Sub-items", "글자 상자로 바꾸기": "Convert to text box", "≡ 글머리 목록으로 바꾸기": "≡ Convert to bullet list", "실행계획": "Plan", "칩": "Pill", "표 (2×2)": "Table (2×2)", "새 글자": "New text",
    "요소": "Element", "요소 JSON (고급)": "Element JSON (advanced)", "JSON 적용": "Apply JSON", "JSON 형식 오류:": "JSON error:", "JSON 오류:": "JSON error:", "type 필요": "type required",
    "요소를 눌러 요청 메모를 단다 → 아래 바에서 한꺼번에 보내기": "Click an element to leave a request memo → send them together from the bar below", "영역을 그려 요청 메모를 단다 → 아래 바에서 한꺼번에 보내기": "Draw a region to leave a request memo → send them together from the bar below",
    "요소를 끌어 옮기고, 두 번 눌러 글자를 고친다": "Drag elements to move them; double-click to edit text", "편집 - 끌기·크기·글자 직접 수정 (E)": "Edit - drag, resize, edit text (E)", "선택 - 요소를 눌러 요청 메모를 단다 (M)": "Select - click an element to leave a request memo (M)",
    "그리기 - 영역을 표시해 요청 메모를 단다 (D)": "Draw - mark a region to leave a request memo (D)", "박스": "Box", "펜": "Pen", "핀": "Pin", "▭ 박스": "▭ Box", "〰 펜": "〰 Pen", "📍 핀": "📍 Pin", "박스 - 끌어서 영역": "Box - drag a region", "펜 - 자유 곡선": "Pen - freehand", "핀 - 한 지점": "Pin - a point",
    "영역 요청": "Region request", "이 영역에서 무엇을 바꿀까요?": "What should change in this region?", "이 지점에서 무엇을 바꿀까요?": "What should change at this point?",
    "무엇을 바꿀까요? (Enter = 추가, Shift+Enter = 줄바꿈 · 그림은 Ctrl+V 로 붙여 넣기)": "What should change? (Enter = add, Shift+Enter = newline · paste images with Ctrl+V)",
    "그림·파일 붙이기(클립보드 그림은 Ctrl+V, 끌어다 놓기도 됨)": "Attach image/file (Ctrl+V for clipboard images, or drag and drop)", "빼기": "Remove", "첨부하지 못했습니다:": "Could not attach:", "첨부 미리보기": "Attachment preview", "원본 열기": "Open original", "내려받기": "Download", "이전": "Previous", "다음": "Next", "이 슬라이드의 모든 요청 첨부": "All attachments on this slide", "열기 ↗": "Open ↗", "파일을 읽지 못했습니다": "Could not read the file", "(첨부 참고)": "(see attachment)",
    "메모 남기기": "Leave memo", "메모를 남겼습니다 - 아래 바에서 보내기": "Memo saved - send it from the bar below", "메모를 남겼습니다 - 아래 바에서 한꺼번에 보내기": "Memo saved - send them together from the bar below", "메모를 저장하지 못했습니다": "Could not save the memo",
    "보낼 요청": "Requests to send", "보내기": "Send", "보내지 못했습니다": "Could not send", "보내기 신호를 쓰지 못했습니다": "Could not write the send signal", "모두 취소": "Discard all", "이 슬라이드 취소": "Discard this slide's",
    "이 슬라이드의 메모를 지웠습니다": "This slide's memos were discarded", "모든 메모를 지웠습니다": "All memos were discarded", "이 슬라이드에 메모가 있으면 그 슬라이드만, 없으면 전체를 지운다": "Discards this slide's memos if any, otherwise all of them",
    "세션에 바로 요청했습니다": "Requested from the session right away", "요청을 남겼습니다 - 세션이 연결되면 전달됩니다": "Request saved - delivered once a session connects", "요청하지 못했습니다": "Could not send the request",
    "이 슬라이드는 검사 결과가 없습니다": "This slide has no check results", "Claude 에게 요청": "Ask Claude", "후속 요청": "Follow up", "후속": "follow-up", "앞선 답 보기": "Show previous answer", "이어서 묻거나 답하기 (Enter = 보내기, Shift+Enter = 줄바꿈 · 그림은 Ctrl+V)": "Follow up or answer (Enter = send, Shift+Enter = newline · paste images with Ctrl+V)",
    "이 요청에 이어서 묻거나 답합니다 - 앞선 요청과 답이 함께 세션에 전달됩니다": "Follow up on this request - the earlier request and answer are sent to the session too", "같은 요청을 세션에 다시 보냅니다(답을 달려면 후속 요청)": "Sends the same request to the session again (use Follow up to answer)",
    "후속 요청을 세션에 보냈습니다": "Follow-up sent to the session", "후속 요청을 남겼습니다 - 세션이 연결되면 전달됩니다": "Follow-up saved - delivered once a session connects", "AI 에게 요청": "Ask the AI", "Codex 에게 요청": "Ask Codex", "＋ 첨부": "＋ Attach", "그림 붙여넣기(Ctrl+V) · 끌어다 놓기 · 파일 고르기": "Paste image (Ctrl+V) · drag and drop · choose file",
    "서버가 AI(claude·codex)를 띄워 편집기 요청을 처리합니다. 터미널 세션(Monitor)과 함께 쓸 수 없습니다.": "The server runs the AI (claude · codex) to handle editor requests. It cannot be used alongside a terminal (Monitor) session.", "서버 재시작으로 세션 종료됨": "session ended by server restart", "유휴로 세션 종료됨": "session ended (idle)", "사용자가 세션 중지": "session stopped by user", "오류로 세션 종료됨": "session ended by error", "요청이 없다.": "No requests.", "이 슬라이드": "This slide", "전체": "All", "완료로 표시": "Mark done", "다시 열기": "Reopen", "이 요청을 지울까요?": "Delete this request?",
    "다듬기": "Polish", "더 길게": "Longer", "더 짧게": "Shorter", "검증": "Verify", "항목 줄이기": "Fewer items", "두 장으로 나누기": "Split into two slides", "글자 크게": "Bigger text", "열 너비 맞추기": "Fit column widths", "설명 다듬기": "Polish descriptions",
    "강조 줄 다시": "Redo highlighted lines", "주석 정리": "Tidy comments", "강조 다시": "Redo emphasis", "문구 바꾸기": "Reword", "색 맞추기": "Match colors", "정렬 맞추기": "Fix alignment", "꾸미기": "Decorate", "크기 맞추기": "Match sizes", "방향 바꾸기": "Change direction",
    "위치 바꾸기": "Move", "이 영역 정리": "Tidy this region", "겹침 해결": "Fix overlaps", "여백 맞추기": "Fix margins", "검사 결과 고치기": "Fix check results",
    "기존 스타일을 유지하며 내용 논리·배치를 다듬어 달라고 세션에 바로 요청": "Ask the session to polish logic and layout while keeping the current style", "이 슬라이드의 검사 결과(겹침·넘침·글자 크기)를 세션에 고쳐 달라고 바로 요청 - 기존 디자인 유지": "Ask the session to fix this slide's check results (overlap, overflow, text size) - keep the design",
    "레이아웃 검사 결과(아래 검사 탭)": "Layout check results (Check tab below)", "레이아웃 검사": "Layout check", "레이아웃 검사 - 저장할 때마다 자동": "Layout check - runs on every save", "다시 검사": "Check again", "검사 중…": "Checking…", "문제 없음.": "No problems.", "규칙": "Rule",
    "발표자 노트": "Speaker notes", "(노트 없음)": "(no notes)", "이 슬라이드의 발표자 노트 - PPTX 슬라이드 노트로 들어간다": "Speaker notes for this slide - exported as PPTX notes", "개요 - 슬라이드 제목 목록": "Outline - slide titles",
    "슬라이드를 누르면 크게 봅니다": "Click a slide to view it large", "이전 슬라이드 (PageUp)": "Previous slide (PageUp)", "다음 슬라이드 (PageDown)": "Next slide (PageDown)", "◀ 이전": "◀ Prev", "다음 ▶": "Next ▶",
    "확대": "Zoom", "축소 (Ctrl+-)": "Zoom out (Ctrl+-)", "확대 (Ctrl+=)": "Zoom in (Ctrl+=)", "확대 (Ctrl+휠)": "Zoom (Ctrl+wheel)", "화면 맞춤 (Ctrl+0)": "Fit to screen (Ctrl+0)", "⤢ 맞춤": "⤢ Fit", "100% 로": "to 100%", "화면 이동": "Pan",
    "최대화 배치": "Maximized layout", "⛶ 최대화": "⛶ Maximize", "🗗 복원": "🗗 Restore", "아래 패널 접기/펴기": "Collapse/expand bottom panel", "오른쪽 패널 접기/펴기 (Ctrl+\\)": "Collapse/expand right panel (Ctrl+\\)", "패널": "Panels", "패널 크기": "Panel size",
    "끌어서 높이 조절 · 두 번 눌러 처음 높이": "Drag to resize · double-click to reset", "끌어서 폭 조절 · 두 번 눌러 처음 폭": "Drag to resize · double-click to reset",
    "발표 (F5 처음부터 · Shift+F5 또는 Shift+클릭 = 현재 슬라이드부터) - 발표 중 N = 노트, Esc = 끝": "Present (F5 from start · Shift+F5 or Shift+click = from current slide) - N = notes, Esc = end", "여기서부터 발표": "Present from here", "처음부터 발표 ·": "Present from start ·", "끝": "End",
    "PPTX 내보내기 (편집 가능한 도형)": "Export PPTX (editable shapes)", "PPTX 내보내기 - 글꼴 포함 (PowerPoint 필요)": "Export PPTX with fonts (needs PowerPoint)", "쓴 글꼴 기록 보기 (마지막 내보내기)": "Show fonts used (last export)",
    "글꼴 받기·설치 안내": "Font download & install guide", "글꼴 받기·설치 안내 ↗": "Font download & install guide ↗", "PowerPoint 렌더 미리보기 닫기": "Close PowerPoint render preview", "PowerPoint 렌더 미리보기 (나란히)": "PowerPoint render preview (side by side)",
    "PowerPoint 로 다시 렌더 (Windows)": "Re-render with PowerPoint (Windows)", "PowerPoint 렌더": "PowerPoint render", "다시 렌더": "Re-render", "아직 렌더 없음 - \"다시 렌더\"": "No render yet - \"Re-render\"", "· 렌더 뒤에 편집됨 - 다시 렌더 필요": "· edited after render - re-render needed",
    "만드는 중": "Building", "글꼴 넣는 중": "Embedding fonts", "내보내기 실패:": "Export failed:", "렌더 실패:": "Render failed:", "⬇ 받기": "⬇ Download", "PowerPoint 렌더 완료": "PowerPoint render finished",
    "글꼴 세트": "Font set", "글꼴 설정 보기·수정…": "View/edit font settings…", "덱 글꼴 세트": "Deck font set", "제목 바꾸기…": "Rename title…", "덱 이름(id) 바꾸기…": "Rename deck (id)…", "새 덱…": "New deck…", "덱 삭제(휴지통)…": "Delete deck (trash)…", "덱 제목": "Deck title", "제목을 바꿨습니다": "Title changed",
    "새 덱 이름(파일 이름 - 영문·숫자·-·_)": "New deck name (file name - letters, digits, -, _)", "새 덱 이름(파일 이름 - 영문·숫자·-·_). 요청·기록·첨부·content 도 함께 옮깁니다": "New deck name (file name - letters, digits, -, _). Requests, history, attachments and content move with it",
    "새 덱 만들기(덱 관리: 오른쪽 클릭 메뉴)": "New deck (deck management: right-click menu)", "템플릿 기본": "template default", "(템플릿 기본)": "(template default)", "작업 공간 지정": "workspace-defined", "글꼴 - 지금 세트": "Fonts - current set",
    "역할별 글꼴": "Fonts by role", "본문 글꼴": "Body font", "제목 글꼴": "Heading font", "글꼴 역할 - 세트의 본문·제목·고정폭 글꼴 중 어느 것을 쓰는지": "Font role - which of the set's body, heading or monospace fonts to use", " · 세트의 이 역할 글꼴 자체가 굵은 서체(굵게 토글과 별개)": " · this role's font in the set is itself a bold face (separate from the Bold toggle)", "작업 공간 글꼴 파일": "Workspace font files", "작업 공간 세트 만들기 (지금 값에서 시작)": "Create workspace set (starting from current values)", "세트 이름": "Set name", "저장하고 이 세트 쓰기": "Save and use this set",
    "글꼴 세트를 바꾸지 못했습니다": "Could not change the font set", "작업 공간 글꼴 세트를 저장했습니다 - PPTX 는 다음 내보내기부터": "Workspace font set saved - applies to PPTX from the next export", "이 PC 에 없음": "not on this PC", "이 작업 공간에서 쓰는 글꼴": "Fonts used by this workspace",
    "단축키": "Shortcuts", "단축키 보기": "Show shortcuts", "편집기 화면 배치 초기화": "Reset editor layout", "덱 설정": "Deck settings", "템플릿·레이아웃 후보와 참고 자료를 미리 보고 검토·승인": "Preview, review and approve template/layout candidates and references",
    "편집기 코드·템플릿(엔진)이 바뀌었습니다. 새로 고침해야 반영됩니다.": "The editor code/templates (engine) changed. Refresh to apply.", "새로 고침": "Refresh", "저장하고 새로 고침": "Save and refresh", "덱을 불러오지 못했습니다": "Could not load the deck",
    "밖에서 바뀐 덱을 다시 불러왔습니다": "Reloaded the deck changed outside", "외부 버전 불러오기": "Load external version", "내 편집으로 덮어쓰기": "Overwrite with my edits", "외부 버전을 불러왔습니다(내 편집은 Ctrl+Z 로 복구)": "Loaded the external version (Ctrl+Z restores my edits)",
    "편집 중에 덱 파일이 밖에서(Claude 등) 바뀌었습니다. 어느 쪽을 남길까요?": "The deck file changed outside (e.g. Claude) while editing. Which version do you want to keep?", "저장하려는 사이 덱 파일이 밖에서(Claude 등) 바뀌었습니다. 어느 쪽을 남길까요?": "The deck file changed outside (e.g. Claude) while saving. Which version do you want to keep?",
    "충돌": "Conflict", "서버 끊김": "Server disconnected", "기록 - 저장할 때마다 남긴 자동 백업으로 되돌리기": "History - revert to automatic backups made on every save", "기록을 읽지 못했습니다": "Could not read history", "기록이 없다.": "No history.",
    "백업이 50개 상한으로 지워져 되돌릴 수 없습니다": "The backup was removed by the 50-backup limit and cannot be restored", "저장 전": "before save", "빌드 전": "before build", "외부 변경 전": "before external change",
    "변경 원장 - 편집기·Claude·빌드·외부의 변경, 출처, 최근 수정 대상, 되돌리기": "Change ledger - changes by the editor, Claude, builds and external edits; source; recently changed items; revert", "모든 변경 - 편집기·Claude·빌드·외부": "All changes - editor · Claude · build · external",
    "최근 수정 대상": "Recently changed", "아직 기록된 변경이 없습니다.": "No changes recorded yet.", "이 필터에 해당하는 변경이 없습니다.": "No changes match this filter.", "원장의 시작": "Start of ledger", "표시": "Show", "숨기기": "Hide", "표시 켜기": "Show marks", "표시 끄기": "Hide marks", "표시 지우기": "Clear marks", "그만 표시": "Stop showing",
    "최근 3개 표시": "Show last 3", "확인함": "Reviewed", "추정": "inferred", "(추정)": "(inferred)", "외부": "External", "협업": "Collaboration", "빌드": "Build", "수정": "Edit", "내 편집이 아닌 변경이 있는 슬라이드 - 변경 탭": "Slide with changes not made by me - Changes tab",
    "현재 편집기에서 수정": "Edited in this editor", "다른 편집기에서 수정": "Edited in another editor", "서버 API 로 저장(정확)": "Saved via server API (exact)", "AI에서 수정, 파일 직접 수정은 추정": "Edited by AI (direct file edits are inferred)", "서버가 꺼진 사이에 바뀜(출처 모름)": "Changed while the server was off (unknown source)",
    "출처를 알 수 없는 변경 - 파일 수동 복사·수정, 서버가 꺼진 사이의 변경": "Change of unknown origin - manual file copy/edit, or changed while the server was off", "출처를 알 수 없는 외부 변경(파일 직접 수정)": "External change of unknown origin (direct file edit)", "정황으로 추정(세션 연결·처리 중 요청)": "Inferred from context (connected session, request in progress)",
    "(바뀐 내용 없음)": "(no changes)", "근거:": "Evidence:", "(내 편집은 기본으로 표시하지 않는다)": "(my own edits are hidden by default)", "변경 표시를 다시 켠다(묶음별 표시 상태는 그대로)": "Turn change marks back on (per-group state is kept)",
    "변경 기록을 보지 않고 작업 - 배지·점선을 모두 감춘다(묶음별 표시 상태는 그대로)": "Work without change marks - hide all badges and dashed outlines (per-group state is kept)", "이 변경 직전 상태로 되돌린다(지금 상태도 기록에 남는다)": "Revert to just before this change (the current state is recorded too)",
    "가장 최근 변경 묶음 3개를 표시한다(내 편집 포함) - 묶음마다 '표시'를 누르는 것과 같다": "Show the 3 most recent change groups (including mine) - same as pressing Show on each", "최근 변경까지 확인한 것으로 - 모든 묶음을 미표시로 바꾼다(묶음마다 '표시'로 다시 볼 수 있다)": "Mark everything up to the latest change as reviewed - hides all groups (Show brings any back)",
    "코드 언어 - 서식 줄 또는 속성 탭에서 바꾼다": "Code language - change it in the format bar or Properties tab", "코드 언어 이름표 표시": "Show code language tag", "캔버스 코드 블록 오른쪽 위 언어 이름표 표시 여부(편집 화면에만, 모든 코드 블록 공통)": "Show the language tag at the top right of code blocks (editor only, all code blocks)",
    "코드를 클립보드에 복사": "Copy code to clipboard", "코드 글자를 클립보드에 복사(줄 번호·색 없이)": "Copy the code text (without line numbers or colors)", "📋 복사": "📋 Copy", "언어": "Language", "언어 찾기 - 이름·별칭": "Find language - name or alias", "언어 찾기 - 예: bash, c#, json, rust": "Find language - e.g. bash, c#, json, rust",
    "입력하면 목록이 좁혀집니다 - 이름·별칭(sh, cs, js, py …)으로 찾기": "Type to narrow the list - by name or alias (sh, cs, js, py …)", "지정 안 함(SQL 색)": "Unset (SQL colors)", "줄 번호": "Line numbers", "시작 번호": "Start number", "강조 줄": "Highlighted lines", "예: 1, 9": "e.g. 1, 9", "예: 2, 13-24 (비우면 전체)": "e.g. 2, 13-24 (empty = all)",
    "코드 왼쪽 줄 번호 열 - 끄면 화면·PPTX 모두 번호 없이": "Line number column - when off, neither the editor nor PPTX shows numbers", "모서리": "Corners", "배경": "Background", "두께(px)": "Thickness (px)", "실선": "Solid", "점선": "Dotted", "파선": "Dashed", "곡선": "Curved", "선 색": "Line color", "점 색": "Dot color",
    "선 모양 - 누를 때마다 바뀜": "Line style - click to cycle", "화살 머리 - 누를 때마다 바뀜": "Arrowhead - click to cycle", "너비": "Width", "높이": "Height", "높이를 줄 수에 맞추기": "Fit height to line count", "행 비율": "Row ratios", "열 비율": "Column ratios", "비우면 고르게 · 예: 44, 46, 70": "Empty = even · e.g. 44, 46, 70",
    "머리": "Header", "머리 글자": "Header text", "머리 면": "Header face", "유형": "Type", "일반": "Normal", "열별 글꼴": "Per-column font", "비우면 위 유형 · 예: body, mono, body": "Empty = type above · e.g. body, mono, body",
    "일반 = 세트의 본문 글꼴 · 코드 = 고정폭(코드) 글꼴 - 본문 셀 전체(머리 행은 항상 본문). 열마다 다르게 하려면 아래 열별 글꼴.": "Normal = the set's body font · Code = monospace (code) font - all body cells (header row is always body). Use per-column font below for a per-column choice.",
    "열마다 body(일반)·mono(코드)·heading(제목 글꼴) - 빈 칸은 위 유형. 머리 행은 항상 본문": "Per column body (normal) · mono (code) · heading (heading font) - blank = type above. Header row is always body", "하위 글자색": "Sub-item color", "하위 크기": "Sub-item size", "항목 간격": "Item spacing", "구분": "Separator", "열 1": "Column 1", "열 2": "Column 2", "실행계획 표": "Plan table", "실행계획 원문 - [[값]] = 경고 강조, [[ok:값]] = 개선 강조 (폭 불변)": "Plan text - [[value]] = warning, [[ok:value]] = improvement (width unchanged)",
    "글머리 - 줄마다 항목, 앞에 공백 두 칸 = 하위 항목": "Bullets - one item per line, two leading spaces = sub-item", "표 - 줄 = 행, 칸은 \" | \" 로 구분 (첫 행 = 머리)": "Table - one row per line, cells separated by \" | \" (first row = header)",
    "글자 - **굵게** · ==강조== · [[토큰|색 글자]] · {page}": "Text - **bold** · ==emphasis== · [[token|colored text]] · {page}", "요소를 누르면 위 서식 줄과 여기서 고칠 수 있다. 색은 토큰 이름으로 고른다(색의 의미 유지).": "Click an element to edit it in the format bar above and here. Colors are chosen by token name (keeps their meaning).",
    "assetRoot 기준 경로. 모서리 핸들은 비율 유지.": "Path relative to assetRoot. Corner handles keep the aspect ratio.", "글자 크기(px) - PPT pt = px × 0.75": "Text size (px) - PPT pt = px × 0.75", "PPT 글자 크기 = px × 0.75 pt": "PPT text size = px × 0.75 pt", "PowerPoint 글자 크기": "PowerPoint text size",
    "px · 슬라이드 1280×720": "px · slide 1280×720", "로고 · 쪽번호만": "Logo · page number only", "로고·쪽번호·바닥 경로만 있는 빈 장": "Blank slide with only logo, page number and footer path", "템플릿 기본 항목(로고·쪽번호·바닥 경로)만 - 본문은 직접 추가": "Only template basics (logo, page number, footer) - add the body yourself",
    "유형 = 이 장이 하는 일(목적·구성) - 예시 내용이 채워져 있으니 고쳐 쓰세요.": "Type = what this slide does (purpose and structure) - sample content is filled in; rewrite it.", "누르면 지금 슬라이드 다음에 들어갑니다(Ctrl+Z 로 되돌리기).": "Inserts after the current slide (Ctrl+Z to undo).",
    "누르면 맨 아래(마지막 슬라이드 다음)에 들어갑니다(Ctrl+Z 로 되돌리기). 특정 슬라이드 다음에 넣으려면 그 썸네일 오른쪽 단추 → 아래에 새 슬라이드.": "Inserts at the end (after the last slide; Ctrl+Z to undo). To insert after a specific slide, use that thumbnail's right-click → New slide below.",
    "누르면 지금 슬라이드를 그 유형으로 바꿉니다 - 제목·발표자 노트·슬라이드 id(요청 메모)는 그대로 옮깁니다(Ctrl+Z 로 되돌리기).": "Changes the current slide to that type - title, speaker notes and slide id (request memos) are kept (Ctrl+Z to undo).",
    "보내지 않은 요청 메모": "Unsent request memos", "세션에 보낸 요청(대기)": "Requests sent to the session (waiting)", "그 슬라이드가 지금은 없습니다": "That slide no longer exists", "편집기": "Editor", "덱(장) - 누르면 바뀐다": "Deck - click to switch", "모드": "Mode",
    "모드: 글자를 바로 고치고, 서식 줄로 굵게·색·크기를 바꿉니다. 저장은 자동입니다.": "mode: edit text directly; use the format bar for bold, color and size. Saving is automatic.", "모드: 요소를 눌러 그 자리에 요청 메모를 남깁니다.": "mode: click an element to leave a request memo on it.", "모드: 영역을 그려 요청합니다.": "mode: draw a region to request a change.",
    "이 슬라이드를 다듬어 줘 - 기존 스타일·레이아웃 규칙은 유지하고, 내용 논리·문장 길이·정렬·여백만 정리. 원문(각주 근거)의 의미는 바꾸지 말 것.": "Polish this slide - keep the existing style and layout rules; only tidy logic, sentence length, alignment and margins. Do not change the meaning of the source (footnote evidence).",
    "기록을 보지 않고 작업할 때 모든 표시를 감춥니다": "hides all marks while you work without history", "서버에 연결할 수 없습니다 ": "Cannot reach the server",
    // ---- 글꼴 안내
    "글꼴 받기·설치 안내 — nexa-slide": "Font download & install guide — nexa-slide", "무료": "Free", "무료 글꼴 목록": "Free fonts", "전용": "Custom", "전용(목록 밖)": "Custom (not listed)", "라이선스": "License", "받을 파일": "File to download", "파일 · 설치": "Files · install", "설치": "Install", "설치 방법": "How to install", "설치 없이 보내기": "Send without installing",
    "산세리프": "Sans-serif", "세리프(명조)": "Serif", "서체 관리자": "Font Book", "모든 사용자용으로 설치": "Install for all users", "슬라이드 글꼴은": "Slide fonts are", "역할마다": "per role", "가나다 ABC 123 - 견본 글자": "가나다 ABC 123 - sample text",
    "되도록 아래 목록의 무료 글꼴": "Prefer the free fonts listed below", "(누구나 직접 받아 문서·상업용으로 쓸 수 있는 SIL OFL 등)로 고릅니다. 받는 사람도 같은 글꼴을 구할 수 있어야 같은 모양으로 보입니다.": "(SIL OFL and similar - anyone can download and use them in documents and commercially). Recipients must be able to get the same font to see the same look.",
    "글꼴 파일은 nexa-slide 엔진에 두지 않습니다. 작업 공간": "Font files are never kept in the nexa-slide engine. Put them in the workspace", "에 두고, 글꼴 세트는 작업 공간": "folder, and define font sets in the workspace", "의": "'s", "로 정합니다.": ".",
    "목록에 없는 글꼴(회사 전용 서체 등)은": "Fonts not in the list (company typefaces etc.) are marked", "으로 표시합니다 — 받는 사람이 구할 수 있는지, 배포가 허용되는지 확인하고, 밖으로 보낼 때는": "— check that recipients can get them and that distribution is allowed; when sending outside, use", "내보내기 → PPTX 글꼴 포함": "Export → PPTX with fonts", "을 씁니다.": ".",
    "작업 공간 글꼴 폴더": "workspace font folder", "Windows 기본 글꼴": "Windows built-in font", "포함 편집 가능 포함": "Embeddable (editable)", "Windows 에 기본 설치": "Installed with Windows", "또는": "or", "에 복사.": "and copy.", "PowerPoint 를 다시 연다.": "Reopen PowerPoint.", "프로그램을 다시 연다.": "Reopen the program.",
    "공식 배포처에서 직접 받습니다. \"세트\"는 nexa-slide 기본 글꼴 세트에서 쓰는 글꼴입니다.": "Download directly from the official source. \"Set\" marks fonts used by nexa-slide's built-in font sets.", "받은 zip 을 풀고 굵기별": "Unzip the download and pick the per-weight", "를 고른다(가변 글꼴보다 정적 파일).": "files (static files rather than variable fonts).",
    "파일을 오른쪽 단추 →": "Right-click the file →", "(현재 사용자) 또는": "(current user) or", "PowerPoint·브라우저를 다시 연다.": "Reopen PowerPoint and the browser.", "에 넣은 글꼴은 그 폴더에서": "Fonts placed in", "로 한 번에 설치(관리자 권한 불필요).": "can be installed from that folder in one go (no admin rights).", "글꼴 파일을 두 번 눌러": "Double-click the font file",
    "맑은 고딕·Consolas 는 Windows 기본 글꼴이라 macOS 에는 없다 — 받는 쪽이 macOS 면 무료 글꼴 세트를 쓴다.": "Malgun Gothic and Consolas ship with Windows and are absent on macOS — use a free font set when the recipient is on macOS.", "도 같은 일을 한다.": "does the same.", "— 편집기": "— editor",
    "내보내기 → PPTX 내보내기 — 글꼴 포함": "Export → Export PPTX — with fonts", "(Windows·PowerPoint 필요): 쓴 글자만 PPTX 안에 넣어 받는 사람이 설치하지 않아도 같은 모양으로 본다. 포함 금지(fsType) 글꼴은 들어가지 않는다. 쓴 글꼴은 내보낼 때마다": "(needs Windows and PowerPoint): embeds only the glyphs used, so recipients see the same look without installing. Fonts that forbid embedding (fsType) are skipped. The fonts used are recorded on every export in", "에 기록된다.": ".",
    // ---- 편집기 - 남은 글
    "세션 연결 없음 ▾": "No session ▾", "세션 연결됨 ▾": "Session connected ▾", "세션 연결 없음. 눌러서 웹 세션을 시작하거나, 터미널 세션에서 watch_requests.py --stream 을 Monitor 로 실행하면 연결된다": "No session. Click to start a web session, or run watch_requests.py --stream with Monitor in a terminal session to connect",
    "내보내기 - PPTX · PowerPoint 렌더 미리보기": "Export - PPTX · PowerPoint render preview", "최대화 배치 - 노트·개요·검사를 오른쪽 아래로 옮기고 가운데를 슬라이드에 (Ctrl+Shift+M)": "Maximized layout - move notes/outline/check to the bottom right and give the center to the slide (Ctrl+Shift+M)",
    "원래 배치로 - 노트·개요·검사를 다시 아래로 (Ctrl+Shift+M)": "Original layout - notes/outline/check back to the bottom (Ctrl+Shift+M)", "(덱 기본)": "(deck default)", "모드에서 요소를 누르거나 ✐": "mode, click an element, or in ✐", "모드에서 영역을 그려 메모를 단 뒤, 아래 바의": "mode draw a region to leave a memo, then send them together with",
    "로 한꺼번에 보낸다. 슬라이드 전체 요청은 여기에.": "in the bar below. Whole-slide requests go here.", "설명 보기/숨기기": "Show/hide description", "build_deck 으로 content 에서 덱을 다시 만든 변경": "Change from rebuilding the deck from content with build_deck", "이 묶음의 변경을 썸네일 배지·캔버스 파란 점선으로 그만 표시": "Stop marking this group's changes with thumbnail badges and blue dashed outlines",
    "닫기 (Esc)": "Close (Esc)", "덱 전체": "Whole deck", "이 서버의 작업 공간": "This server's workspace", "Studio 로": "To Studio",
    // ---- 시작 페이지 - 남은 글
    "템플릿과 작성 방향, 자료를 간단히 적고": "Briefly note the template, direction and materials, then choose", "내용을 둘 폴더·저장소": "the folder/repo for the content", "를 먼저 정합니다. 제작 도구(엔진)와 만든 슬라이드는 서로 다른 폴더에 있습니다.": "first. The tool (engine) and the slides you make live in different folders.",
    "예: 2026 하반기 S&OP 교육": "e.g. 2026 H2 S&OP training", "고른 템플릿과 시작용 내용으로 만든 슬라이드를 미리 봅니다": "Preview slides built from the chosen template and starter content", "예: 신규 담당자가 수요계획 화면을 혼자 쓸 수 있게": "e.g. so a new planner can use the demand-planning screen alone", "예: 현업 계획 담당자 20명, SQL 초급": "e.g. 20 business planners, SQL beginners",
    "분량·구성·말투·강조할 점 - 예: 3시간 강의, 장마다 실습 1개, 용어는 표준 용어로": "Length, structure, tone, emphasis - e.g. 3-hour lecture, one exercise per chapter, standard terminology", "한 줄에 하나 - 파일 경로, 웹 주소, 메모": "One per line - file path, URL, note", "적은 내용은 작업 공간의": "What you write is saved in the workspace's", "에 남습니다. Claude 세션이 초안을 쓸 때 먼저 읽습니다.": ". The Claude session reads it first when drafting.",
    "지정한 폴더를 저장소 관리 기준 폴더(루트)로 씁니다 - 기초 자료 수집·정리와 관련 소스 개발은 여기서 자유롭게 하고, 슬라이드(최종 산출물)는 아래 작업 공간 폴더에 만듭니다. 루트에는 안내": "The chosen folder becomes the repo root - collect and organize source material and develop related code freely there; slides (the deliverable) go in the workspace folder below. Only the guide", "만 두고 이미 있는 파일은 건드리지 않습니다.": "is placed in the root; existing files are left alone.",
    "예: my-talk": "e.g. my-talk", "저장소 루트 아래 이 이름의 폴더에 슬라이드(작업 공간)를 만듭니다 - 예:": "Creates the slides (workspace) in a folder of this name under the repo root - e.g.", "자동 (5600)": "auto (5600)", "비우면 이 PC 에서 비어 있고 다른 작업 공간이 쓰지 않는 포트를 고릅니다.": "Leave empty to pick a port that is free on this PC and unused by other workspaces.",
    "위 버튼과 똑같은 작업 공간을 터미널에서 만듭니다(브리프·빌드·초안 요청·최근 작업 등록 포함). 위에서 고친 값이 바로 반영됩니다.": "Creates the same workspace from a terminal (brief, build, draft request, recent-work entry). Values edited above are reflected immediately.", "끝낼 때는 ② 의": "To stop, run ② with", "를": "replaced by", "으로 바꿔 실행합니다. 다음부터는 ② 만 실행하면 됩니다.": ". From then on, only ② is needed.",
    "예: 표 레이아웃에 각주 칸 추가": "e.g. add a footnote slot to the table layout", "설정 포트(nexa-slide.json · nexa-slide.local.json)": "Configured port (nexa-slide.json · nexa-slide.local.json)", "웹 세션 시작(서버가 꺼져 있으면 먼저 띄움)": "Start a web session (starts the server first if it is off)", "이 작업 공간의 웹 세션 중지(실행 중 턴도 끝낸다)": "Stop this workspace's web session (ends a running turn too)",
    "다섯 단계로 작성 흐름을 익힙니다. 직접 따라 해 보려면": "Learn the workflow in five steps. To follow along, open", "를 열어 같은 화면에서 해 보세요.": "and try it on the same screen.", "작업 공간을 정한다": "Choose a workspace", "제작 도구(nexa-slide 엔진)는 내용을 자기 폴더에 두지 않습니다. 제작마다 작업 공간 폴더를 하나 만듭니다.": "The tool (nexa-slide engine) keeps no content in its own folder. Each production gets one workspace folder.",
    "기본 위치: 문서 폴더 아래": "Default location: under the Documents folder,", "고른 폴더는 저장소 관리 기준 폴더(루트)입니다: 기초 자료를 모아 정리하고 필요하면 관련 소스도 개발합니다(구조 자유). 슬라이드는 그 자료를 근거로": "The chosen folder is the repo root: gather and organize source material and develop related code if needed (any structure). Slides are made from that material in", "에서 만듭니다. 루트에는 폴더를 만들지 않고": ". No folders are created in the root; only", "(개념·서버 실행)와, 없을 때만": "(concepts, running the server) and, if missing,", "를 둡니다.": "are placed.",
    "이미 있는 저장소에 붙이려면 \"폴더·저장소 지정\"으로 그 저장소를 고르고 하위 폴더는 비웁니다. 내용이 그 저장소의 git 이력으로 관리됩니다.": "To attach to an existing repo, choose it with \"Choose folder / repo\" and leave the subfolder empty. Content is then managed by that repo's git history.", "작업 공간(": "Workspace (", ") 구성:": ") layout:", "(포트·템플릿 선택) ·": "(port, template) ·", "(실행기 -": "(launcher -", "(내용 원본) ·": "(content source) ·", "(편집 대상) ·": "(what you edit) ·", "(그림) ·": "(images) ·", "(작성 방향)": "(direction)",
    "템플릿을 고르고 방향을 적는다": "Pick a template and write the direction", "색·글꼴·글자 크기는 엔진의": "Colors, fonts and sizes live in the engine's", "에 있고, 작업 공간은 이름만 고릅니다. 목적·대상·작성 방향·참고 자료를 적어 두면 Claude 세션이 초안을 쓸 때 기준으로 씁니다.": "; the workspace only picks a name. Purpose, audience, direction and materials you write down guide the Claude session when drafting.", "자료에 없는 내용은 지어내지 않고 확인 질문으로 남깁니다.": "Nothing absent from the materials is invented - it is left as a question.",
    "Studio 에서 고친다": "Edit in Studio", "탭: 겹침·넘침·최소 글자 크기·슬라이드 밖을 알려 줍니다.": "tab: reports overlaps, overflow, minimum text size and off-slide elements.", "Claude 세션에 요청한다": "Ask the Claude session", "작업 공간 폴더에서 Claude Code 세션을 열고 요청 감시를 겁니다(작업 공간의": "Open a Claude Code session in the workspace folder and start watching requests (the command is in the workspace's", "에 명령이 있습니다).": ").", "를 Monitor 로 실행": "run with Monitor",
    "머리줄 칩이 \"세션 연결됨\"이 되면, 남긴 메모를 \"요청 N개 보내기\"로 보냅니다. 처리 결과와 답변은 요청 탭에 돌아옵니다.": "Once the header chip says \"Session connected\", send your memos with \"Send N requests\". Results and replies come back in the Requests tab.", "발표하고 내보낸다": "Present and export", "현재 슬라이드부터 · 발표 중": "from the current slide · while presenting",
    "\"내보내기\"로 편집 가능한 PPTX 를 만듭니다(Windows 에 PowerPoint 가 있으면 렌더 미리보기도).": "\"Export\" makes an editable PPTX (with a render preview when PowerPoint is on Windows).", "잘못 고쳤으면 \"기록\"에서 저장 시점으로 되돌립니다(자동 백업 50개).": "If something went wrong, revert to a save point from \"History\" (50 automatic backups).",
    "엔진에 들어 있는 예제 덱으로 Studio 의 기능을 직접 눌러 봅니다. 예제는 엔진 폴더에서 바로 열지 않고, 기준 폴더에 복사본을 만들어 엽니다(처음 한 번).": "Try Studio's features on the example deck bundled with the engine. It is not opened from the engine folder; a copy is made in the projects root (once).", "레이아웃 여러 종(표지 · 글머리 · 표 · 코드 · 비교 · 정리 · 끝)과 발표자 노트": "Several layouts (cover · bullets · table · code · comparison · summary · end) and speaker notes",
    "편집 · 선택 · 그리기 모드, 서식 줄, 실행 취소": "Edit · Select · Draw modes, format bar, undo", "요청 메모 남기기와 보내기, 세션 연결 칩": "Leaving and sending request memos, session chip", "레이아웃 검사 탭, 발표(F5), PPTX 내보내기, 기록으로 되돌리기": "Layout check tab, Present (F5), PPTX export, revert from History", "데모 폴더는 마음껏 고쳐도 됩니다. 처음 상태로 돌리려면 데모 폴더를 지우고 다시 여세요.": "Feel free to change the demo folder. To reset, delete it and open the demo again.",
    "디자인(색 · Font · 글자 크기 · 검사 기준)은 엔진의 템플릿에 있습니다. 작업 공간은 템플릿 이름만 고르고 디자인을 따로 두지 않습니다.": "Design (colors, fonts, sizes, check rules) lives in the engine's templates. A workspace only picks a template name and keeps no design of its own.", "디자인(색 · 글꼴 · 글자 크기 · 검사 기준)은 엔진의 템플릿에 있습니다. 작업 공간은 템플릿 이름만 고르고 디자인을 따로 두지 않습니다.": "Design (colors, fonts, sizes, check rules) lives in the engine's templates. A workspace only picks a template name and keeps no design of its own.",
    "구성 예시가 들어 있는 시작 내용입니다. 새로 만들 때 \"시작용 내용\"에서 고릅니다.": "Starter content with example structures. Choose it under \"Starter content\" when creating.", "참고할 슬라이드·발표 사이트를 등록해 두고 둘러봅니다. 목록은 이 PC 의 사용자 설정에 저장됩니다(엔진·작업 공간 밖).": "Register slide and presentation sites to reference. The list is saved in this PC's user settings (outside the engine and workspaces).", "메모(선택)": "Note (optional)", "이동": "Go",
    "고른 폴더가 저장소 루트가 되고 작업 공간은 그 아래 slides/ 에 만듭니다.": "The chosen folder becomes the repo root; the workspace is created under its slides/.", "로 직접 띄우는 방식은 둘 다 그대로입니다.": "still works either way.", "작업 공간 설정(": "Workspace settings (", ")과 세션 시작 창의 선택이 이 값보다 우선합니다. 비우면 기본(claude · opus).": ") and the choice in the start dialog take precedence. Empty = default (claude · opus).", "(계정에서 쓸 수 있는 모델 ID)": "(model IDs available to the account)", "내용": "Details",
    "켜면 여러 작업 공간을 포트 하나(이 페이지의 포트)로 함께 씁니다. 작업 공간 서버는 뒤에서 따로 돌고(설정 포트가 쓰는 중이면 빈 포트로), 이 서버가 요청을 넘깁니다.\n      끄면 예전처럼 그 작업 공간 서버의 포트로 바로 이동합니다.": "When on, several workspaces share one port (this page's). Workspace servers run separately behind it (on a free port if the configured one is busy) and this server relays requests.\n      When off, you are sent straight to the workspace server's port as before.",
    "디자인 기준": "Design guide", "아카이브 - 종이 미색·테라코타": "Archive - paper cream · terracotta", "블루프린트 - 도면 청록·주황": "Blueprint - drafting teal · orange", "결정 요청 - 차콜·딥 틸": "Brief - charcoal · deep teal", "에디토리얼 - 미색·명조·진홍": "Editorial - cream · serif · crimson", "포레스트 - 숲녹색·크림·테라코타": "Forest - forest green · cream · terracotta",
    "그래파이트 - 흰 바탕·회색 단계·검정": "Graphite - white · grays · black", "키노트 - 어두운 무대·금색": "Keynote - dark stage · gold", "강의 교재 — Material v2": "Lecture — Material v2", "강의 교재 — 큰 글자(일괄 확대)": "Lecture — large text (scaled up)", "원장 - 크림·남색·금색": "Ledger - cream · navy · gold", "공지·온보딩 - 밝은 오렌지": "Notice · onboarding - bright orange",
    "RFP·제안 - 인디고·골드": "RFP · proposal - indigo · gold", "일정·로드맵 - 차분한 블루": "Schedule · roadmap - calm blue", "시그널 - 노랑·검정·빨강": "Signal - yellow · black · red", "스위스 - 흰 바탕·빨강 하나": "Swiss - white · one red",
    "이사회·경영 결정 요청 (11장)": "Board / executive decision request (11 slides)", "사례 연구·회고 이야기 (12장)": "Case study · retrospective story (12 slides)", "수업·학생 발표 (12장)": "Class · student presentation (12 slides)", "컨설팅·문제 해결 (16장)": "Consulting · problem solving (16 slides)", "투자 유치 피치 (13장)": "Investor pitch (13 slides)", "IR·재무 브리핑 (12장)": "IR · finance briefing (12 slides)",
    "강의 교안 (3일 과정)": "Lecture course (3-day)", "강의·교안(이론·이공계) (14장)": "Lecture (theory · STEM) (14 slides)", "마케팅 캠페인·브랜드 (12장)": "Marketing campaign · brand (12 slides)", "사내 공지·온보딩 (10장)": "Internal notice · onboarding (10 slides)", "정기 업무 보고(주간·월간·QBR) (12장)": "Periodic report (weekly · monthly · QBR) (12 slides)", "공공·정책·연구 지원 (15장)": "Public · policy · research funding (15 slides)",
    "리서치·리뷰 보고서 (16장)": "Research · review report (16 slides)", "RFP 제안요청서 요약 - 발주자용 (12장)": "RFP summary - for issuers (12 slides)", "RFP 응답 제안서 - 응답자용 (14장)": "RFP response proposal - for bidders (14 slides)", "B2B 영업·제안서 (16장)": "B2B sales · proposal (16 slides)", "일정·로드맵 (7장)": "Schedule · roadmap (7 slides)", "프로젝트 회고·사례 이야기 (12장)": "Project retrospective · case story (12 slides)",
    "전략·연례 계획 (17장)": "Strategy · annual plan (17 slides)", "강연·이야기·포트폴리오 (11장)": "Talk · story · portfolio (11 slides)", "직무·자격 교육 (15장)": "Job · certification training (15 slides)",
    // ---- 템플릿 · 시작용 내용 (template.json · starter.json 의 label · description — 키는 원문 그대로)
    "사례집·회고·여행·실기 교육·이야기. 오래된 종이 같은 미색 바탕, 테라코타 강조, 명조 제목, 사진 도판(템플릿 검토 승인 gs-tpl-archive — 이전 story 대체).": "Case books · retrospectives · travel · hands-on training · stories. Old-paper ivory background, terracotta accent, serif titles, photo plates (approved in template review gs-tpl-archive — replaces the former story).",
    "기술·제조·인프라·설계 검토. 도면 미색 바탕, 청록 주색과 주황 보조, 각진 모서리(템플릿 검토 승인 gs-tpl-blueprint).": "Technology · manufacturing · infrastructure · design reviews. Drawing-ivory background, teal primary with orange secondary, square corners (approved in template review gs-tpl-blueprint).",
    "1~2장 요약·경영진 결정 요청용. 차콜 바탕 글자에 딥 틸 강조 한 색, 결론 배너와 결정 띠가 눈에 먼저 들어오게.": "1–2 slide summaries and executive decision requests. Charcoal text with a single deep-teal accent, so the conclusion banner and decision strip are seen first.",
    "리서치·케이스·보고서·제안 논지. 미색 바탕, 짙은 남색 글자, 진홍 강조 하나, 명조 제목, 고정폭 라벨, 검정 결론 띠(템플릿 검토 추천 gs-tpl-editorial).": "Research · cases · reports · proposal arguments. Ivory background, dark navy text, one crimson accent, serif titles, monospace labels, black conclusion strip (recommended in template review gs-tpl-editorial).",
    "ESG·연례 보고·워크숍·비영리. 크림 바탕, 숲녹색 주색, 테라코타 보조, 명조 제목, 큰 장식 쪽 번호(템플릿 검토 추천 gs-tpl-forest).": "ESG · annual reports · workshops · non-profits. Cream background, forest-green primary, terracotta secondary, serif titles, large decorative page numbers (recommended in template review gs-tpl-forest).",
    "사내 정리 문서·디자인 시스템·내부 보고. 흰 바탕, 검정 글자, 강조색 없이 회색 단계와 검정 굵기만, 가는 회색 선 구획, 큰 검정 숫자, 모서리 없음(템플릿 검토 승인 참고 덱 101 minimalist-content-cleanup-deck).": "Internal summaries · design systems · internal reports. White background, black text, no accent color — only gray steps and black weights, thin gray dividers, large black numbers, no corners (approved in template review, reference deck 101 minimalist-content-cleanup-deck).",
    "강연·키노트·브랜드·이벤트 제안. 어두운 바탕, 금색 강조 하나, 명조 제목. 한 장 한 문장·전면 사진·큰 숫자가 주인공(템플릿 검토 승인 gs-tpl-keynote).": "Talks · keynotes · brand · event proposals. Dark background, one gold accent, serif titles. One sentence per slide, full-bleed photos and big numbers take the stage (approved in template review gs-tpl-keynote).",
    "lecture 와 같은 색·글꼴·배치에서 빌드할 때 글자를 역할별 최소 크기로 일괄 확대한다(본문 15px · 각주 11px · 경로·쪽번호 12px). 상자 크기는 그대로라 촘촘한 도식(시퀀스 등)은 넘칠 수 있다 — 검사 탭으로 확인할 것.": "Same colors, fonts and layout as lecture, but text is scaled up to per-role minimum sizes at build time (body 15px · footnotes 11px · path/page number 12px). Box sizes stay the same, so dense diagrams (sequences etc.) may overflow — check with the Check tab.",
    "강의·교재용 16:9 레이아웃 21종(기존 디자인 그대로). 글자 크기는 레이아웃에 정한 값을 쓰고, 레이아웃 검사는 본문 11pt · 각주 8pt · 경로·쪽번호 9pt 기준으로 알린다 — 크기 조정은 장 단위 검토에서 슬라이드별로 한다.": "21 16:9 layouts for lectures and course books (existing design as is). Text sizes come from each layout, and the layout check warns against body 11pt · footnotes 8pt · path/page number 9pt — adjust sizes slide by slide in chapter reviews.",
    "IR·재무·이사회·공공 보고. 크림 바탕, 남색 면과 글자, 금색 보조, 명조 제목, 모서리 없음 — 원장풍 가는 선 표(템플릿 검토 추천 gs-tpl-ledger).": "IR · finance · board · public reporting. Cream background, navy panels and text, gold secondary, serif titles, no corners — ledger-style thin-rule tables (recommended in template review gs-tpl-ledger).",
    "사내 공지·환영·온보딩용 캐주얼 톤. 오렌지 강조 + 틸·바이올렛·그린 보조, 둥근 모서리를 크게. 카드·사진·큰 숫자 중심.": "Casual tone for internal notices, welcomes and onboarding. Orange accent + teal · violet · green secondaries, large rounded corners. Cards, photos and big numbers first.",
    "발주자용 RFP 요약·응답자용 제안용 격식 톤. 인디고 기본 + 골드 보조, 표·준수 매트릭스·평가 기준이 주인공.": "Formal tone for client RFP summaries and bidder proposals. Indigo base + gold secondary; tables, compliance matrices and evaluation criteria take the stage.",
    "업무 보고 - 신뢰 네이비": "Status report - trusted navy",
    "주간·월간 진행 보고용. 네이비 한 색 + 상태색(신호등)으로 절제하고, 표·KPI 숫자가 주인공. 바탕은 차가운 회색 면.": "Weekly and monthly progress reports. Restrained with one navy + status colors (traffic lights); tables and KPI numbers take the stage. Cool gray background panels.",
    "간트·마일스톤·로드맵·시간표용. 단계마다 색이 갈리도록 블루·틸·바이올렛을 단계 색으로, 바탕은 옅은 회청색.": "Gantt charts, milestones, roadmaps and timetables. Blue · teal · violet as phase colors so each phase stands apart, on a pale blue-gray background.",
    "안전 교육·현장 교육·초중등 수업·모집 포스터. 흰 바탕, 노랑 강조와 검정 띠, 빨강 경고, 굵은 고딕, 모서리 없음 — 큰 숫자·단계 띠가 주인공(템플릿 검토 추천 gs-tpl-signal).": "Safety and field training · school classes · recruiting posters. White background, yellow accent with black bands, red warnings, bold sans-serif, no corners — big numbers and step bands take the stage (recommended in template review gs-tpl-signal).",
    "이야기·회고 - 따뜻한 미색": "Story · retrospective - warm ivory",
    "프로젝트 회고·고객 사례·연말 회고용. 미색 바탕, 테라코타 강조, 명조 제목(Noto Serif KR). 한 문장·인용·큰 숫자가 주인공.": "Project retrospectives, customer cases and year-end reviews. Ivory background, terracotta accent, serif titles (Noto Serif KR). One sentence, quotes and big numbers take the stage.",
    "데이터 보고·평가·주간/월간 보고·이공계 교안. 흰 바탕, 먹색 글자, 빨강 강조 하나, 모서리 없음(템플릿 검토 승인 gs-tpl-swiss — 이전 report 대체).": "Data reports · evaluations · weekly/monthly reports · STEM course material. White background, ink-black text, one red accent, no corners (approved in template review gs-tpl-swiss — replaces the former report).",
    "결정권자가 한 번에 판단 — 요약·숫자·리스크·결정 요청·부록. 기본 구성: 표지 — 제목형 → 요약 — 결론 먼저 → KPI 대시보드 → 막대 비교 → 선택지 비교(추천 강조) → 범위·민감도 → 리스크·이슈와 요청 → 결정 요청 → 다음 행동·부탁 → 예상 질문(부록) → 끝": "Lets decision makers judge in one pass — summary · numbers · risks · decision request · appendix. Default outline: Cover — title → Summary — conclusion first → KPI dashboard → Bar comparison → Option comparison (recommendation highlighted) → Range · sensitivity → Risks · issues and asks → Decision request → Next actions · asks → Anticipated questions (appendix) → End",
    "목표→사건→선택→결과를 잡지처럼 — 인용·증거·전후 숫자. 기본 구성: 표지 — 사진 전면 → 핵심 한 문장 → 인물·대상 소개(사진+글) → 인용 — 고객·현장의 말 → 마일스톤 → 사진 도판 → 전후 비교 → 숫자 + 근거 차트 → 큰 번호 단계·요점 → 어두운 전환 문장 → 정리 → 끝": "Goal → event → choice → result, magazine style — quotes · evidence · before/after numbers. Default outline: Cover — full-bleed photo → Key sentence → People · subject intro (photo + text) → Quote — voice of the customer/field → Milestones → Photo plate → Before/after → Numbers + evidence chart → Big numbered steps · points → Dark transition sentence → Wrap-up → End",
    "목표→훅→시범→함께→혼자→나가기, 발표는 질문→방법→결과. 기본 구성: 표지 — 제목형 → 질문으로 열기 → 진행 순서 → 개념 설명 → 구조도 → 단계별 풀이 → 확인 문제 → 사진 도판 → 장단점·대비 카드 → 정리 → 예상 질문(부록) → 끝": "Goal → hook → demo → together → alone → exit; presentations go question → method → result. Default outline: Cover — title → Open with a question → Agenda → Concept explanation → Structure diagram → Step-by-step solution → Check question → Photo plate → Pros/cons · contrast cards → Wrap-up → Anticipated questions (appendix) → End",
    "가설·이슈 트리·진단·권고 — 결론형 제목과 해석 패널. 기본 구성: 표지 — 제목형 → 요약 — 결론 먼저 → 진행 순서 → [진단] → 이슈·지표 트리 → 근거 + 해석 패널 → 히트맵·코호트 → 숫자 + 근거 차트 → [제언] → 사분면 우선순위 → 선택지 비교(추천 강조) → 장단점·대비 카드 → 로드맵 Now·Next·Later → 리스크·이슈와 요청 → 결정 요청 → 끝": "Hypotheses · issue trees · diagnosis · recommendations — conclusion-style titles and interpretation panels. Default outline: Cover — title → Summary — conclusion first → Agenda → [Diagnosis] → Issue · metric tree → Evidence + interpretation panel → Heatmap · cohort → Numbers + evidence chart → [Recommendations] → Quadrant priorities → Option comparison (recommendation highlighted) → Pros/cons · contrast cards → Roadmap Now · Next · Later → Risks · issues and asks → Decision request → End",
    "결정 요청 1~2장": "Decision request in 1–2 slides",
    "1장: 결론 배너·근거 3열·결정 띠(무엇을·누가·언제까지·안 하면). 2장: 대안 비교 표.": "Slide 1: conclusion banner · three evidence columns · decision strip (what · who · by when · if not). Slide 2: alternatives comparison table.",
    "문제→해결→시장→트랙션→팀→요청, 숫자 하나가 장마다. 기본 구성: 표지 — 제목형 → 질문으로 열기 → 숫자 하나 → 핵심 한 문장 → 전후 비교 → 깔때기·시장 규모 → 숫자 + 근거 차트 → 단계 흐름 → 팀·인물 카드 → 가격·패키지 → 로드맵 Now·Next·Later → 결정 요청 → 끝": "Problem → solution → market → traction → team → ask, one number per slide. Default outline: Cover — title → Open with a question → One number → Key sentence → Before/after → Funnel · market size → Numbers + evidence chart → Step flow → Team · people cards → Pricing · packages → Roadmap Now · Next · Later → Decision request → End",
    "실적·전망·밸류에이션을 원장풍으로 — 표·범위·요약 패널. 기본 구성: 표지 — 제목형 → 요약 — 결론 먼저 → KPI 대시보드 → 추이 — 선 그래프 → 표 → 구성비 → 구성비 — 도넛 → 범위·민감도 → 근거 + 해석 패널 → 리스크·이슈와 요청 → 예상 질문(부록) → 끝": "Results · outlook · valuation in ledger style — tables · ranges · summary panels. Default outline: Cover — title → Summary — conclusion first → KPI dashboard → Trend — line chart → Table → Composition → Composition — donut → Range · sensitivity → Evidence + interpretation panel → Risks · issues and asks → Anticipated questions (appendix) → End",
    "장·절·소분류·실습 번호 체계, 공통 표지·전체 목차·개정 이력·EoD, 필수/심화, 각주(근거)·노트(원문) 규약을 갖춘 강의 교안 뼈대. 내용은 자리 표시와 일반 예제(주문 관리)다.": "A lecture course skeleton with chapter · section · sub-topic · lab numbering, shared cover · full TOC · revision history · EoD, required/advanced, and footnote (evidence) · notes (source) conventions. Content is placeholders and a generic example (order management).",
    "직관→개념→풀이→한계→흔한 실수→과제. 기본 구성: 표지 — 제목형 → 진행 순서 → 질문으로 열기 → [개념] → 개념 설명 → 구조도 → 단계별 풀이 → [적용] → 코드 설명 → 실습 → 확인 문제 → 정리 → 참고문헌·출처 → 끝": "Intuition → concept → worked solution → limits → common mistakes → assignment. Default outline: Cover — title → Agenda → Open with a question → [Concepts] → Concept explanation → Structure diagram → Step-by-step solution → [Application] → Code walkthrough → Lab → Check question → Wrap-up → References · sources → End",
    "인사이트→전략→실행→성과, 사진·브랜드 톤. 기본 구성: 표지 — 사진 전면 → 핵심 한 문장 → 인용 — 고객·현장의 말 → 깔때기·시장 규모 → 사분면 우선순위 → 구성비 — 도넛 → 사진 도판 → 로드맵 Now·Next·Later → 간트 → KPI 대시보드 → 다음 행동·부탁 → 끝": "Insight → strategy → execution → results, with photos and brand tone. Default outline: Cover — full-bleed photo → Key sentence → Quote — voice of the customer/field → Funnel · market size → Quadrant priorities → Composition — donut → Photo plate → Roadmap Now · Next · Later → Gantt → KPI dashboard → Next actions · asks → End",
    "월간 운영 보고 (11장)": "Monthly operations report (11 slides)",
    "순서 → 결론 KPI → 추이 차트 → 목표 대비 → 잘된 것·미달 → 리스크 → 원인 워터폴 → 로드맵 → 결정 요청.": "Agenda → headline KPIs → trend chart → vs. target → what went well · shortfalls → risks → cause waterfall → roadmap → decision request.",
    "인사 → 숫자로 보는 팀 → 첫 주 할 일 3 → 일정 → 담당 표 → 일하는 방식 → 버디 한마디 → 시간표 → 부탁 3가지.": "Welcome → the team in numbers → three first-week tasks → schedule → owner table → how we work → a word from your buddy → timetable → three asks.",
    "매 회차 같은 배치 — 결론 KPI·추이·상태·이슈·다음 행동. 기본 구성: 표지 — 제목형 → 요약 — 결론 먼저 → KPI 대시보드 → 추이 — 선 그래프 → 막대 비교 → 구성비 → 상태 표(신호등) → 히트맵·코호트 → 리스크·이슈와 요청 → 마일스톤 → 다음 행동·부탁 → 끝": "Same layout every time — headline KPIs · trends · status · issues · next actions. Default outline: Cover — title → Summary — conclusion first → KPI dashboard → Trend — line chart → Bar comparison → Composition → Status table (traffic lights) → Heatmap · cohort → Risks · issues and asks → Milestones → Next actions · asks → End",
    "결론 먼저(BLUF)·대안 비교·근거·예산·요청. 기본 구성: 표지 — 제목형 → 요약 — 결론 먼저 → [현황과 근거] → 근거 + 해석 패널 → 추이 — 선 그래프 → 히트맵·코호트 → 깔때기·시장 규모 → [대안과 실행] → 선택지 비교(추천 강조) → 범위·민감도 → 간트 → 리스크·이슈와 요청 → 결정 요청 → 참고문헌·출처 → 끝": "Bottom line up front (BLUF) · alternatives · evidence · budget · ask. Default outline: Cover — title → Summary — conclusion first → [Situation and evidence] → Evidence + interpretation panel → Trend — line chart → Heatmap · cohort → Funnel · market size → [Alternatives and execution] → Option comparison (recommendation highlighted) → Range · sensitivity → Gantt → Risks · issues and asks → Decision request → References · sources → End",
    "조사·분석 결과를 논지로 전달 — 결론 먼저, 근거 패널, 참고문헌. 기본 구성: 표지 — 제목형 → 요약 — 결론 먼저 → 진행 순서 → [무엇을 봤나] → 근거 + 해석 패널 → 추이 — 선 그래프 → 히트맵·코호트 → 구성비 — 도넛 → [무엇을 뜻하나] → 사분면 우선순위 → 숫자 + 근거 차트 → 범위·민감도 → 리스크·이슈와 요청 → 정리 → 참고문헌·출처 → 끝": "Delivers research and analysis as an argument — conclusion first, evidence panels, references. Default outline: Cover — title → Summary — conclusion first → Agenda → [What we looked at] → Evidence + interpretation panel → Trend — line chart → Heatmap · cohort → Composition — donut → [What it means] → Quadrant priorities → Numbers + evidence chart → Range · sensitivity → Risks · issues and asks → Wrap-up → References · sources → End",
    "사업 한 문장 → 개요 2×2 → 기능·비기능 요구(조항 번호) → 범위 밖 → 평가 기준 → 제출 일정 → 제출물 → 제약 → 접수 방법.": "One-sentence project → 2×2 overview → functional · non-functional requirements (clause numbers) → out of scope → evaluation criteria → submission schedule → deliverables → constraints → how to submit.",
    "제안 요약(결정 요청형) → 준수 매트릭스 → 과제 → 접근 → 일정 → 팀 → 평가 기준별 강점 → 효과 → 리스크 → 범위 밖·가정 → 가격 → 약속.": "Proposal summary (decision-request style) → compliance matrix → challenges → approach → schedule → team → strengths per evaluation criterion → benefits → risks → out of scope · assumptions → price → commitments.",
    "고객 과제→해법→근거→가격·일정→약속, 평가자 채점표. 기본 구성: 표지 — 제목형 → 질문으로 열기 → 요약 — 결론 먼저 → 전후 비교 → [어떻게 푸나] → 단계 흐름 → 구조도 → 사례 제시 → 인용 — 고객·현장의 말 → 숫자 + 근거 차트 → [어떻게 시작하나] → 가격·패키지 → 간트 → 팀·인물 카드 → 결정 요청 → 끝": "Customer challenge → solution → evidence → price · schedule → commitment, with the evaluator's scorecard. Default outline: Cover — title → Open with a question → Summary — conclusion first → Before/after → [How we solve it] → Step flow → Structure diagram → Case → Quote — voice of the customer/field → Numbers + evidence chart → [How we start] → Pricing · packages → Gantt → Team · people cards → Decision request → End",
    "마일스톤 → 로드맵(Now·Next·Later) → 13주 간트 → 교육 3일 시간표 → 이번 달 일정표.": "Milestones → roadmap (Now · Next · Later) → 13-week Gantt → 3-day training timetable → this month's calendar.",
    "한 문장 축 → 큰 숫자 → 흐름 → 목소리 → 잘된 것 → 어려웠던 순간 → 바꾼 것 → 가져갈 것 → 처음 문장으로.": "One-sentence thread → big number → flow → voices → what went well → hardest moment → what we changed → what we keep → back to the first sentence.",
    "비전·전략·연간 계획을 한 흐름으로 — 목표·로드맵·투자. 기본 구성: 표지 — 사진 전면 → 핵심 한 문장 → 진행 순서 → [어디에 있나] → KPI 대시보드 → 추이 — 선 그래프 → 이슈·지표 트리 → [무엇을 고르나] → 선택지 비교(추천 강조) → 사분면 우선순위 → [어떻게 가나] → 로드맵 Now·Next·Later → 마일스톤 → 간트 → 리스크·이슈와 요청 → 다음 행동·부탁 → 끝": "Vision · strategy · annual plan in one flow — goals · roadmap · investment. Default outline: Cover — full-bleed photo → Key sentence → Agenda → [Where we are] → KPI dashboard → Trend — line chart → Issue · metric tree → [What we choose] → Option comparison (recommendation highlighted) → Quadrant priorities → [How we get there] → Roadmap Now · Next · Later → Milestones → Gantt → Risks · issues and asks → Next actions · asks → End",
    "한 장 한 문장·사진·큰 숫자의 리듬. 기본 구성: 표지 — 사진 전면 → 질문으로 열기 → 사진 + 한 문장 → 어두운 전환 문장 → 숫자 하나 → 인용 — 고객·현장의 말 → 마일스톤 → 사진 도판 → 핵심 한 문장 → 큰 번호 단계·요점 → 끝": "A rhythm of one sentence per slide · photos · big numbers. Default outline: Cover — full-bleed photo → Open with a question → Photo + one sentence → Dark transition sentence → One number → Quote — voice of the customer/field → Milestones → Photo plate → Key sentence → Big numbered steps · points → End",
    "현장 사례→규칙→실습→확인→휴대 카드. 기본 구성: 표지 — 제목형 → 진행 순서 → 사례 제시 → [알아야 할 것] → 개념 설명 → 단계 흐름 → 큰 번호 단계·요점 → 장단점·대비 카드 → [해 보기] → 실습 → 확인 문제 → 사례 판단(선택지) → 정리 → 다음 행동·부탁 → 끝": "Field case → rules → practice → check → pocket card. Default outline: Cover — title → Agenda → Case → [What to know] → Concept explanation → Step flow → Big numbered steps · points → Pros/cons · contrast cards → [Try it] → Lab → Check question → Case judgment (options) → Wrap-up → Next actions · asks → End",
    "주간 진행 보고 (8장)": "Weekly progress report (8 slides)",
    "결론 KPI → 약속 대비 채점 → 이슈·요청 → 간트 → 다음 주 약속 → 요청. 매주 복제해 숫자만 바꾸는 고정 배치.": "Headline KPIs → scoring against commitments → issues · asks → Gantt → next week's commitments → asks. A fixed layout you duplicate each week and only change the numbers.",
  };
  // 변수가 든 문구 - [정규식, 바꿀 글]. $1… 로 잡은 값을 넣는다
  const PATTERNS = [  // 앞에 있는 것이 먼저 - 구체적인 것을 일반적인 것보다 위에
    [/^슬라이드 (\d+) 전체에 대한 요청 - 예: (.*) \(Enter = 남기기, Shift\+Enter = 줄바꿈\)$/, "Request for all of slide $1 - e.g. split this table into two slides (Enter = save, Shift+Enter = newline)"],
    [/^이 슬라이드 \((\d+)\)$/, "This slide ($1)"], [/^전체 \((\d+)\)$/, "All ($1)"], [/^· (\d+)자$/, "· $1 chars"], [/^레이아웃 (\S+)$/, "layout $1"], [/^템플릿 (\S+)$/, "template $1"], [/^최소 (.+)$/, "min $1"], [/^덱 전체 (.*)$/, "Whole deck $1"],
    [/^\(작업 공간 - (.+)\)$/, "(workspace - $1)"], [/^\(덱 (\d+)개\)$/, "($1 decks)"], [/^요소 \((\d+)\) - 가려진 요소도 여기서 선택$/, "Elements ($1) - hidden elements can be selected here too"],
    [/^오늘 (\d\d:\d\d)$/, "today $1"], [/^만들 위치: (.*)$/, "Location: $1"], [/^복사 위치: (.*)$/, "Copy location: $1"], [/^(.+) · lecture 바탕$/, "$1 · based on lecture"], [/^(.+) · 템플릿 (\S+)$/, "$1 · template $2"],
    [/^슬라이드 (\d+)(.*)$/, "Slide $1$2"], [/^포트 (\d+)(.*)$/, "Port $1$2"], [/^덱 (\d+)$/, "$1 decks"], [/^요청 (\d+)개 보내기$/, "Send $1 requests"], [/^초안 (\d+)개 보내기$/, "Send $1 drafts"],
    [/^요청 (\d+)$/, "Requests $1"], [/^대기 (\d+)$/, "waiting $1"], [/^처리 중 (\d+)$/, "working $1"], [/^대기 요청 (\d+)$/, "$1 waiting"], [/^턴 (\d+)$/, "turn $1"], [/^턴 (\d+) 시작(.*)$/, "Turn $1 started$2"], [/^턴 (\d+) 끝(.*)$/, "Turn $1 ended$2"],
    [/^세션 처리 중 (\d+)$/, "Session working $1"], [/^요청 처리 중 (\d+)$/, "Working on $1 requests"], [/^웹 세션 처리 중 \(턴 (\d+)\)$/, "Web session working (turn $1)"], [/^웹 세션 처리 중\(턴 (\d+)\)$/, "Web session working (turn $1)"],
    [/^전체 \((\d+)\)$/, "All ($1)"], [/^(\d+) \/ 2000$/, "$1 / 2000"], [/^(\d+)분째$/, "$1 min"], [/^(\d+)분 전$/, "$1 min ago"], [/^(\d+)시간 전$/, "$1 h ago"], [/^(\d+)일 전$/, "$1 days ago"], [/^(\d+)초 전$/, "$1 s ago"],
    [/^레이아웃 검사 - ERROR (\d+) · WARNING (\d+)$/, "Layout check - ERROR $1 · WARNING $2"], [/^시작 페이지 · 포트 (\d+)(.*)$/, "Start page · port $1$2"], [/^작업 공간 서버 · 포트 (\d+)(.*)$/, "Workspace server · port $1$2"],
    [/^시작했습니다 - (.*)$/, "Started - $1"], [/^웹 세션 시작 - (.*)$/, "Web session started - $1"], [/^엔진 개발 세션 시작 - (.*)$/, "Engine session started - $1"], [/^엔진 요청 #(\d+) 을 넣었습니다$/, "Engine request #$1 added"],
    [/^모델을 (.+) 로 바꿨습니다$/, "Model changed to $1"], [/^턴이 끝난 뒤 (.+) 로 바뀝니다$/, "Changes to $1 after this turn"], [/^마지막 · (.*)$/, "last · $1"], [/^상태 (\w+)(.*)$/, "state $1$2"], [/^유형 바꾸기 - 슬라이드 (\d+)$/, "Change type - slide $1"],
    [/^이 세션에 (git 기록|push|저장소 루트 접근) 허용$/, (m, a) => "Allow " + ({ "git 기록": "git commits", push: "push", "저장소 루트 접근": "repo root access" })[a] + " in this session"],
    [/^덱 (\S+) 을 만들었습니다\(표지 1장\)$/, "Deck $1 created (1 cover slide)"], [/^(\S+) → (\S+) 으로 바꿨습니다$/, "Renamed $1 → $2"], [/^(\S+) 을 휴지통으로 옮겼습니다\((.*)\)$/, "Moved $1 to trash ($2)"],
    [/^덱 (\S+) 을 지울까요\? (.*)$/, "Delete deck $1? It moves to decks/.trash/ together with its requests, history, attachments and content."], [/^덱 관리 실패: (.*)$/, "Deck management failed: $1"],
    [/^이 요소 (\d+)개에 요청 메모(\(세션에 보냄\))?$/, "Request memo on these $1 elements$2"], [/^이 요소 (\d+)개에서 무엇을 바꿀까요\?$/, "What should change in these $1 elements?"], [/^요소 (\d+)개 \((.*)\)$/, "$1 elements ($2)"], [/^(\S+) 외 (\d+)$/, "$1 +$2"],
    [/^ID (\w+) · 턴 전$/, "ID $1 · no turn yet"],
    [/^덱 세트 (\S+)$/, "deck set $1"], [/^(작업 공간|템플릿) 세트 (\S+)$/, (m, a, b) => `${a === "작업 공간" ? "workspace" : "template"} set ${b}`], [/^이 브라우저에 없음: (.*) - 대체 글꼴로 보이는 중\(PPTX 는 받는 PC 의 글꼴\)$/, "Not on this browser: $1 - shown with a fallback font (PPTX uses the recipient's fonts)"],
    [/^지금은 터미널 세션 (.+)\(pid (\d+)\)이 맡고 있다 - (.*)$/, "A terminal session $1 (pid $2) holds the queue now - end its Monitor so another session or a web session can take over."], [/^지금은 웹 엔진 세션\((.*)\)이 맡고 있어 터미널 명령은 거절된다 - (.*)$/, "A web engine session ($1) holds the queue now, so the terminal command is refused - press [Stop session] above first, then run it."],
    [/^세션 ID (\w+) 복사$/, "Copy session ID $1"], [/^확인 명령을 복사했습니다 - (.*)$/, "Copied the command - $1"], [/^세션 ID 를 복사했습니다 - (.*)$/, "Copied the session ID - $1"],
    [/^승인 대기 엔진 요청 (\d+)건(.*)$/, "$1 engine requests awaiting approval$2"], [/^기본 메뉴 - 승인 대기 (\d+)건(.*)$/, "Main menu - $1 awaiting approval$2"], [/^승인 대기 (\d+)건$/, "$1 awaiting approval"],
    [/^처리 대기 (\d+)건 · 세션 꺼짐(.*)$/, "$1 waiting · session off$2"], [/^(.+) 님이 (.+) 에 시작을 요청(.*)$/, "$1 asked to start at $2$3"], [/^엔진 요청 #(\d+) 을 넣었습니다 — (.*)$/, "Engine request #$1 added — $2"],
    [/^엔진 개발 세션이 꺼져 있어 관리자가 시작해야 처리됩니다(.*)$/, "The engine session is off; an admin must start it before this is handled$1"],
    [/^세션이 꺼져 있어 대기 요청 (\d+)건이 처리되지 않습니다 - $/, "The session is off, so $1 waiting requests are not being handled - "], [/^(서버 재시작으로 세션 종료됨|유휴로 세션 종료됨|사용자가 세션 중지|오류로 세션 종료됨)\((.+)\)$/, (m, a, b) => EN[a] + "(" + b + ")"], [/^기록 - (.+)$/, "History - $1"], [/^변경 - (.+)$/, "Changes - $1"], [/^이 서버의 작업 공간 (.*)$/, "This server's workspace $1"], [/^작업 공간 ([A-Za-z]:\.+|\/.+)$/, "Workspace $1"], [/^(\d+)개$/, "$1"], [/^#(\d+) 를 거절할까요\?$/, "Reject #$1?"],
    [/^#(\d+) 의 커밋을 main 에 병합하고 서버를 재시작했나요\? 적용됨으로 표시합니다\.(\n병합 커밋\(main\) 해시:)?$/, (m, a, b) => `Did you merge #${a}'s commit into main and restart the server? It will be marked applied.${b ? "\nMerge commit (main) hash:" : ""}`],
  ];
  const KO_NAME = { ko: "한국어", en: "English" };

  let cur = "system";
  try { cur = localStorage.getItem(KEY) || "system"; } catch (e) { /* 저장소 없음 */ }
  const q = new URLSearchParams(location.search).get("lang");
  if (q && ["system", "ko", "en"].includes(q)) { cur = q; try { localStorage.setItem(KEY, q); } catch (e) { /* 무시 */ } }

  const sysLang = () => ((navigator.language || "ko").toLowerCase().startsWith("ko") ? "ko" : "en");
  const effective = () => (cur === "system" ? sysLang() : cur);

  function tr1(s) {  // 글 하나(앞뒤 공백 보존)
    if (effective() !== "en" || !s) return s;
    const m = /^(\s*)([\s\S]*?)(\s*)$/.exec(s), core = m[2];
    if (!core || !/[가-힣]/.test(core)) return s;
    let out = EN[core];
    if (out === undefined && core.includes(" · ")) {  // 조각마다(정확 일치·패턴) - 조각이 하나라도 바뀌면 그 결과
      const src = core.split(" · "), parts = src.map((p) => tr1(p)); if (parts.some((p, i) => p !== src[i])) out = parts.join(" · ");
    }
    if (out === undefined) for (const [re, rep] of PATTERNS) { if (re.test(core)) { out = core.replace(re, rep); break; } }
    if (out === undefined && core.endsWith(":")) { const b = EN[core.slice(0, -1)]; if (b) out = b + ":"; }
    return out === undefined ? s : m[1] + out + m[3];
  }
  const t = (s) => tr1(String(s == null ? "" : s));

  // ---------- DOM 적용 - 원문은 노드별로 기억해 두고 언어가 바뀌면 원문에서 다시 번역
  const ORIG = new WeakMap();
  const ATTRS = ["placeholder", "title", "aria-label"];
  const SKIP = new Set(["SCRIPT", "STYLE", "TEXTAREA", "CODE", "PRE", "KBD"]);
  function applyText(node) {
    if (!ORIG.has(node)) ORIG.set(node, node.nodeValue);
    const o = ORIG.get(node), v = tr1(o);
    if (node.nodeValue !== v) node.nodeValue = v;
  }
  function applyEl(el) {
    for (const a of ATTRS) {
      if (!el.hasAttribute(a)) continue;
      const key = "__i18n_" + a;
      if (!(key in el)) el[key] = el.getAttribute(a);
      const v = tr1(el[key]);
      if (el.getAttribute(a) !== v) el.setAttribute(a, v);
    }
    if (el.tagName === "INPUT" && (el.type === "button" || el.type === "submit") && el.value) {
      if (!("__i18n_value" in el)) el.__i18n_value = el.value;
      el.value = tr1(el.__i18n_value);
    }
  }
  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) { if (root.parentNode && !SKIP.has(root.parentNode.tagName)) applyText(root); return; }
    if (root.nodeType !== 1 && root.nodeType !== 11) return;
    if (root.nodeType === 1) { if (SKIP.has(root.tagName) && root.tagName !== "TEXTAREA") return; applyEl(root); if (root.tagName === "TEXTAREA") return; }
    for (const c of root.childNodes) walk(c);
  }
  let applying = false;
  function applyAll() {
    applying = true;
    try { walk(document.body); document.documentElement.lang = effective(); if (document.title) { const pre = (/^\(\d+\) /.exec(document.title) || [""])[0]; if (!document.__i18n_title) document.__i18n_title = document.title.slice(pre.length); document.title = pre + tr1(document.__i18n_title); } }
    finally { applying = false; }
  }
  // 변경 기록은 비동기로 오므로 "우리가 바꾼 것"은 값이 번역 결과와 같은지로 가려낸다(원문을 영어로 덮어쓰지 않게)
  const mo = new MutationObserver((recs) => {
    applying = true;
    try {
      for (const r of recs) {
        if (r.type === "characterData") {
          const n = r.target, o = ORIG.get(n);
          if (o !== undefined && n.nodeValue === tr1(o)) continue;
          ORIG.delete(n); if (n.parentNode && !SKIP.has(n.parentNode.tagName)) applyText(n);
        } else if (r.type === "attributes") {
          const el = r.target, key = "__i18n_" + r.attributeName;
          if (key in el && el.getAttribute(r.attributeName) === tr1(el[key])) continue;
          delete el[key]; applyEl(el);
        } else for (const n of r.addedNodes) walk(n);
      }
    } finally { applying = false; }
  });
  function start() {
    applyAll();
    mo.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS });
  }
  if (document.body) start(); else document.addEventListener("DOMContentLoaded", start);

  // confirm·prompt·alert 글도 번역(화면 코드는 그대로)
  const _confirm = window.confirm.bind(window), _prompt = window.prompt.bind(window), _alert = window.alert.bind(window);
  window.confirm = (m) => _confirm(t(m));
  window.prompt = (m, d) => _prompt(t(m), d);
  window.alert = (m) => _alert(t(m));

  function set(lang) {
    if (!["system", "ko", "en"].includes(lang)) return;
    cur = lang;
    try { localStorage.setItem(KEY, lang); } catch (e) { /* 무시 */ }
    applyAll();
    document.dispatchEvent(new CustomEvent("nexa-lang", { detail: { lang, effective: effective() } }));
  }
  const options = () => [{ value: "system", label: `System (${KO_NAME[sysLang()]})` }, { value: "en", label: "English" }, { value: "ko", label: "한국어" }];
  window.I18N = { t, set, lang: () => cur, effective, options, apply: applyAll, dict: EN };
})();
