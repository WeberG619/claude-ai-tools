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
  const psTab = tabs.find(t => t.type === "page" && t.url.includes('purespectrum'));
  if (!psTab) { L("No PureSpectrum tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(psTab.webSocketDebuggerUrl);
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

      // Analyze the DOM structure of the sports league question
      let domInfo = await eval_(`
        (function() {
          var results = {};
          // All checkboxes
          var cbs = document.querySelectorAll('input[type="checkbox"]');
          results.checkboxes = [];
          cbs.forEach(function(cb) {
            var parent = cb.parentElement;
            for (var d = 0; d < 3; d++) {
              if (parent && parent.textContent.trim().length < 80 && parent.textContent.trim().length > 0) break;
              parent = parent ? parent.parentElement : null;
            }
            var rect = cb.getBoundingClientRect();
            results.checkboxes.push({
              text: parent ? parent.textContent.trim().substring(0, 60) : '',
              id: cb.id,
              name: cb.name,
              value: cb.value,
              x: Math.round(rect.x),
              y: Math.round(rect.y),
              w: Math.round(rect.width),
              h: Math.round(rect.height),
              visible: rect.width > 0,
              classes: (cb.className || '').substring(0, 50)
            });
          });
          // All input types
          var inputs = document.querySelectorAll('input');
          results.allInputs = [];
          inputs.forEach(function(i) {
            results.allInputs.push({ type: i.type, name: i.name, id: i.id, val: (i.value || '').substring(0, 30) });
          });
          // Look for option-like divs
          results.optionDivs = [];
          var NFL = null;
          document.querySelectorAll('*').forEach(function(el) {
            var t = el.textContent.trim();
            if (t === 'National Football League (NFL)' || t === 'NFL') {
              var rect = el.getBoundingClientRect();
              if (rect.width > 0 && rect.height > 0 && rect.width < 800) {
                results.optionDivs.push({
                  tag: el.tagName,
                  text: t.substring(0, 50),
                  classes: (el.className || '').substring(0, 80),
                  x: Math.round(rect.x + rect.width/2),
                  y: Math.round(rect.y + rect.height/2),
                  cursor: window.getComputedStyle(el).cursor
                });
              }
            }
          });
          return JSON.stringify(results);
        })()
      `);
      L("DOM Analysis:\n" + domInfo);

      // Also check the HTML around the first option
      let optionHTML = await eval_(`
        (function() {
          var all = document.querySelectorAll('*');
          for (var i = 0; i < all.length; i++) {
            if (all[i].textContent.trim() === 'Formula 1 Racing' && all[i].children.length === 0) {
              // Walk up to find the container
              var el = all[i];
              for (var d = 0; d < 3; d++) {
                el = el.parentElement;
              }
              return el.outerHTML.substring(0, 500);
            }
          }
          return 'not found';
        })()
      `);
      L("\nOption HTML:\n" + optionHTML);

      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_survey.png', Buffer.from(ss.data, 'base64'));

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
