(function() {
  var opt = document.querySelector("[data-test='dns-type-dropdown-option-TXT']");
  if (opt) {
    opt.click();
    return "clicked TXT option";
  }
  return "TXT option not found";
})();