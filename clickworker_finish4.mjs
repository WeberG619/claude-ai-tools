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

  // Check the state of everything
  let r = await eval_(`
    const cb = document.querySelector('#mobile_app_installed');
    const submit = document.querySelector('input[type="submit"]');
    const form = submit?.closest('form');

    // Ensure checkbox is checked
    if (cb && !cb.checked) {
      cb.checked = true;
      cb.dispatchEvent(new Event('change', { bubbles: true }));
    }

    return JSON.stringify({
      checkboxChecked: cb?.checked,
      submitValue: submit?.value,
      submitDisabled: submit?.disabled,
      formAction: form?.action,
      formMethod: form?.method,
      formId: form?.id,
      // Check what step we're on - find the active step
      activeStep: document.querySelector('.nav-link.active')?.textContent?.trim().substring(0, 20),
      // Check for any hidden required fields
      requiredFields: Array.from(form?.querySelectorAll('[required]') || []).map(f => ({
        name: f.name, type: f.type, value: f.value?.substring(0, 20), checked: f.checked
      }))
    });
  `);
  console.log("State:", r);

  // Try clicking the submit via JS .click()
  r = await eval_(`
    const submit = document.querySelector('input[type="submit"]');
    if (submit) {
      submit.click();
      return 'clicked';
    }
    return 'not found';
  `);
  console.log("\nJS click result:", r);

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
