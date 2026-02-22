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
  const tab = tabs.find(t => t.type === "page");

  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  ws.addEventListener("error", () => { L("WS error"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); });

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
      // Try Christian athlete first
      L("=== CHRISTIAN ATHLETE ===");
      await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs/1265821/edit" });
      await sleep(5000);

      let url = await eval_(`window.location.href`);
      L("URL: " + url);

      if (url.includes('/edit')) {
        let pageText = await eval_(`document.body.innerText.substring(0, 1000)`);
        if (pageText.includes('no further jobs')) {
          L("No more jobs in this project");
        } else {
          // Get radios
          let radiosJson = await eval_(`
            (function() {
              var radios = document.querySelectorAll('input[type="radio"]');
              return JSON.stringify(Array.from(radios).map(function(r) {
                return { id: r.id, value: (r.value || '').substring(0, 80) };
              }));
            })()
          `);
          let radios = JSON.parse(radiosJson || '[]');
          L("Radios: " + radios.length);

          if (radios.length > 0) {
            await eval_(`
              (function() {
                var radio = document.getElementById('${radios[0].id}');
                if (radio) { radio.checked = true; radio.click(); }
              })()
            `);
            await sleep(300);
            await eval_(`
              (function() {
                var btn = document.querySelector('input[type="submit"][name="submit_job"]');
                if (btn) btn.click();
              })()
            `);
            L("Submitted");
            await sleep(4000);

            let balance = await eval_(`
              (function() {
                var text = document.body.innerText;
                var match = text.match(/Account balance \\$ ([\\d.]+)/);
                return match ? match[1] : 'unknown';
              })()
            `);
            L("Balance: $" + balance);
          }
        }
      } else {
        L("Not on edit page");
      }

      // Try Welcome to clickworker
      L("\n=== WELCOME ===");
      await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs/1137665/edit" });
      await sleep(5000);
      url = await eval_(`window.location.href`);
      L("URL: " + url);

      if (url.includes('/edit')) {
        let pageText = await eval_(`document.body.innerText.substring(0, 500)`);
        if (pageText.includes('no further jobs')) {
          L("No more welcome jobs");
        } else {
          let radios = JSON.parse(await eval_(`
            (function() {
              var radios = document.querySelectorAll('input[type="radio"]');
              return JSON.stringify(Array.from(radios).map(function(r) { return { id: r.id }; }));
            })()
          `) || '[]');
          if (radios.length > 0) {
            await eval_(`(function() { var r = document.getElementById('${radios[0].id}'); if (r) { r.checked = true; r.click(); } })()`);
            await sleep(300);
            await eval_(`(function() { var b = document.querySelector('input[type="submit"][name="submit_job"]'); if (b) b.click(); })()`);
            L("Submitted");
            await sleep(3000);
          } else {
            L("No radios");
          }
        }
      }

      // Now try partner platforms - get their links
      L("\n=== PARTNER PLATFORMS ===");
      await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs" });
      await sleep(4000);

      // Get all partner platform job links
      let partnerLinks = await eval_(`
        (function() {
          var allCards = document.querySelectorAll('[onclick]');
          var links = [];
          allCards.forEach(function(card) {
            var onclick = card.getAttribute('onclick') || '';
            if (onclick.includes('window.open')) {
              var match = onclick.match(/window\\.open\\('([^']+)'/);
              if (match) {
                links.push({
                  text: card.textContent.trim().substring(0, 100),
                  url: match[1]
                });
              }
            }
          });
          // Also get regular links
          var aLinks = document.querySelectorAll('a');
          aLinks.forEach(function(a) {
            if (a.href && (a.href.includes('BitLabs') || a.href.includes('CPX') ||
                a.href.includes('TapResearch') || a.href.includes('Inbrain') ||
                a.href.includes('PollTastic') || a.href.includes('partner'))) {
              links.push({ text: a.textContent.trim().substring(0, 100), url: a.href });
            }
          });
          return JSON.stringify(links.slice(0, 20));
        })()
      `);
      L("Partner links: " + partnerLinks);

      // Get assigned job links
      let assignedLinks = await eval_(`
        (function() {
          var allCards = document.querySelectorAll('[onclick]');
          var links = [];
          allCards.forEach(function(card) {
            var onclick = card.getAttribute('onclick') || '';
            if (onclick.includes('/jobs/') && onclick.includes('/edit')) {
              var match = onclick.match(/['"]([^'"]*\\/jobs\\/[^'"]+)['"]/);
              if (match) {
                links.push({
                  text: card.textContent.trim().substring(0, 100),
                  url: match[1]
                });
              }
            }
          });
          return JSON.stringify(links.slice(0, 20));
        })()
      `);
      L("Assigned links: " + assignedLinks);

      // Check instant jobs section
      let instantSection = await eval_(`
        (function() {
          var heading = null;
          document.querySelectorAll('h1').forEach(function(h) {
            if (h.textContent.includes('Instant Jobs')) heading = h;
          });
          if (heading) {
            var parent = heading.closest('.page-header');
            if (parent && parent.nextElementSibling) {
              return parent.nextElementSibling.innerHTML.substring(0, 1000);
            }
          }
          return 'not found';
        })()
      `);
      L("Instant section HTML: " + instantSection);

      // Get final balance
      let balance = await eval_(`
        (function() {
          var text = document.body.innerText;
          var match = text.match(/Account balance \\$ ([\\d.]+)/);
          return match ? match[1] : 'unknown';
        })()
      `);
      L("\nFINAL BALANCE: $" + balance);

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
