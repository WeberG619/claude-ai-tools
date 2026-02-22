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
      // Navigate to jobs page and get full page text to identify all jobs
      L("=== IDENTIFYING ALL JOBS ===");
      await eval_(`window.location.href = 'https://workplace.clickworker.com/en/workplace/jobs'`);
      await sleep(5000);

      // Get the full page HTML to find job names near their IDs
      let jobMap = await eval_(`
        (function() {
          var results = [];
          // Find all links with job IDs
          var links = document.querySelectorAll('a[href*="/jobs/"]');
          var seenIds = {};
          links.forEach(function(a) {
            var m = a.href.match(/jobs\\/(\\d+)/);
            if (!m || seenIds[m[1]]) return;
            seenIds[m[1]] = true;
            var jobId = m[1];

            // Walk up to find the job container - look for larger parent div
            var el = a;
            for (var i = 0; i < 10; i++) {
              if (!el.parentElement) break;
              el = el.parentElement;
              var text = el.textContent.trim();
              // If this container has a recognizable job name, use it
              if (text.length > 50 && text.length < 500) {
                var firstLine = text.split('\\n')[0].trim();
                if (firstLine.length > 5 && firstLine.length < 100) {
                  results.push({ jobId: jobId, name: firstLine, fullText: text.replace(/\\s+/g, ' ').substring(0, 200) });
                  return;
                }
              }
            }
            // Fallback: just get nearby text
            var container = a.closest('div');
            if (container) {
              results.push({ jobId: jobId, name: 'unknown', fullText: container.textContent.trim().replace(/\\s+/g, ' ').substring(0, 200) });
            }
          });
          return JSON.stringify(results);
        })()
      `);
      L(jobMap);

      // Also get the full page text around each section header
      let sections = await eval_(`
        (function() {
          var text = document.body.innerText;
          // Find key sections
          var markers = ['Instant Jobs', 'Available Jobs', 'Partner Platform', 'Partner platforms'];
          var results = {};
          markers.forEach(function(m) {
            var idx = text.indexOf(m);
            if (idx >= 0) {
              results[m] = text.substring(idx, idx + 500).replace(/\\n/g, ' | ');
            }
          });
          return JSON.stringify(results);
        })()
      `);
      L("\\nPage sections:\\n" + sections);

      // Now check specific unknown job IDs by navigating to their detail pages
      // Known: 51749=UHRS, 1066135=Inbrain, 1225955=PollTastic
      let unknownIds = [1247633, 1079435, 1072443, 1079431, 1170203, 1135821, 1189213, 1235819, 1137673];

      for (const jid of unknownIds) {
        await eval_(`window.location.href = 'https://workplace.clickworker.com/en/workplace/jobs/${jid}'`);
        await sleep(2000);
        let title = await eval_(`
          (function() {
            var h = document.querySelector('h1, h2, h3, [class*="title"]');
            if (h) return h.textContent.trim().substring(0, 100);
            var text = document.body.innerText.substring(0, 300);
            var lines = text.split('\\n').filter(function(l) { return l.trim().length > 3; });
            return lines.slice(0, 3).join(' | ');
          })()
        `);
        L("Job " + jid + ": " + title);
      }

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
