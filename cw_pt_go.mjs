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
      // Navigate to PollTastic job on Clickworker
      // First find the PollTastic job ID - it might be different from Inbrain (1066135)
      L("=== NAVIGATING TO CLICKWORKER JOBS ===");
      await eval_(`window.location.href = 'https://workplace.clickworker.com/en/workplace/jobs'`);
      await sleep(5000);

      // Find PollTastic job link
      let ptLink = await eval_(`
        (function() {
          var links = document.querySelectorAll('a[href]');
          for (var i = 0; i < links.length; i++) {
            if (links[i].textContent.trim().includes('PollTastic')) {
              return links[i].href;
            }
          }
          return 'not found';
        })()
      `);
      L("PollTastic link: " + ptLink);

      if (ptLink === 'not found') {
        // Try clicking on PollTastic text
        let r = await eval_(`
          (function() {
            var all = document.querySelectorAll('*');
            for (var i = 0; i < all.length; i++) {
              if (all[i].textContent.trim().includes('PollTastic') && all[i].children.length === 0) {
                // Get parent link
                var parent = all[i].closest('a');
                if (parent) return parent.href;
              }
            }
            // Try getting job IDs from all job links
            var jobLinks = [];
            document.querySelectorAll('a[href*="/jobs/"]').forEach(function(a) {
              var t = a.textContent.trim();
              if (t.length > 0 && t.length < 100) {
                jobLinks.push({ text: t.substring(0, 60), href: a.href.substring(0, 120) });
              }
            });
            return JSON.stringify(jobLinks);
          })()
        `);
        L("Job links: " + r);
      }

      // Click on PollTastic or navigate to it
      if (ptLink !== 'not found') {
        await eval_(`window.location.href = '${ptLink}'`);
      } else {
        // Try known PollTastic patterns - might share the same job page as other survey providers
        // Let's look for it in the page
        let r = await eval_(`
          (function() {
            var tds = document.querySelectorAll('td, div, span, a');
            for (var i = 0; i < tds.length; i++) {
              var t = tds[i].textContent.trim();
              if (t.includes('PollTastic') && tds[i].closest('a')) {
                var link = tds[i].closest('a');
                link.click();
                return 'clicked PollTastic: ' + link.href;
              }
            }
            return 'could not find PollTastic link';
          })()
        `);
        L("Click attempt: " + r);
      }

      await sleep(8000);

      // Check what loaded
      let url = await eval_(`window.location.href`);
      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("\nURL: " + url);
      L("Page:\n" + pageText.substring(0, 1000));

      // Check all CDP targets for survey iframe
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("\nAll targets:");
      allTabs.forEach(t => L("  " + t.type + ": " + t.url.substring(0, 120)));

      // Find PollTastic/survey target
      let surveyTarget = allTabs.find(t =>
        t.url.includes('polltastic') ||
        t.url.includes('surveywall') ||
        (t.url.includes('surveyb.in') && !t.url.includes('configuration'))
      );

      if (surveyTarget) {
        L("\nFound survey target: " + surveyTarget.url);

        const ws2 = new WebSocket(surveyTarget.webSocketDebuggerUrl);
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

        let sUrl = await eval2(`window.location.href`);
        let sText = await eval2(`document.body.innerText.substring(0, 3000)`);
        L("\nSurvey URL: " + sUrl);
        L("Survey page:\n" + sText.substring(0, 2000));

        // Look for survey cards with prices
        let surveys = await eval2(`
          (function() {
            var results = [];
            var cards = document.querySelectorAll('[class*="SurveyCard"], [class*="survey"], [class*="card"]');
            cards.forEach(function(card) {
              var t = card.textContent.trim();
              var priceMatch = t.match(/\\+(\\d+\\.\\d+)/);
              var timeMatch = t.match(/(\\d+)\\s*min/);
              if (priceMatch) {
                results.push({
                  price: parseFloat(priceMatch[1]),
                  time: timeMatch ? parseInt(timeMatch[1]) : null,
                  text: t.replace(/\\s+/g, ' ').substring(0, 120)
                });
              }
            });
            // Also check all text for dollar amounts
            if (results.length === 0) {
              var allText = document.body.innerText;
              var matches = allText.match(/\\+\\d+\\.\\d+/g);
              if (matches) results.push({ note: 'found prices in text', prices: matches.slice(0, 20) });
            }
            results.sort(function(a, b) { return (b.price || 0) - (a.price || 0); });
            return JSON.stringify(results.slice(0, 15));
          })()
        `);
        L("\n=== AVAILABLE SURVEYS (sorted by price) ===");
        L(surveys);

        ws2.close();
      } else {
        L("\nNo survey iframe target found");
      }

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_pt_go.png', Buffer.from(ss.data, 'base64'));

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
