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

    const clickAt = async (x, y) => {
      await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      await sleep(80);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    };

    (async () => {
      // 1. Find survey card elements by looking at the DOM structure
      let r = await eval_(`
        (function() {
          // Look for elements that contain "usd cents" text and have click handlers
          var all = document.querySelectorAll('*');
          var cards = [];
          for (var i = 0; i < all.length; i++) {
            var el = all[i];
            var t = el.textContent.trim();
            // Survey cards likely have "usd cents" and "min" in their text
            if (t.includes('usd cents') && t.includes('min') && t.length < 200) {
              var rect = el.getBoundingClientRect();
              if (rect.width > 50 && rect.height > 50 && rect.width < 500) {
                // Extract cents and minutes
                var centsMatch = t.match(/(\\d+)\\s*usd cents/);
                var minMatch = t.match(/(\\d+)\\s*min/);
                if (centsMatch && minMatch) {
                  cards.push({
                    cents: parseInt(centsMatch[1]),
                    mins: parseInt(minMatch[1]),
                    text: t.substring(0, 60).replace(/\\n/g, ' '),
                    tag: el.tagName,
                    class: (el.className || '').substring(0, 60),
                    x: Math.round(rect.x + rect.width/2),
                    y: Math.round(rect.y + rect.height/2),
                    w: Math.round(rect.width),
                    h: Math.round(rect.height)
                  });
                }
              }
            }
          }
          // Deduplicate by keeping elements with smallest area (most specific)
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
          // Sort by cents/min ratio (best value first)
          unique.sort(function(a, b) { return (b.cents/b.mins) - (a.cents/a.mins); });
          return JSON.stringify(unique.slice(0, 15));
        })()
      `);
      L("Survey cards found:");
      L(r);

      // Parse cards and pick the best one
      let cards = [];
      try { cards = JSON.parse(r); } catch(e) { L("Parse error: " + e.message); }

      if (cards.length === 0) {
        L("No cards found, trying coordinate click");
        // Try clicking where the first survey should be based on layout
        await clickAt(1223, 350);
        await sleep(5000);
      } else {
        // Pick the one with best cents/min ratio (highest value)
        // But prefer shorter surveys for quick earnings
        // Filter for decent ones (>= 10 cents, <= 15 min)
        let best = cards.filter(c => c.cents >= 10 && c.mins <= 15);
        if (best.length === 0) best = cards;
        // Sort by cents/min ratio
        best.sort((a, b) => (b.cents/b.mins) - (a.cents/a.mins));

        L("\nBest survey: " + best[0].cents + " cents / " + best[0].mins + " min at (" + best[0].x + ", " + best[0].y + ")");

        // Click the survey card
        await clickAt(best[0].x, best[0].y);
        await sleep(8000);
      }

      // Check what happened
      let url = await eval_(`window.location.href`);
      L("URL: " + url);

      // Check for new tabs
      const tabs2 = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("Tabs: " + tabs2.length);
      tabs2.forEach((t, i) => L("  [" + i + "] " + t.type + ": " + t.url.substring(0, 200)));

      let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("Page text:");
      L(pageText.substring(0, 2000));

      // Get clickable elements
      r = await eval_(`
        (function() {
          var els = document.querySelectorAll('a, button, [role="button"], input[type="submit"]');
          var result = [];
          for (var i = 0; i < els.length; i++) {
            var rect = els[i].getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
              result.push({
                tag: els[i].tagName,
                text: els[i].textContent.trim().substring(0, 80),
                href: (els[i].href || '').substring(0, 200),
                x: Math.round(rect.x + rect.width/2),
                y: Math.round(rect.y + rect.height/2)
              });
            }
          }
          return JSON.stringify(result.slice(0, 20));
        })()
      `);
      L("Clickable: " + r);

      // Get inputs
      r = await eval_(`
        (function() {
          var inputs = document.querySelectorAll('input:not([type="hidden"]), select, textarea');
          return JSON.stringify(Array.from(inputs).filter(function(i) {
            return i.offsetParent !== null;
          }).map(function(i) {
            return { type: i.type, id: i.id, name: i.name, placeholder: (i.placeholder||'').substring(0,40) };
          }));
        })()
      `);
      L("Inputs: " + r);

      // Get iframes
      r = await eval_(`
        (function() {
          var iframes = document.querySelectorAll('iframe');
          return JSON.stringify(Array.from(iframes).map(function(f) {
            return { src: (f.src || '').substring(0, 300), id: f.id };
          }));
        })()
      `);
      L("Iframes: " + r);

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_tap_click.png', Buffer.from(ss.data, 'base64'));
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
