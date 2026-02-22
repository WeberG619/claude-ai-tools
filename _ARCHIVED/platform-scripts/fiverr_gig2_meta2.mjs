// Fill Content Type and Genre metadata - click exact tab positions
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("manage_gigs"));
  if (!tab) throw new Error("Gig page not found");
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
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  const { ws, send, eval_ } = await connectToPage();
  console.log("Connected\n");

  // Scroll metadata section into view
  let r = await eval_(`
    const metaSection = document.querySelector('.gig-metadata-group');
    if (metaSection) {
      metaSection.scrollIntoView({ behavior: 'instant', block: 'start' });
      return 'scrolled';
    }
    return 'not found';
  `);
  await sleep(500);

  // Get exact tab positions after scroll
  r = await eval_(`
    const listItems = document.querySelectorAll('.metadata-names-list li');
    const result = Array.from(listItems).map(li => {
      const rect = li.getBoundingClientRect();
      return {
        text: li.textContent.trim(),
        class: li.className || '',
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2),
        w: Math.round(rect.width),
        h: Math.round(rect.height)
      };
    });
    return JSON.stringify(result);
  `);
  console.log("Tab items:", r);
  const tabItems = JSON.parse(r);

  // Click Content Type tab
  const ctTab = tabItems.find(t => t.text === 'Content Type');
  if (ctTab) {
    console.log(`\n=== Clicking Content Type at (${ctTab.x}, ${ctTab.y}) ===`);
    await clickAt(send, ctTab.x, ctTab.y);
    await sleep(1000);

    // Check what's now visible in the content area
    r = await eval_(`
      // After clicking the tab, find the active content panel
      // The content should change - look for checkboxes or other inputs
      const metaGroup = document.querySelector('.gig-metadata-group');
      const metaInput = metaGroup?.querySelector('.gig-metadata-input');
      if (metaInput) {
        // Get all visible labels/checkboxes in the metadata input area
        const labels = Array.from(metaInput.querySelectorAll('label'))
          .filter(el => {
            const rect = el.getBoundingClientRect();
            return el.offsetParent !== null && rect.height > 0 && rect.y > 0;
          })
          .map(el => ({
            text: el.textContent.trim().substring(0, 40),
            x: Math.round(el.getBoundingClientRect().x + 10),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
            checked: el.querySelector('input')?.checked || false
          }));

        // Also check for any header text
        const header = metaInput.querySelector('p, span, [class*="description"]');

        return JSON.stringify({
          labels: labels.slice(0, 25),
          headerText: header?.textContent?.trim()?.substring(0, 100) || '',
          html: metaInput.innerHTML.substring(0, 500)
        });
      }
      return JSON.stringify({ error: 'no metadata input section' });
    `);
    console.log("Content Type panel:", r);
    const ctPanel = JSON.parse(r);

    if (ctPanel.labels) {
      // Check if these are language labels or actual content type labels
      const isLanguage = ctPanel.labels.some(l => ['Albanian', 'Arabic', 'Bengali', 'English'].includes(l.text));
      if (isLanguage) {
        console.log("Still showing language labels - tab click might not have switched");
        // Try clicking via JS
        r = await eval_(`
          const li = Array.from(document.querySelectorAll('.metadata-names-list li'))
            .find(l => l.textContent.trim() === 'Content Type');
          if (li) {
            li.click();
            return 'clicked via JS';
          }
          return 'not found';
        `);
        console.log("JS click:", r);
        await sleep(1000);

        // Check again
        r = await eval_(`
          const metaInput = document.querySelector('.gig-metadata-input');
          const labels = metaInput ? Array.from(metaInput.querySelectorAll('label'))
            .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 0)
            .map(el => el.textContent.trim().substring(0, 40))
            .slice(0, 20) : [];
          return JSON.stringify(labels);
        `);
        console.log("Labels after JS click:", r);
      } else {
        // Select content types
        console.log("Content types:", ctPanel.labels.map(l => l.text).join(', '));
        const targets = ['Article', 'Blog', 'Book', 'Web', 'Academic', 'Business', 'Email', 'Resume', 'Other'];
        for (const label of ctPanel.labels) {
          if (!label.checked && targets.some(t => label.text.includes(t))) {
            console.log(`  Selecting: "${label.text}"`);
            await clickAt(send, label.x, label.y);
            await sleep(200);
          }
        }
      }
    }
  }

  // Check current selected tab
  r = await eval_(`
    const selected = document.querySelector('.metadata-names-list li.selected');
    return selected?.textContent?.trim() || 'none';
  `);
  console.log("\nCurrently selected tab:", r);

  // Try a different approach - check if metadata uses a different DOM structure
  r = await eval_(`
    // Look at the full metadata structure
    const metaGroup = document.querySelector('.gig-metadata-group');
    if (!metaGroup) return JSON.stringify({ error: 'no group' });

    // Find all direct children and their classes
    const structure = [];
    const walkChildren = (el, depth) => {
      if (depth > 3) return;
      for (const child of el.children) {
        const cls = child.className?.toString() || '';
        const text = child.textContent?.trim()?.substring(0, 50) || '';
        if (cls.includes('metadata') || cls.includes('content') || cls.includes('genre') || cls.includes('language')) {
          structure.push({
            tag: child.tagName,
            class: cls.substring(0, 80),
            text: text.substring(0, 50),
            visible: child.offsetParent !== null,
            y: Math.round(child.getBoundingClientRect().y),
            childCount: child.children.length
          });
        }
        walkChildren(child, depth + 1);
      }
    };
    walkChildren(metaGroup, 0);
    return JSON.stringify(structure.slice(0, 20));
  `);
  console.log("\nMetadata DOM structure:", r);

  // Look specifically for content type and genre inputs that might be hidden panels
  r = await eval_(`
    // Find elements with content-type or genre in class names
    const allEls = Array.from(document.querySelectorAll('[class*="content-type"], [class*="contentType"], [class*="genre"], [data-metadata*="content"], [data-metadata*="genre"]'));
    return JSON.stringify(allEls.map(el => ({
      tag: el.tagName,
      class: (el.className?.toString() || '').substring(0, 80),
      visible: el.offsetParent !== null,
      display: getComputedStyle(el).display,
      childCount: el.children.length,
      text: el.textContent?.trim()?.substring(0, 100) || ''
    })));
  `);
  console.log("\nContent type / genre elements:", r);

  // Try checking all containers with their data attributes
  r = await eval_(`
    const metadataContainers = Array.from(document.querySelectorAll('[class*="metadata-values"], [class*="metadata-content"], [class*="meta-values"]'));
    return JSON.stringify(metadataContainers.map(el => ({
      class: (el.className?.toString() || '').substring(0, 80),
      visible: el.offsetParent !== null,
      display: getComputedStyle(el).display,
      y: Math.round(el.getBoundingClientRect().y),
      childCount: el.children.length,
      text: el.textContent?.trim()?.substring(0, 100) || ''
    })));
  `);
  console.log("\nMetadata value containers:", r);

  // Dump the gig metadata input section HTML
  r = await eval_(`
    const metaInput = document.querySelector('.gig-metadata-input');
    if (metaInput) {
      // Get all children container divs
      const kids = Array.from(metaInput.children).map(c => ({
        tag: c.tagName,
        class: (c.className?.toString() || '').substring(0, 80),
        visible: c.offsetParent !== null,
        display: getComputedStyle(c).display,
        childCount: c.children.length,
        textPreview: c.textContent?.trim()?.substring(0, 60) || ''
      }));
      return JSON.stringify(kids);
    }
    return '[]';
  `);
  console.log("\nMetadata input children:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
