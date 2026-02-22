import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 45000);

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

      // Do the entire drag simulation inside the browser using a promise with timeouts
      let dragResult = await eval_(`
        new Promise(function(resolve) {
          var box79 = null;
          var imgs = document.querySelectorAll('.cdk-drag img');
          for (var i = 0; i < imgs.length; i++) {
            if (imgs[i].alt === '79') { box79 = imgs[i].closest('.cdk-drag'); break; }
          }
          if (!box79) { resolve('no box 79'); return; }

          var dz = document.querySelector('#dropZoneList');
          if (!dz) dz = document.querySelector('.drop-zone');
          if (!dz) { resolve('no drop zone'); return; }

          var boxRect = box79.getBoundingClientRect();
          var dzRect = dz.getBoundingClientRect();

          var sx = boxRect.x + boxRect.width / 2;
          var sy = boxRect.y + boxRect.height / 2;
          var tx = dzRect.x + dzRect.width / 2;
          var ty = dzRect.y + dzRect.height / 2;

          var log = [];
          log.push('from (' + Math.round(sx) + ',' + Math.round(sy) + ') to (' + Math.round(tx) + ',' + Math.round(ty) + ')');

          // Dispatch pointer events with proper sequencing
          function makeEvent(type, x, y, extra) {
            return new PointerEvent(type, Object.assign({
              clientX: x, clientY: y,
              screenX: x, screenY: y,
              pageX: x, pageY: y,
              bubbles: true, cancelable: true,
              pointerId: 1, pointerType: 'mouse', isPrimary: true,
              width: 1, height: 1, pressure: type === 'pointerup' ? 0 : 0.5
            }, extra || {}));
          }

          // Step 1: pointerdown on the drag element
          box79.dispatchEvent(makeEvent('pointerdown', sx, sy, { button: 0, buttons: 1 }));
          box79.dispatchEvent(new MouseEvent('mousedown', {
            clientX: sx, clientY: sy, bubbles: true, cancelable: true, button: 0, buttons: 1
          }));
          log.push('pointerdown dispatched');

          // Step 2: move in steps with requestAnimationFrame for proper timing
          var steps = 20;
          var step = 0;

          function doStep() {
            step++;
            if (step <= steps) {
              var px = sx + (tx - sx) * step / steps;
              var py = sy + (ty - sy) * step / steps;
              var target = document.elementFromPoint(px, py) || document.body;
              target.dispatchEvent(makeEvent('pointermove', px, py, { button: 0, buttons: 1 }));
              target.dispatchEvent(new MouseEvent('mousemove', {
                clientX: px, clientY: py, bubbles: true, cancelable: true, button: 0, buttons: 1
              }));
              if (step === 1 || step === steps) log.push('move step ' + step + ' at (' + Math.round(px) + ',' + Math.round(py) + ') target=' + target.tagName + '.' + (target.className || '').substring(0, 30));
              setTimeout(doStep, 30);
            } else {
              // Step 3: pointerup at target
              var dropEl = document.elementFromPoint(tx, ty) || dz;
              dropEl.dispatchEvent(makeEvent('pointerup', tx, ty, { button: 0, buttons: 0 }));
              dropEl.dispatchEvent(new MouseEvent('mouseup', {
                clientX: tx, clientY: ty, bubbles: true, cancelable: true, button: 0, buttons: 0
              }));
              log.push('pointerup at (' + Math.round(tx) + ',' + Math.round(ty) + ') on ' + dropEl.tagName);

              // Check result after a moment
              setTimeout(function() {
                var dzNow = document.querySelector('#dropZoneList') || document.querySelector('.drop-zone');
                var state = dzNow ? dzNow.children.length + ' children: ' + dzNow.innerHTML.substring(0, 200) : 'no dz';
                log.push('drop zone: ' + state);
                resolve(log.join(' | '));
              }, 500);
            }
          }

          setTimeout(doStep, 100);
        })
      `);
      L("Drag result: " + dragResult);

      // Check if page still shows drag question
      let pageCheck = await eval_(`document.body.innerText.substring(0, 400)`);
      L("Page: " + pageCheck.substring(0, 300));

      // If drag didn't work, try DataTransfer approach
      if (pageCheck.includes('drag and drop')) {
        L("Still on drag page. Trying DataTransfer API...");

        let dtResult = await eval_(`
          new Promise(function(resolve) {
            var box79 = null;
            var imgs = document.querySelectorAll('.cdk-drag img');
            for (var i = 0; i < imgs.length; i++) {
              if (imgs[i].alt === '79') { box79 = imgs[i].closest('.cdk-drag'); break; }
            }
            var dz = document.querySelector('#dropZoneList') || document.querySelector('.drop-zone');
            if (!box79 || !dz) { resolve('no elements'); return; }

            var boxRect = box79.getBoundingClientRect();
            var dzRect = dz.getBoundingClientRect();

            // Try HTML5 drag events
            var dt = new DataTransfer();
            dt.setData('text/plain', '79');

            box79.dispatchEvent(new DragEvent('dragstart', {
              clientX: boxRect.x + 50, clientY: boxRect.y + 50,
              dataTransfer: dt, bubbles: true, cancelable: true
            }));

            dz.dispatchEvent(new DragEvent('dragenter', {
              clientX: dzRect.x + 75, clientY: dzRect.y + 75,
              dataTransfer: dt, bubbles: true, cancelable: true
            }));

            dz.dispatchEvent(new DragEvent('dragover', {
              clientX: dzRect.x + 75, clientY: dzRect.y + 75,
              dataTransfer: dt, bubbles: true, cancelable: true
            }));

            dz.dispatchEvent(new DragEvent('drop', {
              clientX: dzRect.x + 75, clientY: dzRect.y + 75,
              dataTransfer: dt, bubbles: true, cancelable: true
            }));

            box79.dispatchEvent(new DragEvent('dragend', {
              clientX: dzRect.x + 75, clientY: dzRect.y + 75,
              dataTransfer: dt, bubbles: true, cancelable: true
            }));

            setTimeout(function() {
              var state = dz.children.length + ': ' + dz.innerHTML.substring(0, 200);
              resolve('DT done. DZ: ' + state);
            }, 500);
          })
        `);
        L("DataTransfer: " + dtResult);
      }

      // If still stuck, try programmatically moving the DOM element
      if (pageCheck.includes('drag and drop')) {
        L("Trying DOM manipulation...");

        let domResult = await eval_(`
          (function() {
            var box79 = null;
            var imgs = document.querySelectorAll('.cdk-drag img');
            for (var i = 0; i < imgs.length; i++) {
              if (imgs[i].alt === '79') { box79 = imgs[i].closest('.cdk-drag'); break; }
            }
            var dz = document.querySelector('#dropZoneList') || document.querySelector('.drop-zone');
            if (!box79 || !dz) return 'no elements';

            // Move the element in the DOM
            dz.appendChild(box79);

            // Trigger Angular change detection
            if (window.ng) {
              try {
                var appRef = window.ng.getComponent(document.querySelector('app-root'));
                if (appRef) appRef.detectChanges();
              } catch(e) {}
            }

            // Also try dispatching cdkDropListDropped event
            dz.dispatchEvent(new Event('cdkDropListDropped', { bubbles: true }));

            return 'Moved box79 to drop zone. DZ now: ' + dz.children.length + ' children';
          })()
        `);
        L("DOM move: " + domResult);
        await sleep(1000);

        let afterDOM = await eval_(`document.body.innerText.substring(0, 400)`);
        L("After DOM move: " + afterDOM.substring(0, 300));
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
