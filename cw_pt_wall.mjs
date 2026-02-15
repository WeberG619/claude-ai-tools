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

  // Find the ayet.io iframe target
  const ayetTarget = tabs.find(t => t.url.includes('ayet.io'));
  if (!ayetTarget) { L("No ayet.io target found"); L("Tabs:"); tabs.forEach(t => L("  " + t.url.substring(0,100))); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  L("Found PollTastic target: " + ayetTarget.url.substring(0, 120));

  const ws = new WebSocket(ayetTarget.webSocketDebuggerUrl);
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
      L("\n=== POLLTASTIC SURVEY WALL ===");
      let url = await eval_(`window.location.href`);
      let pageText = await eval_(`document.body.innerText.substring(0, 5000)`);
      L("URL: " + url);
      L("Page:\n" + pageText.substring(0, 3000));

      // Find survey cards with prices
      let surveys = await eval_(`
        (function() {
          var results = [];
          // Look for all elements with price-like text
          var allEls = document.querySelectorAll('*');
          for (var i = 0; i < allEls.length; i++) {
            var el = allEls[i];
            var t = el.textContent.trim();
            // Look for price patterns like +$X.XX or $X.XX
            if (t.match(/\\+?\\$?\\d+\\.\\d{2}/) && t.length < 200 && el.children.length < 5) {
              var priceMatch = t.match(/(\\d+\\.\\d{2})/);
              var timeMatch = t.match(/(\\d+)\\s*min/i);
              if (priceMatch && parseFloat(priceMatch[1]) >= 0.50) {
                var rect = el.getBoundingClientRect();
                results.push({
                  price: parseFloat(priceMatch[1]),
                  time: timeMatch ? parseInt(timeMatch[1]) : null,
                  text: t.replace(/\\s+/g, ' ').substring(0, 100),
                  tag: el.tagName,
                  x: Math.round(rect.x + rect.width/2),
                  y: Math.round(rect.y + rect.height/2),
                  classes: (el.className||'').substring(0, 60)
                });
              }
            }
          }
          // Deduplicate
          var seen = new Set();
          var unique = results.filter(function(r) {
            var key = r.price + '_' + r.time + '_' + r.y;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
          });
          unique.sort(function(a, b) { return b.price - a.price; });
          return JSON.stringify(unique.slice(0, 20));
        })()
      `);
      L("\n=== SURVEYS SORTED BY PRICE ===");
      L(surveys);

      // Parse and display nicely
      try {
        let parsed = JSON.parse(surveys);
        L("\n--- TOP SURVEYS ---");
        parsed.forEach(function(s, i) {
          let ratio = s.time ? (s.price / s.time * 60).toFixed(2) : '?';
          L((i+1) + ". $" + s.price.toFixed(2) + " / " + (s.time || '?') + "min ($/hr: $" + ratio + ") @ y=" + s.y);
        });
      } catch(e) {}

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_pt_wall.png', Buffer.from(ss.data, 'base64'));
      L("\nScreenshot saved");

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
