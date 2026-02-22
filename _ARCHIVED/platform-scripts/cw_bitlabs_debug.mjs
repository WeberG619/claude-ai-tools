import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 30000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page");

  const ws = new WebSocket(tab.webSocketDebuggerUrl);
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
      // Get the detailed HTML structure around the English checkbox
      let r = await eval_(`
        (function() {
          var cb = document.getElementById('v-0');
          if (!cb) return 'not found';
          // Get parent elements up to 3 levels
          var p1 = cb.parentElement;
          var p2 = p1 ? p1.parentElement : null;
          var p3 = p2 ? p2.parentElement : null;

          var result = 'Input: ' + cb.outerHTML + '\\n';
          if (p1) result += 'Parent1 (' + p1.tagName + '.' + p1.className.substring(0,60) + '): ' + p1.outerHTML.substring(0, 500) + '\\n';
          if (p2) result += 'Parent2 (' + p2.tagName + '.' + p2.className.substring(0,60) + '): tag only\\n';

          // Check computed style
          var style = window.getComputedStyle(cb);
          result += 'Display: ' + style.display + ', Visibility: ' + style.visibility + ', Opacity: ' + style.opacity + ', Position: ' + style.position + '\\n';

          // Check size
          var rect = cb.getBoundingClientRect();
          result += 'Rect: ' + rect.width + 'x' + rect.height + ' at ' + rect.x + ',' + rect.y;

          return result;
        })()
      `);
      L("Checkbox HTML: " + r);

      // Also take a screenshot to see what's visible
      const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_bitlabs_screen.png', Buffer.from(screenshot.data, 'base64'));
      L("Screenshot saved");

      // Look for any visual checkbox/toggle elements near the "English" text
      r = await eval_(`
        (function() {
          // Find the "English" text element
          var allElements = document.querySelectorAll('*');
          var englishEls = [];
          for (var i = 0; i < allElements.length; i++) {
            var el = allElements[i];
            if (el.childNodes.length <= 3 && el.textContent.trim() === 'English' && el.offsetParent !== null) {
              var rect = el.getBoundingClientRect();
              englishEls.push({
                tag: el.tagName,
                class: (el.className || '').substring(0, 80),
                x: Math.round(rect.x),
                y: Math.round(rect.y),
                w: Math.round(rect.width),
                h: Math.round(rect.height),
                parent: el.parentElement ? el.parentElement.tagName + '.' + (el.parentElement.className || '').substring(0, 60) : 'none'
              });
            }
          }
          return JSON.stringify(englishEls);
        })()
      `);
      L("English text elements: " + r);

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
