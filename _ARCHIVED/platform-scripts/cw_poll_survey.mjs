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
      // First, explore the survey wall structure
      L("=== SURVEY WALL EXPLORATION ===");

      let structure = await eval_(`
        (function() {
          // Find all clickable survey elements
          var results = [];

          // Look for links, buttons, cards
          var links = document.querySelectorAll('a[href]');
          for (var i = 0; i < links.length; i++) {
            var t = links[i].textContent.trim().substring(0, 80);
            var h = links[i].href;
            if (t.length > 3 && (t.includes('Min') || t.includes('+') || t.includes('$') || h.includes('survey'))) {
              results.push({ tag: 'a', text: t.substring(0,60), href: h.substring(0,100) });
            }
          }

          // Look for divs that look like cards
          var divs = document.querySelectorAll('div[class*="card"], div[class*="survey"], div[class*="offer"], div[onclick], div[class*="item"]');
          for (var i = 0; i < Math.min(divs.length, 10); i++) {
            var t = divs[i].textContent.trim().substring(0, 80);
            results.push({ tag: 'div', class: divs[i].className.substring(0,60), text: t.substring(0,60) });
          }

          // Look for any elements with click handlers or data attributes
          var clickables = document.querySelectorAll('[data-survey-id], [data-id], [data-offer]');
          for (var i = 0; i < clickables.length; i++) {
            results.push({ tag: clickables[i].tagName, attrs: JSON.stringify(Object.fromEntries(Array.from(clickables[i].attributes).map(a=>[a.name,a.value.substring(0,40)]))) });
          }

          return JSON.stringify(results.slice(0, 20));
        })()
      `);
      L("Structure: " + structure);

      // Also check for iframes that might contain surveys
      let iframes = await eval_(`
        (function() {
          var ifs = document.querySelectorAll('iframe');
          return Array.from(ifs).map(f => ({ src: (f.src||'').substring(0,100), id: f.id, w: f.width, h: f.height }));
        })()
      `);
      L("Iframes: " + JSON.stringify(iframes));

      // Get full page HTML structure around survey cards
      let cardHTML = await eval_(`
        (function() {
          // Try to find elements containing price/payout info
          var all = document.querySelectorAll('*');
          var cards = [];
          for (var i = 0; i < all.length; i++) {
            var t = all[i].textContent.trim();
            var own = '';
            for (var j = 0; j < all[i].childNodes.length; j++) {
              if (all[i].childNodes[j].nodeType === 3) own += all[i].childNodes[j].textContent;
            }
            own = own.trim();
            if (own.match(/^\\+\\d+\\.\\d+$/) || own.match(/^\\$\\d+/)) {
              var parent = all[i].parentElement;
              var grandparent = parent ? parent.parentElement : null;
              var clickTarget = grandparent || parent || all[i];
              var rect = clickTarget.getBoundingClientRect();
              cards.push({
                price: own,
                tag: clickTarget.tagName,
                class: clickTarget.className.substring(0,60),
                x: Math.round(rect.x + rect.width/2),
                y: Math.round(rect.y + rect.height/2),
                w: Math.round(rect.width),
                h: Math.round(rect.height),
                fullText: clickTarget.textContent.trim().substring(0,100)
              });
            }
          }
          return JSON.stringify(cards);
        })()
      `);
      L("Cards: " + cardHTML);

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
