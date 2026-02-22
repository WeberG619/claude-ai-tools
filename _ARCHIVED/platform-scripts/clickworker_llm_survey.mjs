const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  let tab = tabs.find(t => t.type === "page" && t.url.includes("clickworker"));
  if (!tab) tab = tabs.find(t => t.type === "page");
  if (!tab) { console.log("No tab"); return; }

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

  // Navigate to LLM survey
  await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs/1262195/edit" });
  await sleep(5000);

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);

  // Get FULL page text
  r = await eval_(`return document.body.innerText.substring(0, 10000)`);
  console.log("\nFull page:", r);

  // Get ALL form elements including hidden ones
  r = await eval_(`
    const inputs = document.querySelectorAll('input, select, textarea, button');
    return JSON.stringify(Array.from(inputs).map(i => ({
      tag: i.tagName, type: i.type, name: i.name || '', id: i.id || '',
      value: i.value?.substring(0, 80) || '',
      visible: i.offsetParent !== null,
      label: i.labels?.[0]?.textContent?.trim().substring(0, 80) || ''
    })).slice(0, 50));
  `);
  console.log("\nALL form fields:", r);

  // Check for iframes
  r = await eval_(`
    const iframes = document.querySelectorAll('iframe');
    return JSON.stringify(Array.from(iframes).map(f => ({
      src: f.src?.substring(0, 150),
      w: f.width, h: f.height
    })));
  `);
  console.log("\nIframes:", r);

  // Check for external survey links
  r = await eval_(`
    const links = Array.from(document.querySelectorAll('a'));
    return JSON.stringify(links.filter(a => {
      const href = a.href || '';
      return href.includes('survey') || href.includes('form') || href.includes('qualtrics') ||
             href.includes('typeform') || href.includes('google') || href.includes('external') ||
             !href.includes('clickworker');
    }).map(a => ({text: a.textContent?.trim().substring(0, 60), href: a.href})));
  `);
  console.log("\nExternal links:", r);

  // Check for dynamically loaded content / scrollable content
  r = await eval_(`
    const contentDiv = document.querySelector('.card-body, .content, main');
    if (contentDiv) return contentDiv.scrollHeight + ' vs ' + contentDiv.clientHeight;
    return 'no content div';
  `);
  console.log("\nScroll:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
