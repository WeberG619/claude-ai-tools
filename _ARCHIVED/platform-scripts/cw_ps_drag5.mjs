import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 40000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const psTab = tabs.find(t => t.type === "page" && t.url.includes('purespectrum'));
  if (!psTab) { L("No PS tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

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

    // Fire-and-forget send (don't wait for response)
    const fire = (method, params = {}) => { const i = ++id; ws.send(JSON.stringify({ id: i, method, params })); };

    (async () => {
      // Step 1: Reload the page to reset drag state
      L("Reloading page...");
      await send("Page.reload", { ignoreCache: false });
      await sleep(4000);

      // Wait for page to load
      let loaded = false;
      for (let i = 0; i < 10; i++) {
        try {
          let title = await eval_(`document.title`);
          if (title) { loaded = true; break; }
        } catch(e) {}
        await sleep(1000);
      }
      if (!loaded) { L("Page didn't load"); ws.close(); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

      // Wait a bit more for Angular to init
      await sleep(2000);

      // Get fresh positions
      let positions = await eval_(`
        (function() {
          var box79 = null;
          var imgs = document.querySelectorAll('.cdk-drag img');
          for (var i = 0; i < imgs.length; i++) {
            if (imgs[i].alt === '79') { box79 = imgs[i].closest('.cdk-drag'); break; }
          }
          if (!box79) return JSON.stringify({ error: 'no box 79, imgs: ' + imgs.length });
          var br = box79.getBoundingClientRect();

          var dz = document.querySelector('#dropZoneList');
          if (!dz) return JSON.stringify({ error: 'no drop zone' });
          var dr = dz.getBoundingClientRect();

          return JSON.stringify({
            box: { x: Math.round(br.x + br.width/2), y: Math.round(br.y + br.height/2) },
            dz: { x: Math.round(dr.x + dr.width/2), y: Math.round(dr.y + dr.height/2) },
            dzChildren: dz.children.length
          });
        })()
      `);
      L("Positions: " + positions);
      let pos = JSON.parse(positions);
      if (pos.error) { L("Error: " + pos.error); ws.close(); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

      let sx = pos.box.x, sy = pos.box.y;
      let tx = pos.dz.x, ty = pos.dz.y;
      L("Drag: (" + sx + "," + sy + ") -> (" + tx + "," + ty + ")");

      // Step 2: Fire CDP mouse events without awaiting (fire-and-forget to avoid hang)
      // mousePressed
      fire("Input.dispatchMouseEvent", { type: "mousePressed", x: sx, y: sy, button: "left", clickCount: 1, buttons: 1 });
      await sleep(500);

      // mouseMoved - multiple steps
      let steps = 15;
      for (let s = 1; s <= steps; s++) {
        let px = Math.round(sx + (tx - sx) * s / steps);
        let py = Math.round(sy + (ty - sy) * s / steps);
        fire("Input.dispatchMouseEvent", { type: "mouseMoved", x: px, y: py, button: "left", buttons: 1 });
        await sleep(50);
      }

      await sleep(300);

      // mouseReleased
      fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: tx, y: ty, button: "left", clickCount: 1, buttons: 0 });
      await sleep(2000);

      // Step 3: Check result
      let afterDrag = await eval_(`
        (function() {
          var dz = document.querySelector('#dropZoneList');
          var page = document.body.innerText.substring(0, 300);
          return JSON.stringify({
            dzChildren: dz ? dz.children.length : -1,
            dzHTML: dz ? dz.innerHTML.substring(0, 200) : 'null',
            page: page
          });
        })()
      `);
      L("After CDP drag: " + afterDrag);

      let result = JSON.parse(afterDrag);
      if (result.page.includes('drag and drop')) {
        L("Still on drag page. Trying approach 2: setPointerCapture simulation...");

        // Approach 2: CDK uses setPointerCapture on pointerdown
        // We need to dispatch events where CDK expects them (on document after capture)
        let r2 = await eval_(`
          (function() {
            var box79 = null;
            var imgs = document.querySelectorAll('.cdk-drag img');
            for (var i = 0; i < imgs.length; i++) {
              if (imgs[i].alt === '79') { box79 = imgs[i].closest('.cdk-drag'); break; }
            }
            var dz = document.querySelector('#dropZoneList');
            var br = box79.getBoundingClientRect();
            var dr = dz.getBoundingClientRect();
            var sx = br.x + br.width/2, sy = br.y + br.height/2;
            var tx = dr.x + dr.width/2, ty = dr.y + dr.height/2;

            // Override setPointerCapture to track it
            var capturedEl = null;
            var origCapture = Element.prototype.setPointerCapture;
            Element.prototype.setPointerCapture = function(id) {
              capturedEl = this;
              return origCapture.call(this, id);
            };

            // Dispatch pointerdown
            box79.dispatchEvent(new PointerEvent('pointerdown', {
              clientX: sx, clientY: sy, bubbles: true, cancelable: true, composed: true,
              pointerId: 1, pointerType: 'mouse', isPrimary: true,
              button: 0, buttons: 1, pressure: 0.5
            }));

            // If CDK captured pointer, dispatch moves on the captured element
            var moveTarget = capturedEl || document;
            var log = 'captured=' + (capturedEl ? capturedEl.tagName + '.' + (capturedEl.className || '').substring(0,30) : 'none');

            for (var s = 1; s <= 20; s++) {
              var px = sx + (tx - sx) * s / 20;
              var py = sy + (ty - sy) * s / 20;
              moveTarget.dispatchEvent(new PointerEvent('pointermove', {
                clientX: px, clientY: py, bubbles: true, cancelable: true, composed: true,
                pointerId: 1, pointerType: 'mouse', isPrimary: true,
                button: 0, buttons: 1, pressure: 0.5
              }));
            }

            // pointerup
            moveTarget.dispatchEvent(new PointerEvent('pointerup', {
              clientX: tx, clientY: ty, bubbles: true, cancelable: true, composed: true,
              pointerId: 1, pointerType: 'mouse', isPrimary: true,
              button: 0, buttons: 0, pressure: 0
            }));

            Element.prototype.setPointerCapture = origCapture;

            return log + ' | dz: ' + dz.innerHTML.substring(0, 200);
          })()
        `);
        L("SetPointerCapture: " + r2);
        await sleep(1000);

        let page2 = await eval_(`document.body.innerText.substring(0, 300)`);
        L("Page: " + page2.substring(0, 200));
      }

      // If still stuck, try clicking Next anyway (maybe the drop worked visually)
      let page3 = await eval_(`document.body.innerText.substring(0, 300)`);
      if (page3.includes('Next')) {
        L("Clicking Next...");
        let nextBtn = await eval_(`
          (function() {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
              if (btns[i].textContent.trim() === 'Next') {
                var r = btns[i].getBoundingClientRect();
                return JSON.stringify({ x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2), disabled: btns[i].disabled });
              }
            }
            return null;
          })()
        `);
        L("Next btn: " + nextBtn);
        if (nextBtn) {
          let nb = JSON.parse(nextBtn);
          fire("Input.dispatchMouseEvent", { type: "mousePressed", x: nb.x, y: nb.y, button: "left", clickCount: 1 });
          await sleep(100);
          fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: nb.x, y: nb.y, button: "left", clickCount: 1 });
          await sleep(2000);
          let after = await eval_(`document.body.innerText.substring(0, 300)`);
          L("After Next: " + after.substring(0, 200));
        }
      }

      // Screenshot
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
