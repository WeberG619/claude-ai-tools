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
      // Click Sign In
      L("=== CLICKING SIGN IN ===");
      let r = await eval_(`
        (function() {
          var els = document.querySelectorAll('a, button, [role="button"], input[type="submit"]');
          for (var i = 0; i < els.length; i++) {
            var t = els[i].textContent.trim().toLowerCase();
            if (t === 'sign in' || t === 'login' || t === 'log in') {
              els[i].click();
              return 'clicked: ' + els[i].textContent.trim();
            }
          }
          return 'not found';
        })()
      `);
      L("Sign in: " + r);
      await sleep(8000);

      let url = await eval_(`window.location.href`);
      let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
      L("\nURL: " + url);
      L("Page:\n" + pageText.substring(0, 1000));

      // Check if Microsoft login page
      if (url.includes('login.microsoftonline') || url.includes('login.live') || url.includes('microsoft')) {
        L("\n=== MICROSOFT LOGIN ===");

        // Check for email input
        let fields = await eval_(`
          (function() {
            var inputs = [];
            document.querySelectorAll('input:not([type="hidden"])').forEach(function(i) {
              inputs.push({ type: i.type, name: i.name, id: i.id, placeholder: (i.placeholder||'').substring(0,40), value: i.value.substring(0,20) });
            });
            return JSON.stringify(inputs);
          })()
        `);
        L("Fields: " + fields);

        // Enter the Microsoft email
        r = await eval_(`
          (function() {
            var inp = document.querySelector('input[type="email"], input[name="loginfmt"], input#i0116');
            if (!inp) return 'no email field';
            inp.focus();
            inp.value = 'cw_25671709@hotmail.com';
            inp.dispatchEvent(new Event('input', { bubbles: true }));
            inp.dispatchEvent(new Event('change', { bubbles: true }));
            return 'entered email';
          })()
        `);
        L("Email: " + r);
        await sleep(1000);

        // Click Next
        r = await eval_(`
          (function() {
            var btn = document.querySelector('input[type="submit"], button[type="submit"], #idSIButton9');
            if (btn) { btn.click(); return 'clicked next'; }
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
              if (btns[i].textContent.trim().toLowerCase() === 'next') { btns[i].click(); return 'clicked next button'; }
            }
            return 'no next button';
          })()
        `);
        L("Next: " + r);
        await sleep(5000);

        url = await eval_(`window.location.href`);
        pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
        L("\nAfter email - URL: " + url);
        L("Page:\n" + pageText.substring(0, 1000));

        // Check for password field
        fields = await eval_(`
          (function() {
            var inputs = [];
            document.querySelectorAll('input:not([type="hidden"])').forEach(function(i) {
              inputs.push({ type: i.type, name: i.name, id: i.id });
            });
            return JSON.stringify(inputs);
          })()
        `);
        L("Fields: " + fields);
      }

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_uhrs_login.png', Buffer.from(ss.data, 'base64'));
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
