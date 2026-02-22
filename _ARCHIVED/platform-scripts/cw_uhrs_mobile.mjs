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
      // Get the Android link details from the mobile app section
      L("=== CHECKING MOBILE APP INSTRUCTIONS ===");

      // Scroll to mobile app section
      await eval_(`window.scrollTo(0, document.body.scrollHeight)`);
      await sleep(1000);

      // Get all links on page
      let links = await eval_(`
        (function() {
          var results = [];
          document.querySelectorAll('a[href]').forEach(function(a) {
            var t = a.textContent.trim();
            var h = a.href;
            if (h.includes('play.google') || h.includes('apple') || h.includes('android') ||
                h.includes('groups.google') || h.includes('uhrs') || h.includes('mobile') ||
                t.toLowerCase().includes('android') || t.toLowerCase().includes('apple') ||
                t.toLowerCase().includes('download') || t.toLowerCase().includes('install')) {
              results.push({ text: t.substring(0, 80), href: h.substring(0, 200) });
            }
          });
          return JSON.stringify(results);
        })()
      `);
      L("Mobile/download links: " + links);

      // Get the full mobile app section text
      let mobileSection = await eval_(`
        (function() {
          var text = document.body.innerText;
          var idx = text.indexOf('UHRS Mobile App');
          if (idx === -1) idx = text.indexOf('mobile');
          if (idx === -1) return 'no mobile section found';
          return text.substring(idx, idx + 1000);
        })()
      `);
      L("\nMobile section: " + mobileSection);

      // Also check FAQ page
      L("\n=== CHECKING FAQ ===");
      await eval_(`window.location.href = 'https://www.uhrs.ai/faq'`);
      await sleep(3000);

      let faqText = await eval_(`document.body.innerText.substring(0, 5000)`);
      L("FAQ page:\n" + faqText.substring(0, 3000));

      // Get FAQ links
      let faqLinks = await eval_(`
        (function() {
          var results = [];
          document.querySelectorAll('a[href]').forEach(function(a) {
            var h = a.href;
            if (h.includes('play.google') || h.includes('groups.google') || h.includes('android') || h.includes('mobile')) {
              results.push({ text: a.textContent.trim().substring(0, 60), href: h.substring(0, 200) });
            }
          });
          return JSON.stringify(results);
        })()
      `);
      L("\nFAQ mobile links: " + faqLinks);

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
