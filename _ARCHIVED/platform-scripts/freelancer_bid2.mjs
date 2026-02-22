// Bid on Freelancer jobs - uses insertText for Angular forms
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Page not found: ${urlMatch}`);
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
  const pending = new Map();
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p.rej(new Error(msg.error.message));
      else p.res(msg.result);
    }
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const msgId = id++;
    pending.set(msgId, { res, rej });
    ws.send(JSON.stringify({ id: msgId, method, params }));
  });
  const eval_ = async (expr) => {
    const r = await send("Runtime.evaluate", {
      expression: `(() => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

async function fillInput(send, eval_, selector, value) {
  // Focus and select all existing content
  await eval_(`
    const el = document.querySelector(${JSON.stringify(selector)});
    if (el) { el.focus(); el.select(); }
  `);
  await sleep(200);
  // Delete existing
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 }); // Ctrl+A
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA" });
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
  await sleep(100);
  // Insert text via CDP (triggers real input events)
  await send("Input.insertText", { text: value });
  await sleep(200);
  // Blur to trigger validation
  await eval_(`document.querySelector(${JSON.stringify(selector)})?.blur()`);
  await sleep(100);
}

const JOBS = [
  {
    url: "https://www.freelancer.com/projects/academic-writing/Dissertation-Proofreading-Needed/details",
    bidAmount: "300",
    bidDays: "3",
    proposal: `I'd be happy to proofread your Tax Law dissertation with careful attention to detail.

My approach:
- Line-by-line review for grammar, punctuation, and spelling
- Consistency checks on citation format and legal terminology
- Clarity improvements while preserving your academic voice
- Track changes in Word so you can review every edit
- Familiar with Citavi referencing workflows

I work with academic manuscripts regularly and understand the precision required for dissertation submissions. I can turn this around within 3 days with a thorough, professional review.

Happy to discuss your specific requirements or timeline. Looking forward to helping you submit a polished manuscript.`
  },
  {
    url: "https://www.freelancer.com/projects/excel-vba/Excel-Text-Data-Cleanup/details",
    bidAmount: "280",
    bidDays: "3",
    proposal: `I can handle this Excel text data cleanup efficiently and accurately.

My approach:
- Import or paste raw text into properly structured Excel columns
- Run thorough de-duplication using Power Query or VBA
- Validate that every record is unique and properly formatted
- Deliver a clean, single-worksheet workbook ready for immediate use

I work with Excel daily for data processing and can automate the cleanup with a lightweight VBA macro or Power Query for reliability. Fast turnaround, accurate results.

Happy to discuss the specific data volume and format you're working with.`
  },
  {
    url: "https://www.freelancer.com/projects/data-analysis/Excel-Numerical-Data-Cleanup-40214417/details",
    bidAmount: "350",
    bidDays: "4",
    proposal: `I can clean and restructure your numerical spreadsheets into an analysis-ready workbook.

What I'll deliver:
- Strip out duplicates across all sheets
- Standardize number formats, fix inconsistent decimal/thousand separators
- Handle missing values and flag anomalies
- Merge data into a unified, properly structured workbook
- Validate totals and cross-references for accuracy

I'm proficient with Excel formulas, Power Query, and VBA for automated cleanup. If you need any summary statistics or pivot-ready structure, I can set that up as well.

Ready to start immediately once you share the spreadsheets.`
  }
];

