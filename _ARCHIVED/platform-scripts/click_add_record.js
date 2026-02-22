(function() {
  var btns = Array.from(document.querySelectorAll("button, [role=button]"));
  var addBtn = btns.find(function(b) { return b.textContent.trim() === "Add record"; });
  if (addBtn) {
    addBtn.click();
    return "clicked Add record";
  }
  return "Add record not found. Buttons: " + btns.map(function(b){return b.textContent.trim().substring(0,30)}).join(", ");
})();