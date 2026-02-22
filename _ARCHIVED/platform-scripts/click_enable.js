(function() {
  var btns = Array.from(document.querySelectorAll("button, [role=button]"));
  var enableBtn = btns.find(function(b) { return b.textContent.trim() === "Enable"; });
  if (enableBtn) {
    enableBtn.click();
    return "clicked Enable button";
  }
  var links = Array.from(document.querySelectorAll("a"));
  var enableLink = links.find(function(a) { return a.textContent.trim() === "Enable"; });
  if (enableLink) {
    enableLink.click();
    return "clicked Enable link";
  }
  return "Enable not found. Buttons: " + btns.slice(0,10).map(function(b){return b.textContent.trim().substring(0,30)}).join(", ");
})();
