import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 90000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();

  // Find BitLabs iframe target
  const blTarget = tabs.find(t => t.url.includes('bitlabs'));
  if (!blTarget) { L("No BitLabs target found"); tabs.forEach(t => L("  " + t.url.substring(0,100))); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  L("Found BitLabs target: " + blTarget.url);
  const ws = new WebSocket(blTarget.webSocketDebuggerUrl);
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
      // Find and click the $5.08 survey
      L("=== FINDING $5.08 SURVEY ===");

      let result = await eval_(`
        (function() {
          // Find all elements containing "5.08"
          var allEls = document.querySelectorAll('*');
          var candidates = [];
          for (var i = 0; i < allEls.length; i++) {
            var el = allEls[i];
            var t = el.textContent.trim();
            if (t.includes('5.08') && t.length < 50) {
              candidates.push({
                tag: el.tagName,
                text: t,
                classes: (el.className || '').substring(0, 80),
                childCount: el.children.length
              });
            }
          }
          return JSON.stringify(candidates);
        })()
      `);
      L("Elements with 5.08: " + result);

      // Click the survey card containing 5.08
      let clickResult = await eval_(`
        (function() {
          // Strategy 1: Find the element with "5.08" text and click its parent card/link
          var allEls = document.querySelectorAll('*');
          for (var i = 0; i < allEls.length; i++) {
            var el = allEls[i];
            var t = el.textContent.trim();
            // Find the most specific element containing "5.08 USD" or "5.08"
            if (t.includes('5.08') && el.children.length === 0 && t.length < 30) {
              // Found the price text element - now find the clickable parent
              var clickable = el.closest('a, button, [role="button"], [onclick]');
              if (clickable) {
                clickable.click();
                return 'clicked link/button: ' + clickable.tagName + ' - ' + clickable.textContent.trim().substring(0, 80);
              }
              // Try clicking a parent div that looks like a card
              var card = el.closest('[class*="card"], [class*="survey"], [class*="offer"], [class*="item"]');
              if (card) {
                card.click();
                return 'clicked card: ' + card.tagName + '.' + (card.className||'').substring(0,60);
              }
              // Just click the parent
              var parent = el.parentElement;
              for (var j = 0; j < 5; j++) {
                if (!parent) break;
                parent.click();
                if (parent.tagName === 'A' || parent.tagName === 'BUTTON') break;
                parent = parent.parentElement;
              }
              return 'clicked parent chain from: ' + el.tagName + ' text=' + t;
            }
          }

          // Strategy 2: Find by scrolling through survey list items
          var items = document.querySelectorAll('[class*="survey"], [class*="card"], [class*="offer"], li, [class*="item"]');
          for (var i = 0; i < items.length; i++) {
            if (items[i].textContent.includes('5.08')) {
              items[i].click();
              return 'clicked list item: ' + items[i].tagName + '.' + (items[i].className||'').substring(0,60);
            }
          }

          return 'could not find 5.08 element to click';
        })()
      `);
      L("Click result: " + clickResult);

      // Wait for page change
      await sleep(5000);

      // Check what happened
      let url = await eval_(`window.location.href`);
      let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("\nAfter click URL: " + url);
      L("After click page:\n" + pageText.substring(0, 2000));

      // Check all targets for new survey tab
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("\nAll targets after click:");
      allTabs.forEach(t => L("  " + t.type + ": " + t.url.substring(0, 150)));

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
