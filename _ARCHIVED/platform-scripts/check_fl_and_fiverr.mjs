// Check Freelancer email verification status, then inspect Fiverr join page
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) return null;
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
      expression: `(() => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

async function main() {
  // 1. Check Freelancer status
  console.log("=== FREELANCER STATUS ===");
  const fl = await connectToPage("freelancer.com/new-freelancer");
  if (fl) {
    let r = await fl.eval_(`
      return JSON.stringify({
        url: location.href,
        preview: document.body.innerText.substring(0, 1000)
      });
    `);
    console.log(r);

    // If still on email verification, click Next
    const state = JSON.parse(r);
    if (state.url.includes("email-verification")) {
      console.log("\nTrying to click Next on verification page...");
      r = await fl.eval_(`
        const btn = Array.from(document.querySelectorAll('button'))
          .find(b => b.textContent.trim() === 'Next' && b.offsetParent !== null);
        if (btn) {
          const rect = btn.getBoundingClientRect();
          return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
        }
        return null;
      `);
      if (r) {
        const pos = JSON.parse(r);
        await fl.send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
        await sleep(50);
        await fl.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
        console.log("Clicked Next");
        await sleep(3000);

        r = await fl.eval_(`
          return JSON.stringify({ url: location.href, preview: document.body.innerText.substring(0, 500) });
        `);
        console.log("After Next:", r);
      }
    }
    fl.ws.close();
  } else {
    console.log("Freelancer tab not found");
  }

  // 2. Check Fiverr page
  console.log("\n\n=== FIVERR JOIN PAGE ===");
  const fv = await connectToPage("fiverr.com/join");
  if (fv) {
    let r = await fv.eval_(`
      return JSON.stringify({
        url: location.href,
        preview: document.body.innerText.substring(0, 2000),
        allInputs: Array.from(document.querySelectorAll('input'))
          .filter(i => i.offsetParent !== null)
          .map(i => ({ type: i.type, name: i.name, id: i.id, placeholder: i.placeholder, ariaLabel: i.getAttribute('aria-label') })),
        buttons: Array.from(document.querySelectorAll('button'))
          .filter(b => b.offsetParent !== null)
          .map(b => ({ text: b.textContent.trim().substring(0, 50), type: b.type }))
          .filter(b => b.text.length > 0)
      });
    `);
    console.log(r);
    fv.ws.close();
  } else {
    console.log("Fiverr tab not found");
  }
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
