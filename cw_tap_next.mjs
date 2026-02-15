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
  // Check all tabs
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  L("Tabs: " + tabs.length);
  tabs.forEach((t, i) => L("  [" + i + "] " + t.type + ": " + t.url.substring(0, 150)));

  // Close the survey tab (tracking URL) and go back to TapResearch
  // First close the tracking tab
  const trackingTab = tabs.find(t => t.url.includes('sonicmedia') || t.url.includes('tracking'));
  if (trackingTab) {
    const closeWs = new WebSocket(trackingTab.webSocketDebuggerUrl);
    await new Promise(resolve => {
      closeWs.addEventListener("open", () => {
        closeWs.send(JSON.stringify({ id: 1, method: "Page.close" }));
        setTimeout(resolve, 1000);
      });
      closeWs.addEventListener("error", resolve);
    });
    L("Closed tracking tab");
    await sleep(1000);
  }

  // Connect to TapResearch tab
  const tabs2 = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tapTab = tabs2.find(t => t.type === "page" && t.url.includes('tapresearch'));
  if (!tapTab) {
    L("No TapResearch tab found");
    tabs2.forEach((t, i) => L("  [" + i + "] " + t.url.substring(0, 150)));
    writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
    process.exit(1);
  }

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
      // Check current state of TapResearch page
      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("TapResearch page: " + pageText.substring(0, 500));

      // If it's showing the exit survey ("Is something wrong?"), dismiss it
      if (pageText.includes('something wrong') || pageText.includes('narrow down')) {
        // Click "No reason" and Continue
        let r = await eval_(`
          (function() {
            var all = document.querySelectorAll('div, span, label, li');
            for (var i = 0; i < all.length; i++) {
              var t = all[i].textContent.trim();
              if (t === 'No reason. Just wanted to leave.' || t.includes('No reason')) {
                all[i].click();
                return 'clicked: ' + t;
              }
            }
            return 'not found';
          })()
        `);
        L("Exit reason: " + r);
        await sleep(500);

        r = await eval_(`
          (function() {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
              if (btns[i].textContent.trim() === 'Continue') {
                btns[i].click();
                return 'clicked Continue';
              }
            }
            return 'no Continue';
          })()
        `);
        L("Continue: " + r);
        await sleep(5000);
      }

      // Now we should be back at the survey wall
      pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("\nPage after dismiss:");
      L(pageText.substring(0, 1500));

      // Find survey cards again
      let r = await eval_(`
        (function() {
          var all = document.querySelectorAll('*');
          var cards = [];
          for (var i = 0; i < all.length; i++) {
            var el = all[i];
            var t = el.textContent.trim();
            if (t.includes('usd cents') && t.includes('min') && t.length < 200) {
              var rect = el.getBoundingClientRect();
              if (rect.width > 50 && rect.height > 50 && rect.width < 500) {
                var centsMatch = t.match(/(\\d+)\\s*usd cents/);
                var minMatch = t.match(/(\\d+)\\s*min/);
                if (centsMatch && minMatch) {
                  cards.push({
                    cents: parseInt(centsMatch[1]),
                    mins: parseInt(minMatch[1]),
                    text: t.substring(0, 60).replace(/\\n/g, ' '),
                    x: Math.round(rect.x + rect.width/2),
                    y: Math.round(rect.y + rect.height/2),
                    w: Math.round(rect.width),
                    h: Math.round(rect.height)
                  });
                }
              }
            }
          }
          cards.sort(function(a, b) { return (a.w * a.h) - (b.w * b.h); });
          var seen = {};
          var unique = [];
          for (var i = 0; i < cards.length; i++) {
            var key = cards[i].cents + '_' + cards[i].mins;
            if (!seen[key]) {
              seen[key] = true;
              unique.push(cards[i]);
            }
          }
          unique.sort(function(a, b) { return (b.cents/b.mins) - (a.cents/a.mins); });
          return JSON.stringify(unique.slice(0, 10));
        })()
      `);
      L("Survey cards: " + r);

      let cards = [];
      try { cards = JSON.parse(r); } catch(e) {}

      if (cards.length > 0) {
        // Try the 66 cent / 10 min survey (second best value)
        let target = cards.find(c => c.cents === 66) || cards[0];
        L("\nSelecting: " + target.cents + " cents / " + target.mins + " min");
        await clickAt(target.x, target.y);
        await sleep(8000);

        // Check if survey opened
        let tabs3 = await (await fetch(`${CDP_HTTP}/json`)).json();
        L("Tabs: " + tabs3.length);
        tabs3.forEach((t, i) => L("  [" + i + "] " + t.url.substring(0, 150)));

        pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
        L("Page: " + pageText.substring(0, 800));

        // Look for "Let's go!" button
        r = await eval_(`
          (function() {
            var all = document.querySelectorAll('*');
            for (var i = 0; i < all.length; i++) {
              var t = all[i].textContent.trim();
              if (t.toLowerCase().includes("let's go") || t.toLowerCase().includes("lets go")) {
                var rect = all[i].getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0 && rect.width < 300) {
                  return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: t });
                }
              }
            }
            return 'null';
          })()
        `);
        L("Let's go: " + r);
        if (r !== 'null') {
          let btn = JSON.parse(r);
          await clickAt(btn.x, btn.y);
          L("Clicked Let's go at (" + btn.x + ", " + btn.y + ")");
          await sleep(8000);

          // Check for new survey tab
          let tabs4 = await (await fetch(`${CDP_HTTP}/json`)).json();
          L("Tabs after: " + tabs4.length);
          tabs4.forEach((t, i) => L("  [" + i + "] " + t.url.substring(0, 200)));
        }
      }

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_tap_next.png', Buffer.from(ss.data, 'base64'));
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
