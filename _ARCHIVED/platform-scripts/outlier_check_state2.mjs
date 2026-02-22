const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const targets = await (await fetch(`${CDP_HTTP}/json`)).json();
  const outlierTab = targets.find(t => t.type === "page" && t.url?.includes("outlier"));
  if (!outlierTab) { console.log("No Outlier tab found"); return; }

  const ws = new WebSocket(outlierTab.webSocketDebuggerUrl);
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

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);

  r = await eval_(`return document.body.innerText.substring(0, 5000)`);
  console.log("\nPage:", r);

  // Check for buttons
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button'))
      .filter(b => b.offsetParent !== null);
    return JSON.stringify(btns.map(b => ({
      text: b.textContent.trim().substring(0, 60),
      disabled: b.disabled
    })));
  `);
  console.log("\nButtons:", r);

  // Check if Persona iframe is still open
  r = await eval_(`
    const iframes = document.querySelectorAll('iframe');
    return JSON.stringify(Array.from(iframes).filter(f => f.src?.includes('persona')).map(f => ({
      src: f.src.substring(0, 80),
      w: f.offsetWidth,
      h: f.offsetHeight
    })));
  `);
  console.log("\nPersona iframe:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
