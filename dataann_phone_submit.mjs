const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found for: ${urlMatch}`);
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
  return { ws, send, eval_ };
}

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function typeText(send, text) {
  for (const ch of text) {
    await send("Input.dispatchKeyEvent", { type: "keyDown", text: ch });
    await send("Input.dispatchKeyEvent", { type: "keyUp", text: ch });
    await sleep(30);
  }
}

(async () => {
  let { ws, send, eval_ } = await connectToPage("app.dataannotation");

  // Focus and click on the phone input
  let r = await eval_(`
    const tel = document.querySelector('input[type="tel"]');
    if (tel) {
      const rect = tel.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), val: tel.value });
    }
    return 'not found';
  `);
  console.log("Phone input:", r);

  if (r !== 'not found') {
    const info = JSON.parse(r);
    // Click on the phone field
    await clickAt(send, info.x, info.y);
    await sleep(300);

    // Select all existing text and delete it, then type the number
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "End" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "End" });
    await sleep(100);

    // Type the phone number digits
    await typeText(send, "7865879726");
    await sleep(500);

    // Check what the phone field now shows
    r = await eval_(`
      const tel = document.querySelector('input[type="tel"]');
      const hidden = document.querySelector('input[name="user[phone]"]');
      return JSON.stringify({ telValue: tel?.value, hiddenValue: hidden?.value });
    `);
    console.log("Phone values after typing:", r);
  }

  await sleep(500);

  // Find and click submit button ("Looks good!")
  r = await eval_(`
    const submit = document.querySelector('input[type="submit"][value="Looks good!"]');
    if (submit) {
      const rect = submit.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    // Try button approach
    const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Looks good'));
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: btn.textContent.trim() });
    }
    return 'not found';
  `);
  console.log("Submit button:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    await clickAt(send, pos.x, pos.y);
    console.log("Clicked submit");

    await sleep(8000);

    // Check where we ended up
    r = await eval_(`return window.location.href`);
    console.log("\nURL after submit:", r);
    r = await eval_(`return document.body.innerText.substring(0, 5000)`);
    console.log("\nPage:", r);
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
