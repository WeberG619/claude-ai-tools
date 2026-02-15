// Check and complete Fiverr gig setup
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Page not found: ${urlMatch}`);
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
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // Check current page state
  console.log("=== Current State ===");
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      title: document.querySelector('textarea[name="gig[title]"], textarea')?.value || '',
      category: document.querySelector('input[name="gig[category_id]"]')?.value || '',
      subcategory: document.querySelector('input[name="gig[sub_category_id]"]')?.value || '',
      tags: document.querySelector('input[name="gig[tag_list]"]')?.value || '',
      serviceType: document.querySelector('input[name="gig[metadata][service_type]"]')?.value || '',
      allHidden: Array.from(document.querySelectorAll('input[name^="gig["]'))
        .map(i => i.name + '=' + (i.value || '').substring(0, 50)),
      bodyPreview: document.body?.innerText?.substring(0, 2000)
    });
  `);
  console.log(r);

  const state = JSON.parse(r);
  console.log("\nURL:", state.url);
  console.log("Title:", state.title);
  console.log("Category:", state.category);
  console.log("Subcategory:", state.subcategory);
  console.log("Tags:", state.tags);
  console.log("Service Type:", state.serviceType);
  console.log("Hidden inputs:", state.allHidden);

  // Check which step/tab we're on
  console.log("\n=== Form Structure ===");
  r = await eval_(`
    // Find all visible inputs
    const visibleInputs = Array.from(document.querySelectorAll('input, textarea, select'))
      .filter(el => el.offsetParent !== null && el.type !== 'hidden')
      .map(el => ({
        tag: el.tagName, type: el.type, name: el.name || '', id: el.id || '',
        placeholder: (el.placeholder || '').substring(0, 50),
        value: (el.value || '').substring(0, 50),
        class: (el.className?.toString() || '').substring(0, 60),
        rect: { x: Math.round(el.getBoundingClientRect().x), y: Math.round(el.getBoundingClientRect().y), w: Math.round(el.getBoundingClientRect().width) }
      }));

    // Find all buttons
    const buttons = Array.from(document.querySelectorAll('button, a'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 100)
      .map(el => ({
        tag: el.tagName, text: (el.textContent?.trim() || '').substring(0, 50),
        href: el.href || '',
        rect: { x: Math.round(el.getBoundingClientRect().x), y: Math.round(el.getBoundingClientRect().y) }
      }))
      .filter(b => b.text.length > 1);

    // Check for tag chips already present
    const tagChips = Array.from(document.querySelectorAll('[class*="tag-item"], [class*="TagItem"], [class*="chip"], [class*="tag-value"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim().substring(0, 30));

    return JSON.stringify({ visibleInputs, buttons: buttons.slice(0, 20), tagChips });
  `);
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
