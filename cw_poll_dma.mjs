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
      // Check what type of input DMA is - could be text, select, or radio
      L("=== DMA QUESTION ===");
      let elements = await eval_(`
        (function() {
          var inputs = [];
          document.querySelectorAll('input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]):not([type="submit"])').forEach(function(i) {
            if (i.offsetParent !== null || i.style.display !== 'none') inputs.push({ type: i.type, placeholder: i.placeholder, value: i.value, id: i.id, name: i.name });
          });
          var selects = [];
          document.querySelectorAll('select').forEach(function(s) {
            if (s.offsetParent !== null) selects.push({ id: s.id, name: s.name, optCount: s.options.length, first5: Array.from(s.options).slice(0,5).map(o=>o.text) });
          });
          var radios = [];
          document.querySelectorAll('input[type="radio"]').forEach(function(r) {
            var l = (r.labels?.[0]?.textContent || '').trim();
            if (!l) { var p = r.closest('label') || r.parentElement; if (p) l = p.textContent.trim(); }
            radios.push(l.substring(0, 60));
          });
          return JSON.stringify({ inputs: inputs, selects: selects, radios: radios });
        })()
      `);
      L("Elements: " + elements);

      // Try to set the DMA - Sandpoint ID is in Spokane DMA (881)
      // First try select dropdown
      let r = await eval_(`
        (function() {
          var sels = document.querySelectorAll('select');
          for (var j = 0; j < sels.length; j++) {
            var sel = sels[j];
            if (!sel.offsetParent && sel.style.display === 'none') continue;
            for (var i = 0; i < sel.options.length; i++) {
              if (sel.options[i].text.toLowerCase().includes('spokane')) {
                var ns = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set;
                ns.call(sel, sel.options[i].value);
                sel.dispatchEvent(new Event('input', { bubbles: true }));
                sel.dispatchEvent(new Event('change', { bubbles: true }));
                return 'selected: ' + sel.options[i].text;
              }
            }
          }
          return 'no spokane in selects';
        })()
      `);
      L("Select try: " + r);

      // If no select, try text input
      if (r.includes('no spokane')) {
        r = await eval_(`
          (function() {
            var inp = document.querySelector('input[type="text"], input[type="number"], input[type="tel"], input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]):not([type="submit"])');
            if (!inp) return 'no input';
            inp.focus();
            var ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
            ns.call(inp, 'Spokane');
            inp.dispatchEvent(new Event('input', { bubbles: true }));
            inp.dispatchEvent(new Event('change', { bubbles: true }));
            return 'set: Spokane';
          })()
        `);
        L("Input try: " + r);
      }

      // Try radio
      if (r.includes('no input')) {
        r = await eval_(`
          (function() {
            var radios = document.querySelectorAll('input[type="radio"]');
            for (var i = 0; i < radios.length; i++) {
              var l = (radios[i].labels?.[0]?.textContent || '').trim();
              if (!l) { var p = radios[i].closest('label') || radios[i].parentElement; if (p) l = p.textContent.trim(); }
              if (l.toLowerCase().includes('spokane')) {
                radios[i].click();
                if (radios[i].labels && radios[i].labels[0]) radios[i].labels[0].click();
                return 'clicked: ' + l;
              }
            }
            return 'no spokane radio';
          })()
        `);
        L("Radio try: " + r);
      }

      await sleep(500);

      // Click Continue
      r = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim().toLowerCase();
            if (t === 'continue' || t === 'next') { btns[i].click(); return 'clicked'; }
          }
          return 'no continue';
        })()
      `);
      L("Continue: " + r);
      await sleep(5000);

      // Check result
      let url = await eval_(`window.location.href`);
      let pageText = await eval_(`document.body.innerText.substring(0, 1500)`);
      L("\nURL: " + url);
      L("Page: " + pageText.substring(0, 800));

      // Check for new tabs
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      let tabInfo = allTabs.map(t => ({ type: t.type, url: t.url.substring(0, 120) }));
      L("All tabs: " + JSON.stringify(tabInfo));

      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_poll_done.png', Buffer.from(ss.data, 'base64'));
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
