(function() {
  var emailInput = document.querySelector("#email");
  if (!emailInput) return "no email input";

  var form = emailInput.closest("form");
  if (form) {
    form.requestSubmit();
    return "submitted via form.requestSubmit()";
  }

  var submitEvent = new Event("submit", { bubbles: true, cancelable: true });
  var parent = emailInput.parentElement;
  while (parent && parent !== document.body) {
    if (parent.tagName === "FORM") {
      parent.dispatchEvent(submitEvent);
      return "dispatched submit on form";
    }
    parent = parent.parentElement;
  }

  var btn = Array.from(document.querySelectorAll("button")).find(function(b) { return b.textContent.includes("Send Reset"); });
  if (btn) {
    var mousedown = new MouseEvent("mousedown", { bubbles: true });
    var mouseup = new MouseEvent("mouseup", { bubbles: true });
    var click = new MouseEvent("click", { bubbles: true });
    btn.dispatchEvent(mousedown);
    btn.dispatchEvent(mouseup);
    btn.dispatchEvent(click);
    return "dispatched mouse events on button, disabled=" + btn.disabled;
  }
  return "nothing worked";
})();
