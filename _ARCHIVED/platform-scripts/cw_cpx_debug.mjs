import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 45000);

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

    const clickAt = async (x, y) => {
      await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      await sleep(80);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    };

    (async () => {
      // 1. Get form details
      let r = await eval_(`
        (function() {
          var forms = document.querySelectorAll('form');
          return JSON.stringify(Array.from(forms).map(function(f) {
            return {
              action: f.action.substring(0, 200),
              method: f.method,
              id: f.id,
              class: (f.className || '').substring(0, 80),
              inputs: f.querySelectorAll('input').length,
              html: f.outerHTML.substring(0, 800)
            };
          }));
        })()
      `);
      L("Forms: " + r);

      // 2. Check the submit button details
      r = await eval_(`
        (function() {
          var btn = document.querySelector('.submit-btn-block');
          if (!btn) return 'no submit-btn-block found';
          return JSON.stringify({
            tag: btn.tagName,
            type: btn.type,
            class: btn.className,
            disabled: btn.disabled,
            onclick: btn.getAttribute('onclick'),
            form: btn.form ? btn.form.id : 'no form',
            parent: btn.parentElement.tagName + '.' + (btn.parentElement.className || '').substring(0, 60),
            html: btn.outerHTML.substring(0, 300)
          });
        })()
      `);
      L("Submit btn: " + r);

      // 3. Try selecting radio and checking state
      r = await eval_(`
        (function() {
          var radio = document.getElementById('US');
          if (!radio) return 'radio not found';
          var beforeChecked = radio.checked;
          radio.click();
          return 'before: ' + beforeChecked + ', after: ' + radio.checked;
        })()
      `);
      L("Radio click: " + r);
      await sleep(500);

      // 4. Check if there's reCAPTCHA
      r = await eval_(`
        (function() {
          var recaptcha = document.querySelector('[class*="recaptcha"], [class*="captcha"], iframe[src*="recaptcha"]');
          return recaptcha ? 'CAPTCHA FOUND: ' + (recaptcha.src || recaptcha.className).substring(0, 100) : 'no captcha';
        })()
      `);
      L("Captcha: " + r);

      // 5. Click the submit button directly (form.submit is shadowed by button[name=submit])
      r = await eval_(`
        (function() {
          var btn = document.getElementById('submitquestion1');
          if (!btn) return 'button not found';
          btn.click();
          return 'clicked submitquestion1';
        })()
      `);
      L("Submit click: " + r);
      await sleep(5000);

      // 6. Check if page changed
      let url = await eval_(`window.location.href`);
      L("URL after submit: " + url);
      let pageText = await eval_(`document.body.innerText.substring(0, 500)`);
      L("Page after: " + pageText.substring(0, 300));

      // The "Agreed" option is a radio button with id="1"
      r = await eval_(`
        (function() {
          var radio = document.getElementById('1');
          if (radio) { radio.click(); return 'clicked radio 1: checked=' + radio.checked; }
          return 'radio 1 not found';
        })()
      `);
      L("Agree radio: " + r);
      await sleep(500);

      // Click submit button
      r = await eval_(`
        (function() {
          var btn = document.getElementById('submitquestion1');
          if (btn) { btn.click(); return 'submitted'; }
          return 'btn not found';
        })()
      `);
      L("Submit: " + r);
      await sleep(8000);

      // Check what page we're on now
      url = await eval_(`window.location.href`);
      L("After agree URL: " + url);

      // Check for new tabs (survey might open in new tab)
      const tabs2 = await (await fetch(`${CDP_HTTP}/json`)).json();
      L("Tabs: " + tabs2.length);
      tabs2.forEach((t, i) => L("  [" + i + "] " + t.type + ": " + t.url.substring(0, 150)));

      pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("Page text:");
      L(pageText.substring(0, 2000));

      // Get inputs
      r = await eval_(`
        (function() {
          var inputs = document.querySelectorAll('input:not([type="hidden"]), select, textarea');
          return JSON.stringify(Array.from(inputs).filter(function(i) {
            return i.offsetParent !== null;
          }).map(function(i) {
            return { type: i.type, id: i.id, name: i.name, value: (i.value||'').substring(0,40), label: (i.labels&&i.labels[0])?i.labels[0].textContent.trim().substring(0,80):'' };
          }));
        })()
      `);
      L("Inputs: " + r);

      // Screenshot
      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_cpx_debug.png', Buffer.from(ss.data, 'base64'));
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
