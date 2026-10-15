// 헤드리스 Chrome 클릭 스모크 - CDP(원격 디버깅)로 페이지를 열고 단계(JS 식)를 차례로 실행하며 콘솔 오류·예외를 모은다.
//   node smoke.js <시나리오.json>   시나리오 = {base, login?: {id, password}, pages: [{url, steps: [{name, js, wait?}]}]}
//   js 는 페이지 안에서 평가되는 식(await 가능) - 결과가 false 면 FAIL. 콘솔 error/예외가 하나라도 있으면 그 페이지 FAIL.
const fs = require("fs"), { spawn } = require("child_process");
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe", PORT = 9333;
const sc = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let fails = 0;

async function main() {
  const prof = fs.mkdtempSync(require("path").join(require("os").tmpdir(), "nx-smoke-"));
  const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--no-sandbox", `--remote-debugging-port=${PORT}`, `--user-data-dir=${prof}`, "--window-size=1400,1000", "about:blank"], { stdio: "ignore" });
  try {
    let targets;
    let t;
    for (let i = 0; i < 100 && !t; i++) { try { targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json(); t = (targets || []).find((x) => x.type === "page"); } catch (e) { /* 아직 안 떴다 */ } if (!t) await sleep(200); }
    if (!t) throw new Error("Chrome 디버그 포트에서 페이지를 찾지 못했다");
    const ws = new WebSocket(t.webSocketDebuggerUrl);
    await new Promise((r) => (ws.onopen = r));
    let id = 0; const pending = {}; const errors = [];
    ws.onmessage = (m) => {
      const d = JSON.parse(m.data);
      if (d.id && pending[d.id]) { pending[d.id](d); delete pending[d.id]; return; }
      if (d.method === "Runtime.consoleAPICalled" && (d.params.type === "error")) errors.push("console.error: " + d.params.args.map((a) => a.value || a.description || "").join(" "));
      if (d.method === "Runtime.exceptionThrown") errors.push("exception: " + (d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text));
      if (d.method === "Log.entryAdded" && d.params.entry.level === "error" && !/favicon|net::ERR_ABORTED|api\/engine\/notice|api\/image/.test(d.params.entry.text + " " + (d.params.entry.url || ""))) errors.push("log: " + d.params.entry.text + " " + (d.params.entry.url || ""));
    };
    const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
    const evalJs = async (js) => {
      const r = await send("Runtime.evaluate", { expression: `(async () => { ${js.includes("return") ? js : "return (" + js + ")"} })()`, awaitPromise: true, returnByValue: true });
      if (r.result.exceptionDetails) throw new Error(r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text);
      return r.result.result.value;
    };
    await send("Runtime.enable"); await send("Log.enable"); await send("Page.enable");
    const nav = async (url) => { await send("Page.navigate", { url }); await sleep(1500); };
    if (sc.login) {
      await nav(sc.base + "/login");
      const ok = await evalJs(`(await fetch("/api/auth/login", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(${JSON.stringify(sc.login)})})).ok`);
      console.log(ok ? "로그인 OK" : "로그인 FAIL"); if (!ok) fails++;
    }
    for (const p of sc.pages) {
      errors.length = 0;
      await nav(sc.base + p.url); await sleep(p.wait || 1500);
      console.log(`\n== ${p.url}`);
      for (const s of p.steps || []) {
        let v, err = null;
        try { v = await evalJs(s.js); } catch (e) { err = e.message; }
        if (s.wait) await sleep(s.wait);
        const ok = !err && v !== false;
        if (!ok) fails++;
        console.log(`${ok ? "OK  " : "FAIL"} ${s.name}${err ? " - " + err : v === false ? "" : typeof v === "string" && (s.dump || v.length < 200) ? " → " + v : ""}`);
      }
      await sleep(500);
      if (errors.length) { fails++; console.log("FAIL 콘솔 오류:", errors.slice(0, 8)); } else console.log("OK   콘솔 오류 없음");
    }
    ws.close();
  } finally { chrome.kill(); }
  console.log(fails ? `\n실패 ${fails}` : "\n전부 통과");
  process.exit(fails ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
