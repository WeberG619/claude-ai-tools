(function() {
  var result = [];
  var inputs = document.querySelectorAll("input, select, textarea");
  inputs.forEach(function(inp, i) {
    var vis = inp.offsetParent !== null || inp.type === "hidden";
    result.push("INPUT" + i + ": tag=" + inp.tagName + " type=" + (inp.type||"") + " name=" + (inp.name||"") + " id=" + (inp.id||"") + " placeholder=" + (inp.placeholder||"") + " visible=" + vis + " value=" + (inp.value||"").substring(0,40));
  });
  var dialogs = document.querySelectorAll("dialog, [role=dialog], [class*='modal'], [class*='Modal'], [class*='overlay'], [class*='Overlay'], [class*='popup'], [class*='Popup']");
  dialogs.forEach(function(d, i) {
    result.push("DIALOG" + i + ": " + d.tagName + " class=" + d.className.substring(0,80) + " text=" + d.textContent.trim().replace(/\s+/g, " ").substring(0,200));
  });
  var forms = document.querySelectorAll("form");
  forms.forEach(function(f, i) {
    result.push("FORM" + i + ": action=" + (f.action||"") + " text=" + f.textContent.trim().replace(/\s+/g, " ").substring(0,200));
  });
  return result.join("\n");
})();