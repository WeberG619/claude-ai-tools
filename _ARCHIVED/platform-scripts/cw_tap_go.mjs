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
      // Navigate to TapResearch directly
      const tapUrl = "https://www.tapresearch.com/router/offers/d6ed80f2feca2bbe1fec6f8c2c29ff8d/pre_entry?sdk=false&uid=25671709&did=&app_id=2316&offer_reason=0&timestamp=1770633403&tid=919ee19884b43cc25c838eb54cc450ed57eadcd4&sech=a9f0228779132860d9668ed7a906bf800f785602&pass_through_values=eyJqb2JfaWQiOjQ2ODIwMTk4NX0=";
      await send("Page.navigate", { url: tapUrl });
      await sleep(8000);

      let url = await eval_(`window.location.href`);
      L("URL: " + url);
      let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("Page text:");
      L(pageText.substring(0, 2000));

      // Get links/buttons
      let r = await eval_(`
        (function() {
          var els = document.querySelectorAll('a, button, [role="button"]');
          var result = [];
          for (var i = 0; i < els.length; i++) {
            var rect = els[i].getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
              result.push({
                tag: els[i].tagName,
                text: els[i].textContent.trim().substring(0, 60),
                href: (els[i].href || '').substring(0, 200),
                x: Math.round(rect.x + rect.width/2),
                y: Math.round(rect.y + rect.height/2)
              });
            }
          }
          return JSON.stringify(result.slice(0, 20));
        })()
      `);
      L("Clickable: " + r);

      // Get inputs
      r = await eval_(`
        (function() {
          var inputs = document.querySelectorAll('input, select, textarea');
          return JSON.stringify(Array.from(inputs).filter(function(i) {
            return i.offsetParent !== null;
          }).map(function(i) {
            return { type: i.type, id: i.id, name: i.name, label: (i.labels&&i.labels[0])?i.labels[0].textContent.trim().substring(0,60):'' };
          }));
        })()
      `);
      L("Inputs: " + r);

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_tap_direct.png', Buffer.from(ss.data, 'base64'));
      L("Screenshot saved");

      // Also try Inbrain
      L("\n=== INBRAIN ===");
      const inbrainUrl = "https://www.surveyb.in/configuration?params=SFRvMmNyUDJ6R00ybVM2ZVg1WVZBcWdNZzI3ZElwcTlsQkNzdkZUNWxqK3crSTdCRjBvUm93WThCV0VXQVBvOXIxdGVNZVV1MjI2UHh4Yytkc1lQZTBlYWdRbmhWMUVLbytSc0pnTENEbkVlZmFKYzE4clNSb0ZNL216RCtGYis5SGV6MGpvUVFXU1pIcFF6YUl1NVdsdGlOWkNGMDhBV1JTZk1XcWlicU5rZTJxR1IwUUxueDF4OFlhYS90VTFo";
      await send("Page.navigate", { url: inbrainUrl });
      await sleep(8000);

      url = await eval_(`window.location.href`);
      L("URL: " + url);
      pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("Page: " + pageText.substring(0, 2000));

      const ss2 = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_inbrain_screen.png', Buffer.from(ss2.data, 'base64'));
      L("Inbrain screenshot saved");

      // Also try PollTastic
      L("\n=== POLLTASTIC ===");
      const pollUrl = "https://surveys.ayet.io/surveys?adSlot=23863&externalIdentifier=25671709&custom_1=468201993";
      await send("Page.navigate", { url: pollUrl });
      await sleep(8000);

      url = await eval_(`window.location.href`);
      L("URL: " + url);
      pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("Page: " + pageText.substring(0, 2000));

      const ss3 = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_poll_screen.png', Buffer.from(ss3.data, 'base64'));
      L("PollTastic screenshot saved");

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
