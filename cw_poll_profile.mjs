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
      // Navigate to PollTastic directly
      await send("Page.navigate", { url: "https://surveys.ayet.io/?adSlot=23863&externalIdentifier=25671709&custom_1=468201993" });
      await sleep(6000);

      // Accept privacy policy
      let r = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim();
            if (t === 'Accept') {
              btns[i].click();
              return 'clicked Accept';
            }
          }
          return 'Accept not found';
        })()
      `);
      L("Privacy: " + r);
      await sleep(2000);

      // Click "Start Now!" button
      r = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim();
            if (t === 'Start Now!' || t.includes('Start Now')) {
              btns[i].click();
              return 'clicked: ' + t;
            }
          }
          return 'Start Now not found';
        })()
      `);
      L("Start: " + r);
      await sleep(5000);

      let url = await eval_(`window.location.href`);
      L("URL: " + url);
      let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("Page:");
      L(pageText.substring(0, 2000));

      // Get elements
      r = await eval_(`
        (function() {
          var result = { radios: [], inputs: [], selects: [], buttons: [] };
          document.querySelectorAll('input[type="radio"]').forEach(function(r) {
            result.radios.push({ id: r.id, name: r.name, value: r.value, label: (r.labels?.[0]?.textContent||'').trim().substring(0,60) });
          });
          document.querySelectorAll('input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]):not([type="submit"])').forEach(function(i) {
            if (i.offsetParent) result.inputs.push({ type: i.type, id: i.id, name: i.name, placeholder: (i.placeholder||'').substring(0,40) });
          });
          document.querySelectorAll('select').forEach(function(s) {
            if (s.offsetParent) result.selects.push({ id: s.id, name: s.name, options: Array.from(s.options).slice(0,10).map(o => o.text) });
          });
          document.querySelectorAll('button, input[type="submit"]').forEach(function(b) {
            if (b.offsetWidth > 0) result.buttons.push({ text: (b.textContent||b.value||'').trim().substring(0,60) });
          });
          return JSON.stringify(result);
        })()
      `);
      L("Elements: " + r);

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_poll_profile.png', Buffer.from(ss.data, 'base64'));
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
