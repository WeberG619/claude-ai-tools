import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 40000);

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
      // Click on the first $2.88 survey card
      let r = await eval_(`
        (function() {
          var cards = document.querySelectorAll('div[class*="cursor-pointer"]');
          for (var i = 0; i < cards.length; i++) {
            var text = cards[i].textContent.trim();
            if (text.includes('2.88 USD')) {
              cards[i].click();
              return 'clicked $2.88 survey card';
            }
          }
          return 'no $2.88 card found';
        })()
      `);
      L("Click: " + r);
      await sleep(8000);

      // Check what page loaded
      let url = await eval_(`window.location.href`);
      L("URL: " + url);

      let pageText = await eval_(`document.body.innerText.substring(0, 5000)`);
      L("PAGE TEXT:");
      L(pageText);

      // Get form elements
      let formJson = await eval_(`
        (function() {
          var inputs = document.querySelectorAll('input, select, textarea');
          return JSON.stringify(Array.from(inputs).filter(function(i) {
            return i.offsetParent !== null && i.type !== 'hidden';
          }).map(function(i) {
            var opts = '';
            if (i.tagName === 'SELECT') {
              opts = Array.from(i.options).map(function(o) { return o.value + ':' + o.text.substring(0, 30); }).join('|');
            }
            return {
              tag: i.tagName, type: i.type || '', name: i.name || '', id: i.id || '',
              value: (i.value || '').substring(0, 80),
              label: (i.labels && i.labels[0]) ? i.labels[0].textContent.trim().substring(0, 120) : '',
              options: opts
            };
          }).slice(0, 40));
        })()
      `);
      L("FORM: " + formJson);

      // Get buttons
      let btns = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button, input[type="submit"]');
          return JSON.stringify(Array.from(btns).filter(function(b) { return b.offsetParent !== null; }).map(function(b) {
            return { tag: b.tagName, text: b.textContent.trim().substring(0, 50), id: b.id };
          }));
        })()
      `);
      L("BUTTONS: " + btns);

      // Check for iframes
      let iframes = await eval_(`
        (function() {
          return JSON.stringify(Array.from(document.querySelectorAll('iframe')).map(function(f) {
            return { src: (f.src || '').substring(0, 200) };
          }));
        })()
      `);
      L("Iframes: " + iframes);

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
