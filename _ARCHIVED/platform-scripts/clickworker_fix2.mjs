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

  // Set gender to Male
  let r = await eval_(`
    const sel = document.querySelector('#user_gender');
    sel.value = 'm';
    sel.dispatchEvent(new Event('change', { bubbles: true }));
    return sel.options[sel.selectedIndex].text;
  `);
  console.log("Gender:", r);

  // Verify all fields
  r = await eval_(`
    return JSON.stringify({
      gender: document.querySelector('#user_gender')?.options[document.querySelector('#user_gender')?.selectedIndex]?.text,
      firstName: document.querySelector('#user_first_name')?.value,
      lastName: document.querySelector('#user_last_name')?.value,
      username: document.querySelector('#user_username')?.value,
      email: document.querySelector('#user_email')?.value,
      password: document.querySelector('#user_password')?.value ? '(set)' : '(empty)',
      passwordConfirm: document.querySelector('#user_password_confirmation')?.value ? '(set)' : '(empty)'
    });
  `);
  console.log("All fields:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
