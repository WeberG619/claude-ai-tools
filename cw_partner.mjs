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
      // Click on CPX Research from the jobs page
      // First find and click the CPX Research link
      let r = await eval_(`
        (function() {
          var links = document.querySelectorAll('a');
          for (var i = 0; i < links.length; i++) {
            if (links[i].textContent.includes('CPX Research')) {
              return links[i].href;
            }
          }
          // Try looking for job cards
          var cards = document.querySelectorAll('[class*="job"], [class*="card"], .panel');
          var found = [];
          for (var j = 0; j < cards.length; j++) {
            if (cards[j].textContent.includes('CPX Research')) {
              var a = cards[j].querySelector('a');
              if (a) found.push(a.href);
            }
          }
          return found.length > 0 ? found[0] : 'NOT FOUND';
        })()
      `);
      L("CPX Link: " + r);

      // Navigate to CPX Research job page
      if (r && r !== 'NOT FOUND') {
        await send("Page.navigate", { url: r });
      } else {
        // Try the known job ID
        await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs/1072443/edit" });
      }
      await sleep(5000);

      let url = await eval_(`window.location.href`);
      L("URL: " + url);
      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("Page: " + pageText.substring(0, 800));

      // Handle any agreements
      let hasAgree = await eval_(`
        (function() {
          var btns = document.querySelectorAll('input[type="submit"], button');
          for (var i = 0; i < btns.length; i++) {
            if (btns[i].value === 'Agree' || btns[i].textContent.includes('Agree')) {
              btns[i].click();
              return 'clicked agree';
            }
          }
          return 'no agree button';
        })()
      `);
      L("Agree: " + hasAgree);
      if (hasAgree === 'clicked agree') {
        await sleep(4000);
        url = await eval_(`window.location.href`);
        L("After agree URL: " + url);
        pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
        L("After agree page: " + pageText.substring(0, 500));
      }

      // Get iframes
      let iframes = await eval_(`
        (function() {
          var iframes = document.querySelectorAll('iframe');
          return JSON.stringify(Array.from(iframes).map(function(f) {
            return { src: (f.src || '').substring(0, 300), w: f.width, h: f.height, id: f.id };
          }));
        })()
      `);
      L("Iframes: " + iframes);

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_cpx_screen.png', Buffer.from(ss.data, 'base64'));
      L("Screenshot saved");

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
