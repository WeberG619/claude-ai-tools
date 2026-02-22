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

  // Investigate the wizard JS and form event handlers
  let r = await eval_(`
    // Check for event listeners on the form
    const form = document.querySelector('#registration_form');
    const submit = document.querySelector('input[type="submit"]');

    // Check what happens on submit - look at jQuery or vanilla event handlers
    const hasJQuery = typeof jQuery !== 'undefined' || typeof $ !== 'undefined';

    // Check the submit button's onclick
    const submitOnclick = submit?.onclick?.toString()?.substring(0, 200) || 'none';

    // Check the form's onsubmit
    const formOnsubmit = form?.onsubmit?.toString()?.substring(0, 200) || 'none';

    // Look at the recaptcha config
    let recaptchaInfo = null;
    if (typeof grecaptcha !== 'undefined') {
      try {
        // Check for invisible recaptcha with callback
        const badge = document.querySelector('.grecaptcha-badge');
        recaptchaInfo = {
          badgeStyle: badge ? window.getComputedStyle(badge).display : 'no badge',
          tokenLength: document.querySelector('[name="g-recaptcha-response"]')?.value?.length || 0
        };
      } catch(e) {
        recaptchaInfo = 'error: ' + e.message;
      }
    }

    // Check for step wizard JS
    const wizardScripts = Array.from(document.querySelectorAll('script'))
      .filter(s => s.textContent.includes('step') || s.textContent.includes('wizard') || s.textContent.includes('registration'))
      .map(s => s.textContent.substring(0, 200));

    return JSON.stringify({
      hasJQuery,
      submitOnclick,
      formOnsubmit,
      recaptchaInfo,
      wizardScriptsCount: wizardScripts.length,
      wizardSnippets: wizardScripts.slice(0, 3)
    }, null, 2);
  `);
  console.log("Investigation:", r);

  // Try triggering reCAPTCHA execute and then submit
  r = await eval_(`
    // Try executing reCAPTCHA first
    if (typeof grecaptcha !== 'undefined') {
      try {
        // Get the widget ID
        const widgets = grecaptcha.getResponse ? grecaptcha.getResponse() : null;

        // Try executing with the sitekey
        const sitekey = document.querySelector('[data-sitekey]')?.dataset?.sitekey;

        return JSON.stringify({
          currentResponse: widgets?.substring(0, 30) || 'empty',
          sitekey: sitekey?.substring(0, 20) || 'none found'
        });
      } catch(e) {
        return 'grecaptcha error: ' + e.message;
      }
    }
    return 'no grecaptcha';
  `);
  console.log("\nreCAPTCHA state:", r);

  // Let me try: execute grecaptcha, wait for token, then submit
  r = await eval_(`
    return new Promise((resolve) => {
      try {
        // Execute invisible recaptcha
        grecaptcha.execute();

        // Wait for the token to be populated
        let attempts = 0;
        const check = setInterval(() => {
          const token = document.querySelector('[name="g-recaptcha-response"]')?.value;
          attempts++;
          if (token && token.length > 50) {
            clearInterval(check);
            // Now submit the form
            const form = document.querySelector('#registration_form');
            form.submit();
            resolve('token obtained (' + token.length + ' chars), form submitted');
          }
          if (attempts > 20) {
            clearInterval(check);
            resolve('timeout waiting for token, current length: ' + (token?.length || 0));
          }
        }, 500);
      } catch(e) {
        resolve('error: ' + e.message);
      }
    });
  `);
  console.log("\nreCAPTCHA execute + submit:", r);

  await sleep(10000);

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
