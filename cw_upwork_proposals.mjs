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
      // === MYSTERY SHOPPER PROPOSAL ===
      L("=== MYSTERY SHOPPER - FINDING JOB ===");
      await eval_(`window.location.href = 'https://www.upwork.com/nx/search/jobs/?q=mystery%20shopper%20audit%20online%20presence&sort=recency'`);
      await sleep(8000);

      // Find and click the mystery shopper job
      let r = await eval_(`
        (function() {
          var links = document.querySelectorAll('a');
          for (var i = 0; i < links.length; i++) {
            var t = links[i].textContent.trim();
            if (t.includes('Mystery Shoppers') && t.includes('Audit')) {
              return links[i].href;
            }
          }
          return 'not found';
        })()
      `);
      L("Mystery shopper link: " + r);

      if (r !== 'not found') {
        await eval_(`window.location.href = '${r}'`);
        await sleep(5000);

        let url = await eval_(`window.location.href`);
        let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
        L("Job URL: " + url);
        L("Job page:\n" + pageText.substring(0, 1500));

        // Look for Apply/Submit Proposal button
        let applyBtn = await eval_(`
          (function() {
            var btns = document.querySelectorAll('a, button');
            for (var i = 0; i < btns.length; i++) {
              var t = btns[i].textContent.trim().toLowerCase();
              if (t.includes('apply now') || t.includes('submit a proposal') || t.includes('submit proposal')) {
                return { text: btns[i].textContent.trim(), href: btns[i].href || 'button' };
              }
            }
            return null;
          })()
        `);
        L("Apply button: " + JSON.stringify(applyBtn));

        if (applyBtn) {
          // Click Apply
          r = await eval_(`
            (function() {
              var btns = document.querySelectorAll('a, button');
              for (var i = 0; i < btns.length; i++) {
                var t = btns[i].textContent.trim().toLowerCase();
                if (t.includes('apply now') || t.includes('submit a proposal') || t.includes('submit proposal')) {
                  btns[i].click();
                  return 'clicked: ' + btns[i].textContent.trim();
                }
              }
              return 'not found';
            })()
          `);
          L("Apply click: " + r);
          await sleep(5000);

          url = await eval_(`window.location.href`);
          pageText = await eval_(`document.body.innerText.substring(0, 5000)`);
          L("\nProposal page URL: " + url);
          L("Proposal page:\n" + pageText.substring(0, 3000));

          // Get all form fields
          let fields = await eval_(`
            (function() {
              var inputs = [];
              document.querySelectorAll('input:not([type="hidden"]), select, textarea').forEach(function(i) {
                var label = '';
                if (i.labels && i.labels[0]) label = i.labels[0].textContent.trim();
                inputs.push({
                  type: i.type || i.tagName.toLowerCase(),
                  name: i.name || '',
                  id: i.id || '',
                  placeholder: (i.placeholder||'').substring(0,60),
                  label: label.substring(0, 60),
                  value: (i.value||'').substring(0,40)
                });
              });
              return JSON.stringify(inputs);
            })()
          `);
          L("\nForm fields: " + fields);
        }
      }

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_upwork_mystery.png', Buffer.from(ss.data, 'base64'));
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
