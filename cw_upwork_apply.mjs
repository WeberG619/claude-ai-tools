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
      if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); if (m.error) p.rej(new Error(m.error.message)); else p.res(m.result); }
    });
    const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
    const eval_ = async (expr) => { const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result?.value; };

    (async () => {
      // Find the apply/proposal button by scrolling and checking all elements
      L("=== FINDING APPLY BUTTON ===");

      // Scroll down to find the button
      await eval_(`window.scrollTo(0, 500)`);
      await sleep(1000);

      let r = await eval_(`
        (function() {
          var results = [];
          document.querySelectorAll('a, button, [role="button"], [role="link"]').forEach(function(el) {
            var t = el.textContent.trim();
            if (t.length > 0 && t.length < 60) {
              results.push({ text: t, tag: el.tagName, href: (el.href||'').substring(0,100), classes: (el.className||'').substring(0,60) });
            }
          });
          return JSON.stringify(results);
        })()
      `);
      L("All clickable elements:\n" + r);

      // Try looking for the proposal button specifically
      r = await eval_(`
        (function() {
          // Common Upwork patterns
          var selectors = [
            'a[href*="apply"]',
            'a[href*="proposal"]',
            'button[data-test="apply"]',
            '[data-qa="btn-submit-proposal"]',
            '[data-test="submit-proposal"]',
            'a.up-btn-primary',
            'button.up-btn-primary'
          ];
          for (var s = 0; s < selectors.length; s++) {
            var el = document.querySelector(selectors[s]);
            if (el) return 'Found: ' + selectors[s] + ' -> ' + el.textContent.trim() + ' | ' + (el.href||'');
          }
          return 'none found with known selectors';
        })()
      `);
      L("\nKnown selectors: " + r);

      // Get the full page HTML structure around "apply"
      r = await eval_(`
        (function() {
          var html = document.body.innerHTML;
          var idx = html.toLowerCase().indexOf('apply');
          if (idx === -1) {
            idx = html.toLowerCase().indexOf('proposal');
          }
          if (idx === -1) return 'no apply/proposal found in HTML';
          return html.substring(Math.max(0, idx-200), idx+200);
        })()
      `);
      L("\nHTML around apply: " + r);

      // Scroll to bottom
      await eval_(`window.scrollTo(0, document.body.scrollHeight)`);
      await sleep(1000);

      // Check bottom of page
      r = await eval_(`
        (function() {
          var btns = [];
          document.querySelectorAll('a, button').forEach(function(el) {
            var t = el.textContent.trim().toLowerCase();
            if (t.includes('apply') || t.includes('proposal') || t.includes('submit') || t.includes('bid')) {
              var rect = el.getBoundingClientRect();
              btns.push({ text: el.textContent.trim(), visible: rect.height > 0, y: rect.y, href: (el.href||'').substring(0,100) });
            }
          });
          return JSON.stringify(btns);
        })()
      `);
      L("\nApply/proposal buttons: " + r);

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_upwork_apply.png', Buffer.from(ss.data, 'base64'));

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
