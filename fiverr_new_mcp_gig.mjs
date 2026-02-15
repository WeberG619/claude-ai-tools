// Create Fiverr Gig #1: MCP Server Development
// Navigates the gig wizard via CDP
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connect() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("fiverr.com") && !t.url.includes("iframe"));
  if (!tab) throw new Error("No Fiverr tab found");
  console.log(`Connected: ${tab.title} | ${tab.url}`);
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
      expression: expr,
      returnByValue: true,
      awaitPromise: true
    });
    if (r.exceptionDetails) {
      console.error("JS Error:", JSON.stringify(r.exceptionDetails).substring(0, 200));
      return null;
    }
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

// Helper: set React input value
function reactSetValue(selector, value) {
  return `
    (function() {
      const el = document.querySelector('${selector}');
      if (!el) return 'not_found: ${selector}';
      el.focus();
      const nativeSetter = Object.getOwnPropertyDescriptor(
        el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype,
        'value'
      )?.set;
      if (nativeSetter) nativeSetter.call(el, ${JSON.stringify(value)});
      else el.value = ${JSON.stringify(value)};
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      el.dispatchEvent(new Event('blur', { bubbles: true }));
      return 'filled: ${selector}';
    })()
  `;
}

async function main() {
  const { ws, eval_ } = await connect();

  // Step 1: Click "Create a new Gig"
  console.log("\n=== Step 1: Navigate to new gig ===");
  await eval_(`window.location.href = "https://www.fiverr.com/users/weberg619/manage_gigs/new"`);
  await sleep(5000);

  let url = await eval_(`window.location.href`);
  console.log("URL:", url);

  // Step 2: Explore the page structure
  console.log("\n=== Step 2: Analyzing page structure ===");
  const pageAnalysis = await eval_(`
    JSON.stringify({
      url: window.location.href,
      title: document.title,
      h1: document.querySelector('h1')?.textContent?.trim() || 'none',
      h2s: Array.from(document.querySelectorAll('h2')).map(h => h.textContent.trim()).slice(0, 5),
      inputs: Array.from(document.querySelectorAll('input, textarea, select')).map(el => ({
        tag: el.tagName,
        type: el.type || '',
        name: el.name || '',
        id: el.id || '',
        placeholder: (el.placeholder || '').substring(0, 50),
        class: el.className.toString().substring(0, 60),
        ariaLabel: el.getAttribute('aria-label') || ''
      })).slice(0, 20),
      buttons: Array.from(document.querySelectorAll('button')).map(b => ({
        text: b.textContent.trim().substring(0, 40),
        class: b.className.substring(0, 40),
        type: b.type || ''
      })).filter(b => b.text.length > 0).slice(0, 15),
      labels: Array.from(document.querySelectorAll('label')).map(l => l.textContent.trim().substring(0, 40)).slice(0, 15)
    })
  `);
  console.log("Page analysis:", pageAnalysis);

  ws.close();
  console.log("\nDone - check output above to see form structure.");
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
