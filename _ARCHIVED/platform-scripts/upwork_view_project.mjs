// View the project listing
const CDP = 'http://localhost:9222';
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function getPages() {
  const r = await fetch(`${CDP}/json`);
  return (await r.json()).filter(t => t.type === 'page');
}

function connect(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let id = 1;
    const pending = new Map();
    ws.addEventListener('message', e => {
      const msg = JSON.parse(e.data);
      if (msg.id && pending.has(msg.id)) {
        const p = pending.get(msg.id);
        pending.delete(msg.id);
        msg.error ? p.rej(new Error(msg.error.message)) : p.res(msg.result);
      }
    });
    const send = (method, params = {}) => new Promise((res, rej) => {
      const mid = id++;
      pending.set(mid, { res, rej });
      ws.send(JSON.stringify({ id: mid, method, params }));
    });
    const ev = async (expr) => {
      const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result?.value;
    };
    ws.addEventListener('open', () => resolve({ ws, send, ev, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // First, find the project view/preview link
  console.log('=== FINDING PROJECT LINK ===');
  const projectLink = await c.ev(`
    (() => {
      // Look for "More Project Options" or the project title link
      var links = document.querySelectorAll('a');
      var result = [];
      for (var i = 0; i < links.length; i++) {
        var href = links[i].href || '';
        if (href.includes('catalog') || href.includes('project') || href.includes('services')) {
          result.push({ text: links[i].textContent.trim().substring(0, 60), href: href.substring(0, 150) });
        }
      }
      // Also check the More Project Options dropdown
      var btns = document.querySelectorAll('button');
      for (var j = 0; j < btns.length; j++) {
        if (btns[j].textContent.trim().includes('More Project Options')) {
          return JSON.stringify({ moreOptions: true, links: result });
        }
      }
      return JSON.stringify({ moreOptions: false, links: result });
    })()
  `);
  console.log(projectLink);

  // Click "More Project Options" to see the dropdown
  console.log('\n=== MORE PROJECT OPTIONS ===');
  await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim().includes('More Project Options')) {
          btns[i].click();
          return 'Clicked';
        }
      }
      return 'Not found';
    })()
  `);
  await sleep(1000);

  // Check what options appeared
  const options = await c.ev(`
    (() => {
      var items = document.querySelectorAll('[role="menuitem"], [role="option"], .dropdown-item, .menu-item, li a, [class*="menu"] a, [class*="dropdown"] a, [class*="popover"] a, [class*="popover"] button');
      var result = [];
      for (var i = 0; i < items.length; i++) {
        if (items[i].offsetParent || (items[i].closest('[class*="popper"]') && window.getComputedStyle(items[i].closest('[class*="popper"]')).display !== 'none')) {
          var text = items[i].textContent.trim();
          if (text && text.length < 60) {
            result.push({ text: text, tag: items[i].tagName, href: items[i].href ? items[i].href.substring(0, 150) : '' });
          }
        }
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log(options);

  // Look for a visible popper/dropdown
  const dropdown = await c.ev(`
    (() => {
      var poppers = document.querySelectorAll('[class*="popper"], [class*="dropdown-menu"], [role="menu"], [class*="popover"]');
      var result = [];
      for (var i = 0; i < poppers.length; i++) {
        var style = window.getComputedStyle(poppers[i]);
        if (style.display !== 'none' && style.visibility !== 'hidden' && poppers[i].innerText.trim().length > 0) {
          result.push({
            classes: (typeof poppers[i].className === 'string' ? poppers[i].className : '').substring(0, 80),
            text: poppers[i].innerText.trim().substring(0, 300)
          });
        }
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('\nDropdowns:', dropdown);

  // Try clicking the project title to view it
  console.log('\n=== CLICKING PROJECT TITLE ===');
  const titleClick = await c.ev(`
    (() => {
      // Find the project title link
      var links = document.querySelectorAll('a');
      for (var i = 0; i < links.length; i++) {
        if (links[i].textContent.includes('custom Revit') || links[i].textContent.includes('BIM workflow')) {
          return JSON.stringify({ found: true, href: links[i].href, text: links[i].textContent.trim().substring(0, 80) });
        }
      }
      // Try clicking text that looks like the title
      var allEls = document.querySelectorAll('h2, h3, h4, h5, span, div, a, p');
      for (var j = 0; j < allEls.length; j++) {
        var t = allEls[j].textContent.trim();
        if (t.includes('custom Revit') && t.includes('BIM workflow') && allEls[j].children.length < 3) {
          return JSON.stringify({ found: true, tag: allEls[j].tagName, text: t.substring(0, 80), clickable: window.getComputedStyle(allEls[j]).cursor });
        }
      }
      return JSON.stringify({ found: false });
    })()
  `);
  console.log(titleClick);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
