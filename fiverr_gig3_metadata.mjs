// Fix gig #3 metadata (Language + Industry) and save
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
      expression: `(() => { ${expr} })()`,
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
  let { ws, send, eval_ } = await connectToPage("manage_gigs");
  console.log("Connected\n");

  // Scroll down to metadata section
  let r = await eval_(`
    const metaSection = document.querySelector('[class*="metadata"]') ||
      document.querySelector('.gig-metadata');
    if (metaSection) {
      metaSection.scrollIntoView({ block: 'start' });
      return 'scrolled to metadata';
    }
    // Try scrolling down
    window.scrollTo(0, 1000);
    return 'scrolled down';
  `);
  console.log(r);
  await sleep(1000);

  // Explore the metadata section structure
  r = await eval_(`
    // Find all sections that might be metadata
    const allSections = document.body.innerHTML;
    const metaIdx = allSections.indexOf('metadata');
    if (metaIdx > 0) {
      return 'metadata found in HTML at index: ' + metaIdx;
    }
    return 'no metadata in HTML';
  `);
  console.log(r);

  // Look at the page more carefully for Language and Industry
  r = await eval_(`
    // Get everything that says "Language" or "Industry"
    const elements = Array.from(document.querySelectorAll('*'))
      .filter(el => {
        const text = el.textContent.trim();
        return (text === 'Language' || text === 'Industry' || text === 'LANGUAGE' || text === 'INDUSTRY')
          && el.children.length === 0  // leaf node
          && el.offsetParent !== null;
      })
      .map(el => ({
        tag: el.tagName,
        text: el.textContent.trim(),
        class: (el.className?.toString() || '').substring(0, 50),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        parentTag: el.parentElement?.tagName,
        parentClass: (el.parentElement?.className?.toString() || '').substring(0, 50)
      }));
    return JSON.stringify(elements);
  `);
  console.log("Language/Industry elements:", r);

  // Scroll further down
  await eval_(`window.scrollTo(0, 2000)`);
  await sleep(1000);

  r = await eval_(`
    const elements = Array.from(document.querySelectorAll('*'))
      .filter(el => {
        const text = el.textContent.trim();
        return (text === 'Language' || text === 'Industry' || text === 'LANGUAGE' || text === 'INDUSTRY')
          && el.children.length === 0
          && el.offsetParent !== null;
      })
      .map(el => ({
        tag: el.tagName,
        text: el.textContent.trim(),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(elements);
  `);
  console.log("After scroll:", r);

  // Look for the metadata section more broadly - look for checkboxes or dropdowns near metadata
  r = await eval_(`
    // Look for any section with "Gig metadata" header
    const headers = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6, [class*="header"], [class*="title"]'))
      .filter(el => el.textContent.trim().toLowerCase().includes('metadata'))
      .map(el => ({
        tag: el.tagName,
        text: el.textContent.trim().substring(0, 50),
        y: Math.round(el.getBoundingClientRect().y)
      }));
    return JSON.stringify(headers);
  `);
  console.log("Metadata headers:", r);

  // Get all interactive elements in the metadata region
  r = await eval_(`
    // Scroll down more and look for the metadata section
    window.scrollTo(0, 3000);
    return 'scrolled to 3000';
  `);
  await sleep(500);

  r = await eval_(`
    // Look for checkboxes, selects, and dropdowns that appear after the tags section
    const interactives = Array.from(document.querySelectorAll('input[type="checkbox"], select, [class*="select"], [class*="dropdown"], [class*="combo"]'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 0)
      .map(el => ({
        tag: el.tagName,
        type: el.type || '',
        name: el.name || '',
        id: el.id || '',
        class: (el.className?.toString() || '').substring(0, 60),
        text: (el.closest('label') || el.parentElement)?.textContent?.trim()?.substring(0, 40) || '',
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        checked: el.checked
      }));
    return JSON.stringify(interactives);
  `);
  console.log("Interactive elements:", r);

  // Let me look at ALL visible text to find where metadata section is
  r = await eval_(`
    window.scrollTo(0, 0);
    return document.body.innerText.substring(0, 3000);
  `);
  console.log("\nFull page text:\n", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
