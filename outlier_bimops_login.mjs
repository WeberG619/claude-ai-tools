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
  // Step 1: Cancel the current consent screen
  let { ws, send, eval_ } = await connectToPage("accounts.google.com");

  let r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(el => el.textContent.trim() === 'Cancel');
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return 'not found';
  `);
  console.log("Cancel:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    await clickAt(send, pos.x, pos.y);
    console.log("Cancelled consent");
  }
  await sleep(4000);
  ws.close();
  await sleep(1000);

  // Step 2: Check where we are now
  let tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  console.log("\nTabs after cancel:");
  tabs.filter(t => t.type === "page").forEach(t => console.log("  " + t.url.substring(0, 100)));

  // Find the outlier or main page
  let targetTab = tabs.find(t => t.type === "page" && t.url.includes("outlier"));
  if (!targetTab) targetTab = tabs.find(t => t.type === "page" && !t.url.includes("dataannotation.tech/"));

  if (targetTab) {
    const match = targetTab.url.substring(8, 30);
    ({ ws, send, eval_ } = await connectToPage(match));

    r = await eval_(`return window.location.href`);
    console.log("\nCurrent URL:", r);
    r = await eval_(`return document.body.innerText.substring(0, 2000)`);
    console.log("Page:", r);

    // If we're at Outlier login page, click Continue with Google
    if (r.includes('Continue with Google') || r.includes('Login')) {
      r = await eval_(`
        const btn = Array.from(document.querySelectorAll('button'))
          .find(el => el.textContent.includes('Continue with Google'));
        if (btn) {
          const rect = btn.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        }
        return 'not found';
      `);
      if (r !== 'not found') {
        const gPos = JSON.parse(r);
        await clickAt(send, gPos.x, gPos.y);
        console.log("\nClicked Continue with Google");
        await sleep(5000);
        ws.close();
        await sleep(1000);

        // Now at Google chooser
        tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
        const gTab = tabs.find(t => t.type === "page" && t.url.includes("accounts.google"));
        if (gTab) {
          ({ ws, send, eval_ } = await connectToPage("accounts.google"));
          r = await eval_(`return document.body.innerText.substring(0, 1000)`);
          console.log("\nGoogle chooser:", r);

          // Click "Use another account"
          r = await eval_(`
            const li = Array.from(document.querySelectorAll('li'))
              .find(el => el.textContent.includes('Use another account'));
            if (li) {
              const rect = li.getBoundingClientRect();
              return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
            }
            return 'not found';
          `);
          console.log("Use another account:", r);

          if (r !== 'not found') {
            const uPos = JSON.parse(r);
            await clickAt(send, uPos.x, uPos.y);
            console.log("Clicked Use another account");
            await sleep(4000);

            // Email entry page
            r = await eval_(`return document.body.innerText.substring(0, 1000)`);
            console.log("\nPage:", r);

            // Type email
            r = await eval_(`
              const input = document.querySelector('input[type="email"]');
              if (input) {
                input.focus();
                const rect = input.getBoundingClientRect();
                return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
              }
              return 'not found';
            `);
            console.log("Email input:", r);

            if (r !== 'not found') {
              const ePos = JSON.parse(r);
              await clickAt(send, ePos.x, ePos.y);
              await sleep(300);
              await typeText(send, "weber@bimopsstudio.com");
              console.log("Typed email");
              await sleep(500);

              // Click Next
              r = await eval_(`
                const btn = Array.from(document.querySelectorAll('button'))
                  .find(el => el.textContent.trim() === 'Next');
                if (btn) {
                  const rect = btn.getBoundingClientRect();
                  return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
                }
                return 'not found';
              `);
              console.log("Next button:", r);

              if (r !== 'not found') {
                const nPos = JSON.parse(r);
                await clickAt(send, nPos.x, nPos.y);
                console.log("Clicked Next");
                await sleep(6000);

                r = await eval_(`return document.body.innerText.substring(0, 2000)`);
                console.log("\nAfter Next:", r);
              }
            }
          }
        }
      }
    }
    ws.close();
  }
})().catch(e => console.error("Error:", e.message));
