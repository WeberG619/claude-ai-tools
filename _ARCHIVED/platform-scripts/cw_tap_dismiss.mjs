import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 60000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tapTab = tabs.find(t => t.type === "page" && t.url.includes('tapresearch'));
  if (!tapTab) {
    L("No TapResearch tab");
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
      // Examine the exit survey DOM structure carefully
      let r = await eval_(`
        (function() {
          // Find elements with "No reason" text
          var all = document.querySelectorAll('*');
          var matches = [];
          for (var i = 0; i < all.length; i++) {
            // Check own text only (not children)
            var ownText = '';
            for (var j = 0; j < all[i].childNodes.length; j++) {
              if (all[i].childNodes[j].nodeType === 3) ownText += all[i].childNodes[j].textContent;
            }
            ownText = ownText.trim();
            if (ownText.includes('No reason')) {
              var rect = all[i].getBoundingClientRect();
              matches.push({
                tag: all[i].tagName,
                class: (all[i].className || '').substring(0, 80),
                ownText: ownText.substring(0, 80),
                x: Math.round(rect.x + rect.width/2),
                y: Math.round(rect.y + rect.height/2),
                w: Math.round(rect.width),
                h: Math.round(rect.height)
              });
            }
          }
          return JSON.stringify(matches);
        })()
      `);
      L("'No reason' elements: " + r);

      let elements = [];
      try { elements = JSON.parse(r); } catch(e) {}

      if (elements.length > 0) {
        // Click the smallest (most specific) one
        elements.sort((a, b) => (a.w * a.h) - (b.w * b.h));
        let el = elements[0];
        L("Clicking 'No reason' at (" + el.x + ", " + el.y + ") tag=" + el.tag);
        await clickAt(el.x, el.y);
        await sleep(1000);
      }

      // Now find and click Continue button
      r = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          var matches = [];
          for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.trim() === 'Continue') {
              var rect = btns[i].getBoundingClientRect();
              matches.push({
                x: Math.round(rect.x + rect.width/2),
                y: Math.round(rect.y + rect.height/2),
                w: Math.round(rect.width),
                h: Math.round(rect.height),
                disabled: btns[i].disabled,
                class: (btns[i].className || '').substring(0, 80)
              });
            }
          }
          return JSON.stringify(matches);
        })()
      `);
      L("Continue buttons: " + r);

      let buttons = [];
      try { buttons = JSON.parse(r); } catch(e) {}

      if (buttons.length > 0) {
        let btn = buttons[0];
        L("Clicking Continue at (" + btn.x + ", " + btn.y + ") disabled=" + btn.disabled);
        await clickAt(btn.x, btn.y);
        await sleep(5000);
      }

      // Check state
      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("Page after: " + pageText.substring(0, 500));

      // If still showing exit survey, try alternative: reload the page
      if (pageText.includes('something wrong')) {
        L("Still showing exit survey. Trying page reload...");
        // Navigate back to the TapResearch offers URL
        const tapUrl = "https://www.tapresearch.com/router/offers/d6ed80f2feca2bbe1fec6f8c2c29ff8d?tid=919ee19884b43cc25c838eb54cc450ed57eadcd4&uid=25671709&pass_through_values=eyJqb2JfaWQiOjQ2ODIwMTk4NX0=&app_id=2316&timestamp=1770633403&sech=bea16f4f70dbca883eeaa1eb1efb21ac6053666f";
        await send("Page.navigate", { url: tapUrl });
        await sleep(8000);

        pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
        L("After reload: " + pageText.substring(0, 1000));
      }

      // Look for survey cards
      r = await eval_(`
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
                  cards.push({
                    cents: parseInt(centsMatch[1]),
                    mins: parseInt(minMatch[1]),
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
      L("Cards: " + r);

      let cards = [];
      try { cards = JSON.parse(r); } catch(e) {}

      if (cards.length > 0) {
        // Click the 66 cent survey or best available
        let target = cards.find(c => c.cents === 66) || cards.find(c => c.cents >= 25) || cards[0];
        L("Selecting: " + target.cents + "c / " + target.mins + "m at (" + target.x + "," + target.y + ")");
        await clickAt(target.x, target.y);
        await sleep(8000);

        // Check result
        let tabs2 = await (await fetch(`${CDP_HTTP}/json`)).json();
        L("Tabs: " + tabs2.length);
        tabs2.forEach((t, i) => L("  [" + i + "] " + t.url.substring(0, 150)));

        pageText = await eval_(`document.body.innerText.substring(0, 1000)`);
        L("After click: " + pageText.substring(0, 500));

        // Click "Let's go!" if present
        r = await eval_(`
          (function() {
            var all = document.querySelectorAll('div, button, span');
            for (var i = 0; i < all.length; i++) {
              var t = all[i].textContent.trim().toLowerCase();
              if (t === "let's go!" || t === "let's go") {
                var rect = all[i].getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0 && rect.width < 300) {
                  return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
                }
              }
            }
            return 'null';
          })()
        `);
        if (r !== 'null') {
          let pos = JSON.parse(r);
          L("Clicking Let's go at (" + pos.x + "," + pos.y + ")");
          await clickAt(pos.x, pos.y);
          await sleep(8000);

          let tabs3 = await (await fetch(`${CDP_HTTP}/json`)).json();
          L("Tabs after Let's go: " + tabs3.length);
          tabs3.forEach((t, i) => L("  [" + i + "] " + t.url.substring(0, 200)));
        }
      }

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_tap_dismiss.png', Buffer.from(ss.data, 'base64'));
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
