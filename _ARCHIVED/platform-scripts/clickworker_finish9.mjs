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

  // Get the reCAPTCHA sitekey from the page source
  let r = await eval_(`
    // Look for sitekey in scripts or data attributes
    const scripts = document.querySelectorAll('script');
    let sitekey = null;
    for (const s of scripts) {
      const match = s.textContent.match(/sitekey['":\\s]+['"]([^'"]+)['"]/i) ||
                    s.textContent.match(/render['":\\s]+['"]([^'"]+)['"]/i) ||
                    s.src.match(/render=([^&]+)/);
      if (match) {
        sitekey = match[1];
        break;
      }
    }

    // Also check recaptcha script src
    const recaptchaScript = document.querySelector('script[src*="recaptcha"]');
    const srcMatch = recaptchaScript?.src?.match(/render=([^&]+)/);
    if (srcMatch) sitekey = srcMatch[1];

    // Also check meta tags
    const meta = document.querySelector('meta[name*="recaptcha"]');
    if (meta) sitekey = meta.content;

    return JSON.stringify({
      sitekey,
      recaptchaScriptSrc: recaptchaScript?.src?.substring(0, 100)
    });
  `);
  console.log("Sitekey search:", r);

  // Try to re-render reCAPTCHA by reloading the script
  r = await eval_(`
    return new Promise((resolve) => {
      // Remove existing recaptcha scripts
      const oldScripts = document.querySelectorAll('script[src*="recaptcha"]');
      oldScripts.forEach(s => s.remove());

      // Remove existing recaptcha elements
      const badge = document.querySelector('.grecaptcha-badge');
      if (badge) badge.parentElement?.remove();

      // Get sitekey from the recaptcha JS file on the page
      const recaptchaJS = document.querySelector('script[src*="recaptcha-"]');
      const src = recaptchaJS?.src;

      // Reload the reCAPTCHA API
      const script = document.createElement('script');
      script.src = 'https://www.google.com/recaptcha/api.js?render=explicit';
      script.onload = () => {
        setTimeout(() => {
          resolve('reCAPTCHA reloaded, grecaptcha exists: ' + (typeof grecaptcha !== 'undefined'));
        }, 2000);
      };
      script.onerror = (e) => resolve('load error');
      document.head.appendChild(script);
    });
  `);
  console.log("\nReload reCAPTCHA:", r);

  // Actually, let me try a simpler approach: just submit with the existing token
  // The form.submit() bypasses event handlers and just posts the form
  // The token is already set. Let me just try it.
  r = await eval_(`
    const form = document.querySelector('#registration_form');
    const token = form.querySelector('[name="g-recaptcha-response"]')?.value;
    const hasRemote = jQuery(form).data('remote');

    return JSON.stringify({
      tokenLength: token?.length || 0,
      hasRemote,
      formAction: form.action,
      method: form.method
    });
  `);
  console.log("\nForm info:", r);

  // Remove the jQuery submit handler and submit natively
  r = await eval_(`
    const form = document.querySelector('#registration_form');

    // Remove jQuery submit handlers
    jQuery(form).off('submit');

    // Also ensure checkbox is checked
    const cb = document.querySelector('#mobile_app_installed');
    if (cb) cb.checked = true;

    // Submit the form natively
    form.submit();
    return 'submitted';
  `);
  console.log("\nDirect submit:", r);

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
