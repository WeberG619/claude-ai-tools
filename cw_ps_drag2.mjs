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

      // Get precise positions of box with alt="79" and the drop-zone
      let positions = await eval_(`
        (function() {
          var box79 = null;
          var imgs = document.querySelectorAll('.cdk-drag img');
          for (var i = 0; i < imgs.length; i++) {
            if (imgs[i].alt === '79') {
              box79 = imgs[i].closest('.cdk-drag');
              break;
            }
          }
          if (!box79) return JSON.stringify({ error: 'no box 79' });
          var boxRect = box79.getBoundingClientRect();

          // Get the drop zone - it has class 'drop-zone'
          var dz = document.querySelector('.drop-zone');
          if (!dz) dz = document.querySelector('.cdk-drop-list:not(:has(.cdk-drag))');
          if (!dz) {
            // Fallback: find the cdk-drop-list that doesn't contain cdk-drag items
            var lists = document.querySelectorAll('.cdk-drop-list');
            for (var j = 0; j < lists.length; j++) {
              if (lists[j].querySelectorAll('.cdk-drag').length === 0) {
                dz = lists[j];
                break;
              }
            }
          }
          if (!dz) return JSON.stringify({ error: 'no drop zone', lists: document.querySelectorAll('.cdk-drop-list').length });
          var dzRect = dz.getBoundingClientRect();

          return JSON.stringify({
            box: { x: Math.round(boxRect.x + boxRect.width/2), y: Math.round(boxRect.y + boxRect.height/2), w: Math.round(boxRect.width), h: Math.round(boxRect.height) },
            dz: { x: Math.round(dzRect.x + dzRect.width/2), y: Math.round(dzRect.y + dzRect.height/2), w: Math.round(dzRect.width), h: Math.round(dzRect.height) },
            dzClasses: dz.className.substring(0, 100),
            dzHTML: dz.outerHTML.substring(0, 200)
          });
        })()
      `);
      L("Positions: " + positions);
      let pos = JSON.parse(positions);
      if (pos.error) { L("ERROR: " + pos.error); ws.close(); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

      let sx = pos.box.x, sy = pos.box.y;
      let tx = pos.dz.x, ty = pos.dz.y;
      L("Dragging from (" + sx + "," + sy + ") to (" + tx + "," + ty + ")");

      // Method 1: CDP mouse events with slow movement
      // Angular CDK needs pointerdown → pointermove (crossing 5px threshold) → pointerup
      // CDP mousePressed generates both pointerdown + mousedown

      // Press at source
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: sx, y: sy, button: "left", clickCount: 1 });
      await sleep(300);

      // Move slowly - CDK needs movement to detect drag start (5px threshold)
      let steps = 20;
      for (let s = 1; s <= steps; s++) {
        let px = Math.round(sx + (tx - sx) * s / steps);
        let py = Math.round(sy + (ty - sy) * s / steps);
        await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: px, y: py, button: "left" });
        await sleep(30);
      }
      await sleep(200);

      // Release at target
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: tx, y: ty, button: "left", clickCount: 1 });
      await sleep(1000);

      // Check result
      let afterDrag = await eval_(`
        (function() {
          var dz = document.querySelector('.drop-zone');
          if (!dz) {
            var lists = document.querySelectorAll('.cdk-drop-list');
            for (var j = 0; j < lists.length; j++) {
              if (lists[j].querySelectorAll('.cdk-drag').length === 0) { dz = lists[j]; break; }
            }
          }
          var dzChildren = dz ? dz.children.length + ' children, HTML: ' + dz.innerHTML.substring(0, 200) : 'no dz';
          var boxes = document.querySelectorAll('.cdk-drag');
          return JSON.stringify({ dzState: dzChildren, boxCount: boxes.length, pageText: document.body.innerText.substring(0, 300) });
        })()
      `);
      L("After drag method 1: " + afterDrag);

      let result1 = JSON.parse(afterDrag);
      if (result1.dzState.includes('img') || result1.dzState.includes('79')) {
        L("DRAG SUCCEEDED!");
      } else {
        L("Method 1 didn't work. Trying JS-based drag simulation...");

        // Method 2: Dispatch pointer events via JS
        await eval_(`
          (function() {
            var box79 = null;
            var imgs = document.querySelectorAll('.cdk-drag img');
            for (var i = 0; i < imgs.length; i++) {
              if (imgs[i].alt === '79') { box79 = imgs[i].closest('.cdk-drag'); break; }
            }
            if (!box79) return 'no box';

            var boxRect = box79.getBoundingClientRect();
            var sx = boxRect.x + boxRect.width/2;
            var sy = boxRect.y + boxRect.height/2;

            // Find drop zone
            var dz = document.querySelector('.drop-zone');
            if (!dz) {
              var lists = document.querySelectorAll('.cdk-drop-list');
              for (var j = 0; j < lists.length; j++) {
                if (lists[j].querySelectorAll('.cdk-drag').length === 0) { dz = lists[j]; break; }
              }
            }
            var dzRect = dz.getBoundingClientRect();
            var tx = dzRect.x + dzRect.width/2;
            var ty = dzRect.y + dzRect.height/2;

            // Dispatch pointer events on the element
            box79.dispatchEvent(new PointerEvent('pointerdown', {
              clientX: sx, clientY: sy, bubbles: true, cancelable: true,
              pointerId: 1, pointerType: 'mouse', isPrimary: true, button: 0, buttons: 1
            }));

            // Move in steps to cross threshold
            var steps = 15;
            for (var s = 1; s <= steps; s++) {
              var px = sx + (tx - sx) * s / steps;
              var py = sy + (ty - sy) * s / steps;
              document.elementFromPoint(px, py).dispatchEvent(new PointerEvent('pointermove', {
                clientX: px, clientY: py, bubbles: true, cancelable: true,
                pointerId: 1, pointerType: 'mouse', isPrimary: true, button: 0, buttons: 1
              }));
            }

            // Release
            var dropTarget = document.elementFromPoint(tx, ty);
            dropTarget.dispatchEvent(new PointerEvent('pointerup', {
              clientX: tx, clientY: ty, bubbles: true, cancelable: true,
              pointerId: 1, pointerType: 'mouse', isPrimary: true, button: 0
            }));

            return 'dispatched pointer events';
          })()
        `);
        await sleep(1000);

        let afterJS = await eval_(`
          (function() {
            var dz = document.querySelector('.drop-zone');
            if (!dz) {
              var lists = document.querySelectorAll('.cdk-drop-list');
              for (var j = 0; j < lists.length; j++) {
                if (lists[j].querySelectorAll('.cdk-drag').length === 0) { dz = lists[j]; break; }
              }
            }
            return dz ? dz.children.length + ' children: ' + dz.innerHTML.substring(0, 200) : 'no dz';
          })()
        `);
        L("After JS pointer events: " + afterJS);

        if (!afterJS.includes('79')) {
          L("Method 2 didn't work either. Trying touch events...");

          // Method 3: Use Input.dispatchTouchEvent
          await send("Input.dispatchTouchEvent", {
            type: "touchStart",
            touchPoints: [{ x: sx, y: sy }]
          });
          await sleep(300);

          for (let s = 1; s <= 15; s++) {
            let px = Math.round(sx + (tx - sx) * s / 15);
            let py = Math.round(sy + (ty - sy) * s / 15);
            await send("Input.dispatchTouchEvent", {
              type: "touchMove",
              touchPoints: [{ x: px, y: py }]
            });
            await sleep(30);
          }

          await send("Input.dispatchTouchEvent", {
            type: "touchEnd",
            touchPoints: []
          });
          await sleep(1000);

          let afterTouch = await eval_(`
            (function() {
              var dz = document.querySelector('.drop-zone');
              if (!dz) {
                var lists = document.querySelectorAll('.cdk-drop-list');
                for (var j = 0; j < lists.length; j++) {
                  if (lists[j].querySelectorAll('.cdk-drag').length === 0) { dz = lists[j]; break; }
                }
              }
              return dz ? dz.children.length + ' children: ' + dz.innerHTML.substring(0, 200) : 'no dz';
            })()
          `);
          L("After touch events: " + afterTouch);
        }
      }

      // Take screenshot
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
