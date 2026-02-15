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
  const pageTab = tabs.find(t => t.type === "page" && t.url.includes('clickworker'));
  if (!pageTab) { L("No clickworker tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }
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
      // Navigate to jobs page
      L("=== NAVIGATING TO JOBS PAGE ===");
      await eval_(`window.location.href = 'https://workplace.clickworker.com/en/workplace/jobs'`);
      await sleep(5000);

      // Find all job entries with their "Details" links
      let jobs = await eval_(`
        (function() {
          var results = [];
          var links = document.querySelectorAll('a[href*="/jobs/"]');
          links.forEach(function(a) {
            var href = a.href;
            var match = href.match(/jobs\\/(\\d+)/);
            if (!match) return;
            var jobId = match[1];
            var container = a.closest('tr, [class*="job"], [class*="card"], div');
            var title = '';
            if (container) {
              var t = container.textContent.trim().replace(/\\s+/g, ' ');
              title = t.substring(0, 120);
            }
            results.push({ jobId: jobId, title: title, href: href.substring(0, 100) });
          });
          var seen = {};
          return JSON.stringify(results.filter(function(r) {
            if (seen[r.jobId]) return false;
            seen[r.jobId] = true;
            return true;
          }));
        })()
      `);
      L("Jobs found:");
      try {
        let parsed = JSON.parse(jobs);
        parsed.forEach(j => L("  ID " + j.jobId + ": " + j.title.substring(0, 100)));
      } catch(e) { L(jobs); }

      // Click on BitLabs first - they tend to have higher-paying surveys
      let bitlabsLink = await eval_(`
        (function() {
          var links = document.querySelectorAll('a[href*="/jobs/"]');
          for (var i = 0; i < links.length; i++) {
            var container = links[i].closest('div, tr');
            if (container && container.textContent.includes('BitLabs')) {
              return links[i].href;
            }
          }
          return 'not found';
        })()
      `);
      L("\\nBitLabs link: " + bitlabsLink);

      if (bitlabsLink !== 'not found') {
        await eval_(`window.location.href = '${bitlabsLink}'`);
        await sleep(8000);

        let url = await eval_(`window.location.href`);
        let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
        L("\\nBitLabs page URL: " + url);
        L("BitLabs page:\\n" + pageText.substring(0, 2000));

        // Check for iframe targets
        let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
        L("\\nAll targets after BitLabs:");
        allTabs.forEach(t => L("  " + t.type + ": " + t.url.substring(0, 120)));

        // Find BitLabs iframe target
        let blTarget = allTabs.find(t => t.url.includes('bitlabs') || t.url.includes('bitlab'));
        if (blTarget) {
          L("\\nFound BitLabs target: " + blTarget.url);
          try {
            const ws2 = new WebSocket(blTarget.webSocketDebuggerUrl);
            await new Promise((res, rej) => {
              ws2.addEventListener("open", res);
              ws2.addEventListener("error", rej);
              setTimeout(rej, 5000);
            });
            let id2 = 0;
            const pending2 = new Map();
            ws2.addEventListener("message", e => {
              const m = JSON.parse(e.data);
              if (m.id && pending2.has(m.id)) { const p = pending2.get(m.id); pending2.delete(m.id); if (m.error) p.rej(new Error(m.error.message)); else p.res(m.result); }
            });
            const send2 = (method, params = {}) => new Promise((res, rej) => { const i = ++id2; pending2.set(i, { res, rej }); ws2.send(JSON.stringify({ id: i, method, params })); });
            const eval2 = async (expr) => { const r = await send2("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result?.value; };

            let blText = await eval2(`document.body.innerText.substring(0, 3000)`);
            L("\\nBitLabs iframe content:\\n" + blText.substring(0, 2000));

            // Find surveys with prices
            let surveys = await eval2(`
              (function() {
                var results = [];
                var allEls = document.querySelectorAll('*');
                for (var i = 0; i < allEls.length; i++) {
                  var el = allEls[i];
                  var t = el.textContent.trim();
                  if (t.match(/\\$\\d+\\.\\d{2}/) && t.length < 300 && el.children.length < 8) {
                    var priceMatch = t.match(/(\\d+\\.\\d{2})/);
                    var timeMatch = t.match(/(\\d+)\\s*min/i);
                    if (priceMatch && parseFloat(priceMatch[1]) >= 0.50) {
                      results.push({
                        price: parseFloat(priceMatch[1]),
                        time: timeMatch ? parseInt(timeMatch[1]) : null,
                        text: t.replace(/\\s+/g, ' ').substring(0, 120),
                        tag: el.tagName
                      });
                    }
                  }
                }
                var seen = new Set();
                var unique = results.filter(function(r) {
                  var key = r.price + '_' + r.time;
                  if (seen.has(key)) return false;
                  seen.add(key);
                  return true;
                });
                unique.sort(function(a, b) { return b.price - a.price; });
                return JSON.stringify(unique.slice(0, 15));
              })()
            `);
            L("\\n=== BITLABS SURVEYS (sorted by price) ===");
            L(surveys);
            try {
              let parsed = JSON.parse(surveys);
              parsed.forEach(function(s, i) {
                let ratio = s.time ? (s.price / s.time * 60).toFixed(2) : '?';
                L((i+1) + ". $" + s.price.toFixed(2) + " / " + (s.time || '?') + "min ($/hr: $" + ratio + ")");
              });
            } catch(e) {}

            ws2.close();
          } catch(e) { L("BitLabs iframe error: " + e.message); }
        } else {
          L("\\nNo BitLabs iframe target found");
        }
      }

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_partners.png', Buffer.from(ss.data, 'base64'));

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
