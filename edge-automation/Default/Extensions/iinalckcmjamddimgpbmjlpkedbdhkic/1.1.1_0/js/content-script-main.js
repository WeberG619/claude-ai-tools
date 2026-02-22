(function() {
    function D(h, z, j) {
        function F(Z, A) {
            if (!z[Z]) {
                if (!h[Z]) {
                    var q = "function" == typeof require && require;
                    if (!A && q) return q(Z, !0);
                    if (l) return l(Z, !0);
                    var Q = new Error("Cannot find module '" + Z + "'");
                    throw Q.code = "MODULE_NOT_FOUND", Q;
                }
                var I = z[Z] = {
                    exports: {}
                };
                h[Z][0].call(I.exports, (function(D) {
                    var z = h[Z][1][D];
                    return F(z || D);
                }), I, I.exports, D, h, z, j);
            }
            return z[Z].exports;
        }
        for (var l = "function" == typeof require && require, Z = 0; Z < j.length; Z++) F(j[Z]);
        return F;
    }
    return D;
})()({
    1: [ function(D, h, z) {
        "use strict";
        var j = D("1p");
        function F() {
            const D = window.location.hostname + window.location.pathname;
            if (D === "chatgpt.com/") (0, j.init)();
        }
        try {
            var l;
            if (!((l = document.documentElement) !== null && l !== void 0 && l.hasAttribute("gpt-loaded-main"))) {
                var Z;
                (Z = document.documentElement) === null || Z === void 0 || Z.setAttribute("gpt-loaded-main", "true"),
                F();
            }
        } catch (D) {}
    }, {
        "1p": 2
    } ],
    2: [ function(D, h, z) {
        "use strict";
        function j(D) {
            return D.toLowerCase().startsWith("https://chatgpt.com/");
        }
        function F() {
            if (!j(document.location.href)) return false;
            const {fetch: D} = window;
            function h(D) {
                let h = false;
                try {
                    const z = new URL(D);
                    h = z.pathname.endsWith("/conversation");
                } catch (D) {}
                return h;
            }
            const z = async (...z) => {
                let [j, F] = z;
                const A = j.url || j.toString(), q = await D(...z), Q = q.headers.get("content-type") || "";
                if (h(A) && Q.includes("text/event-stream")) {
                    let D;
                    try {
                        D = JSON.parse(F.body);
                    } catch (D) {}
                    let h = D.conversation_id;
                    const z = D.messages, {readable: j, writable: A} = new TransformStream;
                    if (q.body) {
                        const D = q.body.getReader(), j = A.getWriter(), F = new TextDecoder;
                        let Q = "", I = "", E = "", X = "";
                        (async () => {
                            while (true) {
                                const {done: z, value: l} = await D.read();
                                if (z) break;
                                const P = F.decode(l, {
                                    stream: true
                                });
                                let x;
                                Q += P;
                                while ((x = Q.indexOf("\n\n")) !== -1) {
                                    const D = Q.slice(0, x).trim();
                                    if (Q = Q.slice(x + 2), D) {
                                        const z = Z(D);
                                        if (z.event == "delta" || z.event == "message") {
                                            let D;
                                            try {
                                                D = JSON.parse(z.data);
                                            } catch (D) {}
                                            if (D) {
                                                var A, q, f;
                                                if (D.v && typeof D.v == "string") I += D.v; else if (((A = D.v) === null || A === void 0 ? void 0 : A.length) > 0) {
                                                    for (let h of D.v) if (h.v && h.o == "append" && typeof h.v == "string") I += h.v;
                                                } else if ((q = D.v) !== null && q !== void 0 && (f = q.message) !== null && f !== void 0 && f.id) {
                                                    var s, L;
                                                    E = (s = D.v) === null || s === void 0 ? void 0 : (L = s.message) === null || L === void 0 ? void 0 : L.id;
                                                } else if (D.metadata) {
                                                    if (D.conversation_id) h = D.conversation_id;
                                                    if (D.metadata.model_slug) X = D.metadata.model_slug;
                                                }
                                            }
                                        }
                                    }
                                }
                                j.write(l);
                            }
                            if (j.close(), z) for (let D of z) {
                                var P, x, n;
                                if (((x = D.content) === null || x === void 0 ? void 0 : (n = x.parts) === null || n === void 0 ? void 0 : n.length) > 0) {
                                    const z = D.content.parts.join("");
                                    l({
                                        client_ts: +new Date,
                                        session_id: h,
                                        message_id: D.id,
                                        chat_domain: "chatgpt.com",
                                        model: X,
                                        prompt: z,
                                        role: "user",
                                        is_subscribed: false,
                                        language: ""
                                    });
                                }
                            }
                            l({
                                client_ts: +new Date,
                                session_id: h,
                                message_id: E,
                                chat_domain: "chatgpt.com",
                                model: X,
                                prompt: I,
                                role: "system",
                                is_subscribed: false,
                                language: ""
                            });
                        })();
                    }
                    return new Response(j, {
                        headers: q.headers,
                        status: q.status,
                        statusText: q.statusText
                    });
                }
                return q;
            };
            return window.fetch = z, true;
        }
        function l(D) {
            window.postMessage({
                source: "content-script",
                payload: D
            });
        }
        function Z(D) {
            const h = D.split(/\r?\n/), z = {
                event: "message",
                data: "",
                id: "",
                retry: ""
            };
            for (const D of h) {
                if (D.startsWith(":")) continue;
                const [h, ...j] = D.split(":"), F = j.join(":").trimStart();
                switch (h) {
                  case "event":
                    z.event = F;
                    break;

                  case "data":
                    z.data += F + "\n";
                    break;

                  case "id":
                    z.id = F;
                    break;

                  case "retry":
                    z.retry = F;
                    break;
                }
            }
            if (z.data.endsWith("\n")) z.data = z.data.slice(0, -1);
            return z;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.init = F;
    }, {} ]
}, {}, [ 1 ]);