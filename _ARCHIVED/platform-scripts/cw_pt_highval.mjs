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
      // Navigate to PollTastic
      L("=== CHECKING POLLTASTIC FOR HIGH-VALUE SURVEYS ===");
      await eval_(`window.location.href = 'https://workplace.clickworker.com/en/workplace/jobs/1066135/edit'`);
      await sleep(8000);

      // Check all tabs for PollTastic/Inbrain iframe
      let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("All targets:");
      allTabs.forEach(t => L("  " + t.type + ": " + t.url.substring(0, 100)));

      // Find survey target (PollTastic or surveyb.in)
      let surveyTarget = allTabs.find(t => t.url.includes('surveyb.in') || t.url.includes('polltastic'));

      if (!surveyTarget) {
        // Check page content
        let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
        L("\nMain page: " + pageText.substring(0, 800));

        // Check if we need to navigate to PollTastic specifically
        let iframes = await eval_(`JSON.stringify(Array.from(document.querySelectorAll('iframe')).map(f => ({ src: (f.src||'').substring(0,200), id: f.id })))`);
        L("Iframes: " + iframes);

        ws.close();
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
        process.exit(0);
        return;
      }

      L("\nFound survey target: " + surveyTarget.url.substring(0, 100));

      // Connect to survey iframe
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

      let url = await eval2(`window.location.href`);
      let pageText = await eval2(`document.body.innerText.substring(0, 3000)`);
      L("\nURL: " + url);
      L("Page: " + pageText.substring(0, 500));

      // If it's the Inbrain page, check for survey list
      if (url.includes('surveyb.in')) {
        // Check if we're on the survey list or need to click Get Started
        if (pageText.includes('Get Started')) {
          L("\nInbrain needs Get Started - clicking...");
          await eval2(`
            (function() {
              var btns = document.querySelectorAll('button, a, [role="button"]');
              for (var i = 0; i < btns.length; i++) {
                if (btns[i].textContent.trim().toLowerCase().includes('get started')) {
                  btns[i].click(); return 'clicked';
                }
              }
              return 'no button';
            })()
          `);
          await sleep(5000);
          pageText = await eval2(`document.body.innerText.substring(0, 3000)`);
          url = await eval2(`window.location.href`);
          L("After Get Started - URL: " + url);
          L("Page: " + pageText.substring(0, 500));
        }

        // Try to find survey cards with prices
        let surveys = await eval2(`
          (function() {
            var results = [];
            // Look for elements containing dollar amounts
            var all = document.querySelectorAll('*');
            for (var i = 0; i < all.length; i++) {
              var t = all[i].textContent.trim();
              var m = t.match(/\\$(\\d+\\.\\d+)/);
              if (m && t.length < 200) {
                var mins = t.match(/(\\d+)\\s*min/);
                results.push({
                  price: parseFloat(m[1]),
                  time: mins ? parseInt(mins[1]) : null,
                  text: t.substring(0, 100),
                  tag: all[i].tagName
                });
              }
            }
            // Deduplicate by text
            var seen = new Set();
            var unique = [];
            results.forEach(function(r) {
              var key = r.price + '_' + r.time;
              if (!seen.has(key)) { seen.add(key); unique.push(r); }
            });
            // Sort by price desc
            unique.sort(function(a, b) { return b.price - a.price; });
            return JSON.stringify(unique.slice(0, 20));
          })()
        `);
        L("\n=== AVAILABLE SURVEYS ===");
        L(surveys);

        try {
          let parsed = JSON.parse(surveys);
          let highVal = parsed.filter(s => s.price >= 5.00);
          L("\n=== SURVEYS $5+ ===");
          if (highVal.length === 0) {
            L("No surveys paying $5 or more.");
            L("Highest available: " + (parsed.length > 0 ? "$" + parsed[0].price + " / " + parsed[0].time + "min" : "none"));
          } else {
            highVal.forEach(s => L("  $" + s.price + " / " + s.time + "min: " + s.text.substring(0, 80)));
          }
        } catch(e) { L("Parse error: " + e.message); }
      }

      // Now also check PollTastic
      // Navigate main page to PollTastic job
      L("\n=== CHECKING POLLTASTIC JOB ===");
      // PollTastic is a different job - let me check if it loads in the same iframe
      // The job 1066135 might be Inbrain. Let me check all jobs
      let mainPageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("Main page title check: " + mainPageText.substring(0, 200));

      ws2.close();
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
