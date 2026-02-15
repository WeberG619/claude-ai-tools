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
  // Close non-TapResearch page tabs
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  for (const t of tabs) {
    if (t.type === "page" && !t.url.includes('tapresearch')) {
      try {
        const tempWs = new WebSocket(t.webSocketDebuggerUrl);
        await new Promise(resolve => {
          tempWs.addEventListener("open", () => {
            tempWs.send(JSON.stringify({ id: 1, method: "Page.close" }));
            setTimeout(resolve, 500);
          });
          tempWs.addEventListener("error", resolve);
        });
        L("Closed: " + t.url.substring(0, 60));
      } catch(e) {}
    }
  }
  await sleep(1000);

  // Connect to TapResearch
  const tabs2 = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tapTab = tabs2.find(t => t.type === "page" && t.url.includes('tapresearch'));
  if (!tapTab) { L("No TapResearch tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(tapTab.webSocketDebuggerUrl);
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

    const clickAt = async (x, y) => {
      await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      await sleep(80);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    };

    (async () => {
      // Check current page state
      let pageText = await eval_(`document.body.innerText.substring(0, 1000)`);
      L("Current page: " + pageText.substring(0, 300));

      // Dismiss exit survey if showing
      if (pageText.includes('something wrong')) {
        await eval_(`
          (function() {
            var all = document.querySelectorAll('li');
            for (var i = 0; i < all.length; i++) {
              if (all[i].textContent.includes('No reason')) { all[i].click(); return; }
            }
          })()
        `);
        await sleep(500);
        await eval_(`
          (function() {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
              if (btns[i].textContent.trim() === 'Continue') { btns[i].click(); return; }
            }
          })()
        `);
        await sleep(4000);
        pageText = await eval_(`document.body.innerText.substring(0, 1000)`);
        L("After dismiss: " + pageText.substring(0, 300));
      }

      // If page is empty or not survey wall, reload
      if (!pageText.includes('usd cents')) {
        L("Reloading TapResearch...");
        const tapUrl = "https://www.tapresearch.com/router/offers/d6ed80f2feca2bbe1fec6f8c2c29ff8d?tid=919ee19884b43cc25c838eb54cc450ed57eadcd4&uid=25671709&pass_through_values=eyJqb2JfaWQiOjQ2ODIwMTk4NX0=&app_id=2316&timestamp=1770633403&sech=bea16f4f70dbca883eeaa1eb1efb21ac6053666f";
        await send("Page.navigate", { url: tapUrl });
        await sleep(8000);
        pageText = await eval_(`document.body.innerText.substring(0, 1000)`);
        L("After reload: " + pageText.substring(0, 300));
      }

      // Find and click the 81 cent / 15 min survey (highest value)
      let r = await eval_(`
        (function() {
          var all = document.querySelectorAll('div');
          var cards = [];
          for (var i = 0; i < all.length; i++) {
            var t = all[i].textContent.trim();
            if (t.includes('usd cents') && t.includes('min') && t.length < 200) {
              var rect = all[i].getBoundingClientRect();
              if (rect.width > 50 && rect.height > 50 && rect.width < 500) {
                var centsMatch = t.match(/(\\d+)\\s*usd cents/);
                var minMatch = t.match(/(\\d+)\\s*min/);
                if (centsMatch && minMatch) {
                  cards.push({ cents: parseInt(centsMatch[1]), mins: parseInt(minMatch[1]),
                    x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2),
                    w: Math.round(rect.width), h: Math.round(rect.height) });
                }
              }
            }
          }
          cards.sort(function(a, b) { return (a.w*a.h) - (b.w*b.h); });
          var seen = {};
          var unique = [];
          for (var i = 0; i < cards.length; i++) {
            var key = cards[i].cents + '_' + cards[i].mins;
            if (!seen[key]) { seen[key] = true; unique.push(cards[i]); }
          }
          unique.sort(function(a, b) { return b.cents - a.cents; });
          return JSON.stringify(unique.slice(0, 10));
        })()
      `);
      L("Cards: " + r);

      let cards = [];
      try { cards = JSON.parse(r); } catch(e) {}

      if (cards.length === 0) {
        L("No survey cards found");
        const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_survey_v2.png', Buffer.from(ss.data, 'base64'));
        ws.close();
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
        process.exit(0);
      }

      // Pick the 81 cent one or best available
      let target = cards.find(c => c.cents === 81) || cards[0];
      L("Selecting: " + target.cents + "c / " + target.mins + "m");
      await clickAt(target.x, target.y);
      await sleep(6000);

      pageText = await eval_(`document.body.innerText.substring(0, 1000)`);
      L("After click: " + pageText.substring(0, 300));

      // Click "Let's go!" if present
      r = await eval_(`
        (function() {
          var all = document.querySelectorAll('div, button');
          for (var i = 0; i < all.length; i++) {
            var t = all[i].textContent.trim().toLowerCase();
            if ((t === "let's go!" || t === "let's go") && all[i].getBoundingClientRect().width < 300) {
              var rect = all[i].getBoundingClientRect();
              return JSON.stringify({ x: Math.round(rect.x+rect.width/2), y: Math.round(rect.y+rect.height/2) });
            }
          }
          return 'null';
        })()
      `);

      if (r !== 'null') {
        let pos = JSON.parse(r);
        L("Clicking Let's go at (" + pos.x + "," + pos.y + ")");
        await clickAt(pos.x, pos.y);
        await sleep(10000);
      }

      // Check for new survey tab
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("Tabs: " + allTabs.length);
      allTabs.forEach((t, i) => L("  [" + i + "] " + t.type + ": " + t.url.substring(0, 150)));

      let surveyTab = allTabs.find(t => t.type === "page" && !t.url.includes('tapresearch'));
      if (surveyTab) {
        L("\nSurvey tab found: " + surveyTab.url.substring(0, 150));
        // Connect to survey tab for inspection
        ws.close();
        const ws2 = new WebSocket(surveyTab.webSocketDebuggerUrl);
        await new Promise((resolve, reject) => {
          ws2.addEventListener("open", resolve);
          ws2.addEventListener("error", reject);
        });

        let id2 = 0;
        const pending2 = new Map();
        ws2.addEventListener("message", e => {
          const m = JSON.parse(e.data);
          if (m.id && pending2.has(m.id)) {
            const p = pending2.get(m.id);
            pending2.delete(m.id);
            if (m.error) p.rej(new Error(m.error.message));
            else p.res(m.result);
          }
        });
        const send2 = (method, params = {}) => new Promise((res, rej) => {
          const i = ++id2;
          pending2.set(i, { res, rej });
          ws2.send(JSON.stringify({ id: i, method, params }));
        });
        const eval2_ = async (expr) => {
          const r = await send2("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
          if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
          return r.result?.value;
        };

        let surveyUrl = await eval2_(`window.location.href`);
        let surveyText = await eval2_(`document.body.innerText.substring(0, 3000)`);
        L("Survey URL: " + surveyUrl);
        L("Survey page:");
        L(surveyText.substring(0, 2000));

        // Get all interactive elements
        r = await eval2_(`
          (function() {
            var result = { radios: [], inputs: [], selects: [], buttons: [] };
            document.querySelectorAll('input[type="radio"]').forEach(function(r) {
              result.radios.push({ id: r.id, name: r.name, value: r.value, label: (r.labels?.[0]?.textContent||'').trim().substring(0,60) });
            });
            document.querySelectorAll('input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]):not([type="submit"])').forEach(function(i) {
              if (i.offsetParent) result.inputs.push({ type: i.type, id: i.id, name: i.name, placeholder: (i.placeholder||'').substring(0,40) });
            });
            document.querySelectorAll('select').forEach(function(s) {
              if (s.offsetParent) result.selects.push({ id: s.id, name: s.name, count: s.options.length, first5: Array.from(s.options).slice(0,5).map(o=>o.text) });
            });
            document.querySelectorAll('button, input[type="submit"]').forEach(function(b) {
              if (b.offsetWidth > 0) result.buttons.push({ text: b.textContent.trim().substring(0,40) });
            });
            return JSON.stringify(result);
          })()
        `);
        L("Elements: " + r);

        const ss = await send2("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_survey_v2.png', Buffer.from(ss.data, 'base64'));
        L("Screenshot saved");

        ws2.close();
      } else {
        // No survey tab - might still be on TapResearch
        const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_survey_v2.png', Buffer.from(ss.data, 'base64'));
        L("Screenshot saved (no survey tab)");
      }

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
