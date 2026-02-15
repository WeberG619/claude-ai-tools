// Sign up on Freelancer.com via CDP
// Credentials passed via command line args, NOT stored in file
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

const EMAIL = process.argv[2];
const PASS = process.argv[3];

if (!EMAIL || !PASS) {
  console.error("Usage: node signup_freelancer.mjs <email> <password>");
  process.exit(1);
}

async function connectToTab(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found: ${urlMatch}`);

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
  console.log("=== Freelancer.com Signup ===\n");

  // Navigate to signup page
  console.log("Step 1: Navigate to signup...");
  await fetch(`${CDP_HTTP}/json/activate/${(await (await fetch(`${CDP_HTTP}/json`)).json()).find(t => t.url.includes("freelancer.com")).id}`, { method: "PUT" }).catch(() => {});

  let { ws, send, eval_ } = await connectToTab("freelancer.com");

  // Check current page state - are we already on signup? or main page?
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      hasSignup: !!document.querySelector('[class*="signup"], [class*="register"], [href*="signup"]'),
      hasLogin: !!document.querySelector('[class*="login"], [href*="login"]'),
      isLoggedIn: document.body.innerText.includes('Dashboard') || document.body.innerText.includes('My Projects'),
      pagePreview: document.body.innerText.substring(0, 500)
    });
  `);
  console.log("  Current state:", r);

  const state = JSON.parse(r);

  if (state.isLoggedIn) {
    console.log("  Already logged in! Checking account...");
    ws.close();
    return;
  }

  // Navigate to signup page
  console.log("\nStep 2: Going to signup page...");
  await send("Page.navigate", { url: "https://www.freelancer.com/signup" });
  await sleep(5000);

  // Reconnect after navigation
  ws.close();
  ({ ws, send, eval_ } = await connectToTab("freelancer.com"));

  // Check signup form
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      inputs: Array.from(document.querySelectorAll('input')).filter(i => i.offsetParent !== null).map(i => ({
        type: i.type, name: i.name, id: i.id,
        placeholder: i.placeholder,
        label: i.getAttribute('aria-label') || ''
      })),
      buttons: Array.from(document.querySelectorAll('button')).filter(b => b.offsetParent !== null).map(b => ({
        text: b.textContent.trim().substring(0, 50), type: b.type
      })),
      pagePreview: document.body.innerText.substring(0, 1000)
    }, null, 2);
  `);
  console.log("  Signup form:", r);

  ws.close();
  console.log("\n=== Inspection complete ===");
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
