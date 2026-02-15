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
      // Click Accept & Continue
      let r = await eval_(`
        (function() {
          var buttons = document.querySelectorAll('button');
          for (var i = 0; i < buttons.length; i++) {
            if (buttons[i].textContent.trim().includes('Accept')) {
              buttons[i].click();
              return 'clicked Accept & Continue';
            }
          }
          return 'Accept button not found';
        })()
      `);
      L("Accept: " + r);
      await sleep(3000);

      // Now get the survey list
      let pageText = await eval_(`document.body.innerText.substring(0, 4000)`);
      L("PAGE after accept:");
      L(pageText.substring(0, 2000));

      // Find survey cards/links - they should be clickable elements with USD amounts
      r = await eval_(`
        (function() {
          var elements = document.querySelectorAll('*');
          var surveys = [];
          for (var i = 0; i < elements.length; i++) {
            var el = elements[i];
            var text = el.textContent.trim();
            // Look for survey cards - elements that contain USD and minutes and are clickable
            if (text.includes('USD') && text.includes('minutes') && text.length < 50 && el.offsetParent !== null) {
              var rect = el.getBoundingClientRect();
              if (rect.width > 50 && rect.height > 30) {
                surveys.push({
                  text: text,
                  tag: el.tagName,
                  class: (el.className || '').substring(0, 80),
                  x: Math.round(rect.x + rect.width/2),
                  y: Math.round(rect.y + rect.height/2),
                  w: Math.round(rect.width),
                  h: Math.round(rect.height)
                });
              }
            }
          }
          return JSON.stringify(surveys.slice(0, 15));
        })()
      `);
      L("Survey cards: " + r);

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
