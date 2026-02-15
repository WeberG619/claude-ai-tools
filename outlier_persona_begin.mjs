const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const targets = await (await fetch(`${CDP_HTTP}/json`)).json();
  const personaTarget = targets.find(t => t.url?.includes('withpersona.com/widget'));
  if (!personaTarget) { console.log("No Persona target found"); return; }

  const ws = new WebSocket(personaTarget.webSocketDebuggerUrl);
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

  // Click "Begin verifying" button
  let r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.includes('Begin verifying'));
    if (btn) {
      btn.click();
      return 'clicked';
    }
    return 'not found';
  `);
  console.log("Begin verifying:", r);

  await sleep(5000);

  // Check what page shows now
  r = await eval_(`return document.body.innerText.substring(0, 3000)`);
  console.log("\nPersona content:", r);

  // Check for buttons
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button, a'))
      .filter(b => b.offsetParent !== null);
    return JSON.stringify(btns.map(b => ({
      tag: b.tagName,
      text: b.textContent.trim().substring(0, 50),
      href: b.href?.substring(0, 80) || ''
    })));
  `);
  console.log("\nButtons/links:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
