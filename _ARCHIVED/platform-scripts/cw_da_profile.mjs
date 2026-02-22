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
      // Go to main page and find profile/settings link
      L("=== FINDING PROFILE SETTINGS ===");
      await eval_(`window.location.href = 'https://app.dataannotation.tech/workers/starter_assessment_complete'`);
      await sleep(3000);

      // Click on user name menu or profile link
      let links = await eval_(`
        (function() {
          var results = [];
          document.querySelectorAll('a[href]').forEach(function(a) {
            results.push({ text: a.textContent.trim().substring(0, 60), href: a.href.substring(0, 150) });
          });
          return JSON.stringify(results);
        })()
      `);
      L("All links: " + links);

      // Try clicking on the user name
      let r = await eval_(`
        (function() {
          var els = document.querySelectorAll('a, button, [role="button"]');
          for (var i = 0; i < els.length; i++) {
            var t = els[i].textContent.trim();
            if (t.includes('Weber') || t.includes('profile') || t.includes('Profile') || t.includes('settings') || t.includes('Settings')) {
              els[i].click();
              return 'clicked: ' + t.substring(0, 40);
            }
          }
          return 'not found';
        })()
      `);
      L("Click profile: " + r);
      await sleep(3000);

      let url = await eval_(`window.location.href`);
      let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("\nURL: " + url);
      L("Page:\n" + pageText.substring(0, 2000));

      // Check for dropdown menu items
      let menuItems = await eval_(`
        (function() {
          var items = [];
          document.querySelectorAll('[class*="dropdown"], [class*="menu"], [role="menu"], [role="menuitem"], li a, [class*="nav"] a').forEach(function(el) {
            var t = el.textContent.trim();
            var h = el.href || '';
            if (t.length > 0 && t.length < 50) items.push({ text: t, href: h.substring(0, 120) });
          });
          return JSON.stringify(items.slice(0, 20));
        })()
      `);
      L("\nMenu items: " + menuItems);

      // Try visiting profile directly with different URL patterns
      L("\n=== TRYING PROFILE URLS ===");
      let urls = [
        'https://app.dataannotation.tech/workers/settings',
        'https://app.dataannotation.tech/workers/account',
        'https://app.dataannotation.tech/workers/edit',
        'https://app.dataannotation.tech/workers/skills'
      ];
      for (const u of urls) {
        await eval_(`window.location.href = '${u}'`);
        await sleep(2000);
        url = await eval_(`window.location.href`);
        pageText = await eval_(`document.body.innerText.substring(0, 500)`);
        if (!pageText.includes('not found') && !pageText.includes('Page not found')) {
          L("FOUND: " + url + "\n" + pageText.substring(0, 400));
          break;
        } else {
          L("404: " + u);
        }
      }

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_da_profile.png', Buffer.from(ss.data, 'base64'));

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
