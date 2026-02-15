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
      // Get full page text to find job names and IDs
      L("=== FINDING ALL JOB NAMES ===");
      let fullText = await eval_(`document.body.innerText.substring(0, 6000)`);
      L(fullText.substring(0, 5000));

      // Get all job entries with their links
      let jobs = await eval_(`
        (function() {
          var results = [];
          // Each job has a title and a Details link
          var details = document.querySelectorAll('a[href*="/jobs/"]');
          details.forEach(function(a) {
            var href = a.href;
            var match = href.match(/jobs\\/(\\d+)/);
            if (!match) return;
            var jobId = match[1];
            // Get the parent container to find the job title
            var container = a.closest('tr, [class*="job"], [class*="card"], div');
            var title = '';
            if (container) {
              // Get the first significant text before "Details"
              var walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null, false);
              var texts = [];
              var node;
              while (node = walker.nextNode()) {
                var t = node.textContent.trim();
                if (t.length > 3 && t !== 'Details' && t !== 'Hide' && !t.includes('variable')) texts.push(t);
              }
              title = texts.slice(0, 2).join(' | ');
            }
            results.push({ jobId: jobId, title: title.substring(0, 80), href: href.substring(0, 100) });
          });
          // Deduplicate by jobId
          var seen = {};
          return JSON.stringify(results.filter(function(r) {
            if (seen[r.jobId]) return false;
            seen[r.jobId] = true;
            return true;
          }));
        })()
      `);
      L("\n=== JOB MAP ===");
      L(jobs);

      // Try the PollTastic job - likely 1225955 based on 50-day time limit
      let jobIds = [1225955, 1235819, 1137673, 1189213, 1170203, 1135821];
      for (const jid of jobIds) {
        await eval_(`window.location.href = 'https://workplace.clickworker.com/en/workplace/jobs/${jid}/edit'`);
        await sleep(3000);
        let title = await eval_(`document.title || document.body.innerText.substring(0, 200)`);
        let text = await eval_(`document.body.innerText.substring(0, 300)`);
        if (text.includes('PollTastic') || text.includes('polltastic')) {
          L("\nFOUND POLLTASTIC: Job ID " + jid);
          L("Page: " + text.substring(0, 200));

          // Check for iframe targets
          await sleep(5000);
          let allTabs = await (await fetch(`${CDP_HTTP}/json`)).json();
          L("\nTargets:");
          allTabs.forEach(t => L("  " + t.type + ": " + t.url.substring(0, 120)));
          break;
        } else {
          let jobName = text.match(/\n([^\n]*(?:BitLabs|CPX|TapResearch|Inbrain|PollTastic|Phrase|UHRS|MyChips|GameTastic)[^\n]*)/i);
          L("Job " + jid + ": " + (jobName ? jobName[1].trim() : text.substring(0, 100)));
        }
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
