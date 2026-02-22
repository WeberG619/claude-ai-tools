import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];

setTimeout(() => {
  out.push("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 25000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page");
  if (!tab) { out.push("No tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(0); }

  const ws = new WebSocket(tab.webSocketDebuggerUrl);

  ws.addEventListener("error", () => { out.push("WS error"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); });

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
      const r = await send("Runtime.evaluate", {
        expression: expr,
        returnByValue: true, awaitPromise: true
      });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result?.value;
    };

    (async () => {
      // Get assigned job links
      let r = await eval_(`
        (function() {
          const sections = document.querySelectorAll('h2, h3, .section-title');
          const allLinks = document.querySelectorAll('a');
          const jobLinks = [];
          allLinks.forEach(a => {
            if (a.href && a.href.includes('/jobs/') && a.href.includes('/edit')) {
              jobLinks.push({
                text: a.textContent.trim().substring(0, 80),
                href: a.href
              });
            }
          });
          return JSON.stringify(jobLinks);
        })()
      `);
      out.push("Assigned job links: " + r);

      // Get instant job links/buttons
      r = await eval_(`
        (function() {
          const allLinks = document.querySelectorAll('a');
          const instantJobs = [];
          allLinks.forEach(a => {
            const href = a.href || '';
            const text = a.textContent.trim();
            if (href.includes('instant_job') || href.includes('survey') ||
                (text.includes('Survey') && text.includes('$'))) {
              instantJobs.push({
                text: text.substring(0, 100),
                href: href.substring(0, 200)
              });
            }
          });
          // Also check for buttons/divs that might be instant job cards
          const cards = document.querySelectorAll('[class*="instant"], [class*="survey"], [class*="job-card"]');
          cards.forEach(card => {
            const link = card.querySelector('a');
            const text = card.textContent.trim().substring(0, 100);
            if (link) {
              instantJobs.push({
                text: 'CARD: ' + text,
                href: link.href.substring(0, 200)
              });
            }
          });
          return JSON.stringify(instantJobs);
        })()
      `);
      out.push("Instant jobs: " + r);

      // Get ALL links on page
      r = await eval_(`
        (function() {
          const links = document.querySelectorAll('a');
          const all = [];
          links.forEach(a => {
            if (a.href && !a.href.includes('javascript:') && a.offsetParent !== null) {
              all.push({
                text: a.textContent.trim().substring(0, 60),
                href: a.href.substring(0, 150)
              });
            }
          });
          return JSON.stringify(all);
        })()
      `);
      out.push("All visible links: " + r);

      ws.close();
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
      process.exit(0);
    })().catch(e => {
      out.push("Error: " + e.message);
      ws.close();
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
      process.exit(1);
    });
  });
})().catch(e => {
  out.push("Fatal: " + e.message);
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
});
