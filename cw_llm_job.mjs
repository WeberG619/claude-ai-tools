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
  // Close non-TapResearch tabs
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  for (const t of tabs) {
    if (t.type === "page" && !t.url.includes('tapresearch') && !t.url.includes('clickworker')) {
      try {
        const tempWs = new WebSocket(t.webSocketDebuggerUrl);
        await new Promise(resolve => {
          tempWs.addEventListener("open", () => {
            tempWs.send(JSON.stringify({ id: 1, method: "Page.close" }));
            setTimeout(resolve, 500);
          });
          tempWs.addEventListener("error", resolve);
        });
      } catch(e) {}
    }
  }
  await sleep(1000);

  // Get a page tab to navigate
  const tabs2 = await (await fetch(`${CDP_HTTP}/json`)).json();
  const pageTab = tabs2.find(t => t.type === "page");
  if (!pageTab) { L("No page tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

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
      // Navigate to the LLM survey job
      L("Navigating to LLM survey job (1262195)...");
      await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs/1262195/edit" });
      await sleep(8000);

      let url = await eval_(`window.location.href`);
      L("URL: " + url);
      let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("Page:");
      L(pageText.substring(0, 2000));

      // Get all interactive elements
      let r = await eval_(`
        (function() {
          var result = { buttons: [], inputs: [], links: [], iframes: [] };
          document.querySelectorAll('button, input[type="submit"]').forEach(function(b) {
            if (b.offsetWidth > 0) result.buttons.push({ text: b.textContent.trim().substring(0,60), type: b.type, value: (b.value||'').substring(0,40) });
          });
          document.querySelectorAll('input:not([type="hidden"])').forEach(function(i) {
            if (i.offsetParent) result.inputs.push({ type: i.type, id: i.id, name: i.name, value: (i.value||'').substring(0,40) });
          });
          document.querySelectorAll('a').forEach(function(a) {
            if (a.offsetWidth > 0) result.links.push({ text: a.textContent.trim().substring(0,60), href: (a.href||'').substring(0,200) });
          });
          document.querySelectorAll('iframe').forEach(function(f) {
            result.iframes.push({ src: (f.src||'').substring(0,300), id: f.id });
          });
          return JSON.stringify(result);
        })()
      `);
      L("Elements: " + r);

      // Handle agreements/start buttons
      r = await eval_(`
        (function() {
          var btns = document.querySelectorAll('input[type="submit"], button');
          for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].value || btns[i].textContent || '').trim();
            if (t === 'Agree' || t.includes('Start') || t.includes('Accept') || t === 'OK' || t.includes('Begin')) {
              btns[i].click();
              return 'clicked: ' + t;
            }
          }
          return 'no start button';
        })()
      `);
      L("Start: " + r);

      if (r !== 'no start button') {
        await sleep(6000);
        url = await eval_(`window.location.href`);
        L("After start URL: " + url);
        pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
        L("After start page:");
        L(pageText.substring(0, 2000));

        // Check for iframes
        r = await eval_(`
          (function() {
            var iframes = document.querySelectorAll('iframe');
            return JSON.stringify(Array.from(iframes).map(function(f) {
              return { src: (f.src||'').substring(0,300), id: f.id, w: f.offsetWidth, h: f.offsetHeight };
            }));
          })()
        `);
        L("Iframes: " + r);
      }

      // Also check the jobs list to see what's available
      L("\n=== CHECKING JOBS LIST ===");
      await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs" });
      await sleep(6000);

      pageText = await eval_(`document.body.innerText.substring(0, 5000)`);
      L("Jobs page:");
      L(pageText.substring(0, 3000));

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_llm_job.png', Buffer.from(ss.data, 'base64'));
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
