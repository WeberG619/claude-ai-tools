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
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  console.log("Open tabs:");
  tabs.filter(t => t.type === "page").forEach(t => console.log("  " + t.url.substring(0, 120)));

  // Check if Outlier tab exists
  const outlierTab = tabs.find(t => t.type === "page" && t.url.includes("outlier"));
  if (outlierTab) {
    console.log("\nOutlier tab found!");
    let { ws, send, eval_ } = await connectToPage("outlier");
    let r = await eval_(`return window.location.href`);
    console.log("URL:", r);
    r = await eval_(`return document.body.innerText.substring(0, 5000)`);
    console.log("\nPage:", r);
    ws.close();
  } else {
    console.log("\nNo Outlier tab - need to navigate there.");
    // Use the DataAnnotation tab to open Outlier
    const daTab = tabs.find(t => t.type === "page");
    if (daTab) {
      let { ws, send, eval_ } = await connectToPage(daTab.url.includes("dataannotation") ? "dataannotation" : daTab.url.substring(8, 30));
      await eval_(`window.open('https://app.outlier.ai', '_blank')`);
      console.log("Opened Outlier in new tab");
      await sleep(5000);

      // Check tabs again
      const tabs2 = await (await fetch(`${CDP_HTTP}/json`)).json();
      const newOutlier = tabs2.find(t => t.type === "page" && t.url.includes("outlier"));
      if (newOutlier) {
        ws.close();
        await sleep(500);
        let conn = await connectToPage("outlier");
        let r = await conn.eval_(`return window.location.href`);
        console.log("\nOutlier URL:", r);
        r = await conn.eval_(`return document.body.innerText.substring(0, 5000)`);
        console.log("\nPage:", r);
        conn.ws.close();
      }
      ws.close();
    }
  }
})().catch(e => console.error("Error:", e.message));
