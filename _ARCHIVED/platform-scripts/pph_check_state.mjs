// Check PeoplePerHour registration state
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const matches = tabs.filter(t => t.type === "page" && t.url.includes(urlMatch));
  console.log(`Found ${matches.length} tabs matching "${urlMatch}":`);
  matches.forEach(t => console.log(`  - ${t.title} | ${t.url.substring(0, 80)}`));

  const tab = matches[0];
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

async function checkTab(urlMatch) {
  console.log(`\n=== Checking ${urlMatch} ===`);
  try {
    const { ws, send, eval_ } = await connectToPage(urlMatch);

    const r = await eval_(`
      return JSON.stringify({
        url: location.href,
        title: document.title,
        preview: document.body.innerText.substring(0, 3000),
        inputs: Array.from(document.querySelectorAll('input, select, textarea'))
          .filter(i => i.offsetParent !== null)
          .map(i => ({
            tag: i.tagName, type: i.type, name: i.name, id: i.id,
            placeholder: i.placeholder || '',
            value: i.type !== 'password' ? (i.value || '').substring(0, 50) : '***',
            ariaLabel: i.getAttribute('aria-label') || ''
          })),
        buttons: Array.from(document.querySelectorAll('button, input[type="submit"]'))
          .filter(b => b.offsetParent !== null)
          .map(b => ({
            text: b.textContent?.trim().substring(0, 60) || b.value || '',
            type: b.type,
            disabled: b.disabled
          }))
          .filter(b => b.text.length > 0)
      });
    `);

    const state = JSON.parse(r);
    console.log(`URL: ${state.url}`);
    console.log(`Title: ${state.title}`);
    console.log(`\nVisible inputs (${state.inputs.length}):`);
    state.inputs.forEach(i => console.log(`  [${i.tag}] type=${i.type} name="${i.name}" id="${i.id}" placeholder="${i.placeholder}" value="${i.value}"`));
    console.log(`\nButtons (${state.buttons.length}):`);
    state.buttons.forEach(b => console.log(`  "${b.text}" type=${b.type} disabled=${b.disabled}`));
    console.log(`\nPage text preview:\n${state.preview.substring(0, 1500)}`);

    ws.close();
    return state;
  } catch (e) {
    console.log(`Error: ${e.message}`);
    return null;
  }
}

async function main() {
  // Check both PPH tabs
  await checkTab("peopleperhour.com/member-application");
  await checkTab("peopleperhour.com/freelancer/register");
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
