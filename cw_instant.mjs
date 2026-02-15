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

      // Find Instant Jobs section and click on the best-paying survey
      // From earlier we saw $3.02/7min as the best
      let instantJobs = await eval_(`
        (function() {
          var results = [];
          // Find all links/elements that look like instant job survey entries
          var links = document.querySelectorAll('a[href*="instant"], a[href*="survey"], [class*="instant"], [class*="survey"]');
          links.forEach(function(a) {
            var t = a.textContent.trim();
            if (t.includes('$') && t.length < 200) {
              results.push({ text: t.replace(/\\s+/g, ' ').substring(0, 100), href: (a.href||'').substring(0, 150) });
            }
          });
          // Also find survey links in the page
          document.querySelectorAll('a[href]').forEach(function(a) {
            var t = a.textContent.trim();
            if ((t.includes('Survey') || t.includes('$')) && t.length < 100 && a.href.includes('job')) {
              results.push({ text: t.replace(/\\s+/g, ' ').substring(0, 80), href: a.href.substring(0, 150) });
            }
          });
          return JSON.stringify(results.slice(0, 20));
        })()
      `);
      L("Instant job links: " + instantJobs);

      // Look for the "Survey $3.02 7min" entry specifically
      // The Instant Jobs might be in a specific section - let me find and click the highest paying one
      let bestSurvey = await eval_(`
        (function() {
          // Find all elements containing dollar amounts in the instant jobs section
          var text = document.body.innerText;
          var instantIdx = text.indexOf('Instant Jobs');
          if (instantIdx === -1) return 'no instant jobs section';
          var section = text.substring(instantIdx, instantIdx + 2000);
          return section.substring(0, 1500);
        })()
      `);
      L("\nInstant Jobs section:\n" + bestSurvey);

      // Try to find and click the $3.02 survey
      let r = await eval_(`
        (function() {
          // Scroll down to instant jobs
          var instantHeader = null;
          var allEls = document.querySelectorAll('h1, h2, h3, h4, h5, h6, [class*="header"], [class*="title"], strong, b');
          for (var i = 0; i < allEls.length; i++) {
            if (allEls[i].textContent.trim().includes('Instant Jobs')) {
              instantHeader = allEls[i];
              break;
            }
          }
          if (instantHeader) {
            instantHeader.scrollIntoView();
          }

          // Find clickable survey entries - look for links near dollar amounts
          var links = document.querySelectorAll('a[href]');
          var best = null;
          var bestPrice = 0;
          for (var i = 0; i < links.length; i++) {
            var t = links[i].textContent.trim();
            var m = t.match(/\\$\\s*(\\d+\\.\\d+)/);
            if (m) {
              var price = parseFloat(m[1]);
              if (price > bestPrice) {
                bestPrice = price;
                best = { text: t.replace(/\\s+/g, ' ').substring(0, 80), href: links[i].href, price: price };
              }
            }
          }
          if (best) return JSON.stringify(best);
          return 'no priced links found';
        })()
      `);
      L("\nBest survey link: " + r);

      // If we found one, navigate to it
      if (r !== 'no priced links found' && r !== 'no instant jobs section') {
        try {
          let survey = JSON.parse(r);
          L("\nClicking: $" + survey.price + " - " + survey.text);
          await eval_(`window.location.href = '${survey.href}'`);
          await sleep(8000);

          let url = await eval_(`window.location.href`);
          let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
          L("\nSurvey URL: " + url);
          L("Survey page:\n" + pageText.substring(0, 2000));

          // Check all tabs for new targets
          let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
          L("\nAll targets:");
          allTabs.forEach(t => L("  " + t.type + ": " + t.url.substring(0, 120)));
        } catch(e) { L("Parse error: " + e.message); }
      }

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_instant.png', Buffer.from(ss.data, 'base64'));

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