async function main() {
  const { ws, send, eval_ } = await connectToPage("freelancer.com");
  console.log("Connected\n");

  for (const job of JOBS) {
    const jobName = job.url.split('/').slice(-2, -1)[0];
    console.log(`\n${"=".repeat(50)}`);
    console.log(`Bidding: ${jobName}`);
    console.log(`Amount: $${job.bidAmount} | Days: ${job.bidDays}`);
    console.log(`${"=".repeat(50)}`);

    // Navigate to job
    await eval_(`window.location.href = ${JSON.stringify(job.url)}; return 'ok';`);
    await sleep(6000);

    // Check if already bid
    let r = await eval_(`
      const body = document.body?.innerText || '';
      return JSON.stringify({
        alreadyBid: body.includes('You have already bid') || body.includes('Your Bid'),
        title: document.querySelector('h1')?.textContent?.trim() || '',
        hasBidForm: !!document.querySelector('#bidAmountInput')
      });
    `);
    const state = JSON.parse(r);
    console.log(`Title: ${state.title}`);

    if (state.alreadyBid) {
      console.log("SKIP - Already bid");
      continue;
    }

    // Scroll to bid form
    await eval_(`
      const bidSection = document.querySelector('#bidAmountInput');
      if (bidSection) bidSection.scrollIntoView({ block: 'center' });
    `);
    await sleep(500);

    // Fill bid amount
    console.log("Filling amount...");
    await fillInput(send, eval_, '#bidAmountInput', job.bidAmount);

    // Fill days
    console.log("Filling days...");
    await fillInput(send, eval_, '#periodInput', job.bidDays);

    // Fill proposal - this is the key one
    console.log("Filling proposal...");
    await fillInput(send, eval_, '#descriptionTextArea', job.proposal);

    // Verify values
    r = await eval_(`
      return JSON.stringify({
        amount: document.querySelector('#bidAmountInput')?.value,
        days: document.querySelector('#periodInput')?.value,
        desc: document.querySelector('#descriptionTextArea')?.value?.substring(0, 100),
        descLen: document.querySelector('#descriptionTextArea')?.value?.length
      });
    `);
    console.log("Verification:", r);

    const verify = JSON.parse(r);
    if (!verify.desc || verify.descLen < 100) {
      console.log("Proposal not set properly, retrying with character-by-character...");

      // Focus textarea and clear
      await eval_(`
        const el = document.querySelector('#descriptionTextArea');
        el.focus();
        el.value = '';
        el.dispatchEvent(new Event('input', { bubbles: true }));
      `);
      await sleep(200);

      // Type the proposal using insertText in chunks
      const chunks = job.proposal.match(/.{1,50}/gs) || [job.proposal];
      for (const chunk of chunks) {
        await send("Input.insertText", { text: chunk });
        await sleep(50);
      }
      await sleep(500);

      // Verify again
      r = await eval_(`
        return JSON.stringify({
          descLen: document.querySelector('#descriptionTextArea')?.value?.length,
          desc: document.querySelector('#descriptionTextArea')?.value?.substring(0, 80)
        });
      `);
      console.log("After retry:", r);
    }

    // Also fill milestone description
    await eval_(`
      const milestoneInput = document.querySelector('input[placeholder*="milestone"]');
      if (milestoneInput) {
        milestoneInput.focus();
      }
    `);
    await sleep(200);
    await send("Input.insertText", { text: "Complete project delivery" });
    await sleep(300);

    // Set milestone amount to match bid
    await eval_(`
      const milestoneAmounts = document.querySelectorAll('input[type="number"]');
      const milestoneAmt = Array.from(milestoneAmounts).find(el =>
        el.placeholder === '' && el.getBoundingClientRect().y > 800
      );
      if (milestoneAmt) {
        milestoneAmt.focus();
        milestoneAmt.select();
      }
    `);
    await sleep(200);
    await send("Input.insertText", { text: job.bidAmount });
    await sleep(300);

    // Final verification before submit
    r = await eval_(`
      const amount = document.querySelector('#bidAmountInput')?.value;
      const days = document.querySelector('#periodInput')?.value;
      const desc = document.querySelector('#descriptionTextArea')?.value;

      // Find submit button
      const submitBtn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim() === 'Place Bid' && b.offsetParent !== null);

      return JSON.stringify({
        amount, days, descLen: desc?.length,
        descFirst80: desc?.substring(0, 80),
        submitFound: !!submitBtn,
        submitDisabled: submitBtn?.disabled
      });
    `);
    console.log("Pre-submit:", r);

    const preSubmit = JSON.parse(r);
    if (preSubmit.submitFound && !preSubmit.submitDisabled && preSubmit.descLen > 100) {
      console.log("Clicking Place Bid...");
      await eval_(`
        const btn = Array.from(document.querySelectorAll('button'))
          .find(b => b.textContent.trim() === 'Place Bid' && b.offsetParent !== null);
        if (btn) btn.click();
      `);
      await sleep(5000);

      r = await eval_(`
        const body = document.body?.innerText || '';
        return JSON.stringify({
          url: location.href,
          success: body.includes('bid has been placed') || body.includes('successfully') || body.includes('Your Bid'),
          errors: Array.from(document.querySelectorAll('[class*="error" i], [role="alert"], [class*="Error"]'))
            .filter(el => el.offsetParent !== null)
            .map(el => el.textContent.trim().substring(0, 100))
            .filter(t => t.length > 3)
        });
      `);
      console.log("Result:", r);
    } else {
      console.log("Cannot submit - missing data or button disabled");
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
