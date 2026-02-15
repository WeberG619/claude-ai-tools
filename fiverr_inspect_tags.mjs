// Deep inspect Fiverr tag input area
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

  // Get ALL inputs of any type
  let r = await eval_(`
    const allInputs = Array.from(document.querySelectorAll('input'));
    return JSON.stringify(allInputs.map((el, i) => ({
      index: i,
      type: el.type,
      id: el.id || '',
      name: el.name || '',
      value: (el.value || '').substring(0, 60),
      class: (el.className?.toString() || '').substring(0, 60),
      width: Math.round(el.getBoundingClientRect().width),
      height: Math.round(el.getBoundingClientRect().height),
      y: Math.round(el.getBoundingClientRect().y),
      visible: el.offsetParent !== null,
      parent: el.parentElement?.className?.toString()?.substring(0, 60) || ''
    })));
  `);
  console.log("ALL inputs:", r);

  // Also check for contenteditable divs and other editable elements
  r = await eval_(`
    // Check for any element near "Search tags" / "Positive keywords"
    const tagSection = Array.from(document.querySelectorAll('*'))
      .filter(el => el.textContent?.includes('Positive keywords') && el.children.length < 5)
      .map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 60),
        nextSiblingTag: el.nextElementSibling?.tagName,
        nextSiblingClass: (el.nextElementSibling?.className?.toString() || '').substring(0, 60),
        parentTag: el.parentElement?.tagName,
        parentClass: (el.parentElement?.className?.toString() || '').substring(0, 60)
      }));

    // Find the actual tag input container
    const tagContainer = Array.from(document.querySelectorAll('*'))
      .filter(el => {
        const cls = el.className?.toString() || '';
        return (cls.includes('tag-input') || cls.includes('TagInput') || cls.includes('tags-input') ||
                cls.includes('search-tag') || cls.includes('SearchTag'));
      })
      .map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 80),
        innerHTML: el.innerHTML?.substring(0, 300),
        childCount: el.children.length
      }));

    // Look for the garbled text anywhere
    const garbledEl = Array.from(document.querySelectorAll('input, textarea, [contenteditable]'))
      .filter(el => (el.value || el.textContent || '').includes('entryexcel'))
      .map(el => ({
        tag: el.tagName,
        type: el.type || '',
        class: (el.className?.toString() || '').substring(0, 60),
        value: (el.value || el.textContent || '').substring(0, 80)
      }));

    return JSON.stringify({ tagSection: tagSection.slice(0, 3), tagContainer, garbledEl });
  `);
  console.log("\nTag area inspection:", r);

  // Get the HTML of the tag area
  r = await eval_(`
    // Find the section containing "tag_list"
    const tagListInput = document.querySelector('input[name="gig[tag_list]"]');
    if (tagListInput) {
      const parent = tagListInput.closest('div') || tagListInput.parentElement;
      // Walk up to find a meaningful container
      let container = tagListInput;
      for (let i = 0; i < 5; i++) {
        container = container.parentElement;
        if (!container) break;
        if (container.getBoundingClientRect().height > 50) break;
      }
      return JSON.stringify({
        tagListFound: true,
        tagListValue: tagListInput.value,
        containerHTML: container?.outerHTML?.substring(0, 1000) || '',
        containerClass: container?.className?.toString()?.substring(0, 80)
      });
    }
    return JSON.stringify({ tagListFound: false });
  `);
  console.log("\nTag list input area:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
