// Navigate to Freelancer profile edit page and upload photo
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
  let { ws, send, eval_ } = await connectToPage("freelancer.com");
  console.log("Connected\n");

  // Check current URL
  let r = await eval_(`return location.href`);
  console.log("Current URL:", r);

  // First check if there's a "Complete your profile" link/button on the current page
  r = await eval_(`
    const links = Array.from(document.querySelectorAll('a, button'))
      .filter(el => el.offsetParent !== null && (
        el.textContent.trim().toLowerCase().includes('complete your profile') ||
        el.textContent.trim().toLowerCase().includes('edit profile') ||
        el.textContent.trim().toLowerCase().includes('complete profile') ||
        el.href?.includes('settings/profile') ||
        el.href?.includes('new-freelancer')
      ))
      .map(el => ({
        tag: el.tagName,
        text: el.textContent.trim().substring(0, 60),
        href: el.href?.substring(0, 80) || '',
        class: el.className?.toString()?.substring(0, 50)
      }));
    return JSON.stringify(links);
  `);
  console.log("Profile links:", r);

  // Navigate to profile settings
  console.log("\nNavigating to profile settings...");
  await send("Page.navigate", { url: "https://www.freelancer.com/users/settings/profile" });
  await sleep(5000);

  // Check what loaded
  r = await eval_(`return location.href`);
  console.log("New URL:", r);

  // Check page content
  r = await eval_(`
    const fileInputs = Array.from(document.querySelectorAll('input[type="file"]'));
    const avatarEls = Array.from(document.querySelectorAll('[class*="avatar" i], [class*="photo" i], [class*="picture" i], [class*="upload" i]'))
      .filter(el => el.offsetParent !== null || el.tagName === 'INPUT')
      .map(el => ({
        tag: el.tagName,
        class: el.className?.toString()?.substring(0, 60),
        text: el.textContent?.trim()?.substring(0, 40),
        type: el.type || ''
      }));
    return JSON.stringify({
      url: location.href,
      fileInputCount: fileInputs.length,
      fileInputs: fileInputs.map(f => ({ id: f.id, name: f.name, accept: f.accept })),
      avatarEls: avatarEls.slice(0, 10),
      preview: document.body.innerText.substring(0, 2000)
    });
  `);
  console.log("\nPage state:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
