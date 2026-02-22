(function() {
  var btns = Array.from(document.querySelectorAll("button, [role=button]"));
  var saveBtn = btns.find(function(b) { return b.textContent.trim() === "Save"; });
  if (saveBtn) {
    saveBtn.click();
    return "clicked Save";
  }
  return "Save not found. Buttons: " + btns.map(function(b){return b.textContent.trim().substring(0,20)}).filter(function(t){return t}).join(", ");
})();