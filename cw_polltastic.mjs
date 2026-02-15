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

    const clickAt = async (x, y) => {
      await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      await sleep(80);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    };

    (async () => {
      // Navigate to PollTastic via Clickworker job page
      await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs/1225955/edit" });
      await sleep(8000);

      let url = await eval_(`window.location.href`);
      L("URL: " + url);
      let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("Page:");
      L(pageText.substring(0, 1500));

      // Look for agree/start button
      let r = await eval_(`
        (function() {
          var btns = document.querySelectorAll('input[type="submit"], button');
          var found = [];
          for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].value || btns[i].textContent || '').trim();
            found.push(t);
            if (t === 'Agree' || t.includes('Start') || t.includes('Accept') || t === 'OK') {
              btns[i].click();
              return 'clicked: ' + t;
            }
          }
          return 'no start button. Buttons: ' + found.join(', ');
        })()
      `);
      L("Start: " + r);
      await sleep(5000);

      // Check for iframes
      r = await eval_(`
        (function() {
          var iframes = document.querySelectorAll('iframe');
          return JSON.stringify(Array.from(iframes).map(function(f) {
            return { src: (f.src||'').substring(0,400), id: f.id, w: f.offsetWidth, h: f.offsetHeight };
          }));
        })()
      `);
      L("Iframes: " + r);

      // Navigate directly to PollTastic URL
      const pollUrl = "https://surveys.ayet.io/?adSlot=23863&externalIdentifier=25671709&custom_1=468201993";
      await send("Page.navigate", { url: pollUrl });
      await sleep(8000);

      url = await eval_(`window.location.href`);
      L("\nPollTastic URL: " + url);
      pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("Page:");
      L(pageText.substring(0, 2000));

      // Get all interactive elements
      r = await eval_(`
        (function() {
          var els = document.querySelectorAll('a, button, [role="button"], input[type="submit"]');
          var result = [];
          for (var i = 0; i < els.length; i++) {
            var rect = els[i].getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
              result.push({
                tag: els[i].tagName,
                text: els[i].textContent.trim().substring(0, 80),
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

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_polltastic.png', Buffer.from(ss.data, 'base64'));
      L("Screenshot saved");

      // Try clicking "Start Now!" to begin profile
      r = await eval_(`
        (function() {
          var all = document.querySelectorAll('a, button, div, span');
          for (var i = 0; i < all.length; i++) {
            var t = all[i].textContent.trim();
            if (t === 'Start Now!' || t.includes('Start Now') || t === 'Accept') {
              var rect = all[i].getBoundingClientRect();
              if (rect.width > 0) {
                all[i].click();
                return 'clicked: ' + t + ' at (' + Math.round(rect.x + rect.width/2) + ',' + Math.round(rect.y + rect.height/2) + ')';
              }
            }
          }
          return 'Start Now not found';
        })()
      `);
      L("Start Now: " + r);

      if (!r.includes('not found')) {
        await sleep(5000);
        url = await eval_(`window.location.href`);
        L("After Start URL: " + url);
        pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
        L("After Start Page:");
        L(pageText.substring(0, 2000));

        const ss2 = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_polltastic2.png', Buffer.from(ss2.data, 'base64'));
        L("Screenshot 2 saved");
      }

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
