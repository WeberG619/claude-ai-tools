/**
 * set_gmail_signature.js
 *
 * Standalone JS snippet to evaluate via CDP against Gmail Settings > General
 * to set the permanent account signature.
 *
 * Prerequisites:
 *   - Gmail must be open on the Settings > General page
 *     (https://mail.google.com/mail/u/0/#settings/general)
 *   - If not already on that page, this script will redirect.
 *
 * Usage via CDP (from Python):
 *   cdp_evaluate(expression=open("set_gmail_signature.js").read())
 *
 * Or paste directly into DevTools console on gmail.com/settings.
 */

(async function () {
  // -------------------------------------------------------------------------
  // SIGNATURE HTML — keep in sync with get_signature.py get_html_signature()
  // -------------------------------------------------------------------------
  const SIGNATURE_HTML = `<div style="font-family:Arial,sans-serif;font-size:13px;color:#333;line-height:1.5;max-width:480px;">
  <strong style="font-size:14px;color:#111;">Weber Gouin</strong><br>
  <span style="color:#555;">Principal / BIM Specialist</span>
  <span style="color:#999;"> &nbsp;|&nbsp; </span>
  <span style="color:#555;">BIM Ops Studio</span><br>
  <br>
  <table style="border-collapse:collapse;font-size:12px;color:#555;">
    <tr>
      <td style="padding:1px 8px 1px 0;color:#999;white-space:nowrap;">Phone</td>
      <td style="padding:1px 0;">(786) 587-9726</td>
    </tr>
    <tr>
      <td style="padding:1px 8px 1px 0;color:#999;white-space:nowrap;">Business</td>
      <td style="padding:1px 0;"><a href="mailto:weber@bimopsstudio.com" style="color:#1a73e8;text-decoration:none;">weber@bimopsstudio.com</a></td>
    </tr>
    <tr>
      <td style="padding:1px 8px 1px 0;color:#999;white-space:nowrap;">BD Architect</td>
      <td style="padding:1px 0;"><a href="mailto:weber@bdarchitect.net" style="color:#1a73e8;text-decoration:none;">weber@bdarchitect.net</a></td>
    </tr>
    <tr>
      <td style="padding:1px 8px 1px 0;color:#999;white-space:nowrap;">WG Design</td>
      <td style="padding:1px 0;"><a href="mailto:weber@wgdesigndrafting.com" style="color:#1a73e8;text-decoration:none;">weber@wgdesigndrafting.com</a></td>
    </tr>
    <tr>
      <td style="padding:1px 8px 1px 0;color:#999;white-space:nowrap;">Location</td>
      <td style="padding:1px 0;">Sandpoint, ID</td>
    </tr>
  </table>
</div>`;

  // -------------------------------------------------------------------------
  // Helper: wait for an element to appear in the DOM
  // -------------------------------------------------------------------------
  function waitForElement(selector, timeout = 8000) {
    return new Promise((resolve, reject) => {
      const existing = document.querySelector(selector);
      if (existing) return resolve(existing);

      const observer = new MutationObserver(() => {
        const el = document.querySelector(selector);
        if (el) {
          observer.disconnect();
          resolve(el);
        }
      });
      observer.observe(document.body, { childList: true, subtree: true });

      setTimeout(() => {
        observer.disconnect();
        reject(new Error(`Timeout waiting for: ${selector}`));
      }, timeout);
    });
  }

  // -------------------------------------------------------------------------
  // Step 1: Make sure we're on the Settings > General page
  // -------------------------------------------------------------------------
  if (!window.location.href.includes("#settings/general") &&
      !window.location.href.includes("settings/general")) {
    console.log("Navigating to Gmail Settings > General...");
    window.location.href = "https://mail.google.com/mail/u/0/#settings/general";
    return "Navigated to settings page. Run this script again once the page loads.";
  }

  // -------------------------------------------------------------------------
  // Step 2: Find the signature editor section
  // Gmail's settings use contenteditable divs for the signature editor.
  // The section header text is "Signature".
  // -------------------------------------------------------------------------

  // Look for "Create new" button (no signatures yet)
  const createNewBtn = [...document.querySelectorAll("div[role='button'], span[role='button'], button")]
    .find(el => el.textContent.trim() === "Create new");

  if (createNewBtn) {
    console.log("No signature found. Clicking 'Create new'...");
    createNewBtn.click();

    // Wait for the name input dialog
    try {
      const nameInput = await waitForElement("input[type='text'][aria-label], input[placeholder]", 5000);
      nameInput.value = "BIM Ops Studio";
      nameInput.dispatchEvent(new Event("input", { bubbles: true }));
      nameInput.dispatchEvent(new Event("change", { bubbles: true }));

      // Click Create/OK button in dialog
      const createBtn = [...document.querySelectorAll("button, div[role='button']")]
        .find(el => ["Create", "OK", "Save"].includes(el.textContent.trim()));
      if (createBtn) createBtn.click();

      // Give it a moment to render the editor
      await new Promise(r => setTimeout(r, 1500));
    } catch (e) {
      console.warn("Could not find name input dialog:", e.message);
    }
  }

  // -------------------------------------------------------------------------
  // Step 3: Find the contenteditable signature body and set its content
  // -------------------------------------------------------------------------

  // Gmail signature editors are contenteditable divs inside the settings panel.
  // They typically have aria-label containing "Signature" or are inside
  // a table row labelled "Signature".
  let sigEditor = null;

  // Strategy A: aria-label contains "Signature"
  sigEditor = document.querySelector('[aria-label*="Signature"][contenteditable="true"]');

  // Strategy B: look for contenteditable inside the signature table section
  if (!sigEditor) {
    const allEditable = document.querySelectorAll('[contenteditable="true"]');
    for (const el of allEditable) {
      // Walk up to see if any ancestor mentions "signature" in its text or label
      let parent = el.parentElement;
      let depth = 0;
      while (parent && depth < 10) {
        const label = parent.getAttribute("aria-label") || "";
        if (label.toLowerCase().includes("signature")) {
          sigEditor = el;
          break;
        }
        // Check if sibling header text says "Signature"
        const prevSib = parent.previousElementSibling;
        if (prevSib && prevSib.textContent.trim() === "Signature") {
          sigEditor = el;
          break;
        }
        parent = parent.parentElement;
        depth++;
      }
      if (sigEditor) break;
    }
  }

  if (!sigEditor) {
    return "ERROR: Could not find the signature editor. Make sure Gmail Settings > General is fully loaded and a signature exists (or was just created).";
  }

  // -------------------------------------------------------------------------
  // Step 4: Set the HTML content and fire input events so Gmail saves it
  // -------------------------------------------------------------------------
  sigEditor.focus();
  sigEditor.innerHTML = SIGNATURE_HTML;

  // Trigger events so Gmail's React/Angular layer picks up the change
  sigEditor.dispatchEvent(new Event("input", { bubbles: true }));
  sigEditor.dispatchEvent(new Event("change", { bubbles: true }));
  sigEditor.dispatchEvent(new KeyboardEvent("keyup", { bubbles: true }));

  // -------------------------------------------------------------------------
  // Step 5: Scroll to and click "Save Changes" button
  // -------------------------------------------------------------------------
  await new Promise(r => setTimeout(r, 500));

  const saveBtn = [...document.querySelectorAll("button, input[type='button'], div[role='button']")]
    .find(el => el.textContent.trim() === "Save Changes");

  if (saveBtn) {
    saveBtn.scrollIntoView({ behavior: "smooth", block: "center" });
    await new Promise(r => setTimeout(r, 400));
    saveBtn.click();
    return "SUCCESS: Signature set and 'Save Changes' clicked. Verify in Gmail settings.";
  }

  return "Signature HTML inserted into editor. 'Save Changes' button not found — scroll down and save manually.";
})();
