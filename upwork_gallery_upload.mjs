// Upload image to gallery and complete remaining steps
const CDP = 'http://localhost:9222';
const sleep = ms => new Promise(r => setTimeout(r, ms));
import fs from 'fs';
import path from 'path';

async function getPages() {
  const r = await fetch(`${CDP}/json`);
  return (await r.json()).filter(t => t.type === 'page');
}

function connect(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let id = 1;
    const pending = new Map();
    ws.addEventListener('message', e => {
      const msg = JSON.parse(e.data);
      if (msg.id && pending.has(msg.id)) {
        const p = pending.get(msg.id);
        pending.delete(msg.id);
        msg.error ? p.rej(new Error(msg.error.message)) : p.res(msg.result);
      }
    });
    const send = (method, params = {}) => new Promise((res, rej) => {
      const mid = id++;
      pending.set(mid, { res, rej });
      ws.send(JSON.stringify({ id: mid, method, params }));
    });
    const ev = async (expr) => {
      const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result?.value;
    };
    const typeText = async (text) => {
      for (const char of text) {
        await send('Input.dispatchKeyEvent', { type: 'char', text: char, unmodifiedText: char });
        await sleep(8);
      }
    };
    ws.addEventListener('open', () => resolve({ ws, send, ev, typeText, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Create a simple placeholder image using canvas in the browser
  console.log('=== CREATING AND UPLOADING IMAGE ===');

  // First, find the file input element
  const fileInputInfo = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input[type="file"]');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        result.push({
          accept: inputs[i].accept,
          multiple: inputs[i].multiple,
          name: inputs[i].name,
          id: inputs[i].id
        });
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('File inputs:', fileInputInfo);

  // Use DOM.getDocument and query to find the file input node ID
  const doc = await c.send('DOM.getDocument', {});
  const rootNodeId = doc.root.nodeId;

  // Find file input elements via DOM
  const fileInputNodes = await c.send('DOM.querySelectorAll', {
    nodeId: rootNodeId,
    selector: 'input[type="file"][accept*="image"]'
  });
  console.log('File input nodes:', JSON.stringify(fileInputNodes));

  if (fileInputNodes.nodeIds && fileInputNodes.nodeIds.length > 0) {
    const fileNodeId = fileInputNodes.nodeIds[0];

    // Create a simple PNG image - a blue gradient with text
    // Generate a minimal valid PNG in the browser and convert to blob
    const imageCreated = await c.ev(`
      (async () => {
        var canvas = document.createElement('canvas');
        canvas.width = 1200;
        canvas.height = 800;
        var ctx = canvas.getContext('2d');

        // Background gradient
        var gradient = ctx.createLinearGradient(0, 0, 1200, 800);
        gradient.addColorStop(0, '#1a1a2e');
        gradient.addColorStop(1, '#16213e');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 1200, 800);

        // Grid pattern
        ctx.strokeStyle = 'rgba(0, 180, 255, 0.1)';
        ctx.lineWidth = 1;
        for (var i = 0; i < 1200; i += 40) {
          ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, 800); ctx.stroke();
        }
        for (var j = 0; j < 800; j += 40) {
          ctx.beginPath(); ctx.moveTo(0, j); ctx.lineTo(1200, j); ctx.stroke();
        }

        // Title
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 48px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Custom Revit C# Plugin Development', 600, 200);

        // Subtitle
        ctx.fillStyle = '#00b4ff';
        ctx.font = '28px Arial';
        ctx.fillText('BIM Automation | API Add-ins | Workflow Tools', 600, 260);

        // Features
        ctx.fillStyle = '#cccccc';
        ctx.font = '22px Arial';
        ctx.textAlign = 'left';
        var features = [
          '\\u2713  Revit API C# Add-in Development',
          '\\u2713  Custom Ribbon Buttons & UI Panels',
          '\\u2713  Batch Processing & Automation',
          '\\u2713  Data Extraction & Reporting',
          '\\u2713  Family & Parameter Management',
          '\\u2713  Dynamo Script Integration'
        ];
        for (var k = 0; k < features.length; k++) {
          ctx.fillText(features[k], 200, 360 + k * 45);
        }

        // Footer
        ctx.fillStyle = '#888888';
        ctx.font = '18px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Revit 2024 / 2025 / 2026  |  Visual Studio Solution + DLL + Documentation', 600, 720);

        // Convert to blob
        var blob = await new Promise(function(resolve) {
          canvas.toBlob(resolve, 'image/png');
        });

        // Store globally so we can use it
        window.__projectImage = blob;
        return 'Image created: ' + blob.size + ' bytes';
      })()
    `);
    console.log(imageCreated);

    // Now use the File API to set the file on the input
    const fileSet = await c.ev(`
      (async () => {
        var fileInput = document.querySelector('input[type="file"][accept*="image"]');
        if (!fileInput) return 'No file input found';

        var blob = window.__projectImage;
        var file = new File([blob], 'revit-plugin-service.png', { type: 'image/png' });

        // Create a DataTransfer to set files
        var dt = new DataTransfer();
        dt.items.add(file);
        fileInput.files = dt.files;

        // Dispatch change event
        fileInput.dispatchEvent(new Event('change', { bubbles: true }));

        return 'File set: ' + file.name + ' (' + file.size + ' bytes)';
      })()
    `);
    console.log(fileSet);
    await sleep(5000);
  }

  // Check if image uploaded
  console.log('\n=== CHECKING UPLOAD ===');
  const uploadState = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 1500)`);
  console.log(uploadState);

  // Try clicking Continue
  console.log('\n=== CONTINUE ===');
  await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && (btns[i].textContent.trim().includes('Continue') || btns[i].textContent.trim().includes('Save & Continue'))) {
          btns[i].click();
          return 'Clicked: ' + btns[i].textContent.trim();
        }
      }
    })()
  `);
  await sleep(3000);

  // Check what step we're on
  const currentStep = await c.ev(`
    (() => {
      var text = (document.querySelector('main') || document.body).innerText;
      if (text.includes('Requirements') && text.includes('Active')) return 'Step 4: Requirements';
      if (text.includes('Description') && text.includes('Active')) return 'Step 5: Description';
      if (text.includes('Gallery') && text.includes('Active')) return 'Still on Step 3: Gallery';
      return 'Unknown: ' + text.substring(0, 300);
    })()
  `);
  console.log('Current step:', currentStep);

  const pageText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 2000)`);
  console.log(pageText);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
