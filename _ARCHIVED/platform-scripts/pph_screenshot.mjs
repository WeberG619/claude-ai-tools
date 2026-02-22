// Take screenshot of PPH page
const CDP_HTTP = "http://localhost:9222";
const fs = await import('fs');

async function main() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("peopleperhour.com/member-application"));
  if (!tab) throw new Error("PPH tab not found");

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

  // Take full page screenshot
  const result = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
  const buffer = Buffer.from(result.data, 'base64');
  fs.writeFileSync('/mnt/d/_CLAUDE-TOOLS/pph_screenshot.png', buffer);
  console.log(`Screenshot saved: ${buffer.length} bytes`);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
