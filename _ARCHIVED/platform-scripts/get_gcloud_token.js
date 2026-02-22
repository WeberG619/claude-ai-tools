(function() {
  try {
    var req = new XMLHttpRequest();
    req.open("GET", "https://console.cloud.google.com/m/token?project=bim-ops-youtube", false);
    req.withCredentials = true;
    req.send();
    if (req.status === 200) {
      return "TOKEN:" + req.responseText.substring(0, 200);
    }
    return "Status " + req.status + ": " + req.responseText.substring(0, 200);
  } catch(e) {
    return "Error: " + e.message;
  }
})();
