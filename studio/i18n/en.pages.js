/* nexa-slide 영어 표시 사전 - 글꼴 페이지·글꼴 창·계정·로그인·발표자·인쇄 페이지에서 en.js 에 없던 글(협업 세션 담당, docs/dev/i18n.md 4절). 형식은 en.js 머리 주석과 같다. */
(function () {
  const L = (window.NEXA_LOCALES = window.NEXA_LOCALES || {});
  const en = (L.en = L.en || { name: "English", dict: {}, patterns: [] });
  Object.assign(en.dict, {
    "기본 세트(default·modern)는 엔진 템플릿에 있고, 회사 서체 같은 전용 글꼴은 이 작업 공간이": "Default sets (default · modern) are in the engine templates; dedicated fonts such as a company typeface are managed in this workspace's",
    "폴더로 관리합니다.\n        글꼴은 되도록 무료 글꼴로 -": "folder.\n        Prefer free fonts where possible -",
    "(쓰는 글꼴이 무료·시스템 기본·전용 중 무엇인지 확인)": "(check whether each font in use is free, a system default or dedicated)",
    "fonts/ 에 글꼴 파일이 없습니다. 전용 글꼴은 이 폴더에 .ttf·.otf 로 둡니다.": "No font files in fonts/. Put dedicated fonts in this folder as .ttf · .otf.",
    "(화면 글꼴 목록) ·": "(screen font stack) ·",
    "(PPTX 글꼴 이름 - 영문·한글) ·": "(PPTX font names - Latin · Korean) ·",
    "(검사용 파일, fonts/ 또는 설치 폴더에서 찾음). 빠진 역할은 기본값.": "(files for checks, looked up in fonts/ or the install folder). Missing roles use the default.",
    "와": "and"
  });
  en.patterns.push(
    [/^측정 (.+\.(?:ttf|otf|ttc)(?: · .+)?)$/, "measured $1"],
  );
  // ---- 보기 전용 공유 링크(engine-request #2): 보기 페이지 view.html · 계정 페이지의 공유 링크 카드
  Object.assign(en.dict, {
    "슬라이드 보기": "Slides", "비밀번호가 필요한 공유 링크": "This shared link needs a password", "이 슬라이드를 보려면 보낸 사람에게 받은 비밀번호를 넣어 주세요.": "Enter the password you received from the sender to view these slides.",
    "이 링크는 열 수 없습니다": "This link cannot be opened", "실패가 잦아 잠시 잠겼습니다 - 몇 분 뒤에 다시": "Too many failed attempts - try again in a few minutes", "비밀번호가 맞지 않습니다": "Wrong password",
    "슬라이드를 읽지 못했습니다": "Could not load the slides", "보여 줄 슬라이드가 없습니다": "No slides to show", "← → 넘기기": "← → navigate", "F 전체 화면": "F fullscreen",
    "이전 (←)": "Previous (←)", "다음 (→)": "Next (→)", "전체 화면 (F)": "Fullscreen (F)",
    "공유 링크": "Shared links", "내가 만든 것": "mine", "로그인 없이 덱 하나를 보기만 하는 토큰 주소입니다 - Studio 의 내보내기 ▾ \"공유 링크…\" 에서 만듭니다. 주소는 만들 때만 보이고 여기서는 볼 수 없습니다. 회수하면 그 주소는 바로 열리지 않습니다.":
      "Token URLs that show one deck read-only without login - create them in Studio under Export ▾ \"Share link…\". The URL is shown only when created and cannot be seen here. Revoking makes it stop working at once.",
    "작업 공간 / 덱": "Workspace / deck",
  });
})();
