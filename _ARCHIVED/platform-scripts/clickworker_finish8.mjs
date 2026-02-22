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

  // Get the full submit handler
  let r = await eval_(`
    const form = document.querySelector('#registration_form');
    const events = jQuery._data(form, 'events');
    if (events && events.submit) {
      return events.submit[0].handler.toString();
    }
    return 'no handler';
  `);
  console.log("Full handler:", r);

  // Check form validity
  r = await eval_(`
    const form = document.querySelector('#registration_form');
    return JSON.stringify({
      hasNeedsValidation: form.classList.contains('needs-validation'),
      checkValidity: form.checkValidity(),
      formClasses: form.className.substring(0, 100)
    });
  `);
  console.log("\nForm validation:", r);

  // Check which fields fail validation
  r = await eval_(`
    const form = document.querySelector('#registration_form');
    const invalids = [];
    form.querySelectorAll('input, select, textarea').forEach(el => {
      if (!el.checkValidity()) {
        invalids.push({
          name: el.name,
          type: el.type,
          validity: {
            valueMissing: el.validity.valueMissing,
            typeMismatch: el.validity.typeMismatch,
            patternMismatch: el.validity.patternMismatch,
            tooShort: el.validity.tooShort,
            customError: el.validity.customError
          },
          validationMessage: el.validationMessage?.substring(0, 60),
          value: el.type === 'password' ? '***' : el.value?.substring(0, 20)
        });
      }
    });
    return JSON.stringify(invalids, null, 2);
  `);
  console.log("\nInvalid fields:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
