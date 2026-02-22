(function() {
  var result = [];
  var form = document.querySelector("form");
  if (!form) return "no form found";
  result.push("FORM text: " + form.textContent.trim().replace(/\s+/g, " ").substring(0, 500));
  var allElements = form.querySelectorAll("*");
  allElements.forEach(function(el, i) {
    if (el.tagName === "INPUT" || el.tagName === "SELECT" || el.tagName === "TEXTAREA") {
      result.push("FIELD" + i + ": " + el.tagName + " type=" + (el.type||"") + " id=" + (el.id||"") + " value=" + (el.value||"").substring(0,40));
    }
    if (el.tagName === "BUTTON" || el.getAttribute("role") === "button") {
      result.push("BTN" + i + ": " + el.textContent.trim().substring(0,50));
    }
    if (el.tagName === "LABEL") {
      result.push("LABEL" + i + ": " + el.textContent.trim().substring(0,50) + " for=" + (el.htmlFor||""));
    }
    if (el.getAttribute("role") === "listbox" || el.getAttribute("role") === "combobox" || el.getAttribute("role") === "option") {
      result.push("SELECT" + i + ": role=" + el.getAttribute("role") + " text=" + el.textContent.trim().substring(0,50));
    }
  });
  return result.join("\n");
})();