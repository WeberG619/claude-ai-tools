(function() {
  var result = [];
  var dialogs = document.querySelectorAll("[class*='modal'], [class*='Modal'], [class*='overlay'], [class*='Overlay'], [class*='dialog'], [class*='Dialog'], [role=dialog]");
  dialogs.forEach(function(d, i) {
    result.push("DIALOG" + i + ": tag=" + d.tagName + " class=" + d.className.substring(0,100));
    result.push("  innerHTML length: " + d.innerHTML.length);
    result.push("  text: " + d.textContent.trim().replace(/\s+/g, " ").substring(0,500));
    var children = d.querySelectorAll("*");
    result.push("  children: " + children.length);
  });
  var allDivs = document.querySelectorAll("div[class]");
  var floating = [];
  allDivs.forEach(function(d) {
    var style = window.getComputedStyle(d);
    if ((style.position === "fixed" || style.position === "absolute") && style.zIndex > 100 && d.offsetParent !== null) {
      floating.push("FLOAT: z=" + style.zIndex + " pos=" + style.position + " class=" + d.className.substring(0,60) + " text=" + d.textContent.trim().replace(/\s+/g, " ").substring(0,200));
    }
  });
  floating.forEach(function(f) { result.push(f); });
  return result.join("\n");
})();