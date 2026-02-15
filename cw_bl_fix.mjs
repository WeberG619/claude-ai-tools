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
  const surveyTab = tabs.find(t => t.type === "page" && t.url.includes('samplicio'));
  if (!surveyTab) { L("No survey tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(surveyTab.webSocketDebuggerUrl);
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

    const cdpClick = async (x, y) => {
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      await sleep(100);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      // First: find ALL clickable elements on the page
      L("=== FINDING ALL BUTTONS/LINKS ===");
      let allBtns = await eval_(`
        (function() {
          var results = [];
          // Check everything that could be a button
          var all = document.querySelectorAll('*');
          for (var i = 0; i < all.length; i++) {
            var el = all[i];
            var style = window.getComputedStyle(el);
            var t = el.textContent.trim();
            var tag = el.tagName;
            // Look for buttons, links, or clickable-looking elements
            if ((tag === 'BUTTON' || tag === 'A' || tag === 'INPUT' ||
                 el.getAttribute('role') === 'button' ||
                 style.cursor === 'pointer') &&
                t.length > 0 && t.length < 50 && el.children.length < 3) {
              var rect = el.getBoundingClientRect();
              if (rect.width > 0 && rect.height > 0) {
                results.push({
                  tag: tag,
                  text: t.substring(0, 40),
                  type: el.type || '',
                  href: (el.href || '').substring(0, 60),
                  x: Math.round(rect.x + rect.width/2),
                  y: Math.round(rect.y + rect.height/2),
                  w: Math.round(rect.width),
                  h: Math.round(rect.height),
                  classes: (el.className || '').substring(0, 60),
                  cursor: style.cursor
                });
              }
            }
          }
          return JSON.stringify(results);
        })()
      `);
      L("Clickable elements:");
      try {
        let parsed = JSON.parse(allBtns);
        parsed.forEach(b => L("  " + b.tag + " '" + b.text + "' at (" + b.x + "," + b.y + ") " + b.w + "x" + b.h + " cursor=" + b.cursor + " classes=" + b.classes));
      } catch(e) { L(allBtns.substring(0, 500)); }

      // Also check for the specific Continue/arrow button
      let continueBtn = await eval_(`
        (function() {
          // Search by innerHTML for arrow character
          var all = document.querySelectorAll('*');
          for (var i = 0; i < all.length; i++) {
            var html = all[i].innerHTML;
            var text = all[i].textContent.trim();
            if ((text.includes('Continue') || text.includes('→') || html.includes('rarr') || html.includes('arrow') || html.includes('&#')) &&
                all[i].children.length < 3 && text.length < 30 && text.length > 2) {
              var rect = all[i].getBoundingClientRect();
              if (rect.width > 30 && rect.height > 15) {
                return JSON.stringify({
                  tag: all[i].tagName,
                  text: text,
                  html: html.substring(0, 100),
                  x: Math.round(rect.x + rect.width/2),
                  y: Math.round(rect.y + rect.height/2),
                  classes: (all[i].className || '').substring(0, 80)
                });
              }
            }
          }
          return 'not found';
        })()
      `);
      L("\nContinue button search: " + continueBtn);

      // If found, click it
      if (continueBtn !== 'not found') {
        let cb = JSON.parse(continueBtn);
        L("Clicking Continue at (" + cb.x + ", " + cb.y + ")");
        await cdpClick(cb.x, cb.y);
        await sleep(5000);

        // Check new page
        let newUrl = await eval_(`window.location.href`);
        let newPage = await eval_(`document.body.innerText.substring(0, 2000)`);
        L("\nNew URL: " + newUrl);
        L("New page:\n" + newPage.substring(0, 1500));

        // Screenshot
        const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_survey.png', Buffer.from(ss.data, 'base64'));
      } else {
        L("Continue button still not found. Trying form submit...");
        await eval_(`
          (function() {
            var forms = document.querySelectorAll('form');
            for (var i = 0; i < forms.length; i++) {
              forms[i].submit();
              return 'submitted form ' + i;
            }
            return 'no forms';
          })()
        `);
        await sleep(5000);

        let newPage = await eval_(`document.body.innerText.substring(0, 1000)`);
        L("After form submit:\n" + newPage.substring(0, 500));
      }

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
