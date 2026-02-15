const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found`);
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
  const pending = new Map();
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p.rej(new Error(msg.error.message));
      else p.res(msg.result);
    }
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const msgId = id++;
    pending.set(msgId, { res, rej });
    ws.send(JSON.stringify({ id: msgId, method, params }));
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

async function main() {
  let { ws, send, eval_ } = await connectToPage("accounts.google.com");

  // Type email into the identifier field
  let r = await eval_(`
    const inp = document.getElementById('identifierId');
    if (inp) {
      inp.focus();
      inp.value = '';
      return 'focused';
    }
    return 'not found';
  `);
  console.log("Focus:", r);
  await sleep(300);

  // Type the email
  await send("Input.insertText", { text: "weberg619@gmail.com" });
  await sleep(500);

  // Click Next
  r = await eval_(`
    const nextBtn = Array.from(document.querySelectorAll('button'))
      .find(el => el.textContent.trim() === 'Next' && el.offsetParent !== null);
    if (nextBtn) {
      nextBtn.click();
      return 'clicked next';
    }
    return 'not found';
  `);
  console.log("Next:", r);
  await sleep(5000);

  // Check what's on screen now
  ws.close(); await sleep(1000);

  // Check all tabs
  const tabs = await (await fetch(CDP_HTTP + "/json")).json();
  const googleTab = tabs.find(t => t.type === "page" && t.url.includes("google.com"));
  const outlierTab = tabs.find(t => t.type === "page" && t.url.includes("outlier"));

  if (googleTab) {
    ({ ws, send, eval_ } = await connectToPage("google.com"));
    r = await eval_(`return document.body.innerText.substring(0, 3000)`);
    console.log("\nGoogle page:");
    console.log(r);

    // Check for password field
    r = await eval_(`
      const pwInput = document.querySelector('input[type="password"]');
      return pwInput ? 'password field found' : 'no password field';
    `);
    console.log("\nPassword field:", r);

    ws.close();
  }

  if (outlierTab && (!googleTab || outlierTab.id !== googleTab.id)) {
    const conn = await connectToPage("outlier");
    if (conn) {
      r = await conn.eval_(`return window.location.href`);
      console.log("\nOutlier URL:", r);
      r = await conn.eval_(`return document.body.innerText.substring(0, 2000)`);
      console.log("\nOutlier page:", r);
      conn.ws.close();
    }
  }
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
