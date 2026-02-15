// Create professional image, save to disk, upload via CDP DOM.setFileInputFiles
import fs from 'fs';

const CDP = 'http://localhost:9222';
const sleep = ms => new Promise(r => setTimeout(r, ms));

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

  // Step 1: Create a professional image in the browser and get base64
  console.log('=== CREATING PROFESSIONAL IMAGE ===');
  const base64 = await c.ev(`
    (() => {
      var canvas = document.createElement('canvas');
      canvas.width = 1600;
      canvas.height = 1200;
      var ctx = canvas.getContext('2d');

      // Dark professional background
      var bg = ctx.createLinearGradient(0, 0, 1600, 1200);
      bg.addColorStop(0, '#0f0f23');
      bg.addColorStop(0.5, '#1a1a3e');
      bg.addColorStop(1, '#0f0f23');
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, 1600, 1200);

      // Subtle grid
      ctx.strokeStyle = 'rgba(0, 150, 255, 0.06)';
      ctx.lineWidth = 1;
      for (var i = 0; i < 1600; i += 30) { ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, 1200); ctx.stroke(); }
      for (var j = 0; j < 1200; j += 30) { ctx.beginPath(); ctx.moveTo(0, j); ctx.lineTo(1600, j); ctx.stroke(); }

      // Accent lines
      ctx.strokeStyle = 'rgba(0, 180, 255, 0.3)';
      ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(100, 120); ctx.lineTo(1500, 120); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(100, 1080); ctx.lineTo(1500, 1080); ctx.stroke();

      // Blue accent bar at top
      ctx.fillStyle = '#0096ff';
      ctx.fillRect(100, 100, 6, 80);

      // Main title
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 56px Arial, Helvetica, sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText('Custom Revit Plugin Development', 130, 165);

      // Subtitle
      ctx.fillStyle = '#0096ff';
      ctx.font = '28px Arial';
      ctx.fillText('C# / .NET  |  Revit API  |  BIM Automation', 130, 210);

      // Service boxes
      var services = [
        { title: 'Add-in Development', desc: 'Custom ribbon buttons,\\ncommands, and tools', icon: '{ }' },
        { title: 'Workflow Automation', desc: 'Batch processing,\\ndata extraction, reports', icon: '\\u21BB' },
        { title: 'Family & Parameters', desc: 'Shared params, family\\nmanagement, templates', icon: '\\u25A1' },
        { title: 'AI Integration', desc: 'LLM + Revit bridge,\\nnamed pipes IPC', icon: '\\u2699' }
      ];

      var boxW = 320;
      var boxH = 280;
      var startX = 100;
      var startY = 300;
      var gap = 60;

      services.forEach(function(svc, idx) {
        var x = startX + idx * (boxW + gap);
        var y = startY;

        // Box background
        ctx.fillStyle = 'rgba(255, 255, 255, 0.04)';
        ctx.strokeStyle = 'rgba(0, 150, 255, 0.2)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect(x, y, boxW, boxH, 12);
        ctx.fill();
        ctx.stroke();

        // Icon
        ctx.fillStyle = '#0096ff';
        ctx.font = '48px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(svc.icon, x + boxW/2, y + 70);

        // Title
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 22px Arial';
        ctx.fillText(svc.title, x + boxW/2, y + 130);

        // Description
        ctx.fillStyle = '#888888';
        ctx.font = '17px Arial';
        var lines = svc.desc.split('\\n');
        lines.forEach(function(line, li) {
          ctx.fillText(line, x + boxW/2, y + 170 + li * 25);
        });
      });

      // Tech stack section
      ctx.fillStyle = '#0096ff';
      ctx.fillRect(100, 650, 6, 50);
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 32px Arial';
      ctx.textAlign = 'left';
      ctx.fillText('Tech Stack', 130, 685);

      var techs = ['C#', '.NET', 'Revit API', 'WPF/XAML', 'Python', 'Dynamo', 'Named Pipes', 'Git'];
      var techX = 130;
      techs.forEach(function(tech) {
        ctx.fillStyle = 'rgba(0, 150, 255, 0.15)';
        ctx.strokeStyle = 'rgba(0, 150, 255, 0.4)';
        var w = ctx.measureText(tech).width + 30;
        ctx.beginPath();
        ctx.roundRect(techX, 710, w, 36, 18);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = '#ffffff';
        ctx.font = '16px Arial';
        ctx.fillText(tech, techX + 15, 734);
        techX += w + 15;
      });

      // Deliverables section
      ctx.fillStyle = '#0096ff';
      ctx.fillRect(100, 800, 6, 50);
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 32px Arial';
      ctx.fillText('What You Get', 130, 835);

      var deliverables = [
        '\\u2713  Complete Visual Studio solution with source code',
        '\\u2713  Compiled DLL + .addin manifest file',
        '\\u2713  Installation guide and documentation',
        '\\u2713  Revit 2024 / 2025 / 2026 compatibility',
        '\\u2713  Post-delivery support and bug fixes'
      ];
      ctx.font = '20px Arial';
      ctx.fillStyle = '#cccccc';
      deliverables.forEach(function(d, i) {
        ctx.fillText(d, 130, 880 + i * 38);
      });

      // Footer
      ctx.fillStyle = '#444444';
      ctx.font = '16px Arial';
      ctx.textAlign = 'center';
      ctx.fillText('BIM Ops Studio  |  Weber Gouin  |  Revit BIM Specialist', 800, 1050);

      return canvas.toDataURL('image/png').split(',')[1];
    })()
  `);

  console.log('Image base64 length:', base64?.length || 0);

  // Save to Windows filesystem
  const winPath = 'D:\\\\_CLAUDE-TOOLS\\\\revit-plugin-service.png';
  const linuxPath = '/mnt/d/_CLAUDE-TOOLS/revit-plugin-service.png';

  fs.writeFileSync(linuxPath, Buffer.from(base64, 'base64'));
  console.log('Saved to:', linuxPath);

  // Use DOM.setFileInputFiles to upload
  console.log('\n=== UPLOADING VIA CDP ===');

  // Get the document and find the image file input
  const doc = await c.send('DOM.getDocument', {});
  const fileInputs = await c.send('DOM.querySelectorAll', {
    nodeId: doc.root.nodeId,
    selector: 'input[type="file"][accept*="image"]'
  });

  if (fileInputs.nodeIds && fileInputs.nodeIds.length > 0) {
    await c.send('DOM.setFileInputFiles', {
      files: [winPath],
      nodeId: fileInputs.nodeIds[0]
    });
    console.log('File set on input');
  } else {
    console.log('No image file input found');
  }

  await sleep(5000);

  // Check upload state
  console.log('\n=== UPLOAD STATE ===');
  const uploadState = await c.ev(`
    (() => {
      var imgs = document.querySelectorAll('img');
      var uploadedImgs = [];
      for (var i = 0; i < imgs.length; i++) {
        if (imgs[i].src && imgs[i].src.includes('blob:')) {
          uploadedImgs.push(imgs[i].src.substring(0, 60));
        }
      }
      var text = (document.querySelector('main') || document.body).innerText;
      var hasError = text.includes('Please add at least one');
      var hasCover = text.includes('cover image');
      return JSON.stringify({ uploadedImgs, hasError, hasCover, textExcerpt: text.substring(0, 800) });
    })()
  `);
  console.log(uploadState);

  // If image was uploaded, try to set it as cover and continue
  const setCover = await c.ev(`
    (() => {
      // Look for "Set as cover" or similar button
      var btns = document.querySelectorAll('button, [role="button"]');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim().toLowerCase();
        if (btns[i].offsetParent && (t.includes('cover') || t.includes('set as'))) {
          btns[i].click();
          return 'Set as cover: ' + btns[i].textContent.trim();
        }
      }
      return 'No cover button found';
    })()
  `);
  console.log('Cover:', setCover);
  await sleep(2000);

  // Try to continue
  console.log('\n=== CONTINUING ===');
  await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim().includes('Continue')) {
          btns[i].click();
          return 'Clicked Continue';
        }
      }
    })()
  `);
  await sleep(3000);

  const nextPage = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 1500)`);
  console.log(nextPage);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
