import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 30000);

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
      // First go to the account page
      L("=== FINDING TAX DETAILS PAGE ===");
      await eval_(`window.location.href = 'https://workplace.clickworker.com/en/workplace/account'`);
      await sleep(5000);

      let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      let url = await eval_(`window.location.href`);
      L("URL: " + url);
      L("Page:\n" + pageText.substring(0, 1500));

      // Find all links on the page related to tax/payment
      let links = await eval_(`
        (function() {
          var results = [];
          document.querySelectorAll('a[href]').forEach(function(a) {
            var t = a.textContent.trim().toLowerCase();
            var h = a.href;
            if (t.includes('tax') || t.includes('payment') || t.includes('payout') || t.includes('billing') ||
                h.includes('tax') || h.includes('payment') || h.includes('payout') || h.includes('billing')) {
              results.push({ text: a.textContent.trim().substring(0, 60), href: h.substring(0, 150) });
            }
          });
          return JSON.stringify(results);
        })()
      `);
      L("\nTax/payment links: " + links);

      // Also get ALL navigation links
      let navLinks = await eval_(`
        (function() {
          var results = [];
          document.querySelectorAll('a[href], button').forEach(function(el) {
            var t = el.textContent.trim();
            var h = el.href || '';
            if (t.length > 0 && t.length < 60 && (h.includes('workplace') || h.includes('account'))) {
              results.push({ text: t.substring(0, 50), href: h.substring(0, 120) });
            }
          });
          return JSON.stringify(results.slice(0, 30));
        })()
      `);
      L("\nAll nav links: " + navLinks);

      // Try clicking the "Complete tax-details now" link from the banner
      let r = await eval_(`
        (function() {
          var links = document.querySelectorAll('a[href]');
          for (var i = 0; i < links.length; i++) {
            var t = links[i].textContent.trim().toLowerCase();
            if (t.includes('tax') || t.includes('complete tax')) {
              return links[i].href;
            }
          }
          return 'no tax link found';
        })()
      `);
      L("\nTax link URL: " + r);

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
