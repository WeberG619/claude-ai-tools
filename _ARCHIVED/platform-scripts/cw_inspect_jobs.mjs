import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const out = [];

setTimeout(() => {
  out.push("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 20000);

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
      const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result?.value;
    };

    (async () => {
      // Get the HTML structure around assigned jobs section
      let r = await eval_(`
        (function() {
          // Find elements containing "Assigned Jobs"
          const all = document.querySelectorAll('*');
          for (const el of all) {
            if (el.childNodes.length > 0 && el.textContent.includes('Assigned Jobs') &&
                !el.textContent.includes('Available Jobs') && el.tagName !== 'BODY') {
              return 'TAG: ' + el.tagName + ' CLASS: ' + el.className + ' ID: ' + el.id +
                     '\\nHTML: ' + el.outerHTML.substring(0, 3000);
            }
          }
          return 'not found';
        })()
      `);
      out.push("ASSIGNED SECTION: " + r?.substring(0, 2000));

      // Get the Instant Jobs section HTML
      r = await eval_(`
        (function() {
          const all = document.querySelectorAll('*');
          for (const el of all) {
            if (el.childNodes.length > 0 && el.textContent.includes('Instant Jobs') &&
                el.textContent.length < 5000 && el.tagName !== 'BODY' && el.tagName !== 'HTML') {
              return 'TAG: ' + el.tagName + ' CLASS: ' + el.className +
                     '\\nHTML: ' + el.outerHTML.substring(0, 3000);
            }
          }
          return 'not found';
        })()
      `);
      out.push("INSTANT SECTION: " + r?.substring(0, 2000));

      // Get all clickable elements that have $ in their text (survey job cards)
      r = await eval_(`
        (function() {
          const clickables = document.querySelectorAll('a, button, [onclick], [role="button"], [data-href]');
          const results = [];
          clickables.forEach(el => {
            const text = el.textContent.trim();
            if (text.includes('$') || text.includes('Survey') || text.includes('survey')) {
              results.push({
                tag: el.tagName,
                text: text.substring(0, 100),
                href: el.href || el.getAttribute('data-href') || '',
                onclick: el.getAttribute('onclick')?.substring(0, 100) || '',
                class: el.className?.substring(0, 80) || '',
                id: el.id || ''
              });
            }
          });
          return JSON.stringify(results.slice(0, 30));
        })()
      `);
      out.push("CLICKABLE SURVEY ELEMENTS: " + r);

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
