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
})();
