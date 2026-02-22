(function() {
  var scripts = Array.from(document.querySelectorAll("script"));
  var textContent = scripts.map(function(s) { return s.textContent; }).join("\n");
  var supabaseMatch = textContent.match(/supabase[^"]*url[^"]*"([^"]+)"/i);
  var anonMatch = textContent.match(/anon[^"]*key[^"]*"([^"]+)"/i);
  var nextData = document.querySelector("#__NEXT_DATA__");
  var env = {};
  if (nextData) {
    try {
      var data = JSON.parse(nextData.textContent);
      env = data.props && data.props.pageProps && data.props.pageProps.env || data.runtimeConfig || {};
    } catch(e) {}
  }
  return JSON.stringify({
    supabaseUrl: supabaseMatch ? supabaseMatch[1] : null,
    anonKey: anonMatch ? anonMatch[1] : null,
    envKeys: Object.keys(env).join(","),
    nextData: nextData ? nextData.textContent.substring(0, 500) : "none"
  });
})();
