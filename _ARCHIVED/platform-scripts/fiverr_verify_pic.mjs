const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found for: ${urlMatch}`);
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
  return { ws, send, eval_ };
}

(async () => {
  let { ws, send, eval_ } = await connectToPage("fiverr");

  // Reload the profile page to verify
  await send("Page.navigate", { url: "https://www.fiverr.com/users/weberg619" });
  await sleep(5000);

  // Check avatar image
  let r = await eval_(`
    const imgs = document.querySelectorAll('img');
    const profileImgs = Array.from(imgs).filter(i =>
      i.src.includes('profile') || i.src.includes('avatar') ||
      i.className.includes('profile') || i.className.includes('avatar') ||
      i.closest('.profile-pict, .user-profile-image, [class*="avatar"]')
    );
    return JSON.stringify(profileImgs.map(i => ({
      src: i.src,
      w: i.naturalWidth,
      h: i.naturalHeight,
      classes: i.className.substring(0, 60)
    })));
  `);
  console.log("Profile images:", r);

  // Take a screenshot to visually verify
  const screenshot = await send("Page.captureScreenshot", {
    format: "png",
    clip: { x: 400, y: 80, width: 400, height: 250, scale: 1 }
  });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\fiverr_profile_check.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved to D:\\_CLAUDE-TOOLS\\fiverr_profile_check.png");

  ws.close();
})().catch(e => console.error("Error:", e.message));
