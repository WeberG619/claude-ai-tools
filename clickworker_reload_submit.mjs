const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

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

  // Navigate back to the registration page
  await send("Page.navigate", { url: "https://workplace.clickworker.com/en/users/new/" });
  await sleep(5000);

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);

  // Check what step we're on
  r = await eval_(`
    const active = document.querySelector('.nav-link.active');
    return active?.textContent?.trim().substring(0, 30) || 'no active step';
  `);
  console.log("Active step:", r);

  // Get the page text briefly
  r = await eval_(`
    const text = document.body.innerText;
    // Find step-related text
    const lines = text.split('\\n').filter(l => l.trim().length > 0);
    return lines.slice(0, 30).join('\\n');
  `);
  console.log("\nPage start:", r);

  // Check for reCAPTCHA sitekey from the bundled JS
  r = await eval_(`
    // Look in all script sources for the sitekey
    const allScripts = Array.from(document.querySelectorAll('script'));
    for (const s of allScripts) {
      if (s.textContent.includes('recaptcha') || s.textContent.includes('sitekey') || s.textContent.includes('6L')) {
        const match = s.textContent.match(/6L[a-zA-Z0-9_-]{38}/);
        if (match) return 'Found sitekey in inline: ' + match[0];
      }
    }

    // Check the recaptcha JS bundle
    const recaptchaBundle = document.querySelector('script[src*="recaptcha-"]');
    if (recaptchaBundle) return 'Bundle src: ' + recaptchaBundle.src;

    // Check if grecaptcha has getResponse working now
    try {
      const resp = grecaptcha.getResponse();
      return 'getResponse: ' + (resp?.substring(0, 20) || 'empty');
    } catch(e) {
      return 'getResponse error: ' + e.message;
    }
  `);
  console.log("\nSitekey search:", r);

  // Fetch the recaptcha bundle to find the sitekey
  r = await eval_(`
    const scripts = Array.from(document.querySelectorAll('script[src]'));
    const recaptchaScript = scripts.find(s => s.src.includes('recaptcha-'));
    if (!recaptchaScript) return 'no recaptcha bundle';

    const resp = await fetch(recaptchaScript.src);
    const text = await resp.text();
    // Find sitekey pattern (starts with 6L)
    const match = text.match(/6L[a-zA-Z0-9_-]{38}/);
    if (match) return 'Sitekey: ' + match[0];

    // Try other patterns
    const match2 = text.match(/sitekey['":\\s]+['"]([^'"]+)['"]/);
    if (match2) return 'Sitekey2: ' + match2[1];

    return 'No sitekey found in bundle (length: ' + text.length + ')';
  `);
  console.log("\nBundle sitekey:", r);

  // Check visible form fields and checkboxes
  r = await eval_(`
    const cbs = document.querySelectorAll('input[type="checkbox"]');
    return JSON.stringify(Array.from(cbs).filter(cb => cb.offsetParent !== null).map(cb => ({
      name: cb.name, id: cb.id, checked: cb.checked,
      label: cb.parentElement?.textContent?.trim().substring(0, 60)
    })));
  `);
  console.log("\nVisible checkboxes:", r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_state.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
