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
  const pageTab = tabs.find(t => t.type === "page" && t.url.includes('ayet.io'));
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
      L("=== DMA CODE FIX ===");

      // Check current page state
      let pageText = await eval_(`document.body.innerText.substring(0, 500)`);
      L("Page: " + pageText.substring(0, 200));

      // Check what the input field looks like
      let inputInfo = await eval_(`
        (function() {
          var inp = document.querySelector('input[type="text"], input[type="number"], input[type="tel"], input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]):not([type="submit"])');
          if (!inp) return 'no input found';
          return JSON.stringify({ type: inp.type, placeholder: inp.placeholder, value: inp.value, id: inp.id, name: inp.name, pattern: inp.pattern });
        })()
      `);
      L("Input: " + inputInfo);

      // Set DMA code to 881 (Spokane, WA - covers Sandpoint, ID)
      let r = await eval_(`
        (function() {
          var inp = document.querySelector('input[type="text"], input[type="number"], input[type="tel"], input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]):not([type="submit"])');
          if (!inp) return 'no input';
          inp.focus();
          // Clear first
          var ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
          ns.call(inp, '');
          inp.dispatchEvent(new Event('input', { bubbles: true }));
          // Now set to 881
          ns.call(inp, '881');
          inp.dispatchEvent(new Event('input', { bubbles: true }));
          inp.dispatchEvent(new Event('change', { bubbles: true }));
          inp.dispatchEvent(new Event('blur', { bubbles: true }));
          return 'set: 881 (Spokane WA)';
        })()
      `);
      L("DMA set: " + r);
      await sleep(1000);

      // Click Continue
      r = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim().toLowerCase();
            if (t === 'continue' || t === 'next') { btns[i].click(); return 'clicked ' + btns[i].textContent.trim(); }
          }
          return 'no continue';
        })()
      `);
      L("Continue: " + r);
      await sleep(5000);

      // Check what we got
      let url = await eval_(`window.location.href`);
      pageText = await eval_(`document.body.innerText.substring(0, 1500)`);
      L("\nURL: " + url);
      L("Page: " + pageText.substring(0, 800));

      // Check for questions left
      let left = await eval_(`
        (function() {
          var m = document.body.innerText.match(/(\\d+) Questions? left/);
          return m ? m[0] : 'none found';
        })()
      `);
      L("Questions left: " + left);

      // If still on DMA, try "Spokane, WA" format
      if (pageText.includes('DMA')) {
        L("Still on DMA - trying different format...");
        r = await eval_(`
          (function() {
            var inp = document.querySelector('input[type="text"], input[type="number"], input[type="tel"], input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]):not([type="submit"])');
            if (!inp) return 'no input';
            inp.focus();
            var ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
            ns.call(inp, 'Spokane, WA');
            inp.dispatchEvent(new Event('input', { bubbles: true }));
            inp.dispatchEvent(new Event('change', { bubbles: true }));
            return 'set: Spokane, WA';
          })()
        `);
        L("Retry: " + r);
        await sleep(1000);

        // Check if autocomplete appeared
        let autocomplete = await eval_(`
          (function() {
            var items = document.querySelectorAll('[class*="option"], [class*="suggestion"], [class*="result"], [class*="dropdown"], [role="option"], [role="listbox"] li, ul li');
            var results = [];
            for (var i = 0; i < Math.min(items.length, 10); i++) {
              var t = items[i].textContent.trim();
              if (t.length > 2 && t.length < 100) results.push(t.substring(0, 60));
            }
            return JSON.stringify(results);
          })()
        `);
        L("Autocomplete: " + autocomplete);

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
        L("Continue2: " + r);
        await sleep(5000);

        url = await eval_(`window.location.href`);
        pageText = await eval_(`document.body.innerText.substring(0, 1000)`);
        L("URL2: " + url);
        L("Page2: " + pageText.substring(0, 500));
      }

      // Check tabs
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("Tabs: " + JSON.stringify(allTabs.map(t => ({ type: t.type, url: t.url.substring(0, 100) }))));

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
