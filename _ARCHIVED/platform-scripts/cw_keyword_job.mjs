import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 120000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const pageTab = tabs.find(t => t.type === "page");

  const ws = new WebSocket(pageTab.webSocketDebuggerUrl);
  ws.addEventListener("error", () => { L("WS error"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); });

  ws.addEventListener("open", () => {
    let id = 0;
    const pending = new Map();
    ws.addEventListener("message", e => {
      const m = JSON.parse(e.data);
      if (m.id && pending.has(m.id)) {
        const p = pending.get(m.id);
        pending.delete(m.id);
        if (m.error) p.rej(new Error(m.error.message));
        else p.res(m.result);
      }
    });
    const send = (method, params = {}) => new Promise((res, rej) => {
      const i = ++id;
      pending.set(i, { res, rej });
      ws.send(JSON.stringify({ id: i, method, params }));
    });
    const eval_ = async (expr) => {
      const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result?.value;
    };

    (async () => {
      // Navigate to the keyword search job
      // Job ID 1262113 = "Search for a given keyword and report inaccurate suggestion!"
      await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs/1262113/edit" });
      await sleep(8000);

      let url = await eval_(`window.location.href`);
      L("URL: " + url);
      let pageText = await eval_(`document.body.innerText.substring(0, 5000)`);
      L("Page:");
      L(pageText.substring(0, 4000));

      // Get all interactive elements
      let r = await eval_(`
        (function() {
          var result = { radios: [], inputs: [], selects: [], buttons: [], textareas: [], iframes: [] };
          document.querySelectorAll('input[type="radio"]').forEach(function(r) {
            var label = (r.labels?.[0]?.textContent||'').trim();
            result.radios.push({ id: r.id, name: r.name, value: r.value, label: label.substring(0,80) });
          });
          document.querySelectorAll('input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]):not([type="submit"])').forEach(function(i) {
            if (i.offsetParent) result.inputs.push({ type: i.type, id: i.id, name: i.name, value: (i.value||'').substring(0,40), placeholder: (i.placeholder||'').substring(0,60) });
          });
          document.querySelectorAll('select').forEach(function(s) {
            if (s.offsetParent) result.selects.push({ id: s.id, name: s.name, options: Array.from(s.options).slice(0,10).map(o => o.text + '=' + o.value) });
          });
          document.querySelectorAll('button, input[type="submit"]').forEach(function(b) {
            if (b.offsetWidth > 0) result.buttons.push({ text: (b.textContent||b.value||'').trim().substring(0,60), type: b.type, value: (b.value||'').substring(0,40) });
          });
          document.querySelectorAll('textarea').forEach(function(t) {
            if (t.offsetParent) result.textareas.push({ id: t.id, name: t.name });
          });
          document.querySelectorAll('iframe').forEach(function(f) {
            result.iframes.push({ src: (f.src||'').substring(0,300), id: f.id });
          });
          return JSON.stringify(result);
        })()
      `);
      L("Elements: " + r);

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_keyword.png', Buffer.from(ss.data, 'base64'));
      L("Screenshot saved");

      ws.close();
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
      process.exit(0);
    })().catch(e => {
      L("Error: " + e.message);
      ws.close();
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
      process.exit(1);
    });
  });
})().catch(e => {
  L("Fatal: " + e.message);
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
});
