const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(CDP_HTTP + "/json")).json();
  console.log("All tabs:");
  tabs.filter(t => t.type === "page").forEach((t, i) => console.log(`  ${i}: ${t.url.substring(0, 120)}`));

  // Find the Google auth tab
  const googleTab = tabs.find(t => t.type === "page" && t.url.includes("accounts.google.com"));
  if (googleTab) {
    console.log("\nGoogle auth tab found - activating it...");
    // Use CDP to bring this tab to front
    const ws = new WebSocket(googleTab.webSocketDebuggerUrl);
    await new Promise(r => ws.addEventListener("open", r));
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

    // Bring tab to front
    await send("Page.bringToFront");
    console.log("Tab brought to front!");

    // Also activate via target
    try {
      await fetch(`${CDP_HTTP}/json/activate/${googleTab.id}`, { method: "PUT" });
      console.log("Tab activated via HTTP API");
    } catch(e) {}

    ws.close();
  } else {
    console.log("\nNo Google auth tab found");
  }
})().catch(e => console.error("Error:", e.message));
