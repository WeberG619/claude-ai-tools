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
      // Navigate back to the avatar survey job page
      await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs/1262735/edit" });
      await sleep(5000);

      let url = await eval_(`window.location.href`);
      L("URL: " + url);

      if (url.includes('two_fa')) {
        L("BLOCKED BY 2FA");
        ws.close();
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
        process.exit(0);
      }

      // Enter the code
      let r = await eval_(`
        (function() {
          var input = document.getElementById('output_467772889__code');
          if (!input) {
            // Try finding by name
            input = document.querySelector('input[name*="code"]');
          }
          if (input) {
            var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(input, 'lsdfuj3847');
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            return 'entered code: ' + input.value;
          }
          return 'code field not found';
        })()
      `);
      L("Code: " + r);

      // Check the consent checkbox
      r = await eval_(`
        (function() {
          var checkbox = document.querySelector('input[type="checkbox"][name*="consent"]');
          if (checkbox) {
            checkbox.checked = true;
            checkbox.dispatchEvent(new Event('change', { bubbles: true }));
            checkbox.click();
            return 'consent checked';
          }
          return 'no consent checkbox';
        })()
      `);
      L("Consent: " + r);
      await sleep(500);

      // Click Send/Submit
      r = await eval_(`
        (function() {
          var btn = document.querySelector('input[type="submit"][name="submit_job"]');
          if (btn) { btn.click(); return 'submitted'; }
          return 'no submit button';
        })()
      `);
      L("Submit: " + r);
      await sleep(5000);

      // Check result
      url = await eval_(`window.location.href`);
      L("Result URL: " + url);

      let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
      L("Result page: " + pageText.substring(0, 1000));

      // Check balance
      r = await eval_(`
        (function() {
          var text = document.body.innerText;
          var match = text.match(/Account balance \\$ ([\\d.]+)/);
          return match ? match[1] : 'unknown';
        })()
      `);
      L("Balance: $" + r);

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
