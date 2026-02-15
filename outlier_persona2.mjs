const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  // Find all targets including iframes
  const targets = await (await fetch(`${CDP_HTTP}/json`)).json();
  console.log("All targets:");
  for (const t of targets) {
    console.log(`  ${t.type}: ${t.url?.substring(0, 100)}`);
  }

  // Find the Persona iframe target
  const personaTarget = targets.find(t => t.url?.includes('persona'));
  if (!personaTarget) {
    console.log("\nNo Persona target found. Trying via page CDP...");

    // Connect to the Outlier page
    const outlierTab = targets.find(t => t.type === "page" && t.url?.includes("outlier"));
    if (!outlierTab) { console.log("No Outlier tab"); return; }

    const ws = new WebSocket(outlierTab.webSocketDebuggerUrl);
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

    // Get all frame targets
    const frameTree = await send("Page.getFrameTree");
    console.log("\nFrame tree:", JSON.stringify(frameTree, null, 2));

    // Take screenshot with device metrics for proper rendering
    const screenshot = await send("Page.captureScreenshot", {
      format: "png",
      captureBeyondViewport: false
    });

    // Save screenshot with Windows path
    const eval_ = async (expr) => {
      const r = await send("Runtime.evaluate", {
        expression: `(async () => { ${expr} })()`,
        returnByValue: true, awaitPromise: true
      });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result?.value;
    };

    // Save screenshot using a data URL approach - write to D:\ via node fs
    const fs = await import('fs');
    const path = await import('path');
    const screenshotPath = 'D:\\_CLAUDE-TOOLS\\outlier_screen.png';
    fs.writeFileSync(screenshotPath, Buffer.from(screenshot.data, 'base64'));
    console.log("Screenshot saved to:", screenshotPath);

    // Try to find the Persona frame and evaluate JS in it
    const frames = frameTree.frameTree;
    let personaFrame = null;

    function findPersonaFrame(node) {
      if (node.frame?.url?.includes('persona')) return node.frame;
      if (node.childFrames) {
        for (const child of node.childFrames) {
          const found = findPersonaFrame(child);
          if (found) return found;
        }
      }
      return null;
    }

    personaFrame = findPersonaFrame(frames);
    console.log("\nPersona frame:", personaFrame ? JSON.stringify(personaFrame) : "not found in frame tree");

    if (personaFrame) {
      // Execute JS in the Persona frame context
      try {
        const r = await send("Runtime.evaluate", {
          expression: `document.body.innerText.substring(0, 3000)`,
          returnByValue: true,
          contextId: undefined // we need the right context
        });
        console.log("\nMain page text (not iframe):", r.result?.value?.substring(0, 200));
      } catch(e) {
        console.log("Error evaluating:", e.message);
      }

      // Use Page.createIsolatedWorld for the iframe
      try {
        const world = await send("Page.createIsolatedWorld", {
          frameId: personaFrame.id,
          worldName: "persona_inspect"
        });
        console.log("\nCreated isolated world:", JSON.stringify(world));

        const r2 = await send("Runtime.evaluate", {
          expression: "document.body ? document.body.innerText.substring(0, 3000) : 'no body'",
          returnByValue: true,
          contextId: world.executionContextId
        });
        console.log("\nPersona content:", r2.result?.value);
      } catch(e) {
        console.log("Error with isolated world:", e.message);
      }
    }

    ws.close();
  } else {
    console.log("\nFound Persona target:", personaTarget.url?.substring(0, 100));
    // Connect directly to Persona iframe
    const ws = new WebSocket(personaTarget.webSocketDebuggerUrl);
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

    const r = await send("Runtime.evaluate", {
      expression: "document.body.innerText.substring(0, 3000)",
      returnByValue: true
    });
    console.log("\nPersona content:", r.result?.value);

    ws.close();
  }
})().catch(e => console.error("Error:", e.message));
