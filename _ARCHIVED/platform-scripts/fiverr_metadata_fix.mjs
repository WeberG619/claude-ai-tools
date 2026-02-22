// Fix metadata: handle the tabbed AI engine / Programming language sections
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connect() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("fiverr.com") && t.url.includes("edit"));
  if (!tab) throw new Error("No Fiverr edit tab");
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
    const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) { console.error("JS Err:", JSON.stringify(r.exceptionDetails).substring(0, 500)); return null; }
    return r.result?.value;
  };
  async function cdpClick(x, y) {
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
    await sleep(100);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1, buttons: 1 });
    await sleep(80);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
  }
  return { ws, send, eval_, cdpClick };
}

async function main() {
  const { ws, send, eval_, cdpClick } = await connect();

  // Step 1: Scroll to metadata section and understand the tab structure
  console.log("=== Step 1: Understand metadata tabs ===");

  // First, get the tab headers and their click targets
  const tabInfo = await eval_(`
    (function() {
      const metaGroup = document.querySelector('.gig-metadata-group');
      if (!metaGroup) return 'no metadata group';
      metaGroup.scrollIntoView({ block: 'center' });

      const tabsList = metaGroup.querySelector('ul, [class*="tabs"]');
      const tabItems = tabsList ? Array.from(tabsList.children) : [];

      return JSON.stringify(tabItems.map(li => {
        const rect = li.getBoundingClientRect();
        return {
          text: li.textContent.trim().substring(0, 30),
          class: li.className,
          isSelected: li.classList.contains('selected'),
          x: Math.round(rect.x + rect.width / 2),
          y: Math.round(rect.y + rect.height / 2),
          visible: rect.width > 0
        };
      }));
    })()
  `);
  console.log("Tabs:", tabInfo);

  const tabs = JSON.parse(tabInfo);

  // Step 2: Click "Programming language" tab via CDP
  console.log("\n=== Step 2: Click Programming Language tab ===");
  const langTab = tabs.find(t => t.text.toLowerCase().includes('programming'));
  if (langTab) {
    console.log(`Clicking "${langTab.text}" at (${langTab.x}, ${langTab.y})`);
    await cdpClick(langTab.x, langTab.y);
    await sleep(1500);

    // Check what checkboxes appeared
    const langCbs = await eval_(`
      (function() {
        const metaGroup = document.querySelector('.gig-metadata-group');
        const cbs = Array.from(metaGroup.querySelectorAll('input[type="checkbox"]')).filter(cb => cb.offsetParent !== null);
        return JSON.stringify({
          visibleCount: cbs.length,
          options: cbs.map(cb => {
            const label = cb.closest('label');
            const rect = label ? label.getBoundingClientRect() : cb.getBoundingClientRect();
            return {
              text: label?.textContent?.trim() || '?',
              checked: cb.checked,
              x: Math.round(rect.x + 15),
              y: Math.round(rect.y + rect.height / 2)
            };
          }),
          // Also check the header text
          headerText: metaGroup.querySelector('.meta-header.multi-select-header')?.textContent?.trim()?.substring(0, 80) || '',
          // Check selected tab
          selectedTab: Array.from(metaGroup.querySelectorAll('li.selected')).map(li => li.textContent.trim().substring(0, 30))
        });
      })()
    `);
    console.log("Language checkboxes:", langCbs);

    const langData = JSON.parse(langCbs);
    if (langData.visibleCount > 0) {
      // Find Python, JavaScript, TypeScript
      const toClick = langData.options.filter(o =>
        ['Python', 'JavaScript', 'TypeScript', 'Node.js', 'C#'].some(t =>
          o.text.toLowerCase().includes(t.toLowerCase())
        ) && !o.checked
      );

      if (toClick.length === 0) {
        // If specific languages not found, just check first 3
        console.log("Specific languages not found, checking first 3...");
        const firstThree = langData.options.filter(o => !o.checked).slice(0, 3);
        for (const cb of firstThree) {
          console.log(`  Clicking "${cb.text}" at (${cb.x}, ${cb.y})`);
          await cdpClick(cb.x, cb.y);
          await sleep(500);
        }
      } else {
        for (const cb of toClick) {
          console.log(`  Clicking "${cb.text}" at (${cb.x}, ${cb.y})`);
          await cdpClick(cb.x, cb.y);
          await sleep(500);
        }
      }
    } else {
      console.log("No visible checkboxes! The tab content might not have loaded.");
      // Try clicking the tab header again more precisely
      const headerCoords = await eval_(`
        (function() {
          const metaGroup = document.querySelector('.gig-metadata-group');
          const lis = Array.from(metaGroup.querySelectorAll('li'));
          const langLi = lis.find(li => li.textContent.trim().toLowerCase().includes('programming'));
          if (langLi) {
            const rect = langLi.getBoundingClientRect();
            return JSON.stringify({
              x: Math.round(rect.x + rect.width / 2),
              y: Math.round(rect.y + rect.height / 2),
              text: langLi.textContent.trim(),
              class: langLi.className
            });
          }
          return null;
        })()
      `);
      console.log("Header coords:", headerCoords);

      if (headerCoords) {
        const hc = JSON.parse(headerCoords);
        await cdpClick(hc.x, hc.y);
        await sleep(2000);

        // Check again
        const afterClick = await eval_(`
          (function() {
            const metaGroup = document.querySelector('.gig-metadata-group');
            const cbs = Array.from(metaGroup.querySelectorAll('input[type="checkbox"]')).filter(cb => cb.offsetParent !== null);
            return JSON.stringify({
              visibleCount: cbs.length,
              selectedTab: Array.from(metaGroup.querySelectorAll('li.selected')).map(li => li.textContent.trim()),
              fullHTML: metaGroup.querySelector('.meta-multi-select:not(.divided-list)')?.innerHTML?.substring(0, 300) || 'not found',
              allMultiSelects: Array.from(metaGroup.querySelectorAll('.meta-multi-select')).map(ms => ({
                class: ms.className,
                visible: ms.offsetParent !== null,
                childCount: ms.children.length,
                text: ms.textContent.substring(0, 100)
              }))
            });
          })()
        `);
        console.log("After second click:", afterClick);
      }
    }
  }

  // Step 3: Verify programming language is now selected
  await sleep(500);
  const verifyLang = await eval_(`
    (function() {
      const metaGroup = document.querySelector('.gig-metadata-group');
      const cbs = Array.from(metaGroup.querySelectorAll('input[type="checkbox"]'));
      return JSON.stringify({
        total: cbs.length,
        checked: cbs.filter(cb => cb.checked).map(cb => cb.closest('label')?.textContent?.trim()),
        tabs: Array.from(metaGroup.querySelectorAll('li')).filter(li => !li.classList.contains('option')).map(li => ({
          text: li.textContent.trim().substring(0, 20),
          class: li.className,
          selected: li.classList.contains('selected'),
          invalid: li.classList.contains('invalid')
        }))
      });
    })()
  `);
  console.log("\nVerify state:", verifyLang);

  // Step 4: Switch back to AI engine tab and verify those are still checked
  console.log("\n=== Step 4: Check AI engine tab ===");
  const aiTab = tabs.find(t => t.text.toLowerCase().includes('ai engine'));
  if (aiTab) {
    await cdpClick(aiTab.x, aiTab.y);
    await sleep(1000);

    const aiState = await eval_(`
      (function() {
        const metaGroup = document.querySelector('.gig-metadata-group');
        const cbs = Array.from(metaGroup.querySelectorAll('input[type="checkbox"]')).filter(cb => cb.offsetParent !== null);
        const checked = cbs.filter(cb => cb.checked);
        return JSON.stringify({
          visibleCount: cbs.length,
          checkedCount: checked.length,
          checked: checked.map(cb => cb.closest('label')?.textContent?.trim())
        });
      })()
    `);
    console.log("AI engine state:", aiState);

    const aiData = JSON.parse(aiState);
    if (aiData.checkedCount === 0) {
      // Re-check Claude, GPT, Langchain
      console.log("AI engine checkboxes unchecked! Re-checking...");
      const toRecheck = await eval_(`
        (function() {
          const metaGroup = document.querySelector('.gig-metadata-group');
          const cbs = Array.from(metaGroup.querySelectorAll('input[type="checkbox"]')).filter(cb => cb.offsetParent !== null);
          const targets = [];
          for (const cb of cbs) {
            const label = cb.closest('label')?.textContent?.trim() || '';
            if (['Claude', 'GPT', 'Langchain'].includes(label)) {
              const el = cb.closest('label');
              const rect = el.getBoundingClientRect();
              targets.push({ label, x: Math.round(rect.x + 15), y: Math.round(rect.y + rect.height / 2) });
            }
          }
          return JSON.stringify(targets);
        })()
      `);

      const aiTargets = JSON.parse(toRecheck);
      for (const t of aiTargets) {
        console.log(`  Re-checking "${t.label}" at (${t.x}, ${t.y})`);
        await cdpClick(t.x, t.y);
        await sleep(500);
      }
    }
  }

  // Step 5: Final verification
  console.log("\n=== Step 5: Final check ===");
  const finalState = await eval_(`
    JSON.stringify({
      title: document.querySelector('textarea')?.value,
      categories: Array.from(document.querySelectorAll('[class*="singleValue"]')).map(s => s.textContent.trim()),
      tags: Array.from(document.querySelectorAll('.react-tags__selected-tag')).map(t => t.textContent.trim()),
      metaTabs: (() => {
        const metaGroup = document.querySelector('.gig-metadata-group');
        return Array.from(metaGroup?.querySelectorAll('li') || [])
          .filter(li => !li.classList.contains('option'))
          .map(li => ({ text: li.textContent.trim().substring(0, 20), invalid: li.classList.contains('invalid') }));
      })(),
      allCheckedMeta: Array.from(document.querySelectorAll('.gig-metadata-group input[type="checkbox"]'))
        .filter(cb => cb.checked)
        .map(cb => cb.closest('label')?.textContent?.trim()),
      errors: Array.from(document.querySelectorAll('[class*="error"]'))
        .map(e => e.textContent.trim().substring(0, 80))
        .filter(t => t.length > 0)
    })
  `);
  console.log("Final:", finalState);

  // Try save if no errors
  const fState = JSON.parse(finalState);
  if (!fState.errors.some(e => e.includes('metadata'))) {
    console.log("\nSaving...");
    await eval_(`document.querySelector('button').textContent`); // just a noop to ensure page is ready
    await eval_(`
      Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Save & Preview')?.click()
    `);
    await sleep(5000);
    console.log("URL:", await eval_(`window.location.href`));
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
