import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 60000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const psTab = tabs.find(t => t.type === "page" && t.url.includes('purespectrum'));
  if (!psTab) { L("No PureSpectrum tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(psTab.webSocketDebuggerUrl);
  ws.addEventListener("error", () => { L("WS error"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); });

  ws.addEventListener("open", () => {
    let id = 0;
    const pending = new Map();
    ws.addEventListener("message", e => {
      const m = JSON.parse(e.data);
      if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); if (m.error) p.rej(new Error(m.error.message)); else p.res(m.result); }
    });
    const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
    const eval_ = async (expr) => { const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result?.value; };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      // Check what's inside each draggable box
      let boxInfo = await eval_(`
        (function() {
          var boxes = document.querySelectorAll('.cdk-drag');
          var results = [];
          boxes.forEach(function(box, i) {
            var rect = box.getBoundingClientRect();
            results.push({
              idx: i,
              innerHTML: box.innerHTML.substring(0, 200),
              text: box.textContent.trim(),
              x: Math.round(rect.x + rect.width/2),
              y: Math.round(rect.y + rect.height/2),
              w: Math.round(rect.width),
              h: Math.round(rect.height),
              hasImg: box.querySelector('img') ? true : false,
              hasSvg: box.querySelector('svg') ? true : false,
              hasCanvas: box.querySelector('canvas') ? true : false,
              bgImage: window.getComputedStyle(box).backgroundImage.substring(0, 80),
              children: box.children.length
            });
          });
          // Drop zone
          var dz = document.querySelector('.drop-zone, .cdk-drop-list');
          var dzRect = dz ? dz.getBoundingClientRect() : {};
          return JSON.stringify({
            boxes: results,
            dropZone: dz ? { x: Math.round(dzRect.x + dzRect.width/2), y: Math.round(dzRect.y + dzRect.height/2), w: Math.round(dzRect.width), h: Math.round(dzRect.height) } : null
          });
        })()
      `);
      L("Box info: " + boxInfo);

      let info = JSON.parse(boxInfo);

      // Find which box likely contains "79"
      // The boxes might use background images with numbers
      // Let me check each box's computed style more carefully
      let boxStyles = await eval_(`
        (function() {
          var boxes = document.querySelectorAll('.cdk-drag');
          var results = [];
          boxes.forEach(function(box, i) {
            var style = window.getComputedStyle(box);
            var child = box.firstElementChild;
            var childStyle = child ? window.getComputedStyle(child) : null;
            results.push({
              idx: i,
              bg: style.backgroundImage.substring(0, 100),
              color: style.color,
              fontSize: style.fontSize,
              display: style.display,
              childTag: child ? child.tagName : 'none',
              childText: child ? child.textContent.trim() : '',
              childBg: childStyle ? childStyle.backgroundImage.substring(0, 100) : '',
              fullHTML: box.outerHTML.substring(0, 300)
            });
          });
          return JSON.stringify(results);
        })()
      `);
      L("\nBox styles: " + boxStyles);

      // Try using JS to simulate the Angular CDK drag-drop
      // CDK listens for pointer events, so dispatch those
      let targetBoxIdx = -1;
      let parsed = JSON.parse(boxStyles);
      // Check which box might have 79 - look at inner content
      for (let b of parsed) {
        if (b.childText.includes('79') || b.fullHTML.includes('79')) {
          targetBoxIdx = b.idx;
          break;
        }
      }

      if (targetBoxIdx < 0) {
        L("\nCan't determine which box has 79. Trying all three...");
        // Try each box - the one that works should advance
        for (let tryIdx = 0; tryIdx < info.boxes.length; tryIdx++) {
          let box = info.boxes[tryIdx];
          let dz = info.dropZone;
          if (!dz) { L("No drop zone!"); break; }

          L("\nTrying box " + tryIdx + " at (" + box.x + "," + box.y + ") -> drop at (" + dz.x + "," + dz.y + ")");

          // Simulate pointer drag using CDP
          // 1. Press at source
          await send("Input.dispatchMouseEvent", { type: "mousePressed", x: box.x, y: box.y, button: "left", clickCount: 1 });
          await sleep(200);

          // 2. Move slowly to target (CDK needs movement to detect drag)
          let steps = 10;
          for (let s = 1; s <= steps; s++) {
            let px = box.x + (dz.x - box.x) * s / steps;
            let py = box.y + (dz.y - box.y) * s / steps;
            await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: Math.round(px), y: Math.round(py), button: "left" });
            await sleep(50);
          }

          // 3. Release at target
          await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: dz.x, y: dz.y, button: "left", clickCount: 1 });
          await sleep(500);

          // Check if something changed
          let changed = await eval_(`
            (function() {
              var dz = document.querySelector('.drop-zone, .cdk-drop-list');
              return dz ? dz.children.length + ' children, text: ' + dz.textContent.trim() : 'no dz';
            })()
          `);
          L("Drop zone after: " + changed);
        }
      }

      await sleep(2000);

      // Try clicking Next
      let nextResult = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.trim() === 'Next') {
              var rect = btns[i].getBoundingClientRect();
              return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
            }
          }
          return null;
        })()
      `);
      if (nextResult) {
        let nr = JSON.parse(nextResult);
        await send("Input.dispatchMouseEvent", { type: "mousePressed", x: nr.x, y: nr.y, button: "left", clickCount: 1 });
        await sleep(100);
        await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: nr.x, y: nr.y, button: "left", clickCount: 1 });
        L("Clicked Next");
      }
      await sleep(3000);

      // Check result
      let url = await eval_(`window.location.href`);
      let page = await eval_(`document.body.innerText.substring(0, 1000)`);
      L("\nAfter: " + url.substring(0, 60));
      L("Page:\n" + page.substring(0, 500));

      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_survey.png', Buffer.from(ss.data, 'base64'));

      ws.close();
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
      process.exit(0);
    })().catch(e => {
      L("Error: " + e.message);
      ws.close();
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
      process.exit(1);
    });
  });
})().catch(e => {
  L("Fatal: " + e.message);
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
});
