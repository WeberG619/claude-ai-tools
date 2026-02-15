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
  const tab = tabs.find(t => t.type === "page");
  if (!tab) { console.log("No tab"); return; }

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

  // Navigate to Clickworker signup
  await send("Page.navigate", { url: "https://workplace.clickworker.com/en/users/new/" });
  await sleep(8000);

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 2000)`);
  console.log("\nPage:", r);

  // Check if we're on the signup form or if we're already logged in / on step 2
  if (r.includes('Step 1') && r.includes('Gender')) {
    // Still on step 1 - fix gender
    r = await eval_(`
      const sel = document.querySelector('#user_gender');
      if (sel) {
        sel.selectedIndex = 1; // Male
        sel.dispatchEvent(new Event('change', { bubbles: true }));
        return 'Set to: ' + sel.options[sel.selectedIndex].text;
      }
      return 'no select found';
    `);
    console.log("\nGender fix:", r);

    // Check all field values
    r = await eval_(`
      return JSON.stringify({
        gender: document.querySelector('#user_gender')?.options[document.querySelector('#user_gender')?.selectedIndex]?.text,
        firstName: document.querySelector('#user_first_name')?.value,
        lastName: document.querySelector('#user_last_name')?.value,
        username: document.querySelector('#user_username')?.value,
        email: document.querySelector('#user_email')?.value
      });
    `);
    console.log("Fields:", r);
  } else if (r.includes('Step 2') || r.includes('logged in') || r.includes('dashboard') || r.includes('Workplace')) {
    console.log("\nAlready past step 1!");
  }

  // Check for forms/buttons
  r = await eval_(`
    const inputs = document.querySelectorAll('input, select, textarea');
    return JSON.stringify(Array.from(inputs).filter(i => i.offsetParent !== null).map(i => ({
      type: i.type, name: i.name, value: i.value?.substring(0, 30)
    })));
  `);
  console.log("\nInputs:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
