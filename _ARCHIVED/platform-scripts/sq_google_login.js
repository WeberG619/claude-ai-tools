(function() {
  var btns = Array.from(document.querySelectorAll("button, a, [role=button]"));
  var googleBtn = btns.find(function(b) { return b.textContent.includes("Continue with Google"); });
  if (googleBtn) {
    googleBtn.click();
    return "clicked Continue with Google";
  }
  return "not found: " + btns.slice(0,10).map(function(b){return b.textContent.trim().substring(0,30)}).join(", ");
})();
