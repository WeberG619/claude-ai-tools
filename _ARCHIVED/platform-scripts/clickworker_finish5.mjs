const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("clickworker"));
  if (!tab) { console.log("No Clickworker tab"); return; }

  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
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
    const i = id++;
    pending.set(i, { res, rej });
    ws.send(JSON.stringify({ id: i, method, params }));
  });
  const eval_ = async (expr) => {
    const r = await send("Runtime.evaluate", {
      expression: `(async () => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };

  // Check for reCAPTCHA
  let r = await eval_(`
    const recaptcha = document.querySelector('.g-recaptcha, [data-sitekey], .grecaptcha-badge, iframe[src*="recaptcha"]');
    const scripts = Array.from(document.querySelectorAll('script[src*="recaptcha"]'));
    const recaptchaToken = document.querySelector('[name="g-recaptcha-response"]');
    return JSON.stringify({
      recaptchaElement: recaptcha ? { tag: recaptcha.tagName, class: recaptcha.className?.substring(0, 50), sitekey: recaptcha.dataset?.sitekey?.substring(0, 20) } : null,
      recaptchaScripts: scripts.map(s => s.src.substring(0, 80)),
      tokenField: recaptchaToken ? { name: recaptchaToken.name, value: recaptchaToken.value?.substring(0, 20) || 'empty' } : null,
      grecaptchaExists: typeof grecaptcha !== 'undefined'
    });
  `);
  console.log("reCAPTCHA check:", r);

  // Check for JS errors by listening to console
  r = await eval_(`
    const errors = [];
    const origError = console.error;
    console.error = (...args) => { errors.push(args.join(' ')); origError.apply(console, args); };

    // Try form.requestSubmit
    const form = document.querySelector('#registration_form');
    const submit = document.querySelector('input[type="submit"]');

    try {
      if (form && submit) {
        form.requestSubmit(submit);
        return 'requestSubmit called - errors: ' + JSON.stringify(errors);
      }
      return 'form or submit not found';
    } catch(e) {
      return 'Error: ' + e.message + ' - console errors: ' + JSON.stringify(errors);
    }
  `);
  console.log("\nrequestSubmit:", r);

  await sleep(12000);

  r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 3000)`);
  console.log("\nPage:", r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_state.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
