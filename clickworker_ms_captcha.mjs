const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  let tab = tabs.find(t => t.type === "page" && (t.url.includes("signup.live") || t.url.includes("live.com") || t.url.includes("microsoft")));
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

  // Find the challenge iframe position
  let r = await eval_(`
    const iframes = document.querySelectorAll('iframe');
    return JSON.stringify(Array.from(iframes).map(f => {
      const rect = f.getBoundingClientRect();
      return {
        src: f.src?.substring(0, 80),
        x: rect.x, y: rect.y, w: rect.width, h: rect.height,
        visible: rect.width > 0 && rect.height > 0
      };
    }));
  `);
  console.log("Iframes:", r);

  // Find the visible hsprotect iframe
  const iframes = JSON.parse(r);
  const challengeIframe = iframes.find(f => f.src.includes('hsprotect') && f.visible);

  if (challengeIframe) {
    console.log("\nChallenge iframe at:", challengeIframe.x, challengeIframe.y, challengeIframe.w, "x", challengeIframe.h);

    // The "press and hold" button is typically in the center of the iframe
    const btnX = challengeIframe.x + challengeIframe.w / 2;
    const btnY = challengeIframe.y + challengeIframe.h / 2;

    console.log("Pressing at:", btnX, btnY);

    // Move to button
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: btnX, y: btnY });
    await sleep(100);

    // Press and HOLD for 3 seconds
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: btnX, y: btnY, button: "left", clickCount: 1 });
    console.log("Mouse pressed - holding...");
    await sleep(3000);

    // Release
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: btnX, y: btnY, button: "left", clickCount: 1 });
    console.log("Mouse released");

    await sleep(5000);
  } else {
    console.log("No visible challenge iframe found");
  }

  r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 4000)`);
  console.log("\nPage:", r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_ms_captcha.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
