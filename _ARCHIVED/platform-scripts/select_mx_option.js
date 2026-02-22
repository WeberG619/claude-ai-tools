(function() {
  var opt = document.querySelector("[data-test='dns-type-dropdown-option-MX']");
  if (opt) {
    opt.click();
    return "clicked MX option";
  }
  return "MX option not found";
})();