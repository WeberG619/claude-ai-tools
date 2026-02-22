(function() {
  var btns = Array.from(document.querySelectorAll("button, [role=button]"));
  var verifyBtn = btns.find(function(b) { return b.textContent.trim() === "Verify DNS Records"; });
  if (verifyBtn) {
    verifyBtn.click();
    return "clicked Verify DNS Records";
  }
  return "Verify button not found. Buttons: " + btns.map(function(b){return b.textContent.trim().substring(0,30)}).filter(function(t){return t}).join(", ");
})();