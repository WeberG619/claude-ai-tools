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
        var j = h.exports = {}, F, l;
        function Z() {
            throw new Error("setTimeout has not been defined");
        }
        function A() {
            throw new Error("clearTimeout has not been defined");
        }
        function q(D) {
            if (F === setTimeout) return setTimeout(D, 0);
            if ((F === Z || !F) && setTimeout) return F = setTimeout, setTimeout(D, 0);
            try {
                return F(D, 0);
            } catch (h) {
                try {
                    return F.call(null, D, 0);
                } catch (h) {
                    return F.call(this, D, 0);
                }
            }
        }
        function Q(D) {
            if (l === clearTimeout) return clearTimeout(D);
            if ((l === A || !l) && clearTimeout) return l = clearTimeout, clearTimeout(D);
            try {
                return l(D);
            } catch (h) {
                try {
                    return l.call(null, D);
                } catch (h) {
                    return l.call(this, D);
                }
            }
        }
        (function() {
            try {
                if (typeof setTimeout === "function") F = setTimeout; else F = Z;
            } catch (D) {
                F = Z;
            }
            try {
                if (typeof clearTimeout === "function") l = clearTimeout; else l = A;
            } catch (D) {
                l = A;
            }
        })();
        var I = [], E = false, X, f = -1;
        function s() {
            if (!E || !X) return;
            if (E = false, X.length) I = X.concat(I); else f = -1;
            if (I.length) L();
        }
        function L() {
            if (E) return;
            var D = q(s);
            E = true;
            var h = I.length;
            while (h) {
                X = I, I = [];
                while (++f < h) if (X) X[f].run();
                f = -1, h = I.length;
            }
            X = null, E = false, Q(D);
        }
        function P(D, h) {
            this.fun = D, this.array = h;
        }
        function x() {}
        j.nextTick = function(D) {
            var h = new Array(arguments.length - 1);
            if (arguments.length > 1) for (var z = 1; z < arguments.length; z++) h[z - 1] = arguments[z];
            if (I.push(new P(D, h)), I.length === 1 && !E) q(L);
        }, P.prototype.run = function() {
            this.fun.apply(null, this.array);
        }, j.title = "browser", j.browser = true, j.env = {}, j.argv = [], j.version = "",
        j.versions = {}, j.on = x, j.addListener = x, j.once = x, j.off = x, j.removeListener = x,
        j.removeAllListeners = x, j.emit = x, j.prependListener = x, j.prependOnceListener = x,
        j.listeners = function(D) {
            return [];
        }, j.binding = function(D) {
            throw new Error("process.binding is not supported");
        }, j.cwd = function() {
            return "/";
        }, j.chdir = function(D) {
            throw new Error("process.chdir is not supported");
        }, j.umask = function() {
            return 0;
        };
    }, {} ],
    2: [ function(D, h, z) {
        "use strict";
        function j(D) {
            if (D) throw D;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.bail = j;
    }, {} ],
    3: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.characterEntities = void 0;
        const j = {
            AElig: "Æ",
            AMP: "&",
            Aacute: "Á",
            Abreve: "Ă",
            Acirc: "Â",
            Acy: "А",
            Afr: "𝔄",
            Agrave: "À",
            Alpha: "Α",
            Amacr: "Ā",
            And: "⩓",
            Aogon: "Ą",
            Aopf: "𝔸",
            ApplyFunction: "⁡",
            Aring: "Å",
            Ascr: "𝒜",
            Assign: "≔",
            Atilde: "Ã",
            Auml: "Ä",
            Backslash: "∖",
            Barv: "⫧",
            Barwed: "⌆",
            Bcy: "Б",
            Because: "∵",
            Bernoullis: "ℬ",
            Beta: "Β",
            Bfr: "𝔅",
            Bopf: "𝔹",
            Breve: "˘",
            Bscr: "ℬ",
            Bumpeq: "≎",
            CHcy: "Ч",
            COPY: "©",
            Cacute: "Ć",
            Cap: "⋒",
            CapitalDifferentialD: "ⅅ",
            Cayleys: "ℭ",
            Ccaron: "Č",
            Ccedil: "Ç",
            Ccirc: "Ĉ",
            Cconint: "∰",
            Cdot: "Ċ",
            Cedilla: "¸",
            CenterDot: "·",
            Cfr: "ℭ",
            Chi: "Χ",
            CircleDot: "⊙",
            CircleMinus: "⊖",
            CirclePlus: "⊕",
            CircleTimes: "⊗",
            ClockwiseContourIntegral: "∲",
            CloseCurlyDoubleQuote: "”",
            CloseCurlyQuote: "’",
            Colon: "∷",
            Colone: "⩴",
            Congruent: "≡",
            Conint: "∯",
            ContourIntegral: "∮",
            Copf: "ℂ",
            Coproduct: "∐",
            CounterClockwiseContourIntegral: "∳",
            Cross: "⨯",
            Cscr: "𝒞",
            Cup: "⋓",
            CupCap: "≍",
            DD: "ⅅ",
            DDotrahd: "⤑",
            DJcy: "Ђ",
            DScy: "Ѕ",
            DZcy: "Џ",
            Dagger: "‡",
            Darr: "↡",
            Dashv: "⫤",
            Dcaron: "Ď",
            Dcy: "Д",
            Del: "∇",
            Delta: "Δ",
            Dfr: "𝔇",
            DiacriticalAcute: "´",
            DiacriticalDot: "˙",
            DiacriticalDoubleAcute: "˝",
            DiacriticalGrave: "`",
            DiacriticalTilde: "˜",
            Diamond: "⋄",
            DifferentialD: "ⅆ",
            Dopf: "𝔻",
            Dot: "¨",
            DotDot: "⃜",
            DotEqual: "≐",
            DoubleContourIntegral: "∯",
            DoubleDot: "¨",
            DoubleDownArrow: "⇓",
            DoubleLeftArrow: "⇐",
            DoubleLeftRightArrow: "⇔",
            DoubleLeftTee: "⫤",
            DoubleLongLeftArrow: "⟸",
            DoubleLongLeftRightArrow: "⟺",
            DoubleLongRightArrow: "⟹",
            DoubleRightArrow: "⇒",
            DoubleRightTee: "⊨",
            DoubleUpArrow: "⇑",
            DoubleUpDownArrow: "⇕",
            DoubleVerticalBar: "∥",
            DownArrow: "↓",
            DownArrowBar: "⤓",
            DownArrowUpArrow: "⇵",
            DownBreve: "̑",
            DownLeftRightVector: "⥐",
            DownLeftTeeVector: "⥞",
            DownLeftVector: "↽",
            DownLeftVectorBar: "⥖",
            DownRightTeeVector: "⥟",
            DownRightVector: "⇁",
            DownRightVectorBar: "⥗",
            DownTee: "⊤",
            DownTeeArrow: "↧",
            Downarrow: "⇓",
            Dscr: "𝒟",
            Dstrok: "Đ",
            ENG: "Ŋ",
            ETH: "Ð",
            Eacute: "É",
            Ecaron: "Ě",
            Ecirc: "Ê",
            Ecy: "Э",
            Edot: "Ė",
            Efr: "𝔈",
            Egrave: "È",
            Element: "∈",
            Emacr: "Ē",
            EmptySmallSquare: "◻",
            EmptyVerySmallSquare: "▫",
            Eogon: "Ę",
            Eopf: "𝔼",
            Epsilon: "Ε",
            Equal: "⩵",
            EqualTilde: "≂",
            Equilibrium: "⇌",
            Escr: "ℰ",
            Esim: "⩳",
            Eta: "Η",
            Euml: "Ë",
            Exists: "∃",
            ExponentialE: "ⅇ",
            Fcy: "Ф",
            Ffr: "𝔉",
            FilledSmallSquare: "◼",
            FilledVerySmallSquare: "▪",
            Fopf: "𝔽",
            ForAll: "∀",
            Fouriertrf: "ℱ",
            Fscr: "ℱ",
            GJcy: "Ѓ",
            GT: ">",
            Gamma: "Γ",
            Gammad: "Ϝ",
            Gbreve: "Ğ",
            Gcedil: "Ģ",
            Gcirc: "Ĝ",
            Gcy: "Г",
            Gdot: "Ġ",
            Gfr: "𝔊",
            Gg: "⋙",
            Gopf: "𝔾",
            GreaterEqual: "≥",
            GreaterEqualLess: "⋛",
            GreaterFullEqual: "≧",
            GreaterGreater: "⪢",
            GreaterLess: "≷",
            GreaterSlantEqual: "⩾",
            GreaterTilde: "≳",
            Gscr: "𝒢",
            Gt: "≫",
            HARDcy: "Ъ",
            Hacek: "ˇ",
            Hat: "^",
            Hcirc: "Ĥ",
            Hfr: "ℌ",
            HilbertSpace: "ℋ",
            Hopf: "ℍ",
            HorizontalLine: "─",
            Hscr: "ℋ",
            Hstrok: "Ħ",
            HumpDownHump: "≎",
            HumpEqual: "≏",
            IEcy: "Е",
            IJlig: "Ĳ",
            IOcy: "Ё",
            Iacute: "Í",
            Icirc: "Î",
            Icy: "И",
            Idot: "İ",
            Ifr: "ℑ",
            Igrave: "Ì",
            Im: "ℑ",
            Imacr: "Ī",
            ImaginaryI: "ⅈ",
            Implies: "⇒",
            Int: "∬",
            Integral: "∫",
            Intersection: "⋂",
            InvisibleComma: "⁣",
            InvisibleTimes: "⁢",
            Iogon: "Į",
            Iopf: "𝕀",
            Iota: "Ι",
            Iscr: "ℐ",
            Itilde: "Ĩ",
            Iukcy: "І",
            Iuml: "Ï",
            Jcirc: "Ĵ",
            Jcy: "Й",
            Jfr: "𝔍",
            Jopf: "𝕁",
            Jscr: "𝒥",
            Jsercy: "Ј",
            Jukcy: "Є",
            KHcy: "Х",
            KJcy: "Ќ",
            Kappa: "Κ",
            Kcedil: "Ķ",
            Kcy: "К",
            Kfr: "𝔎",
            Kopf: "𝕂",
            Kscr: "𝒦",
            LJcy: "Љ",
            LT: "<",
            Lacute: "Ĺ",
            Lambda: "Λ",
            Lang: "⟪",
            Laplacetrf: "ℒ",
            Larr: "↞",
            Lcaron: "Ľ",
            Lcedil: "Ļ",
            Lcy: "Л",
            LeftAngleBracket: "⟨",
            LeftArrow: "←",
            LeftArrowBar: "⇤",
            LeftArrowRightArrow: "⇆",
            LeftCeiling: "⌈",
            LeftDoubleBracket: "⟦",
            LeftDownTeeVector: "⥡",
            LeftDownVector: "⇃",
            LeftDownVectorBar: "⥙",
            LeftFloor: "⌊",
            LeftRightArrow: "↔",
            LeftRightVector: "⥎",
            LeftTee: "⊣",
            LeftTeeArrow: "↤",
            LeftTeeVector: "⥚",
            LeftTriangle: "⊲",
            LeftTriangleBar: "⧏",
            LeftTriangleEqual: "⊴",
            LeftUpDownVector: "⥑",
            LeftUpTeeVector: "⥠",
            LeftUpVector: "↿",
            LeftUpVectorBar: "⥘",
            LeftVector: "↼",
            LeftVectorBar: "⥒",
            Leftarrow: "⇐",
            Leftrightarrow: "⇔",
            LessEqualGreater: "⋚",
            LessFullEqual: "≦",
            LessGreater: "≶",
            LessLess: "⪡",
            LessSlantEqual: "⩽",
            LessTilde: "≲",
            Lfr: "𝔏",
            Ll: "⋘",
            Lleftarrow: "⇚",
            Lmidot: "Ŀ",
            LongLeftArrow: "⟵",
            LongLeftRightArrow: "⟷",
            LongRightArrow: "⟶",
            Longleftarrow: "⟸",
            Longleftrightarrow: "⟺",
            Longrightarrow: "⟹",
            Lopf: "𝕃",
            LowerLeftArrow: "↙",
            LowerRightArrow: "↘",
            Lscr: "ℒ",
            Lsh: "↰",
            Lstrok: "Ł",
            Lt: "≪",
            Map: "⤅",
            Mcy: "М",
            MediumSpace: " ",
            Mellintrf: "ℳ",
            Mfr: "𝔐",
            MinusPlus: "∓",
            Mopf: "𝕄",
            Mscr: "ℳ",
            Mu: "Μ",
            NJcy: "Њ",
            Nacute: "Ń",
            Ncaron: "Ň",
            Ncedil: "Ņ",
            Ncy: "Н",
            NegativeMediumSpace: "​",
            NegativeThickSpace: "​",
            NegativeThinSpace: "​",
            NegativeVeryThinSpace: "​",
            NestedGreaterGreater: "≫",
            NestedLessLess: "≪",
            NewLine: "\n",
            Nfr: "𝔑",
            NoBreak: "⁠",
            NonBreakingSpace: " ",
            Nopf: "ℕ",
            Not: "⫬",
            NotCongruent: "≢",
            NotCupCap: "≭",
            NotDoubleVerticalBar: "∦",
            NotElement: "∉",
            NotEqual: "≠",
            NotEqualTilde: "≂̸",
            NotExists: "∄",
            NotGreater: "≯",
            NotGreaterEqual: "≱",
            NotGreaterFullEqual: "≧̸",
            NotGreaterGreater: "≫̸",
            NotGreaterLess: "≹",
            NotGreaterSlantEqual: "⩾̸",
            NotGreaterTilde: "≵",
            NotHumpDownHump: "≎̸",
            NotHumpEqual: "≏̸",
            NotLeftTriangle: "⋪",
            NotLeftTriangleBar: "⧏̸",
            NotLeftTriangleEqual: "⋬",
            NotLess: "≮",
            NotLessEqual: "≰",
            NotLessGreater: "≸",
            NotLessLess: "≪̸",
            NotLessSlantEqual: "⩽̸",
            NotLessTilde: "≴",
            NotNestedGreaterGreater: "⪢̸",
            NotNestedLessLess: "⪡̸",
            NotPrecedes: "⊀",
            NotPrecedesEqual: "⪯̸",
            NotPrecedesSlantEqual: "⋠",
            NotReverseElement: "∌",
            NotRightTriangle: "⋫",
            NotRightTriangleBar: "⧐̸",
            NotRightTriangleEqual: "⋭",
            NotSquareSubset: "⊏̸",
            NotSquareSubsetEqual: "⋢",
            NotSquareSuperset: "⊐̸",
            NotSquareSupersetEqual: "⋣",
            NotSubset: "⊂⃒",
            NotSubsetEqual: "⊈",
            NotSucceeds: "⊁",
            NotSucceedsEqual: "⪰̸",
            NotSucceedsSlantEqual: "⋡",
            NotSucceedsTilde: "≿̸",
            NotSuperset: "⊃⃒",
            NotSupersetEqual: "⊉",
            NotTilde: "≁",
            NotTildeEqual: "≄",
            NotTildeFullEqual: "≇",
            NotTildeTilde: "≉",
            NotVerticalBar: "∤",
            Nscr: "𝒩",
            Ntilde: "Ñ",
            Nu: "Ν",
            OElig: "Œ",
            Oacute: "Ó",
            Ocirc: "Ô",
            Ocy: "О",
            Odblac: "Ő",
            Ofr: "𝔒",
            Ograve: "Ò",
            Omacr: "Ō",
            Omega: "Ω",
            Omicron: "Ο",
            Oopf: "𝕆",
            OpenCurlyDoubleQuote: "“",
            OpenCurlyQuote: "‘",
            Or: "⩔",
            Oscr: "𝒪",
            Oslash: "Ø",
            Otilde: "Õ",
            Otimes: "⨷",
            Ouml: "Ö",
            OverBar: "‾",
            OverBrace: "⏞",
            OverBracket: "⎴",
            OverParenthesis: "⏜",
            PartialD: "∂",
            Pcy: "П",
            Pfr: "𝔓",
            Phi: "Φ",
            Pi: "Π",
            PlusMinus: "±",
            Poincareplane: "ℌ",
            Popf: "ℙ",
            Pr: "⪻",
            Precedes: "≺",
            PrecedesEqual: "⪯",
            PrecedesSlantEqual: "≼",
            PrecedesTilde: "≾",
            Prime: "″",
            Product: "∏",
            Proportion: "∷",
            Proportional: "∝",
            Pscr: "𝒫",
            Psi: "Ψ",
            QUOT: '"',
            Qfr: "𝔔",
            Qopf: "ℚ",
            Qscr: "𝒬",
            RBarr: "⤐",
            REG: "®",
            Racute: "Ŕ",
            Rang: "⟫",
            Rarr: "↠",
            Rarrtl: "⤖",
            Rcaron: "Ř",
            Rcedil: "Ŗ",
            Rcy: "Р",
            Re: "ℜ",
            ReverseElement: "∋",
            ReverseEquilibrium: "⇋",
            ReverseUpEquilibrium: "⥯",
            Rfr: "ℜ",
            Rho: "Ρ",
            RightAngleBracket: "⟩",
            RightArrow: "→",
            RightArrowBar: "⇥",
            RightArrowLeftArrow: "⇄",
            RightCeiling: "⌉",
            RightDoubleBracket: "⟧",
            RightDownTeeVector: "⥝",
            RightDownVector: "⇂",
            RightDownVectorBar: "⥕",
            RightFloor: "⌋",
            RightTee: "⊢",
            RightTeeArrow: "↦",
            RightTeeVector: "⥛",
            RightTriangle: "⊳",
            RightTriangleBar: "⧐",
            RightTriangleEqual: "⊵",
            RightUpDownVector: "⥏",
            RightUpTeeVector: "⥜",
            RightUpVector: "↾",
            RightUpVectorBar: "⥔",
            RightVector: "⇀",
            RightVectorBar: "⥓",
            Rightarrow: "⇒",
            Ropf: "ℝ",
            RoundImplies: "⥰",
            Rrightarrow: "⇛",
            Rscr: "ℛ",
            Rsh: "↱",
            RuleDelayed: "⧴",
            SHCHcy: "Щ",
            SHcy: "Ш",
            SOFTcy: "Ь",
            Sacute: "Ś",
            Sc: "⪼",
            Scaron: "Š",
            Scedil: "Ş",
            Scirc: "Ŝ",
            Scy: "С",
            Sfr: "𝔖",
            ShortDownArrow: "↓",
            ShortLeftArrow: "←",
            ShortRightArrow: "→",
            ShortUpArrow: "↑",
            Sigma: "Σ",
            SmallCircle: "∘",
            Sopf: "𝕊",
            Sqrt: "√",
            Square: "□",
            SquareIntersection: "⊓",
            SquareSubset: "⊏",
            SquareSubsetEqual: "⊑",
            SquareSuperset: "⊐",
            SquareSupersetEqual: "⊒",
            SquareUnion: "⊔",
            Sscr: "𝒮",
            Star: "⋆",
            Sub: "⋐",
            Subset: "⋐",
            SubsetEqual: "⊆",
            Succeeds: "≻",
            SucceedsEqual: "⪰",
            SucceedsSlantEqual: "≽",
            SucceedsTilde: "≿",
            SuchThat: "∋",
            Sum: "∑",
            Sup: "⋑",
            Superset: "⊃",
            SupersetEqual: "⊇",
            Supset: "⋑",
            THORN: "Þ",
            TRADE: "™",
            TSHcy: "Ћ",
            TScy: "Ц",
            Tab: "\t",
            Tau: "Τ",
            Tcaron: "Ť",
            Tcedil: "Ţ",
            Tcy: "Т",
            Tfr: "𝔗",
            Therefore: "∴",
            Theta: "Θ",
            ThickSpace: "  ",
            ThinSpace: " ",
            Tilde: "∼",
            TildeEqual: "≃",
            TildeFullEqual: "≅",
            TildeTilde: "≈",
            Topf: "𝕋",
            TripleDot: "⃛",
            Tscr: "𝒯",
            Tstrok: "Ŧ",
            Uacute: "Ú",
            Uarr: "↟",
            Uarrocir: "⥉",
            Ubrcy: "Ў",
            Ubreve: "Ŭ",
            Ucirc: "Û",
            Ucy: "У",
            Udblac: "Ű",
            Ufr: "𝔘",
            Ugrave: "Ù",
            Umacr: "Ū",
            UnderBar: "_",
            UnderBrace: "⏟",
            UnderBracket: "⎵",
            UnderParenthesis: "⏝",
            Union: "⋃",
            UnionPlus: "⊎",
            Uogon: "Ų",
            Uopf: "𝕌",
            UpArrow: "↑",
            UpArrowBar: "⤒",
            UpArrowDownArrow: "⇅",
            UpDownArrow: "↕",
            UpEquilibrium: "⥮",
            UpTee: "⊥",
            UpTeeArrow: "↥",
            Uparrow: "⇑",
            Updownarrow: "⇕",
            UpperLeftArrow: "↖",
            UpperRightArrow: "↗",
            Upsi: "ϒ",
            Upsilon: "Υ",
            Uring: "Ů",
            Uscr: "𝒰",
            Utilde: "Ũ",
            Uuml: "Ü",
            VDash: "⊫",
            Vbar: "⫫",
            Vcy: "В",
            Vdash: "⊩",
            Vdashl: "⫦",
            Vee: "⋁",
            Verbar: "‖",
            Vert: "‖",
            VerticalBar: "∣",
            VerticalLine: "|",
            VerticalSeparator: "❘",
            VerticalTilde: "≀",
            VeryThinSpace: " ",
            Vfr: "𝔙",
            Vopf: "𝕍",
            Vscr: "𝒱",
            Vvdash: "⊪",
            Wcirc: "Ŵ",
            Wedge: "⋀",
            Wfr: "𝔚",
            Wopf: "𝕎",
            Wscr: "𝒲",
            Xfr: "𝔛",
            Xi: "Ξ",
            Xopf: "𝕏",
            Xscr: "𝒳",
            YAcy: "Я",
            YIcy: "Ї",
            YUcy: "Ю",
            Yacute: "Ý",
            Ycirc: "Ŷ",
            Ycy: "Ы",
            Yfr: "𝔜",
            Yopf: "𝕐",
            Yscr: "𝒴",
            Yuml: "Ÿ",
            ZHcy: "Ж",
            Zacute: "Ź",
            Zcaron: "Ž",
            Zcy: "З",
            Zdot: "Ż",
            ZeroWidthSpace: "​",
            Zeta: "Ζ",
            Zfr: "ℨ",
            Zopf: "ℤ",
            Zscr: "𝒵",
            aacute: "á",
            abreve: "ă",
            ac: "∾",
            acE: "∾̳",
            acd: "∿",
            acirc: "â",
            acute: "´",
            acy: "а",
            aelig: "æ",
            af: "⁡",
            afr: "𝔞",
            agrave: "à",
            alefsym: "ℵ",
            aleph: "ℵ",
            alpha: "α",
            amacr: "ā",
            amalg: "⨿",
            amp: "&",
            and: "∧",
            andand: "⩕",
            andd: "⩜",
            andslope: "⩘",
            andv: "⩚",
            ang: "∠",
            ange: "⦤",
            angle: "∠",
            angmsd: "∡",
            angmsdaa: "⦨",
            angmsdab: "⦩",
            angmsdac: "⦪",
            angmsdad: "⦫",
            angmsdae: "⦬",
            angmsdaf: "⦭",
            angmsdag: "⦮",
            angmsdah: "⦯",
            angrt: "∟",
            angrtvb: "⊾",
            angrtvbd: "⦝",
            angsph: "∢",
            angst: "Å",
            angzarr: "⍼",
            aogon: "ą",
            aopf: "𝕒",
            ap: "≈",
            apE: "⩰",
            apacir: "⩯",
            ape: "≊",
            apid: "≋",
            apos: "'",
            approx: "≈",
            approxeq: "≊",
            aring: "å",
            ascr: "𝒶",
            ast: "*",
            asymp: "≈",
            asympeq: "≍",
            atilde: "ã",
            auml: "ä",
            awconint: "∳",
            awint: "⨑",
            bNot: "⫭",
            backcong: "≌",
            backepsilon: "϶",
            backprime: "‵",
            backsim: "∽",
            backsimeq: "⋍",
            barvee: "⊽",
            barwed: "⌅",
            barwedge: "⌅",
            bbrk: "⎵",
            bbrktbrk: "⎶",
            bcong: "≌",
            bcy: "б",
            bdquo: "„",
            becaus: "∵",
            because: "∵",
            bemptyv: "⦰",
            bepsi: "϶",
            bernou: "ℬ",
            beta: "β",
            beth: "ℶ",
            between: "≬",
            bfr: "𝔟",
            bigcap: "⋂",
            bigcirc: "◯",
            bigcup: "⋃",
            bigodot: "⨀",
            bigoplus: "⨁",
            bigotimes: "⨂",
            bigsqcup: "⨆",
            bigstar: "★",
            bigtriangledown: "▽",
            bigtriangleup: "△",
            biguplus: "⨄",
            bigvee: "⋁",
            bigwedge: "⋀",
            bkarow: "⤍",
            blacklozenge: "⧫",
            blacksquare: "▪",
            blacktriangle: "▴",
            blacktriangledown: "▾",
            blacktriangleleft: "◂",
            blacktriangleright: "▸",
            blank: "␣",
            blk12: "▒",
            blk14: "░",
            blk34: "▓",
            block: "█",
            bne: "=⃥",
            bnequiv: "≡⃥",
            bnot: "⌐",
            bopf: "𝕓",
            bot: "⊥",
            bottom: "⊥",
            bowtie: "⋈",
            boxDL: "╗",
            boxDR: "╔",
            boxDl: "╖",
            boxDr: "╓",
            boxH: "═",
            boxHD: "╦",
            boxHU: "╩",
            boxHd: "╤",
            boxHu: "╧",
            boxUL: "╝",
            boxUR: "╚",
            boxUl: "╜",
            boxUr: "╙",
            boxV: "║",
            boxVH: "╬",
            boxVL: "╣",
            boxVR: "╠",
            boxVh: "╫",
            boxVl: "╢",
            boxVr: "╟",
            boxbox: "⧉",
            boxdL: "╕",
            boxdR: "╒",
            boxdl: "┐",
            boxdr: "┌",
            boxh: "─",
            boxhD: "╥",
            boxhU: "╨",
            boxhd: "┬",
            boxhu: "┴",
            boxminus: "⊟",
            boxplus: "⊞",
            boxtimes: "⊠",
            boxuL: "╛",
            boxuR: "╘",
            boxul: "┘",
            boxur: "└",
            boxv: "│",
            boxvH: "╪",
            boxvL: "╡",
            boxvR: "╞",
            boxvh: "┼",
            boxvl: "┤",
            boxvr: "├",
            bprime: "‵",
            breve: "˘",
            brvbar: "¦",
            bscr: "𝒷",
            bsemi: "⁏",
            bsim: "∽",
            bsime: "⋍",
            bsol: "\\",
            bsolb: "⧅",
            bsolhsub: "⟈",
            bull: "•",
            bullet: "•",
            bump: "≎",
            bumpE: "⪮",
            bumpe: "≏",
            bumpeq: "≏",
            cacute: "ć",
            cap: "∩",
            capand: "⩄",
            capbrcup: "⩉",
            capcap: "⩋",
            capcup: "⩇",
            capdot: "⩀",
            caps: "∩︀",
            caret: "⁁",
            caron: "ˇ",
            ccaps: "⩍",
            ccaron: "č",
            ccedil: "ç",
            ccirc: "ĉ",
            ccups: "⩌",
            ccupssm: "⩐",
            cdot: "ċ",
            cedil: "¸",
            cemptyv: "⦲",
            cent: "¢",
            centerdot: "·",
            cfr: "𝔠",
            chcy: "ч",
            check: "✓",
            checkmark: "✓",
            chi: "χ",
            cir: "○",
            cirE: "⧃",
            circ: "ˆ",
            circeq: "≗",
            circlearrowleft: "↺",
            circlearrowright: "↻",
            circledR: "®",
            circledS: "Ⓢ",
            circledast: "⊛",
            circledcirc: "⊚",
            circleddash: "⊝",
            cire: "≗",
            cirfnint: "⨐",
            cirmid: "⫯",
            cirscir: "⧂",
            clubs: "♣",
            clubsuit: "♣",
            colon: ":",
            colone: "≔",
            coloneq: "≔",
            comma: ",",
            commat: "@",
            comp: "∁",
            compfn: "∘",
            complement: "∁",
            complexes: "ℂ",
            cong: "≅",
            congdot: "⩭",
            conint: "∮",
            copf: "𝕔",
            coprod: "∐",
            copy: "©",
            copysr: "℗",
            crarr: "↵",
            cross: "✗",
            cscr: "𝒸",
            csub: "⫏",
            csube: "⫑",
            csup: "⫐",
            csupe: "⫒",
            ctdot: "⋯",
            cudarrl: "⤸",
            cudarrr: "⤵",
            cuepr: "⋞",
            cuesc: "⋟",
            cularr: "↶",
            cularrp: "⤽",
            cup: "∪",
            cupbrcap: "⩈",
            cupcap: "⩆",
            cupcup: "⩊",
            cupdot: "⊍",
            cupor: "⩅",
            cups: "∪︀",
            curarr: "↷",
            curarrm: "⤼",
            curlyeqprec: "⋞",
            curlyeqsucc: "⋟",
            curlyvee: "⋎",
            curlywedge: "⋏",
            curren: "¤",
            curvearrowleft: "↶",
            curvearrowright: "↷",
            cuvee: "⋎",
            cuwed: "⋏",
            cwconint: "∲",
            cwint: "∱",
            cylcty: "⌭",
            dArr: "⇓",
            dHar: "⥥",
            dagger: "†",
            daleth: "ℸ",
            darr: "↓",
            dash: "‐",
            dashv: "⊣",
            dbkarow: "⤏",
            dblac: "˝",
            dcaron: "ď",
            dcy: "д",
            dd: "ⅆ",
            ddagger: "‡",
            ddarr: "⇊",
            ddotseq: "⩷",
            deg: "°",
            delta: "δ",
            demptyv: "⦱",
            dfisht: "⥿",
            dfr: "𝔡",
            dharl: "⇃",
            dharr: "⇂",
            diam: "⋄",
            diamond: "⋄",
            diamondsuit: "♦",
            diams: "♦",
            die: "¨",
            digamma: "ϝ",
            disin: "⋲",
            div: "÷",
            divide: "÷",
            divideontimes: "⋇",
            divonx: "⋇",
            djcy: "ђ",
            dlcorn: "⌞",
            dlcrop: "⌍",
            dollar: "$",
            dopf: "𝕕",
            dot: "˙",
            doteq: "≐",
            doteqdot: "≑",
            dotminus: "∸",
            dotplus: "∔",
            dotsquare: "⊡",
            doublebarwedge: "⌆",
            downarrow: "↓",
            downdownarrows: "⇊",
            downharpoonleft: "⇃",
            downharpoonright: "⇂",
            drbkarow: "⤐",
            drcorn: "⌟",
            drcrop: "⌌",
            dscr: "𝒹",
            dscy: "ѕ",
            dsol: "⧶",
            dstrok: "đ",
            dtdot: "⋱",
            dtri: "▿",
            dtrif: "▾",
            duarr: "⇵",
            duhar: "⥯",
            dwangle: "⦦",
            dzcy: "џ",
            dzigrarr: "⟿",
            eDDot: "⩷",
            eDot: "≑",
            eacute: "é",
            easter: "⩮",
            ecaron: "ě",
            ecir: "≖",
            ecirc: "ê",
            ecolon: "≕",
            ecy: "э",
            edot: "ė",
            ee: "ⅇ",
            efDot: "≒",
            efr: "𝔢",
            eg: "⪚",
            egrave: "è",
            egs: "⪖",
            egsdot: "⪘",
            el: "⪙",
            elinters: "⏧",
            ell: "ℓ",
            els: "⪕",
            elsdot: "⪗",
            emacr: "ē",
            empty: "∅",
            emptyset: "∅",
            emptyv: "∅",
            emsp13: " ",
            emsp14: " ",
            emsp: " ",
            eng: "ŋ",
            ensp: " ",
            eogon: "ę",
            eopf: "𝕖",
            epar: "⋕",
            eparsl: "⧣",
            eplus: "⩱",
            epsi: "ε",
            epsilon: "ε",
            epsiv: "ϵ",
            eqcirc: "≖",
            eqcolon: "≕",
            eqsim: "≂",
            eqslantgtr: "⪖",
            eqslantless: "⪕",
            equals: "=",
            equest: "≟",
            equiv: "≡",
            equivDD: "⩸",
            eqvparsl: "⧥",
            erDot: "≓",
            erarr: "⥱",
            escr: "ℯ",
            esdot: "≐",
            esim: "≂",
            eta: "η",
            eth: "ð",
            euml: "ë",
            euro: "€",
            excl: "!",
            exist: "∃",
            expectation: "ℰ",
            exponentiale: "ⅇ",
            fallingdotseq: "≒",
            fcy: "ф",
            female: "♀",
            ffilig: "ﬃ",
            fflig: "ﬀ",
            ffllig: "ﬄ",
            ffr: "𝔣",
            filig: "ﬁ",
            fjlig: "fj",
            flat: "♭",
            fllig: "ﬂ",
            fltns: "▱",
            fnof: "ƒ",
            fopf: "𝕗",
            forall: "∀",
            fork: "⋔",
            forkv: "⫙",
            fpartint: "⨍",
            frac12: "½",
            frac13: "⅓",
            frac14: "¼",
            frac15: "⅕",
            frac16: "⅙",
            frac18: "⅛",
            frac23: "⅔",
            frac25: "⅖",
            frac34: "¾",
            frac35: "⅗",
            frac38: "⅜",
            frac45: "⅘",
            frac56: "⅚",
            frac58: "⅝",
            frac78: "⅞",
            frasl: "⁄",
            frown: "⌢",
            fscr: "𝒻",
            gE: "≧",
            gEl: "⪌",
            gacute: "ǵ",
            gamma: "γ",
            gammad: "ϝ",
            gap: "⪆",
            gbreve: "ğ",
            gcirc: "ĝ",
            gcy: "г",
            gdot: "ġ",
            ge: "≥",
            gel: "⋛",
            geq: "≥",
            geqq: "≧",
            geqslant: "⩾",
            ges: "⩾",
            gescc: "⪩",
            gesdot: "⪀",
            gesdoto: "⪂",
            gesdotol: "⪄",
            gesl: "⋛︀",
            gesles: "⪔",
            gfr: "𝔤",
            gg: "≫",
            ggg: "⋙",
            gimel: "ℷ",
            gjcy: "ѓ",
            gl: "≷",
            glE: "⪒",
            gla: "⪥",
            glj: "⪤",
            gnE: "≩",
            gnap: "⪊",
            gnapprox: "⪊",
            gne: "⪈",
            gneq: "⪈",
            gneqq: "≩",
            gnsim: "⋧",
            gopf: "𝕘",
            grave: "`",
            gscr: "ℊ",
            gsim: "≳",
            gsime: "⪎",
            gsiml: "⪐",
            gt: ">",
            gtcc: "⪧",
            gtcir: "⩺",
            gtdot: "⋗",
            gtlPar: "⦕",
            gtquest: "⩼",
            gtrapprox: "⪆",
            gtrarr: "⥸",
            gtrdot: "⋗",
            gtreqless: "⋛",
            gtreqqless: "⪌",
            gtrless: "≷",
            gtrsim: "≳",
            gvertneqq: "≩︀",
            gvnE: "≩︀",
            hArr: "⇔",
            hairsp: " ",
            half: "½",
            hamilt: "ℋ",
            hardcy: "ъ",
            harr: "↔",
            harrcir: "⥈",
            harrw: "↭",
            hbar: "ℏ",
            hcirc: "ĥ",
            hearts: "♥",
            heartsuit: "♥",
            hellip: "…",
            hercon: "⊹",
            hfr: "𝔥",
            hksearow: "⤥",
            hkswarow: "⤦",
            hoarr: "⇿",
            homtht: "∻",
            hookleftarrow: "↩",
            hookrightarrow: "↪",
            hopf: "𝕙",
            horbar: "―",
            hscr: "𝒽",
            hslash: "ℏ",
            hstrok: "ħ",
            hybull: "⁃",
            hyphen: "‐",
            iacute: "í",
            ic: "⁣",
            icirc: "î",
            icy: "и",
            iecy: "е",
            iexcl: "¡",
            iff: "⇔",
            ifr: "𝔦",
            igrave: "ì",
            ii: "ⅈ",
            iiiint: "⨌",
            iiint: "∭",
            iinfin: "⧜",
            iiota: "℩",
            ijlig: "ĳ",
            imacr: "ī",
            image: "ℑ",
            imagline: "ℐ",
            imagpart: "ℑ",
            imath: "ı",
            imof: "⊷",
            imped: "Ƶ",
            in: "∈",
            incare: "℅",
            infin: "∞",
            infintie: "⧝",
            inodot: "ı",
            int: "∫",
            intcal: "⊺",
            integers: "ℤ",
            intercal: "⊺",
            intlarhk: "⨗",
            intprod: "⨼",
            iocy: "ё",
            iogon: "į",
            iopf: "𝕚",
            iota: "ι",
            iprod: "⨼",
            iquest: "¿",
            iscr: "𝒾",
            isin: "∈",
            isinE: "⋹",
            isindot: "⋵",
            isins: "⋴",
            isinsv: "⋳",
            isinv: "∈",
            it: "⁢",
            itilde: "ĩ",
            iukcy: "і",
            iuml: "ï",
            jcirc: "ĵ",
            jcy: "й",
            jfr: "𝔧",
            jmath: "ȷ",
            jopf: "𝕛",
            jscr: "𝒿",
            jsercy: "ј",
            jukcy: "є",
            kappa: "κ",
            kappav: "ϰ",
            kcedil: "ķ",
            kcy: "к",
            kfr: "𝔨",
            kgreen: "ĸ",
            khcy: "х",
            kjcy: "ќ",
            kopf: "𝕜",
            kscr: "𝓀",
            lAarr: "⇚",
            lArr: "⇐",
            lAtail: "⤛",
            lBarr: "⤎",
            lE: "≦",
            lEg: "⪋",
            lHar: "⥢",
            lacute: "ĺ",
            laemptyv: "⦴",
            lagran: "ℒ",
            lambda: "λ",
            lang: "⟨",
            langd: "⦑",
            langle: "⟨",
            lap: "⪅",
            laquo: "«",
            larr: "←",
            larrb: "⇤",
            larrbfs: "⤟",
            larrfs: "⤝",
            larrhk: "↩",
            larrlp: "↫",
            larrpl: "⤹",
            larrsim: "⥳",
            larrtl: "↢",
            lat: "⪫",
            latail: "⤙",
            late: "⪭",
            lates: "⪭︀",
            lbarr: "⤌",
            lbbrk: "❲",
            lbrace: "{",
            lbrack: "[",
            lbrke: "⦋",
            lbrksld: "⦏",
            lbrkslu: "⦍",
            lcaron: "ľ",
            lcedil: "ļ",
            lceil: "⌈",
            lcub: "{",
            lcy: "л",
            ldca: "⤶",
            ldquo: "“",
            ldquor: "„",
            ldrdhar: "⥧",
            ldrushar: "⥋",
            ldsh: "↲",
            le: "≤",
            leftarrow: "←",
            leftarrowtail: "↢",
            leftharpoondown: "↽",
            leftharpoonup: "↼",
            leftleftarrows: "⇇",
            leftrightarrow: "↔",
            leftrightarrows: "⇆",
            leftrightharpoons: "⇋",
            leftrightsquigarrow: "↭",
            leftthreetimes: "⋋",
            leg: "⋚",
            leq: "≤",
            leqq: "≦",
            leqslant: "⩽",
            les: "⩽",
            lescc: "⪨",
            lesdot: "⩿",
            lesdoto: "⪁",
            lesdotor: "⪃",
            lesg: "⋚︀",
            lesges: "⪓",
            lessapprox: "⪅",
            lessdot: "⋖",
            lesseqgtr: "⋚",
            lesseqqgtr: "⪋",
            lessgtr: "≶",
            lesssim: "≲",
            lfisht: "⥼",
            lfloor: "⌊",
            lfr: "𝔩",
            lg: "≶",
            lgE: "⪑",
            lhard: "↽",
            lharu: "↼",
            lharul: "⥪",
            lhblk: "▄",
            ljcy: "љ",
            ll: "≪",
            llarr: "⇇",
            llcorner: "⌞",
            llhard: "⥫",
            lltri: "◺",
            lmidot: "ŀ",
            lmoust: "⎰",
            lmoustache: "⎰",
            lnE: "≨",
            lnap: "⪉",
            lnapprox: "⪉",
            lne: "⪇",
            lneq: "⪇",
            lneqq: "≨",
            lnsim: "⋦",
            loang: "⟬",
            loarr: "⇽",
            lobrk: "⟦",
            longleftarrow: "⟵",
            longleftrightarrow: "⟷",
            longmapsto: "⟼",
            longrightarrow: "⟶",
            looparrowleft: "↫",
            looparrowright: "↬",
            lopar: "⦅",
            lopf: "𝕝",
            loplus: "⨭",
            lotimes: "⨴",
            lowast: "∗",
            lowbar: "_",
            loz: "◊",
            lozenge: "◊",
            lozf: "⧫",
            lpar: "(",
            lparlt: "⦓",
            lrarr: "⇆",
            lrcorner: "⌟",
            lrhar: "⇋",
            lrhard: "⥭",
            lrm: "‎",
            lrtri: "⊿",
            lsaquo: "‹",
            lscr: "𝓁",
            lsh: "↰",
            lsim: "≲",
            lsime: "⪍",
            lsimg: "⪏",
            lsqb: "[",
            lsquo: "‘",
            lsquor: "‚",
            lstrok: "ł",
            lt: "<",
            ltcc: "⪦",
            ltcir: "⩹",
            ltdot: "⋖",
            lthree: "⋋",
            ltimes: "⋉",
            ltlarr: "⥶",
            ltquest: "⩻",
            ltrPar: "⦖",
            ltri: "◃",
            ltrie: "⊴",
            ltrif: "◂",
            lurdshar: "⥊",
            luruhar: "⥦",
            lvertneqq: "≨︀",
            lvnE: "≨︀",
            mDDot: "∺",
            macr: "¯",
            male: "♂",
            malt: "✠",
            maltese: "✠",
            map: "↦",
            mapsto: "↦",
            mapstodown: "↧",
            mapstoleft: "↤",
            mapstoup: "↥",
            marker: "▮",
            mcomma: "⨩",
            mcy: "м",
            mdash: "—",
            measuredangle: "∡",
            mfr: "𝔪",
            mho: "℧",
            micro: "µ",
            mid: "∣",
            midast: "*",
            midcir: "⫰",
            middot: "·",
            minus: "−",
            minusb: "⊟",
            minusd: "∸",
            minusdu: "⨪",
            mlcp: "⫛",
            mldr: "…",
            mnplus: "∓",
            models: "⊧",
            mopf: "𝕞",
            mp: "∓",
            mscr: "𝓂",
            mstpos: "∾",
            mu: "μ",
            multimap: "⊸",
            mumap: "⊸",
            nGg: "⋙̸",
            nGt: "≫⃒",
            nGtv: "≫̸",
            nLeftarrow: "⇍",
            nLeftrightarrow: "⇎",
            nLl: "⋘̸",
            nLt: "≪⃒",
            nLtv: "≪̸",
            nRightarrow: "⇏",
            nVDash: "⊯",
            nVdash: "⊮",
            nabla: "∇",
            nacute: "ń",
            nang: "∠⃒",
            nap: "≉",
            napE: "⩰̸",
            napid: "≋̸",
            napos: "ŉ",
            napprox: "≉",
            natur: "♮",
            natural: "♮",
            naturals: "ℕ",
            nbsp: " ",
            nbump: "≎̸",
            nbumpe: "≏̸",
            ncap: "⩃",
            ncaron: "ň",
            ncedil: "ņ",
            ncong: "≇",
            ncongdot: "⩭̸",
            ncup: "⩂",
            ncy: "н",
            ndash: "–",
            ne: "≠",
            neArr: "⇗",
            nearhk: "⤤",
            nearr: "↗",
            nearrow: "↗",
            nedot: "≐̸",
            nequiv: "≢",
            nesear: "⤨",
            nesim: "≂̸",
            nexist: "∄",
            nexists: "∄",
            nfr: "𝔫",
            ngE: "≧̸",
            nge: "≱",
            ngeq: "≱",
            ngeqq: "≧̸",
            ngeqslant: "⩾̸",
            nges: "⩾̸",
            ngsim: "≵",
            ngt: "≯",
            ngtr: "≯",
            nhArr: "⇎",
            nharr: "↮",
            nhpar: "⫲",
            ni: "∋",
            nis: "⋼",
            nisd: "⋺",
            niv: "∋",
            njcy: "њ",
            nlArr: "⇍",
            nlE: "≦̸",
            nlarr: "↚",
            nldr: "‥",
            nle: "≰",
            nleftarrow: "↚",
            nleftrightarrow: "↮",
            nleq: "≰",
            nleqq: "≦̸",
            nleqslant: "⩽̸",
            nles: "⩽̸",
            nless: "≮",
            nlsim: "≴",
            nlt: "≮",
            nltri: "⋪",
            nltrie: "⋬",
            nmid: "∤",
            nopf: "𝕟",
            not: "¬",
            notin: "∉",
            notinE: "⋹̸",
            notindot: "⋵̸",
            notinva: "∉",
            notinvb: "⋷",
            notinvc: "⋶",
            notni: "∌",
            notniva: "∌",
            notnivb: "⋾",
            notnivc: "⋽",
            npar: "∦",
            nparallel: "∦",
            nparsl: "⫽⃥",
            npart: "∂̸",
            npolint: "⨔",
            npr: "⊀",
            nprcue: "⋠",
            npre: "⪯̸",
            nprec: "⊀",
            npreceq: "⪯̸",
            nrArr: "⇏",
            nrarr: "↛",
            nrarrc: "⤳̸",
            nrarrw: "↝̸",
            nrightarrow: "↛",
            nrtri: "⋫",
            nrtrie: "⋭",
            nsc: "⊁",
            nsccue: "⋡",
            nsce: "⪰̸",
            nscr: "𝓃",
            nshortmid: "∤",
            nshortparallel: "∦",
            nsim: "≁",
            nsime: "≄",
            nsimeq: "≄",
            nsmid: "∤",
            nspar: "∦",
            nsqsube: "⋢",
            nsqsupe: "⋣",
            nsub: "⊄",
            nsubE: "⫅̸",
            nsube: "⊈",
            nsubset: "⊂⃒",
            nsubseteq: "⊈",
            nsubseteqq: "⫅̸",
            nsucc: "⊁",
            nsucceq: "⪰̸",
            nsup: "⊅",
            nsupE: "⫆̸",
            nsupe: "⊉",
            nsupset: "⊃⃒",
            nsupseteq: "⊉",
            nsupseteqq: "⫆̸",
            ntgl: "≹",
            ntilde: "ñ",
            ntlg: "≸",
            ntriangleleft: "⋪",
            ntrianglelefteq: "⋬",
            ntriangleright: "⋫",
            ntrianglerighteq: "⋭",
            nu: "ν",
            num: "#",
            numero: "№",
            numsp: " ",
            nvDash: "⊭",
            nvHarr: "⤄",
            nvap: "≍⃒",
            nvdash: "⊬",
            nvge: "≥⃒",
            nvgt: ">⃒",
            nvinfin: "⧞",
            nvlArr: "⤂",
            nvle: "≤⃒",
            nvlt: "<⃒",
            nvltrie: "⊴⃒",
            nvrArr: "⤃",
            nvrtrie: "⊵⃒",
            nvsim: "∼⃒",
            nwArr: "⇖",
            nwarhk: "⤣",
            nwarr: "↖",
            nwarrow: "↖",
            nwnear: "⤧",
            oS: "Ⓢ",
            oacute: "ó",
            oast: "⊛",
            ocir: "⊚",
            ocirc: "ô",
            ocy: "о",
            odash: "⊝",
            odblac: "ő",
            odiv: "⨸",
            odot: "⊙",
            odsold: "⦼",
            oelig: "œ",
            ofcir: "⦿",
            ofr: "𝔬",
            ogon: "˛",
            ograve: "ò",
            ogt: "⧁",
            ohbar: "⦵",
            ohm: "Ω",
            oint: "∮",
            olarr: "↺",
            olcir: "⦾",
            olcross: "⦻",
            oline: "‾",
            olt: "⧀",
            omacr: "ō",
            omega: "ω",
            omicron: "ο",
            omid: "⦶",
            ominus: "⊖",
            oopf: "𝕠",
            opar: "⦷",
            operp: "⦹",
            oplus: "⊕",
            or: "∨",
            orarr: "↻",
            ord: "⩝",
            order: "ℴ",
            orderof: "ℴ",
            ordf: "ª",
            ordm: "º",
            origof: "⊶",
            oror: "⩖",
            orslope: "⩗",
            orv: "⩛",
            oscr: "ℴ",
            oslash: "ø",
            osol: "⊘",
            otilde: "õ",
            otimes: "⊗",
            otimesas: "⨶",
            ouml: "ö",
            ovbar: "⌽",
            par: "∥",
            para: "¶",
            parallel: "∥",
            parsim: "⫳",
            parsl: "⫽",
            part: "∂",
            pcy: "п",
            percnt: "%",
            period: ".",
            permil: "‰",
            perp: "⊥",
            pertenk: "‱",
            pfr: "𝔭",
            phi: "φ",
            phiv: "ϕ",
            phmmat: "ℳ",
            phone: "☎",
            pi: "π",
            pitchfork: "⋔",
            piv: "ϖ",
            planck: "ℏ",
            planckh: "ℎ",
            plankv: "ℏ",
            plus: "+",
            plusacir: "⨣",
            plusb: "⊞",
            pluscir: "⨢",
            plusdo: "∔",
            plusdu: "⨥",
            pluse: "⩲",
            plusmn: "±",
            plussim: "⨦",
            plustwo: "⨧",
            pm: "±",
            pointint: "⨕",
            popf: "𝕡",
            pound: "£",
            pr: "≺",
            prE: "⪳",
            prap: "⪷",
            prcue: "≼",
            pre: "⪯",
            prec: "≺",
            precapprox: "⪷",
            preccurlyeq: "≼",
            preceq: "⪯",
            precnapprox: "⪹",
            precneqq: "⪵",
            precnsim: "⋨",
            precsim: "≾",
            prime: "′",
            primes: "ℙ",
            prnE: "⪵",
            prnap: "⪹",
            prnsim: "⋨",
            prod: "∏",
            profalar: "⌮",
            profline: "⌒",
            profsurf: "⌓",
            prop: "∝",
            propto: "∝",
            prsim: "≾",
            prurel: "⊰",
            pscr: "𝓅",
            psi: "ψ",
            puncsp: " ",
            qfr: "𝔮",
            qint: "⨌",
            qopf: "𝕢",
            qprime: "⁗",
            qscr: "𝓆",
            quaternions: "ℍ",
            quatint: "⨖",
            quest: "?",
            questeq: "≟",
            quot: '"',
            rAarr: "⇛",
            rArr: "⇒",
            rAtail: "⤜",
            rBarr: "⤏",
            rHar: "⥤",
            race: "∽̱",
            racute: "ŕ",
            radic: "√",
            raemptyv: "⦳",
            rang: "⟩",
            rangd: "⦒",
            range: "⦥",
            rangle: "⟩",
            raquo: "»",
            rarr: "→",
            rarrap: "⥵",
            rarrb: "⇥",
            rarrbfs: "⤠",
            rarrc: "⤳",
            rarrfs: "⤞",
            rarrhk: "↪",
            rarrlp: "↬",
            rarrpl: "⥅",
            rarrsim: "⥴",
            rarrtl: "↣",
            rarrw: "↝",
            ratail: "⤚",
            ratio: "∶",
            rationals: "ℚ",
            rbarr: "⤍",
            rbbrk: "❳",
            rbrace: "}",
            rbrack: "]",
            rbrke: "⦌",
            rbrksld: "⦎",
            rbrkslu: "⦐",
            rcaron: "ř",
            rcedil: "ŗ",
            rceil: "⌉",
            rcub: "}",
            rcy: "р",
            rdca: "⤷",
            rdldhar: "⥩",
            rdquo: "”",
            rdquor: "”",
            rdsh: "↳",
            real: "ℜ",
            realine: "ℛ",
            realpart: "ℜ",
            reals: "ℝ",
            rect: "▭",
            reg: "®",
            rfisht: "⥽",
            rfloor: "⌋",
            rfr: "𝔯",
            rhard: "⇁",
            rharu: "⇀",
            rharul: "⥬",
            rho: "ρ",
            rhov: "ϱ",
            rightarrow: "→",
            rightarrowtail: "↣",
            rightharpoondown: "⇁",
            rightharpoonup: "⇀",
            rightleftarrows: "⇄",
            rightleftharpoons: "⇌",
            rightrightarrows: "⇉",
            rightsquigarrow: "↝",
            rightthreetimes: "⋌",
            ring: "˚",
            risingdotseq: "≓",
            rlarr: "⇄",
            rlhar: "⇌",
            rlm: "‏",
            rmoust: "⎱",
            rmoustache: "⎱",
            rnmid: "⫮",
            roang: "⟭",
            roarr: "⇾",
            robrk: "⟧",
            ropar: "⦆",
            ropf: "𝕣",
            roplus: "⨮",
            rotimes: "⨵",
            rpar: ")",
            rpargt: "⦔",
            rppolint: "⨒",
            rrarr: "⇉",
            rsaquo: "›",
            rscr: "𝓇",
            rsh: "↱",
            rsqb: "]",
            rsquo: "’",
            rsquor: "’",
            rthree: "⋌",
            rtimes: "⋊",
            rtri: "▹",
            rtrie: "⊵",
            rtrif: "▸",
            rtriltri: "⧎",
            ruluhar: "⥨",
            rx: "℞",
            sacute: "ś",
            sbquo: "‚",
            sc: "≻",
            scE: "⪴",
            scap: "⪸",
            scaron: "š",
            sccue: "≽",
            sce: "⪰",
            scedil: "ş",
            scirc: "ŝ",
            scnE: "⪶",
            scnap: "⪺",
            scnsim: "⋩",
            scpolint: "⨓",
            scsim: "≿",
            scy: "с",
            sdot: "⋅",
            sdotb: "⊡",
            sdote: "⩦",
            seArr: "⇘",
            searhk: "⤥",
            searr: "↘",
            searrow: "↘",
            sect: "§",
            semi: ";",
            seswar: "⤩",
            setminus: "∖",
            setmn: "∖",
            sext: "✶",
            sfr: "𝔰",
            sfrown: "⌢",
            sharp: "♯",
            shchcy: "щ",
            shcy: "ш",
            shortmid: "∣",
            shortparallel: "∥",
            shy: "­",
            sigma: "σ",
            sigmaf: "ς",
            sigmav: "ς",
            sim: "∼",
            simdot: "⩪",
            sime: "≃",
            simeq: "≃",
            simg: "⪞",
            simgE: "⪠",
            siml: "⪝",
            simlE: "⪟",
            simne: "≆",
            simplus: "⨤",
            simrarr: "⥲",
            slarr: "←",
            smallsetminus: "∖",
            smashp: "⨳",
            smeparsl: "⧤",
            smid: "∣",
            smile: "⌣",
            smt: "⪪",
            smte: "⪬",
            smtes: "⪬︀",
            softcy: "ь",
            sol: "/",
            solb: "⧄",
            solbar: "⌿",
            sopf: "𝕤",
            spades: "♠",
            spadesuit: "♠",
            spar: "∥",
            sqcap: "⊓",
            sqcaps: "⊓︀",
            sqcup: "⊔",
            sqcups: "⊔︀",
            sqsub: "⊏",
            sqsube: "⊑",
            sqsubset: "⊏",
            sqsubseteq: "⊑",
            sqsup: "⊐",
            sqsupe: "⊒",
            sqsupset: "⊐",
            sqsupseteq: "⊒",
            squ: "□",
            square: "□",
            squarf: "▪",
            squf: "▪",
            srarr: "→",
            sscr: "𝓈",
            ssetmn: "∖",
            ssmile: "⌣",
            sstarf: "⋆",
            star: "☆",
            starf: "★",
            straightepsilon: "ϵ",
            straightphi: "ϕ",
            strns: "¯",
            sub: "⊂",
            subE: "⫅",
            subdot: "⪽",
            sube: "⊆",
            subedot: "⫃",
            submult: "⫁",
            subnE: "⫋",
            subne: "⊊",
            subplus: "⪿",
            subrarr: "⥹",
            subset: "⊂",
            subseteq: "⊆",
            subseteqq: "⫅",
            subsetneq: "⊊",
            subsetneqq: "⫋",
            subsim: "⫇",
            subsub: "⫕",
            subsup: "⫓",
            succ: "≻",
            succapprox: "⪸",
            succcurlyeq: "≽",
            succeq: "⪰",
            succnapprox: "⪺",
            succneqq: "⪶",
            succnsim: "⋩",
            succsim: "≿",
            sum: "∑",
            sung: "♪",
            sup1: "¹",
            sup2: "²",
            sup3: "³",
            sup: "⊃",
            supE: "⫆",
            supdot: "⪾",
            supdsub: "⫘",
            supe: "⊇",
            supedot: "⫄",
            suphsol: "⟉",
            suphsub: "⫗",
            suplarr: "⥻",
            supmult: "⫂",
            supnE: "⫌",
            supne: "⊋",
            supplus: "⫀",
            supset: "⊃",
            supseteq: "⊇",
            supseteqq: "⫆",
            supsetneq: "⊋",
            supsetneqq: "⫌",
            supsim: "⫈",
            supsub: "⫔",
            supsup: "⫖",
            swArr: "⇙",
            swarhk: "⤦",
            swarr: "↙",
            swarrow: "↙",
            swnwar: "⤪",
            szlig: "ß",
            target: "⌖",
            tau: "τ",
            tbrk: "⎴",
            tcaron: "ť",
            tcedil: "ţ",
            tcy: "т",
            tdot: "⃛",
            telrec: "⌕",
            tfr: "𝔱",
            there4: "∴",
            therefore: "∴",
            theta: "θ",
            thetasym: "ϑ",
            thetav: "ϑ",
            thickapprox: "≈",
            thicksim: "∼",
            thinsp: " ",
            thkap: "≈",
            thksim: "∼",
            thorn: "þ",
            tilde: "˜",
            times: "×",
            timesb: "⊠",
            timesbar: "⨱",
            timesd: "⨰",
            tint: "∭",
            toea: "⤨",
            top: "⊤",
            topbot: "⌶",
            topcir: "⫱",
            topf: "𝕥",
            topfork: "⫚",
            tosa: "⤩",
            tprime: "‴",
            trade: "™",
            triangle: "▵",
            triangledown: "▿",
            triangleleft: "◃",
            trianglelefteq: "⊴",
            triangleq: "≜",
            triangleright: "▹",
            trianglerighteq: "⊵",
            tridot: "◬",
            trie: "≜",
            triminus: "⨺",
            triplus: "⨹",
            trisb: "⧍",
            tritime: "⨻",
            trpezium: "⏢",
            tscr: "𝓉",
            tscy: "ц",
            tshcy: "ћ",
            tstrok: "ŧ",
            twixt: "≬",
            twoheadleftarrow: "↞",
            twoheadrightarrow: "↠",
            uArr: "⇑",
            uHar: "⥣",
            uacute: "ú",
            uarr: "↑",
            ubrcy: "ў",
            ubreve: "ŭ",
            ucirc: "û",
            ucy: "у",
            udarr: "⇅",
            udblac: "ű",
            udhar: "⥮",
            ufisht: "⥾",
            ufr: "𝔲",
            ugrave: "ù",
            uharl: "↿",
            uharr: "↾",
            uhblk: "▀",
            ulcorn: "⌜",
            ulcorner: "⌜",
            ulcrop: "⌏",
            ultri: "◸",
            umacr: "ū",
            uml: "¨",
            uogon: "ų",
            uopf: "𝕦",
            uparrow: "↑",
            updownarrow: "↕",
            upharpoonleft: "↿",
            upharpoonright: "↾",
            uplus: "⊎",
            upsi: "υ",
            upsih: "ϒ",
            upsilon: "υ",
            upuparrows: "⇈",
            urcorn: "⌝",
            urcorner: "⌝",
            urcrop: "⌎",
            uring: "ů",
            urtri: "◹",
            uscr: "𝓊",
            utdot: "⋰",
            utilde: "ũ",
            utri: "▵",
            utrif: "▴",
            uuarr: "⇈",
            uuml: "ü",
            uwangle: "⦧",
            vArr: "⇕",
            vBar: "⫨",
            vBarv: "⫩",
            vDash: "⊨",
            vangrt: "⦜",
            varepsilon: "ϵ",
            varkappa: "ϰ",
            varnothing: "∅",
            varphi: "ϕ",
            varpi: "ϖ",
            varpropto: "∝",
            varr: "↕",
            varrho: "ϱ",
            varsigma: "ς",
            varsubsetneq: "⊊︀",
            varsubsetneqq: "⫋︀",
            varsupsetneq: "⊋︀",
            varsupsetneqq: "⫌︀",
            vartheta: "ϑ",
            vartriangleleft: "⊲",
            vartriangleright: "⊳",
            vcy: "в",
            vdash: "⊢",
            vee: "∨",
            veebar: "⊻",
            veeeq: "≚",
            vellip: "⋮",
            verbar: "|",
            vert: "|",
            vfr: "𝔳",
            vltri: "⊲",
            vnsub: "⊂⃒",
            vnsup: "⊃⃒",
            vopf: "𝕧",
            vprop: "∝",
            vrtri: "⊳",
            vscr: "𝓋",
            vsubnE: "⫋︀",
            vsubne: "⊊︀",
            vsupnE: "⫌︀",
            vsupne: "⊋︀",
            vzigzag: "⦚",
            wcirc: "ŵ",
            wedbar: "⩟",
            wedge: "∧",
            wedgeq: "≙",
            weierp: "℘",
            wfr: "𝔴",
            wopf: "𝕨",
            wp: "℘",
            wr: "≀",
            wreath: "≀",
            wscr: "𝓌",
            xcap: "⋂",
            xcirc: "◯",
            xcup: "⋃",
            xdtri: "▽",
            xfr: "𝔵",
            xhArr: "⟺",
            xharr: "⟷",
            xi: "ξ",
            xlArr: "⟸",
            xlarr: "⟵",
            xmap: "⟼",
            xnis: "⋻",
            xodot: "⨀",
            xopf: "𝕩",
            xoplus: "⨁",
            xotime: "⨂",
            xrArr: "⟹",
            xrarr: "⟶",
            xscr: "𝓍",
            xsqcup: "⨆",
            xuplus: "⨄",
            xutri: "△",
            xvee: "⋁",
            xwedge: "⋀",
            yacute: "ý",
            yacy: "я",
            ycirc: "ŷ",
            ycy: "ы",
            yen: "¥",
            yfr: "𝔶",
            yicy: "ї",
            yopf: "𝕪",
            yscr: "𝓎",
            yucy: "ю",
            yuml: "ÿ",
            zacute: "ź",
            zcaron: "ž",
            zcy: "з",
            zdot: "ż",
            zeetrf: "ℨ",
            zeta: "ζ",
            zfr: "𝔷",
            zhcy: "ж",
            zigrarr: "⇝",
            zopf: "𝕫",
            zscr: "𝓏",
            zwj: "‍",
            zwnj: "‌"
        };
        z.characterEntities = j;
    }, {} ],
    4: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.decodeNamedCharacterReference = l;
        var j = D("character-entities");
        const F = {}.hasOwnProperty;
        function l(D) {
            return F.call(j.characterEntities, D) ? j.characterEntities[D] : false;
        }
    }, {
        "character-entities": 3
    } ],
    5: [ function(D, h, z) {
        "use strict";
        function j(D) {
            let h, z, j, Z, A, q, Q;
            return I(), {
                feed: E,
                reset: I
            };
            function I() {
                h = true, z = "", j = 0, Z = -1, A = void 0, q = void 0, Q = "";
            }
            function E(D) {
                if (z = z ? z + D : D, h && l(z)) z = z.slice(F.length);
                h = false;
                const A = z.length;
                let q = 0, Q = false;
                while (q < A) {
                    if (Q) {
                        if (z[q] === "\n") ++q;
                        Q = false;
                    }
                    let D = -1, h = Z, F;
                    for (let l = j; D < 0 && l < A; ++l) if (F = z[l], F === ":" && h < 0) h = l - q; else if (F === "\r") Q = true,
                    D = l - q; else if (F === "\n") D = l - q;
                    if (D < 0) {
                        j = A - q, Z = h;
                        break;
                    } else j = 0, Z = -1;
                    X(z, q, h, D), q += D + 1;
                }
                if (q === A) z = ""; else if (q > 0) z = z.slice(q);
            }
            function X(h, z, j, F) {
                if (F === 0) {
                    if (Q.length > 0) D({
                        type: "event",
                        id: A,
                        event: q || void 0,
                        data: Q.slice(0, -1)
                    }), Q = "", A = void 0;
                    return void (q = void 0);
                }
                const l = j < 0, Z = h.slice(z, z + (l ? F : j));
                let I = 0;
                if (l) I = F; else if (h[z + j + 1] === " ") I = j + 2; else I = j + 1;
                const E = z + I, X = F - I, f = h.slice(E, E + X).toString();
                if (Z === "data") Q += f ? "".concat(f, "\n") : "\n"; else if (Z === "event") q = f; else if (Z === "id" && !f.includes("\0")) A = f; else if (Z === "retry") {
                    const h = parseInt(f, 10);
                    if (!Number.isNaN(h)) D({
                        type: "reconnect-interval",
                        value: h
                    });
                }
            }
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        });
        const F = [ 239, 187, 191 ];
        function l(D) {
            return F.every(((h, z) => D.charCodeAt(z) === h));
        }
        z.createParser = j;
    }, {} ],
    6: [ function(D, h, z) {
        "use strict";
        const j = D("map-age-cleaner");
        class F {
            constructor(D, h) {
                if (this.maxAge = D, this[Symbol.toStringTag] = "Map", this.data = new Map, j(this.data),
                h) for (const [D, z] of h) this.set(D, z);
            }
            get size() {
                return this.data.size;
            }
            clear() {
                this.data.clear();
            }
            delete(D) {
                return this.data.delete(D);
            }
            has(D) {
                return this.data.has(D);
            }
            get(D) {
                const h = this.data.get(D);
                if (h) return h.data;
                return;
            }
            set(D, h) {
                return this.data.set(D, {
                    maxAge: Date.now() + this.maxAge,
                    data: h
                }), this;
            }
            values() {
                return this.createIterator((D => D[1].data));
            }
            keys() {
                return this.data.keys();
            }
            entries() {
                return this.createIterator((D => [ D[0], D[1].data ]));
            }
            forEach(D, h) {
                for (const [z, j] of this.entries()) D.apply(h, [ j, z, this ]);
            }
            [Symbol.iterator]() {
                return this.entries();
            }
            * createIterator(D) {
                for (const h of this.data.entries()) yield D(h);
            }
        }
        h.exports = F;
    }, {
        "map-age-cleaner": 10
    } ],
    7: [ function(D, h, z) {
        "use strict";
        var j = Object.prototype.hasOwnProperty, F = Object.prototype.toString, l = Object.defineProperty, Z = Object.getOwnPropertyDescriptor, A = function D(h) {
            if (typeof Array.isArray === "function") return Array.isArray(h);
            return F.call(h) === "[object Array]";
        }, q = function D(h) {
            if (!h || F.call(h) !== "[object Object]") return false;
            var z = j.call(h, "constructor"), l = h.constructor && h.constructor.prototype && j.call(h.constructor.prototype, "isPrototypeOf"), Z;
            if (h.constructor && !z && !l) return false;
            for (Z in h) ;
            return typeof Z === "undefined" || j.call(h, Z);
        }, Q = function D(h, z) {
            if (l && z.name === "__proto__") l(h, z.name, {
                enumerable: true,
                configurable: true,
                value: z.newValue,
                writable: true
            }); else h[z.name] = z.newValue;
        }, I = function D(h, z) {
            if (z === "__proto__") if (!j.call(h, z)) return; else if (Z) return Z(h, z).value;
            return h[z];
        };
        h.exports = function D() {
            var h, z, j, F, l, Z, E = arguments[0], X = 1, f = arguments.length, s = false;
            if (typeof E === "boolean") s = E, E = arguments[1] || {}, X = 2;
            if (E == null || typeof E !== "object" && typeof E !== "function") E = {};
            for (;X < f; ++X) if (h = arguments[X], h != null) for (z in h) if (j = I(E, z),
            F = I(h, z), E !== F) if (s && F && (q(F) || (l = A(F)))) {
                if (l) l = false, Z = j && A(j) ? j : []; else Z = j && q(j) ? j : {};
                Q(E, {
                    name: z,
                    newValue: D(s, Z, F)
                });
            } else if (typeof F !== "undefined") Q(E, {
                name: z,
                newValue: F
            });
            return E;
        };
    }, {} ],
    8: [ function(D, h, z) {
        "use strict";
        function j(D) {
            if (typeof D !== "object" || D === null) return false;
            const h = Object.getPrototypeOf(D);
            return (h === null || h === Object.prototype || Object.getPrototypeOf(h) === null) && !(Symbol.toStringTag in D) && !(Symbol.iterator in D);
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.default = j;
    }, {} ],
    9: [ function(D, h, z) {
        "use strict";
        function j(D, h) {
            const z = String(D);
            let j = z.indexOf(h), F = j, l = 0, Z = 0;
            if (typeof h !== "string") throw new TypeError("Expected substring");
            while (j !== -1) {
                if (j === F) {
                    if (++l > Z) Z = l;
                } else l = 1;
                F = j + h.length, j = z.indexOf(h, F);
            }
            return Z;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.longestStreak = j;
    }, {} ],
    10: [ function(D, h, z) {
        "use strict";
        const j = D("p-defer");
        function F(D, h = "maxAge") {
            let z, F, l;
            const Z = async () => {
                if (z !== void 0) return;
                const Z = async Z => {
                    l = j();
                    const A = Z[1][h] - Date.now();
                    if (A <= 0) return D.delete(Z[0]), void l.resolve();
                    if (z = Z[0], F = setTimeout((() => {
                        if (D.delete(Z[0]), l) l.resolve();
                    }), A), typeof F.unref === "function") F.unref();
                    return l.promise;
                };
                try {
                    for (const h of D) await Z(h);
                } catch (D) {}
                z = void 0;
            }, A = () => {
                if (z = void 0, F !== void 0) clearTimeout(F), F = void 0;
                if (l !== void 0) l.reject(void 0), l = void 0;
            }, q = D.set.bind(D);
            return D.set = (h, j) => {
                if (D.has(h)) D.delete(h);
                const F = q(h, j);
                if (z && z === h) A();
                return Z(), F;
            }, Z(), D;
        }
        h.exports = F;
    }, {
        "p-defer": 111
    } ],
    11: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), Object.defineProperty(z, "fromMarkdown", {
            enumerable: true,
            get: function() {
                return j.fromMarkdown;
            }
        });
        var j = D("k8");
    }, {
        k8: 12
    } ],
    12: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.fromMarkdown = void 0;
        var j = D("mdast-util-to-string"), F = D("micromark/lib/parse.js"), l = D("micromark/lib/preprocess.js"), Z = D("micromark/lib/postprocess.js"), A = D("micromark-util-decode-numeric-character-reference"), q = D("micromark-util-decode-string"), Q = D("micromark-util-normalize-identifier"), I = D("decode-named-character-reference"), E = D("unist-util-stringify-position");
        const X = {}.hasOwnProperty, f = function(D, h, z) {
            if (typeof h !== "string") z = h, h = void 0;
            return s(z)((0, Z.postprocess)((0, F.parse)(z).document().write((0, l.preprocess)()(D, h, true))));
        };
        function s(D = {}) {
            const h = L({
                transforms: [],
                canContainEols: [ "emphasis", "fragment", "heading", "paragraph", "strong" ],
                enter: {
                    autolink: P(BW),
                    autolinkProtocol: k,
                    autolinkEmail: k,
                    atxHeading: P(Cv),
                    blockQuote: P(hO),
                    characterEscape: k,
                    characterReference: k,
                    codeFenced: P(VB),
                    codeFencedFenceInfo: n,
                    codeFencedFenceMeta: n,
                    codeIndented: P(VB, n),
                    codeText: P(zi, n),
                    codeTextData: k,
                    data: k,
                    codeFlowValue: k,
                    definition: P(dj),
                    definitionDestinationString: n,
                    definitionLabelString: n,
                    definitionTitleString: n,
                    emphasis: P(Su),
                    hardBreakEscape: P(Oq),
                    hardBreakTrailing: P(Oq),
                    htmlFlow: P(rB, n),
                    htmlFlowData: k,
                    htmlText: P(rB, n),
                    htmlTextData: k,
                    image: P(KU),
                    label: n,
                    link: P(BW),
                    listItem: P(mX),
                    listItemValue: K,
                    listOrdered: P(yi, H),
                    listUnordered: P(yi),
                    paragraph: P(ol),
                    reference: N,
                    referenceString: n,
                    resourceDestinationString: n,
                    resourceTitleString: n,
                    setextHeading: P(Cv),
                    strong: P(tR),
                    thematicBreak: P(qe)
                },
                exit: {
                    atxHeading: J(),
                    atxHeadingSequence: r,
                    autolink: J(),
                    autolinkEmail: LD,
                    autolinkProtocol: xk,
                    blockQuote: J(),
                    characterEscapeValue: W,
                    characterReferenceMarkerHexadecimal: Ar,
                    characterReferenceMarkerNumeric: Ar,
                    characterReferenceValue: qk,
                    codeFenced: J(T),
                    codeFencedFence: S,
                    codeFencedFenceInfo: c,
                    codeFencedFenceMeta: M,
                    codeFlowValue: W,
                    codeIndented: J(e),
                    codeText: J(o),
                    codeTextData: W,
                    data: W,
                    definition: J(),
                    definitionDestinationString: G,
                    definitionLabelString: v,
                    definitionTitleString: m,
                    emphasis: J(),
                    hardBreakEscape: J(p),
                    hardBreakTrailing: J(p),
                    htmlFlow: J(u),
                    htmlFlowData: W,
                    htmlText: J(O),
                    htmlTextData: W,
                    image: J(B),
                    label: R,
                    labelText: Y,
                    lineEnding: U,
                    link: J(b),
                    listItem: J(),
                    listOrdered: J(),
                    listUnordered: J(),
                    paragraph: J(),
                    referenceString: kN,
                    resourceDestinationString: V,
                    resourceTitleString: i,
                    resource: g,
                    setextHeading: J(y),
                    setextHeadingLineSequence: C,
                    setextHeadingText: t,
                    strong: J(),
                    thematicBreak: J()
                }
            }, D.mdastExtensions || []), z = {};
            return F;
            function F(D) {
                let z = {
                    type: "root",
                    children: []
                };
                const j = [ z ], F = [], A = [], q = {
                    stack: j,
                    tokenStack: F,
                    config: h,
                    enter: w,
                    exit: a,
                    buffer: n,
                    resume: d,
                    setData: Z,
                    getData: f
                };
                let Q = -1;
                while (++Q < D.length) if (D[Q][1].type === "listOrdered" || D[Q][1].type === "listUnordered") if (D[Q][0] === "enter") A.push(Q); else {
                    const h = A.pop();
                    Q = l(D, h, Q);
                }
                Q = -1;
                while (++Q < D.length) {
                    const z = h[D[Q][0]];
                    if (X.call(z, D[Q][1].type)) z[D[Q][1].type].call(Object.assign({
                        sliceSerialize: D[Q][2].sliceSerialize
                    }, q), D[Q][1]);
                }
                if (F.length > 0) {
                    const D = F[F.length - 1], h = D[1] || x;
                    h.call(q, void 0, D[0]);
                }
                z.position = {
                    start: s(D.length > 0 ? D[0][1].start : {
                        line: 1,
                        column: 1,
                        offset: 0
                    }),
                    end: s(D.length > 0 ? D[D.length - 2][1].end : {
                        line: 1,
                        column: 1,
                        offset: 0
                    })
                }, Q = -1;
                while (++Q < h.transforms.length) z = h.transforms[Q](z) || z;
                return z;
            }
            function l(D, h, z) {
                let j = h - 1, F = -1, l = false, Z, A, q, Q;
                while (++j <= z) {
                    const h = D[j];
                    if (h[1].type === "listUnordered" || h[1].type === "listOrdered" || h[1].type === "blockQuote") {
                        if (h[0] === "enter") F++; else F--;
                        Q = void 0;
                    } else if (h[1].type === "lineEndingBlank") {
                        if (h[0] === "enter") {
                            if (Z && !Q && !F && !q) q = j;
                            Q = void 0;
                        }
                    } else if (h[1].type === "linePrefix" || h[1].type === "listItemValue" || h[1].type === "listItemMarker" || h[1].type === "listItemPrefix" || h[1].type === "listItemPrefixWhitespace") ; else Q = void 0;
                    if (!F && h[0] === "enter" && h[1].type === "listItemPrefix" || F === -1 && h[0] === "exit" && (h[1].type === "listUnordered" || h[1].type === "listOrdered")) {
                        if (Z) {
                            let F = j;
                            A = void 0;
                            while (F--) {
                                const h = D[F];
                                if (h[1].type === "lineEnding" || h[1].type === "lineEndingBlank") {
                                    if (h[0] === "exit") continue;
                                    if (A) D[A][1].type = "lineEndingBlank", l = true;
                                    h[1].type = "lineEnding", A = F;
                                } else if (h[1].type === "linePrefix" || h[1].type === "blockQuotePrefix" || h[1].type === "blockQuotePrefixWhitespace" || h[1].type === "blockQuoteMarker" || h[1].type === "listItemIndent") ; else break;
                            }
                            if (q && (!A || q < A)) Z._spread = true;
                            Z.end = Object.assign({}, A ? D[A][1].start : h[1].end), D.splice(A || j, 0, [ "exit", Z, h[2] ]),
                            j++, z++;
                        }
                        if (h[1].type === "listItemPrefix") Z = {
                            type: "listItem",
                            _spread: false,
                            start: Object.assign({}, h[1].start)
                        }, D.splice(j, 0, [ "enter", Z, h[2] ]), j++, z++, q = void 0, Q = true;
                    }
                }
                return D[h][1]._spread = l, z;
            }
            function Z(D, h) {
                z[D] = h;
            }
            function f(D) {
                return z[D];
            }
            function s(D) {
                return {
                    line: D.line,
                    column: D.column,
                    offset: D.offset
                };
            }
            function P(D, h) {
                return z;
                function z(z) {
                    if (w.call(this, D(z), z), h) h.call(this, z);
                }
            }
            function n() {
                this.stack.push({
                    type: "fragment",
                    children: []
                });
            }
            function w(D, h, z) {
                const j = this.stack[this.stack.length - 1];
                return j.children.push(D), this.stack.push(D), this.tokenStack.push([ h, z ]), D.position = {
                    start: s(h.start)
                }, D;
            }
            function J(D) {
                return h;
                function h(h) {
                    if (D) D.call(this, h);
                    a.call(this, h);
                }
            }
            function a(D, h) {
                const z = this.stack.pop(), j = this.tokenStack.pop();
                if (!j) throw new Error("Cannot close `" + D.type + "` (" + (0, E.stringifyPosition)({
                    start: D.start,
                    end: D.end
                }) + "): it’s not open"); else if (j[0].type !== D.type) if (h) h.call(this, D, j[0]); else {
                    const h = j[1] || x;
                    h.call(this, D, j[0]);
                }
                return z.position.end = s(D.end), z;
            }
            function d() {
                return (0, j.toString)(this.stack.pop());
            }
            function H() {
                Z("expectingFirstListItemValue", true);
            }
            function K(D) {
                if (f("expectingFirstListItemValue")) {
                    const h = this.stack[this.stack.length - 2];
                    h.start = Number.parseInt(this.sliceSerialize(D), 10), Z("expectingFirstListItemValue");
                }
            }
            function c() {
                const D = this.resume(), h = this.stack[this.stack.length - 1];
                h.lang = D;
            }
            function M() {
                const D = this.resume(), h = this.stack[this.stack.length - 1];
                h.meta = D;
            }
            function S() {
                if (f("flowCodeInside")) return;
                this.buffer(), Z("flowCodeInside", true);
            }
            function T() {
                const D = this.resume(), h = this.stack[this.stack.length - 1];
                h.value = D.replace(/^(\r?\n|\r)|(\r?\n|\r)$/g, ""), Z("flowCodeInside");
            }
            function e() {
                const D = this.resume(), h = this.stack[this.stack.length - 1];
                h.value = D.replace(/(\r?\n|\r)$/g, "");
            }
            function v(D) {
                const h = this.resume(), z = this.stack[this.stack.length - 1];
                z.label = h, z.identifier = (0, Q.normalizeIdentifier)(this.sliceSerialize(D)).toLowerCase();
            }
            function m() {
                const D = this.resume(), h = this.stack[this.stack.length - 1];
                h.title = D;
            }
            function G() {
                const D = this.resume(), h = this.stack[this.stack.length - 1];
                h.url = D;
            }
            function r(D) {
                const h = this.stack[this.stack.length - 1];
                if (!h.depth) {
                    const z = this.sliceSerialize(D).length;
                    h.depth = z;
                }
            }
            function t() {
                Z("setextHeadingSlurpLineEnding", true);
            }
            function C(D) {
                const h = this.stack[this.stack.length - 1];
                h.depth = this.sliceSerialize(D).charCodeAt(0) === 61 ? 1 : 2;
            }
            function y() {
                Z("setextHeadingSlurpLineEnding");
            }
            function k(D) {
                const h = this.stack[this.stack.length - 1];
                let z = h.children[h.children.length - 1];
                if (!z || z.type !== "text") z = {
                    type: "text",
                    value: ""
                }, z.position = {
                    start: s(D.start)
                }, h.children.push(z);
                this.stack.push(z);
            }
            function W(D) {
                const h = this.stack.pop();
                h.value += this.sliceSerialize(D), h.position.end = s(D.end);
            }
            function U(D) {
                const z = this.stack[this.stack.length - 1];
                if (f("atHardBreak")) {
                    const h = z.children[z.children.length - 1];
                    return h.position.end = s(D.end), void Z("atHardBreak");
                }
                if (!f("setextHeadingSlurpLineEnding") && h.canContainEols.includes(z.type)) k.call(this, D),
                W.call(this, D);
            }
            function p() {
                Z("atHardBreak", true);
            }
            function u() {
                const D = this.resume(), h = this.stack[this.stack.length - 1];
                h.value = D;
            }
            function O() {
                const D = this.resume(), h = this.stack[this.stack.length - 1];
                h.value = D;
            }
            function o() {
                const D = this.resume(), h = this.stack[this.stack.length - 1];
                h.value = D;
            }
            function b() {
                const D = this.stack[this.stack.length - 1];
                if (f("inReference")) D.type += "Reference", D.referenceType = f("referenceType") || "shortcut",
                delete D.url, delete D.title; else delete D.identifier, delete D.label;
                Z("referenceType");
            }
            function B() {
                const D = this.stack[this.stack.length - 1];
                if (f("inReference")) D.type += "Reference", D.referenceType = f("referenceType") || "shortcut",
                delete D.url, delete D.title; else delete D.identifier, delete D.label;
                Z("referenceType");
            }
            function Y(D) {
                const h = this.stack[this.stack.length - 2], z = this.sliceSerialize(D);
                h.label = (0, q.decodeString)(z), h.identifier = (0, Q.normalizeIdentifier)(z).toLowerCase();
            }
            function R() {
                const D = this.stack[this.stack.length - 1], h = this.resume(), z = this.stack[this.stack.length - 1];
                if (Z("inReference", true), z.type === "link") z.children = D.children; else z.alt = h;
            }
            function V() {
                const D = this.resume(), h = this.stack[this.stack.length - 1];
                h.url = D;
            }
            function i() {
                const D = this.resume(), h = this.stack[this.stack.length - 1];
                h.title = D;
            }
            function g() {
                Z("inReference");
            }
            function N() {
                Z("referenceType", "collapsed");
            }
            function kN(D) {
                const h = this.resume(), z = this.stack[this.stack.length - 1];
                z.label = h, z.identifier = (0, Q.normalizeIdentifier)(this.sliceSerialize(D)).toLowerCase(),
                Z("referenceType", "full");
            }
            function Ar(D) {
                Z("characterReferenceType", D.type);
            }
            function qk(D) {
                const h = this.sliceSerialize(D), z = f("characterReferenceType");
                let j;
                if (z) j = (0, A.decodeNumericCharacterReference)(h, z === "characterReferenceMarkerNumeric" ? 10 : 16),
                Z("characterReferenceType"); else j = (0, I.decodeNamedCharacterReference)(h);
                const F = this.stack.pop();
                F.value += j, F.position.end = s(D.end);
            }
            function xk(D) {
                W.call(this, D);
                const h = this.stack[this.stack.length - 1];
                h.url = this.sliceSerialize(D);
            }
            function LD(D) {
                W.call(this, D);
                const h = this.stack[this.stack.length - 1];
                h.url = "mailto:" + this.sliceSerialize(D);
            }
            function hO() {
                return {
                    type: "blockquote",
                    children: []
                };
            }
            function VB() {
                return {
                    type: "code",
                    lang: null,
                    meta: null,
                    value: ""
                };
            }
            function zi() {
                return {
                    type: "inlineCode",
                    value: ""
                };
            }
            function dj() {
                return {
                    type: "definition",
                    identifier: "",
                    label: null,
                    title: null,
                    url: ""
                };
            }
            function Su() {
                return {
                    type: "emphasis",
                    children: []
                };
            }
            function Cv() {
                return {
                    type: "heading",
                    depth: void 0,
                    children: []
                };
            }
            function Oq() {
                return {
                    type: "break"
                };
            }
            function rB() {
                return {
                    type: "html",
                    value: ""
                };
            }
            function KU() {
                return {
                    type: "image",
                    title: null,
                    url: "",
                    alt: null
                };
            }
            function BW() {
                return {
                    type: "link",
                    title: null,
                    url: "",
                    children: []
                };
            }
            function yi(D) {
                return {
                    type: "list",
                    ordered: D.type === "listOrdered",
                    start: null,
                    spread: D._spread,
                    children: []
                };
            }
            function mX(D) {
                return {
                    type: "listItem",
                    spread: D._spread,
                    checked: null,
                    children: []
                };
            }
            function ol() {
                return {
                    type: "paragraph",
                    children: []
                };
            }
            function tR() {
                return {
                    type: "strong",
                    children: []
                };
            }
            function An() {
                return {
                    type: "text",
                    value: ""
                };
            }
            function qe() {
                return {
                    type: "thematicBreak"
                };
            }
        }
        function L(D, h) {
            let z = -1;
            while (++z < h.length) {
                const j = h[z];
                if (Array.isArray(j)) L(D, j); else P(D, j);
            }
            return D;
        }
        function P(D, h) {
            let z;
            for (z in h) if (X.call(h, z)) {
                const j = z === "canContainEols" || z === "transforms", F = X.call(D, z) ? D[z] : void 0, l = F || (D[z] = j ? [] : {}), Z = h[z];
                if (Z) if (j) D[z] = [ ...l, ...Z ]; else Object.assign(l, Z);
            }
        }
        function x(D, h) {
            if (D) throw new Error("Cannot close `" + D.type + "` (" + (0, E.stringifyPosition)({
                start: D.start,
                end: D.end
            }) + "): a different token (`" + h.type + "`, " + (0, E.stringifyPosition)({
                start: h.start,
                end: h.end
            }) + ") is open"); else throw new Error("Cannot close document, a token (`" + h.type + "`, " + (0,
            E.stringifyPosition)({
                start: h.start,
                end: h.end
            }) + ") is still open");
        }
        z.fromMarkdown = f;
    }, {
        "decode-named-character-reference": 4,
        "mdast-util-to-string": 62,
        "micromark-util-decode-numeric-character-reference": 96,
        "micromark-util-decode-string": 97,
        "micromark-util-normalize-identifier": 99,
        "micromark/lib/parse.js": 108,
        "micromark/lib/postprocess.js": 109,
        "micromark/lib/preprocess.js": 110,
        "unist-util-stringify-position": 124
    } ],
    13: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), Object.defineProperty(z, "phrasing", {
            enumerable: true,
            get: function() {
                return j.phrasing;
            }
        });
        var j = D("k8");
    }, {
        k8: 14
    } ],
    14: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.phrasing = void 0;
        var j = D("unist-util-is");
        const F = (0, j.convert)([ "break", "delete", "emphasis", "footnote", "footnoteReference", "image", "imageReference", "inlineCode", "link", "linkReference", "strong", "text" ]);
        z.phrasing = F;
    }, {
        "unist-util-is": 123
    } ],
    15: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), Object.defineProperty(z, "defaultHandlers", {
            enumerable: true,
            get: function() {
                return F.handle;
            }
        }), Object.defineProperty(z, "toMarkdown", {
            enumerable: true,
            get: function() {
                return j.toMarkdown;
            }
        });
        var j = D("k8"), F = D("hP");
    }, {
        hP: 26,
        k8: 37
    } ],
    16: [ function(D, h, z) {
        "use strict";
        function j(D, h) {
            let z = -1, F;
            if (h.extensions) while (++z < h.extensions.length) j(D, h.extensions[z]);
            for (F in h) if (F === "extensions") ; else if (F === "unsafe" || F === "join") D[F] = [ ...D[F] || [], ...h[F] || [] ]; else if (F === "handlers") D[F] = Object.assign(D[F], h[F] || {}); else D.options[F] = h[F];
            return D;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.configure = j;
    }, {} ],
    17: [ function(D, h, z) {
        "use strict";
        function j(D, h, z, j) {
            const l = z.enter("blockquote"), Z = z.createTracker(j);
            Z.move("> "), Z.shift(2);
            const A = z.indentLines(z.containerFlow(D, Z.current()), F);
            return l(), A;
        }
        function F(D, h, z) {
            return ">" + (z ? "" : " ") + D;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.blockquote = j;
    }, {} ],
    18: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.hardBreak = F;
        var j = D("NQ");
        function F(D, h, z, F) {
            let l = -1;
            while (++l < z.unsafe.length) if (z.unsafe[l].character === "\n" && (0, j.patternInScope)(z.stack, z.unsafe[l])) return /[ \t]/.test(F.before) ? "" : " ";
            return "\\\n";
        }
    }, {
        NQ: 59
    } ],
    19: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.code = Z;
        var j = D("longest-streak"), F = D("rf"), l = D("Ai");
        function Z(D, h, z, Z) {
            const q = (0, l.checkFence)(z), Q = D.value || "", I = q === "`" ? "GraveAccent" : "Tilde";
            if ((0, F.formatCodeAsIndented)(D, z)) {
                const D = z.enter("codeIndented"), h = z.indentLines(Q, A);
                return D(), h;
            }
            const E = z.createTracker(Z), X = q.repeat(Math.max((0, j.longestStreak)(Q, q) + 1, 3)), f = z.enter("codeFenced");
            let s = E.move(X);
            if (D.lang) {
                const h = z.enter(`codeFencedLang${I}`);
                s += E.move(z.safe(D.lang, {
                    before: s,
                    after: " ",
                    encode: [ "`" ],
                    ...E.current()
                })), h();
            }
            if (D.lang && D.meta) {
                const h = z.enter(`codeFencedMeta${I}`);
                s += E.move(" "), s += E.move(z.safe(D.meta, {
                    before: s,
                    after: "\n",
                    encode: [ "`" ],
                    ...E.current()
                })), h();
            }
            if (s += E.move("\n"), Q) s += E.move(Q + "\n");
            return s += E.move(X), f(), s;
        }
        function A(D, h, z) {
            return (z ? "" : "    ") + D;
        }
    }, {
        Ai: 46,
        rf: 54,
        "longest-streak": 9
    } ],
    20: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.definition = F;
        var j = D("Cp");
        function F(D, h, z, F) {
            const l = (0, j.checkQuote)(z), Z = l === '"' ? "Quote" : "Apostrophe", A = z.enter("definition");
            let q = z.enter("label");
            const Q = z.createTracker(F);
            let I = Q.move("[");
            if (I += Q.move(z.safe(z.associationId(D), {
                before: I,
                after: "]",
                ...Q.current()
            })), I += Q.move("]: "), q(), !D.url || /[\0- \u007F]/.test(D.url)) q = z.enter("destinationLiteral"),
            I += Q.move("<"), I += Q.move(z.safe(D.url, {
                before: I,
                after: ">",
                ...Q.current()
            })), I += Q.move(">"); else q = z.enter("destinationRaw"), I += Q.move(z.safe(D.url, {
                before: I,
                after: D.title ? " " : "\n",
                ...Q.current()
            }));
            if (q(), D.title) q = z.enter(`title${Z}`), I += Q.move(" " + l), I += Q.move(z.safe(D.title, {
                before: I,
                after: l,
                ...Q.current()
            })), I += Q.move(l), q();
            return A(), I;
        }
    }, {
        Cp: 48
    } ],
    21: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.emphasis = F;
        var j = D("Jd");
        function F(D, h, z, F) {
            const l = (0, j.checkEmphasis)(z), Z = z.enter("emphasis"), A = z.createTracker(F);
            let q = A.move(l);
            return q += A.move(z.containerPhrasing(D, {
                before: q,
                after: l,
                ...A.current()
            })), q += A.move(l), Z(), q;
        }
        function l(D, h, z) {
            return z.options.emphasis || "*";
        }
        F.peek = l;
    }, {
        Jd: 45
    } ],
    22: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.heading = F;
        var j = D("Pj");
        function F(D, h, z, F) {
            const l = Math.max(Math.min(6, D.depth || 1), 1), Z = z.createTracker(F);
            if ((0, j.formatHeadingAsSetext)(D, z)) {
                const h = z.enter("headingSetext"), j = z.enter("phrasing"), F = z.containerPhrasing(D, {
                    ...Z.current(),
                    before: "\n",
                    after: "\n"
                });
                return j(), h(), F + "\n" + (l === 1 ? "=" : "-").repeat(F.length - (Math.max(F.lastIndexOf("\r"), F.lastIndexOf("\n")) + 1));
            }
            const A = "#".repeat(l), q = z.enter("headingAtx"), Q = z.enter("phrasing");
            Z.move(A + " ");
            let I = z.containerPhrasing(D, {
                before: "# ",
                after: "\n",
                ...Z.current()
            });
            if (/^[\t ]/.test(I)) I = "&#x" + I.charCodeAt(0).toString(16).toUpperCase() + ";" + I.slice(1);
            if (I = I ? A + " " + I : A, z.options.closeAtx) I += " " + A;
            return Q(), q(), I;
        }
    }, {
        Pj: 55
    } ],
    23: [ function(D, h, z) {
        "use strict";
        function j(D) {
            return D.value || "";
        }
        function F() {
            return "<";
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.html = j, j.peek = F;
    }, {} ],
    24: [ function(D, h, z) {
        "use strict";
        function j(D, h, z, j) {
            const F = D.referenceType, l = z.enter("imageReference");
            let Z = z.enter("label");
            const A = z.createTracker(j);
            let q = A.move("![");
            const Q = z.safe(D.alt, {
                before: q,
                after: "]",
                ...A.current()
            });
            q += A.move(Q + "]["), Z();
            const I = z.stack;
            z.stack = [], Z = z.enter("reference");
            const E = z.safe(z.associationId(D), {
                before: q,
                after: "]",
                ...A.current()
            });
            if (Z(), z.stack = I, l(), F === "full" || !Q || Q !== E) q += A.move(E + "]"); else if (F === "shortcut") q = q.slice(0, -1); else q += A.move("]");
            return q;
        }
        function F() {
            return "!";
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.imageReference = j, j.peek = F;
    }, {} ],
    25: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.image = F;
        var j = D("Cp");
        function F(D, h, z, F) {
            const l = (0, j.checkQuote)(z), Z = l === '"' ? "Quote" : "Apostrophe", A = z.enter("image");
            let q = z.enter("label");
            const Q = z.createTracker(F);
            let I = Q.move("![");
            if (I += Q.move(z.safe(D.alt, {
                before: I,
                after: "]",
                ...Q.current()
            })), I += Q.move("]("), q(), !D.url && D.title || /[\0- \u007F]/.test(D.url)) q = z.enter("destinationLiteral"),
            I += Q.move("<"), I += Q.move(z.safe(D.url, {
                before: I,
                after: ">",
                ...Q.current()
            })), I += Q.move(">"); else q = z.enter("destinationRaw"), I += Q.move(z.safe(D.url, {
                before: I,
                after: D.title ? " " : ")",
                ...Q.current()
            }));
            if (q(), D.title) q = z.enter(`title${Z}`), I += Q.move(" " + l), I += Q.move(z.safe(D.title, {
                before: I,
                after: l,
                ...Q.current()
            })), I += Q.move(l), q();
            return I += Q.move(")"), A(), I;
        }
        function l() {
            return "!";
        }
        F.peek = l;
    }, {
        Cp: 48
    } ],
    26: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.handle = void 0;
        var j = D("Dp"), F = D("aP"), l = D("uN"), Z = D("JW"), A = D("9C"), q = D("ja"), Q = D("2P"), I = D("Zq"), E = D("MV"), X = D("To"), f = D("5f"), s = D("Cr"), L = D("sp"), P = D("Eo"), x = D("zW"), n = D("os"), w = D("js"), J = D("Qa"), a = D("k7");
        const d = {
            blockquote: j.blockquote,
            break: F.hardBreak,
            code: l.code,
            definition: Z.definition,
            emphasis: A.emphasis,
            hardBreak: F.hardBreak,
            heading: q.heading,
            html: Q.html,
            image: I.image,
            imageReference: E.imageReference,
            inlineCode: X.inlineCode,
            link: f.link,
            linkReference: s.linkReference,
            list: L.list,
            listItem: P.listItem,
            paragraph: x.paragraph,
            root: n.root,
            strong: w.strong,
            text: J.text,
            thematicBreak: a.thematicBreak
        };
        z.handle = d;
    }, {
        Dp: 17,
        aP: 18,
        uN: 19,
        JW: 20,
        "9C": 21,
        ja: 22,
        "2P": 23,
        MV: 24,
        Zq: 25,
        To: 27,
        Cr: 28,
        "5f": 29,
        Eo: 30,
        sp: 31,
        zW: 32,
        os: 33,
        js: 34,
        Qa: 35,
        k7: 36
    } ],
    27: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.inlineCode = F;
        var j = D("xG");
        function F(D, h, z) {
            let F = D.value || "", l = "`", Z = -1;
            while (new RegExp("(^|[^`])" + l + "([^`]|$)").test(F)) l += "`";
            if (/[^ \r\n]/.test(F) && (/^[ \r\n]/.test(F) && /[ \r\n]$/.test(F) || /^`|`$/.test(F))) F = " " + F + " ";
            while (++Z < z.unsafe.length) {
                const D = z.unsafe[Z], h = (0, j.patternCompile)(D);
                let l;
                if (!D.atBreak) continue;
                while (l = h.exec(F)) {
                    let D = l.index;
                    if (F.charCodeAt(D) === 10 && F.charCodeAt(D - 1) === 13) D--;
                    F = F.slice(0, D) + " " + F.slice(l.index + 1);
                }
            }
            return l + F + l;
        }
        function l() {
            return "`";
        }
        F.peek = l;
    }, {
        xG: 58
    } ],
    28: [ function(D, h, z) {
        "use strict";
        function j(D, h, z, j) {
            const F = D.referenceType, l = z.enter("linkReference");
            let Z = z.enter("label");
            const A = z.createTracker(j);
            let q = A.move("[");
            const Q = z.containerPhrasing(D, {
                before: q,
                after: "]",
                ...A.current()
            });
            q += A.move(Q + "]["), Z();
            const I = z.stack;
            z.stack = [], Z = z.enter("reference");
            const E = z.safe(z.associationId(D), {
                before: q,
                after: "]",
                ...A.current()
            });
            if (Z(), z.stack = I, l(), F === "full" || !Q || Q !== E) q += A.move(E + "]"); else if (F === "shortcut") q = q.slice(0, -1); else q += A.move("]");
            return q;
        }
        function F() {
            return "[";
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.linkReference = j, j.peek = F;
    }, {} ],
    29: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.link = l;
        var j = D("Cp"), F = D("Yo");
        function l(D, h, z, l) {
            const Z = (0, j.checkQuote)(z), A = Z === '"' ? "Quote" : "Apostrophe", q = z.createTracker(l);
            let Q, I;
            if ((0, F.formatLinkAsAutolink)(D, z)) {
                const h = z.stack;
                z.stack = [], Q = z.enter("autolink");
                let j = q.move("<");
                return j += q.move(z.containerPhrasing(D, {
                    before: j,
                    after: ">",
                    ...q.current()
                })), j += q.move(">"), Q(), z.stack = h, j;
            }
            Q = z.enter("link"), I = z.enter("label");
            let E = q.move("[");
            if (E += q.move(z.containerPhrasing(D, {
                before: E,
                after: "](",
                ...q.current()
            })), E += q.move("]("), I(), !D.url && D.title || /[\0- \u007F]/.test(D.url)) I = z.enter("destinationLiteral"),
            E += q.move("<"), E += q.move(z.safe(D.url, {
                before: E,
                after: ">",
                ...q.current()
            })), E += q.move(">"); else I = z.enter("destinationRaw"), E += q.move(z.safe(D.url, {
                before: E,
                after: D.title ? " " : ")",
                ...q.current()
            }));
            if (I(), D.title) I = z.enter(`title${A}`), E += q.move(" " + Z), E += q.move(z.safe(D.title, {
                before: E,
                after: Z,
                ...q.current()
            })), E += q.move(Z), I();
            return E += q.move(")"), Q(), E;
        }
        function Z(D, h, z) {
            return (0, F.formatLinkAsAutolink)(D, z) ? "<" : "[";
        }
        l.peek = Z;
    }, {
        Cp: 48,
        Yo: 56
    } ],
    30: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.listItem = l;
        var j = D("QY"), F = D("f5");
        function l(D, h, z, l) {
            const Z = (0, F.checkListItemIndent)(z);
            let A = z.bulletCurrent || (0, j.checkBullet)(z);
            if (h && h.type === "list" && h.ordered) A = (typeof h.start === "number" && h.start > -1 ? h.start : 1) + (z.options.incrementListMarker === false ? 0 : h.children.indexOf(D)) + A;
            let q = A.length + 1;
            if (Z === "tab" || Z === "mixed" && (h && h.type === "list" && h.spread || D.spread)) q = Math.ceil(q / 4) * 4;
            const Q = z.createTracker(l);
            Q.move(A + " ".repeat(q - A.length)), Q.shift(q);
            const I = z.enter("listItem"), E = z.indentLines(z.containerFlow(D, Q.current()), X);
            return I(), E;
            function X(D, h, z) {
                if (h) return (z ? "" : " ".repeat(q)) + D;
                return (z ? A : A + " ".repeat(q - A.length)) + D;
            }
        }
    }, {
        QY: 44,
        f5: 47
    } ],
    31: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.list = q;
        var j = D("QY"), F = D("pN"), l = D("tZ"), Z = D("hh"), A = D("Pt");
        function q(D, h, z, q) {
            const Q = z.enter("list"), I = z.bulletCurrent;
            let E = D.ordered ? (0, l.checkBulletOrdered)(z) : (0, j.checkBullet)(z);
            const X = D.ordered ? (0, Z.checkBulletOrderedOther)(z) : (0, F.checkBulletOther)(z), f = z.bulletLastUsed;
            let s = false;
            if (h && (D.ordered ? z.options.bulletOrderedOther : z.options.bulletOther) && f && E === f) s = true;
            if (!D.ordered) {
                const h = D.children ? D.children[0] : void 0;
                if ((E === "*" || E === "-") && h && (!h.children || !h.children[0]) && z.stack[z.stack.length - 1] === "list" && z.stack[z.stack.length - 2] === "listItem" && z.stack[z.stack.length - 3] === "list" && z.stack[z.stack.length - 4] === "listItem" && z.indexStack[z.indexStack.length - 1] === 0 && z.indexStack[z.indexStack.length - 2] === 0 && z.indexStack[z.indexStack.length - 3] === 0) s = true;
                if ((0, A.checkRule)(z) === E && h) {
                    let h = -1;
                    while (++h < D.children.length) {
                        const z = D.children[h];
                        if (z && z.type === "listItem" && z.children && z.children[0] && z.children[0].type === "thematicBreak") {
                            s = true;
                            break;
                        }
                    }
                }
            }
            if (s) E = X;
            z.bulletCurrent = E;
            const L = z.containerFlow(D, q);
            return z.bulletLastUsed = E, z.bulletCurrent = I, Q(), L;
        }
    }, {
        hh: 41,
        tZ: 42,
        pN: 43,
        QY: 44,
        Pt: 50
    } ],
    32: [ function(D, h, z) {
        "use strict";
        function j(D, h, z, j) {
            const F = z.enter("paragraph"), l = z.enter("phrasing"), Z = z.containerPhrasing(D, j);
            return l(), F(), Z;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.paragraph = j;
    }, {} ],
    33: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.root = F;
        var j = D("mdast-util-phrasing");
        function F(D, h, z, F) {
            const l = D.children.some((D => (0, j.phrasing)(D))), Z = l ? z.containerPhrasing : z.containerFlow;
            return Z.call(z, D, F);
        }
    }, {
        "mdast-util-phrasing": 13
    } ],
    34: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.strong = F;
        var j = D("UE");
        function F(D, h, z, F) {
            const l = (0, j.checkStrong)(z), Z = z.enter("strong"), A = z.createTracker(F);
            let q = A.move(l + l);
            return q += A.move(z.containerPhrasing(D, {
                before: q,
                after: l,
                ...A.current()
            })), q += A.move(l + l), Z(), q;
        }
        function l(D, h, z) {
            return z.options.strong || "*";
        }
        F.peek = l;
    }, {
        UE: 51
    } ],
    35: [ function(D, h, z) {
        "use strict";
        function j(D, h, z, j) {
            return z.safe(D.value, j);
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.text = j;
    }, {} ],
    36: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.thematicBreak = l;
        var j = D("VF"), F = D("Pt");
        function l(D, h, z) {
            const l = ((0, F.checkRule)(z) + (z.options.ruleSpaces ? " " : "")).repeat((0, j.checkRuleRepetition)(z));
            return z.options.ruleSpaces ? l.slice(0, -1) : l;
        }
    }, {
        VF: 49,
        Pt: 50
    } ],
    37: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.toMarkdown = s;
        var j = D("zwitch"), F = D("hq"), l = D("Ti"), Z = D("eu"), A = D("CH"), q = D("pw"), Q = D("gD"), I = D("zw"), E = D("4O"), X = D("SV"), f = D("wQ");
        function s(D, h = {}) {
            const z = {
                enter: I,
                indentLines: E.indentLines,
                associationId: q.association,
                containerPhrasing: n,
                containerFlow: w,
                createTracker: f.track,
                safe: J,
                stack: [],
                unsafe: [],
                join: [],
                handlers: {},
                options: {},
                indexStack: [],
                handle: void 0
            };
            if ((0, F.configure)(z, {
                unsafe: A.unsafe,
                join: Z.join,
                handlers: l.handle
            }), (0, F.configure)(z, h), z.options.tightDefinitions) (0, F.configure)(z, {
                join: [ x ]
            });
            z.handle = (0, j.zwitch)("type", {
                invalid: L,
                unknown: P,
                handlers: z.handlers
            });
            let Q = z.handle(D, void 0, z, {
                before: "\n",
                after: "\n",
                now: {
                    line: 1,
                    column: 1
                },
                lineShift: 0
            });
            if (Q && Q.charCodeAt(Q.length - 1) !== 10 && Q.charCodeAt(Q.length - 1) !== 13) Q += "\n";
            return Q;
            function I(D) {
                return z.stack.push(D), h;
                function h() {
                    z.stack.pop();
                }
            }
        }
        function L(D) {
            throw new Error("Cannot handle value `" + D + "`, expected node");
        }
        function P(D) {
            throw new Error("Cannot handle unknown node `" + D.type + "`");
        }
        function x(D, h) {
            if (D.type === "definition" && D.type === h.type) return 0;
        }
        function n(D, h) {
            return (0, Q.containerPhrasing)(D, this, h);
        }
        function w(D, h) {
            return (0, I.containerFlow)(D, this, h);
        }
        function J(D, h) {
            return (0, X.safe)(this, D, h);
        }
    }, {
        hq: 16,
        Ti: 26,
        eu: 38,
        CH: 39,
        pw: 40,
        zw: 52,
        gD: 53,
        "4O": 57,
        SV: 60,
        wQ: 61,
        zwitch: 152
    } ],
    38: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.join = void 0;
        var j = D("8F"), F = D("5K");
        const l = [ Z ];
        function Z(D, h, z, l) {
            if (h.type === "code" && (0, j.formatCodeAsIndented)(h, l) && (D.type === "list" || D.type === h.type && (0,
            j.formatCodeAsIndented)(D, l))) return false;
            if (D.type === "list" && D.type === h.type && Boolean(D.ordered) === Boolean(h.ordered) && !(D.ordered ? l.options.bulletOrderedOther : l.options.bulletOther)) return false;
            if ("spread" in z && typeof z.spread === "boolean") {
                if (D.type === "paragraph" && (D.type === h.type || h.type === "definition" || h.type === "heading" && (0,
                F.formatHeadingAsSetext)(h, l))) return;
                return z.spread ? 1 : 0;
            }
        }
        z.join = l;
    }, {
        "8F": 54,
        "5K": 55
    } ],
    39: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.unsafe = void 0;
        const j = [ "autolink", "destinationLiteral", "destinationRaw", "reference", "titleQuote", "titleApostrophe" ], F = [ {
            character: "\t",
            after: "[\\r\\n]",
            inConstruct: "phrasing"
        }, {
            character: "\t",
            before: "[\\r\\n]",
            inConstruct: "phrasing"
        }, {
            character: "\t",
            inConstruct: [ "codeFencedLangGraveAccent", "codeFencedLangTilde" ]
        }, {
            character: "\r",
            inConstruct: [ "codeFencedLangGraveAccent", "codeFencedLangTilde", "codeFencedMetaGraveAccent", "codeFencedMetaTilde", "destinationLiteral", "headingAtx" ]
        }, {
            character: "\n",
            inConstruct: [ "codeFencedLangGraveAccent", "codeFencedLangTilde", "codeFencedMetaGraveAccent", "codeFencedMetaTilde", "destinationLiteral", "headingAtx" ]
        }, {
            character: " ",
            after: "[\\r\\n]",
            inConstruct: "phrasing"
        }, {
            character: " ",
            before: "[\\r\\n]",
            inConstruct: "phrasing"
        }, {
            character: " ",
            inConstruct: [ "codeFencedLangGraveAccent", "codeFencedLangTilde" ]
        }, {
            character: "!",
            after: "\\[",
            inConstruct: "phrasing",
            notInConstruct: j
        }, {
            character: '"',
            inConstruct: "titleQuote"
        }, {
            atBreak: true,
            character: "#"
        }, {
            character: "#",
            inConstruct: "headingAtx",
            after: "(?:[\r\n]|$)"
        }, {
            character: "&",
            after: "[#A-Za-z]",
            inConstruct: "phrasing"
        }, {
            character: "'",
            inConstruct: "titleApostrophe"
        }, {
            character: "(",
            inConstruct: "destinationRaw"
        }, {
            before: "\\]",
            character: "(",
            inConstruct: "phrasing",
            notInConstruct: j
        }, {
            atBreak: true,
            before: "\\d+",
            character: ")"
        }, {
            character: ")",
            inConstruct: "destinationRaw"
        }, {
            atBreak: true,
            character: "*",
            after: "(?:[ \t\r\n*])"
        }, {
            character: "*",
            inConstruct: "phrasing",
            notInConstruct: j
        }, {
            atBreak: true,
            character: "+",
            after: "(?:[ \t\r\n])"
        }, {
            atBreak: true,
            character: "-",
            after: "(?:[ \t\r\n-])"
        }, {
            atBreak: true,
            before: "\\d+",
            character: ".",
            after: "(?:[ \t\r\n]|$)"
        }, {
            atBreak: true,
            character: "<",
            after: "[!/?A-Za-z]"
        }, {
            character: "<",
            after: "[!/?A-Za-z]",
            inConstruct: "phrasing",
            notInConstruct: j
        }, {
            character: "<",
            inConstruct: "destinationLiteral"
        }, {
            atBreak: true,
            character: "="
        }, {
            atBreak: true,
            character: ">"
        }, {
            character: ">",
            inConstruct: "destinationLiteral"
        }, {
            atBreak: true,
            character: "["
        }, {
            character: "[",
            inConstruct: "phrasing",
            notInConstruct: j
        }, {
            character: "[",
            inConstruct: [ "label", "reference" ]
        }, {
            character: "\\",
            after: "[\\r\\n]",
            inConstruct: "phrasing"
        }, {
            character: "]",
            inConstruct: [ "label", "reference" ]
        }, {
            atBreak: true,
            character: "_"
        }, {
            character: "_",
            inConstruct: "phrasing",
            notInConstruct: j
        }, {
            atBreak: true,
            character: "`"
        }, {
            character: "`",
            inConstruct: [ "codeFencedLangGraveAccent", "codeFencedMetaGraveAccent" ]
        }, {
            character: "`",
            inConstruct: "phrasing",
            notInConstruct: j
        }, {
            atBreak: true,
            character: "~"
        } ];
        z.unsafe = F;
    }, {} ],
    40: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.association = F;
        var j = D("micromark-util-decode-string");
        function F(D) {
            if (D.label || !D.identifier) return D.label || "";
            return (0, j.decodeString)(D.identifier);
        }
    }, {
        "micromark-util-decode-string": 97
    } ],
    41: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.checkBulletOrderedOther = F;
        var j = D("Nh");
        function F(D) {
            const h = (0, j.checkBulletOrdered)(D), z = D.options.bulletOrderedOther;
            if (!z) return h === "." ? ")" : ".";
            if (z !== "." && z !== ")") throw new Error("Cannot serialize items with `" + z + "` for `options.bulletOrderedOther`, expected `*`, `+`, or `-`");
            if (z === h) throw new Error("Expected `bulletOrdered` (`" + h + "`) and `bulletOrderedOther` (`" + z + "`) to be different");
            return z;
        }
    }, {
        Nh: 42
    } ],
    42: [ function(D, h, z) {
        "use strict";
        function j(D) {
            const h = D.options.bulletOrdered || ".";
            if (h !== "." && h !== ")") throw new Error("Cannot serialize items with `" + h + "` for `options.bulletOrdered`, expected `.` or `)`");
            return h;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.checkBulletOrdered = j;
    }, {} ],
    43: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.checkBulletOther = F;
        var j = D("1W");
        function F(D) {
            const h = (0, j.checkBullet)(D), z = D.options.bulletOther;
            if (!z) return h === "*" ? "-" : "*";
            if (z !== "*" && z !== "+" && z !== "-") throw new Error("Cannot serialize items with `" + z + "` for `options.bulletOther`, expected `*`, `+`, or `-`");
            if (z === h) throw new Error("Expected `bullet` (`" + h + "`) and `bulletOther` (`" + z + "`) to be different");
            return z;
        }
    }, {
        "1W": 44
    } ],
    44: [ function(D, h, z) {
        "use strict";
        function j(D) {
            const h = D.options.bullet || "*";
            if (h !== "*" && h !== "+" && h !== "-") throw new Error("Cannot serialize items with `" + h + "` for `options.bullet`, expected `*`, `+`, or `-`");
            return h;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.checkBullet = j;
    }, {} ],
    45: [ function(D, h, z) {
        "use strict";
        function j(D) {
            const h = D.options.emphasis || "*";
            if (h !== "*" && h !== "_") throw new Error("Cannot serialize emphasis with `" + h + "` for `options.emphasis`, expected `*`, or `_`");
            return h;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.checkEmphasis = j;
    }, {} ],
    46: [ function(D, h, z) {
        "use strict";
        function j(D) {
            const h = D.options.fence || "`";
            if (h !== "`" && h !== "~") throw new Error("Cannot serialize code with `" + h + "` for `options.fence`, expected `` ` `` or `~`");
            return h;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.checkFence = j;
    }, {} ],
    47: [ function(D, h, z) {
        "use strict";
        function j(D) {
            const h = D.options.listItemIndent || "tab";
            if (h === 1 || h === "1") return "one";
            if (h !== "tab" && h !== "one" && h !== "mixed") throw new Error("Cannot serialize items with `" + h + "` for `options.listItemIndent`, expected `tab`, `one`, or `mixed`");
            return h;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.checkListItemIndent = j;
    }, {} ],
    48: [ function(D, h, z) {
        "use strict";
        function j(D) {
            const h = D.options.quote || '"';
            if (h !== '"' && h !== "'") throw new Error("Cannot serialize title with `" + h + "` for `options.quote`, expected `\"`, or `'`");
            return h;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.checkQuote = j;
    }, {} ],
    49: [ function(D, h, z) {
        "use strict";
        function j(D) {
            const h = D.options.ruleRepetition || 3;
            if (h < 3) throw new Error("Cannot serialize rules with repetition `" + h + "` for `options.ruleRepetition`, expected `3` or more");
            return h;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.checkRuleRepetition = j;
    }, {} ],
    50: [ function(D, h, z) {
        "use strict";
        function j(D) {
            const h = D.options.rule || "*";
            if (h !== "*" && h !== "-" && h !== "_") throw new Error("Cannot serialize rules with `" + h + "` for `options.rule`, expected `*`, `-`, or `_`");
            return h;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.checkRule = j;
    }, {} ],
    51: [ function(D, h, z) {
        "use strict";
        function j(D) {
            const h = D.options.strong || "*";
            if (h !== "*" && h !== "_") throw new Error("Cannot serialize strong with `" + h + "` for `options.strong`, expected `*`, or `_`");
            return h;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.checkStrong = j;
    }, {} ],
    52: [ function(D, h, z) {
        "use strict";
        function j(D, h, z) {
            const j = h.indexStack, l = D.children || [], Z = h.createTracker(z), A = [];
            let q = -1;
            j.push(-1);
            while (++q < l.length) {
                const z = l[q];
                if (j[j.length - 1] = q, A.push(Z.move(h.handle(z, D, h, {
                    before: "\n",
                    after: "\n",
                    ...Z.current()
                }))), z.type !== "list") h.bulletLastUsed = void 0;
                if (q < l.length - 1) A.push(Z.move(F(z, l[q + 1], D, h)));
            }
            return j.pop(), A.join("");
        }
        function F(D, h, z, j) {
            let F = j.join.length;
            while (F--) {
                const l = j.join[F](D, h, z, j);
                if (l === true || l === 1) break;
                if (typeof l === "number") return "\n".repeat(1 + l);
                if (l === false) return "\n\n\x3c!----\x3e\n\n";
            }
            return "\n\n";
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.containerFlow = j;
    }, {} ],
    53: [ function(D, h, z) {
        "use strict";
        function j(D, h, z) {
            const j = h.indexStack, F = D.children || [], l = [];
            let Z = -1, A = z.before;
            j.push(-1);
            let q = h.createTracker(z);
            while (++Z < F.length) {
                const Q = F[Z];
                let I;
                if (j[j.length - 1] = Z, Z + 1 < F.length) {
                    let z = h.handle.handlers[F[Z + 1].type];
                    if (z && z.peek) z = z.peek;
                    I = z ? z(F[Z + 1], D, h, {
                        before: "",
                        after: "",
                        ...q.current()
                    }).charAt(0) : "";
                } else I = z.after;
                if (l.length > 0 && (A === "\r" || A === "\n") && Q.type === "html") l[l.length - 1] = l[l.length - 1].replace(/(\r?\n|\r)$/, " "),
                A = " ", q = h.createTracker(z), q.move(l.join(""));
                l.push(q.move(h.handle(Q, D, h, {
                    ...q.current(),
                    before: A,
                    after: I
                }))), A = l[l.length - 1].slice(-1);
            }
            return j.pop(), l.join("");
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.containerPhrasing = j;
    }, {} ],
    54: [ function(D, h, z) {
        "use strict";
        function j(D, h) {
            return Boolean(!h.options.fences && D.value && !D.lang && /[^ \r\n]/.test(D.value) && !/^[\t ]*(?:[\r\n]|$)|(?:^|[\r\n])[\t ]*$/.test(D.value));
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.formatCodeAsIndented = j;
    }, {} ],
    55: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.formatHeadingAsSetext = l;
        var j = D("unist-util-visit"), F = D("mdast-util-to-string");
        function l(D, h) {
            let z = false;
            return (0, j.visit)(D, (D => {
                if ("value" in D && /\r?\n|\r/.test(D.value) || D.type === "break") return z = true,
                j.EXIT;
            })), Boolean((!D.depth || D.depth < 3) && (0, F.toString)(D) && (h.options.setext || z));
        }
    }, {
        "mdast-util-to-string": 62,
        "unist-util-visit": 127
    } ],
    56: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.formatLinkAsAutolink = F;
        var j = D("mdast-util-to-string");
        function F(D, h) {
            const z = (0, j.toString)(D);
            return Boolean(!h.options.resourceLink && D.url && !D.title && D.children && D.children.length === 1 && D.children[0].type === "text" && (z === D.url || "mailto:" + z === D.url) && /^[a-z][a-z+.-]+:/i.test(D.url) && !/[\0- <>\u007F]/.test(D.url));
        }
    }, {
        "mdast-util-to-string": 62
    } ],
    57: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.indentLines = F;
        const j = /\r?\n|\r/g;
        function F(D, h) {
            const z = [];
            let F = 0, l = 0, Z;
            while (Z = j.exec(D)) A(D.slice(F, Z.index)), z.push(Z[0]), F = Z.index + Z[0].length,
            l++;
            return A(D.slice(F)), z.join("");
            function A(D) {
                z.push(h(D, l, !D));
            }
        }
    }, {} ],
    58: [ function(D, h, z) {
        "use strict";
        function j(D) {
            if (!D._compiled) {
                const h = (D.atBreak ? "[\\r\\n][\\t ]*" : "") + (D.before ? "(?:" + D.before + ")" : "");
                D._compiled = new RegExp((h ? "(" + h + ")" : "") + (/[|\\{}()[\]^$+*?.-]/.test(D.character) ? "\\" : "") + D.character + (D.after ? "(?:" + D.after + ")" : ""), "g");
            }
            return D._compiled;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.patternCompile = j;
    }, {} ],
    59: [ function(D, h, z) {
        "use strict";
        function j(D, h) {
            return F(D, h.inConstruct, true) && !F(D, h.notInConstruct, false);
        }
        function F(D, h, z) {
            if (typeof h === "string") h = [ h ];
            if (!h || h.length === 0) return z;
            let j = -1;
            while (++j < h.length) if (D.includes(h[j])) return true;
            return false;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.patternInScope = j;
    }, {} ],
    60: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.safe = l;
        var j = D("bk"), F = D("Bt");
        function l(D, h, z) {
            const l = (z.before || "") + (h || "") + (z.after || ""), q = [], Q = [], I = {};
            let E = -1;
            while (++E < D.unsafe.length) {
                const h = D.unsafe[E];
                if (!(0, F.patternInScope)(D.stack, h)) continue;
                const z = (0, j.patternCompile)(h);
                let Z;
                while (Z = z.exec(l)) {
                    const D = "before" in h || Boolean(h.atBreak), z = "after" in h, j = Z.index + (D ? Z[1].length : 0);
                    if (q.includes(j)) {
                        if (I[j].before && !D) I[j].before = false;
                        if (I[j].after && !z) I[j].after = false;
                    } else q.push(j), I[j] = {
                        before: D,
                        after: z
                    };
                }
            }
            q.sort(Z);
            let X = z.before ? z.before.length : 0;
            const f = l.length - (z.after ? z.after.length : 0);
            E = -1;
            while (++E < q.length) {
                const D = q[E];
                if (D < X || D >= f) continue;
                if (D + 1 < f && q[E + 1] === D + 1 && I[D].after && !I[D + 1].before && !I[D + 1].after || q[E - 1] === D - 1 && I[D].before && !I[D - 1].before && !I[D - 1].after) continue;
                if (X !== D) Q.push(A(l.slice(X, D), "\\"));
                if (X = D, /[!-/:-@[-`{-~]/.test(l.charAt(D)) && (!z.encode || !z.encode.includes(l.charAt(D)))) Q.push("\\"); else Q.push("&#x" + l.charCodeAt(D).toString(16).toUpperCase() + ";"),
                X++;
            }
            return Q.push(A(l.slice(X, f), z.after)), Q.join("");
        }
        function Z(D, h) {
            return D - h;
        }
        function A(D, h) {
            const z = /\\(?=[!-/:-@[-`{-~])/g, j = [], F = [], l = D + h;
            let Z = -1, A = 0, q;
            while (q = z.exec(l)) j.push(q.index);
            while (++Z < j.length) {
                if (A !== j[Z]) F.push(D.slice(A, j[Z]));
                F.push("\\"), A = j[Z];
            }
            return F.push(D.slice(A)), F.join("");
        }
    }, {
        bk: 58,
        Bt: 59
    } ],
    61: [ function(D, h, z) {
        "use strict";
        function j(D) {
            const h = D || {}, z = h.now || {};
            let j = h.lineShift || 0, F = z.line || 1, l = z.column || 1;
            return {
                move: q,
                current: Z,
                shift: A
            };
            function Z() {
                return {
                    now: {
                        line: F,
                        column: l
                    },
                    lineShift: j
                };
            }
            function A(D) {
                j += D;
            }
            function q(D) {
                const h = D || "", z = h.split(/\r?\n|\r/g), Z = z[z.length - 1];
                return F += z.length - 1, l = z.length === 1 ? l + Z.length : 1 + Z.length + j,
                h;
            }
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.track = j;
    }, {} ],
    62: [ function(D, h, z) {
        "use strict";
        function j(D, h) {
            var {includeImageAlt: z = true} = h || {};
            return F(D, z);
        }
        function F(D, h) {
            return D && typeof D === "object" && (D.value || (h ? D.alt : "") || "children" in D && l(D.children, h) || Array.isArray(D) && l(D, h)) || "";
        }
        function l(D, h) {
            var z = [], j = -1;
            while (++j < D.length) z[j] = F(D[j], h);
            return z.join("");
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.toString = j;
    }, {} ],
    63: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), Object.defineProperty(z, "attention", {
            enumerable: true,
            get: function() {
                return j.attention;
            }
        }), Object.defineProperty(z, "autolink", {
            enumerable: true,
            get: function() {
                return F.autolink;
            }
        }), Object.defineProperty(z, "blankLine", {
            enumerable: true,
            get: function() {
                return l.blankLine;
            }
        }), Object.defineProperty(z, "blockQuote", {
            enumerable: true,
            get: function() {
                return Z.blockQuote;
            }
        }), Object.defineProperty(z, "characterEscape", {
            enumerable: true,
            get: function() {
                return A.characterEscape;
            }
        }), Object.defineProperty(z, "characterReference", {
            enumerable: true,
            get: function() {
                return q.characterReference;
            }
        }), Object.defineProperty(z, "codeFenced", {
            enumerable: true,
            get: function() {
                return Q.codeFenced;
            }
        }), Object.defineProperty(z, "codeIndented", {
            enumerable: true,
            get: function() {
                return I.codeIndented;
            }
        }), Object.defineProperty(z, "codeText", {
            enumerable: true,
            get: function() {
                return E.codeText;
            }
        }), Object.defineProperty(z, "content", {
            enumerable: true,
            get: function() {
                return X.content;
            }
        }), Object.defineProperty(z, "definition", {
            enumerable: true,
            get: function() {
                return f.definition;
            }
        }), Object.defineProperty(z, "hardBreakEscape", {
            enumerable: true,
            get: function() {
                return s.hardBreakEscape;
            }
        }), Object.defineProperty(z, "headingAtx", {
            enumerable: true,
            get: function() {
                return L.headingAtx;
            }
        }), Object.defineProperty(z, "htmlFlow", {
            enumerable: true,
            get: function() {
                return P.htmlFlow;
            }
        }), Object.defineProperty(z, "htmlText", {
            enumerable: true,
            get: function() {
                return x.htmlText;
            }
        }), Object.defineProperty(z, "labelEnd", {
            enumerable: true,
            get: function() {
                return n.labelEnd;
            }
        }), Object.defineProperty(z, "labelStartImage", {
            enumerable: true,
            get: function() {
                return w.labelStartImage;
            }
        }), Object.defineProperty(z, "labelStartLink", {
            enumerable: true,
            get: function() {
                return J.labelStartLink;
            }
        }), Object.defineProperty(z, "lineEnding", {
            enumerable: true,
            get: function() {
                return a.lineEnding;
            }
        }), Object.defineProperty(z, "list", {
            enumerable: true,
            get: function() {
                return d.list;
            }
        }), Object.defineProperty(z, "setextUnderline", {
            enumerable: true,
            get: function() {
                return H.setextUnderline;
            }
        }), Object.defineProperty(z, "thematicBreak", {
            enumerable: true,
            get: function() {
                return K.thematicBreak;
            }
        });
        var j = D("IN"), F = D("vA"), l = D("wD"), Z = D("7c"), A = D("Y0"), q = D("i8"), Q = D("s2"), I = D("R8"), E = D("nm"), X = D("kR"), f = D("8p"), s = D("1c"), L = D("jF"), P = D("X1"), x = D("RN"), n = D("KB"), w = D("0o"), J = D("G3"), a = D("Ma"), d = D("Rz"), H = D("OS"), K = D("Vo");
    }, {
        IN: 64,
        vA: 65,
        wD: 66,
        "7c": 67,
        Y0: 68,
        i8: 69,
        s2: 70,
        R8: 71,
        nm: 72,
        kR: 73,
        "8p": 74,
        "1c": 75,
        jF: 76,
        X1: 77,
        RN: 78,
        KB: 79,
        "0o": 80,
        G3: 81,
        Ma: 82,
        Rz: 83,
        OS: 84,
        Vo: 85
    } ],
    64: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.attention = void 0;
        var j = D("micromark-util-chunked"), F = D("micromark-util-classify-character"), l = D("micromark-util-resolve-all");
        const Z = {
            name: "attention",
            tokenize: q,
            resolveAll: A
        };
        function A(D, h) {
            let z = -1, F, Z, A, q, I, E, X, f;
            while (++z < D.length) if (D[z][0] === "enter" && D[z][1].type === "attentionSequence" && D[z][1]._close) {
                F = z;
                while (F--) if (D[F][0] === "exit" && D[F][1].type === "attentionSequence" && D[F][1]._open && h.sliceSerialize(D[F][1]).charCodeAt(0) === h.sliceSerialize(D[z][1]).charCodeAt(0)) {
                    if ((D[F][1]._close || D[z][1]._open) && (D[z][1].end.offset - D[z][1].start.offset) % 3 && !((D[F][1].end.offset - D[F][1].start.offset + D[z][1].end.offset - D[z][1].start.offset) % 3)) continue;
                    E = D[F][1].end.offset - D[F][1].start.offset > 1 && D[z][1].end.offset - D[z][1].start.offset > 1 ? 2 : 1;
                    const s = Object.assign({}, D[F][1].end), L = Object.assign({}, D[z][1].start);
                    if (Q(s, -E), Q(L, E), q = {
                        type: E > 1 ? "strongSequence" : "emphasisSequence",
                        start: s,
                        end: Object.assign({}, D[F][1].end)
                    }, I = {
                        type: E > 1 ? "strongSequence" : "emphasisSequence",
                        start: Object.assign({}, D[z][1].start),
                        end: L
                    }, A = {
                        type: E > 1 ? "strongText" : "emphasisText",
                        start: Object.assign({}, D[F][1].end),
                        end: Object.assign({}, D[z][1].start)
                    }, Z = {
                        type: E > 1 ? "strong" : "emphasis",
                        start: Object.assign({}, q.start),
                        end: Object.assign({}, I.end)
                    }, D[F][1].end = Object.assign({}, q.start), D[z][1].start = Object.assign({}, I.end),
                    X = [], D[F][1].end.offset - D[F][1].start.offset) X = (0, j.push)(X, [ [ "enter", D[F][1], h ], [ "exit", D[F][1], h ] ]);
                    if (X = (0, j.push)(X, [ [ "enter", Z, h ], [ "enter", q, h ], [ "exit", q, h ], [ "enter", A, h ] ]),
                    X = (0, j.push)(X, (0, l.resolveAll)(h.parser.constructs.insideSpan.null, D.slice(F + 1, z), h)),
                    X = (0, j.push)(X, [ [ "exit", A, h ], [ "enter", I, h ], [ "exit", I, h ], [ "exit", Z, h ] ]),
                    D[z][1].end.offset - D[z][1].start.offset) f = 2, X = (0, j.push)(X, [ [ "enter", D[z][1], h ], [ "exit", D[z][1], h ] ]); else f = 0;
                    (0, j.splice)(D, F - 1, z - F + 3, X), z = F + X.length - f - 2;
                    break;
                }
            }
            z = -1;
            while (++z < D.length) if (D[z][1].type === "attentionSequence") D[z][1].type = "data";
            return D;
        }
        function q(D, h) {
            const z = this.parser.constructs.attentionMarkers.null, j = this.previous, l = (0,
            F.classifyCharacter)(j);
            let Z;
            return A;
            function A(h) {
                return D.enter("attentionSequence"), Z = h, q(h);
            }
            function q(A) {
                if (A === Z) return D.consume(A), q;
                const Q = D.exit("attentionSequence"), I = (0, F.classifyCharacter)(A), E = !I || I === 2 && l || z.includes(A), X = !l || l === 2 && I || z.includes(j);
                return Q._open = Boolean(Z === 42 ? E : E && (l || !X)), Q._close = Boolean(Z === 42 ? X : X && (I || !E)),
                h(A);
            }
        }
        function Q(D, h) {
            D.column += h, D.offset += h, D._bufferIndex += h;
        }
        z.attention = Z;
    }, {
        "micromark-util-chunked": 93,
        "micromark-util-classify-character": 94,
        "micromark-util-resolve-all": 100
    } ],
    65: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.autolink = void 0;
        var j = D("micromark-util-character");
        const F = {
            name: "autolink",
            tokenize: l
        };
        function l(D, h, z) {
            let F = 1;
            return l;
            function l(h) {
                return D.enter("autolink"), D.enter("autolinkMarker"), D.consume(h), D.exit("autolinkMarker"),
                D.enter("autolinkProtocol"), Z;
            }
            function Z(h) {
                if ((0, j.asciiAlpha)(h)) return D.consume(h), A;
                return (0, j.asciiAtext)(h) ? I(h) : z(h);
            }
            function A(D) {
                return D === 43 || D === 45 || D === 46 || (0, j.asciiAlphanumeric)(D) ? q(D) : I(D);
            }
            function q(h) {
                if (h === 58) return D.consume(h), Q;
                if ((h === 43 || h === 45 || h === 46 || (0, j.asciiAlphanumeric)(h)) && F++ < 32) return D.consume(h),
                q;
                return I(h);
            }
            function Q(h) {
                if (h === 62) return D.exit("autolinkProtocol"), s(h);
                if (h === null || h === 32 || h === 60 || (0, j.asciiControl)(h)) return z(h);
                return D.consume(h), Q;
            }
            function I(h) {
                if (h === 64) return D.consume(h), F = 0, E;
                if ((0, j.asciiAtext)(h)) return D.consume(h), I;
                return z(h);
            }
            function E(D) {
                return (0, j.asciiAlphanumeric)(D) ? X(D) : z(D);
            }
            function X(h) {
                if (h === 46) return D.consume(h), F = 0, E;
                if (h === 62) return D.exit("autolinkProtocol").type = "autolinkEmail", s(h);
                return f(h);
            }
            function f(h) {
                if ((h === 45 || (0, j.asciiAlphanumeric)(h)) && F++ < 63) return D.consume(h),
                h === 45 ? f : X;
                return z(h);
            }
            function s(z) {
                return D.enter("autolinkMarker"), D.consume(z), D.exit("autolinkMarker"), D.exit("autolink"),
                h;
            }
        }
        z.autolink = F;
    }, {
        "micromark-util-character": 91
    } ],
    66: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.blankLine = void 0;
        var j = D("micromark-factory-space"), F = D("micromark-util-character");
        const l = {
            tokenize: Z,
            partial: true
        };
        function Z(D, h, z) {
            return (0, j.factorySpace)(D, l, "linePrefix");
            function l(D) {
                return D === null || (0, F.markdownLineEnding)(D) ? h(D) : z(D);
            }
        }
        z.blankLine = l;
    }, {
        "micromark-factory-space": 88,
        "micromark-util-character": 91
    } ],
    67: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.blockQuote = void 0;
        var j = D("micromark-factory-space"), F = D("micromark-util-character");
        const l = {
            name: "blockQuote",
            tokenize: Z,
            continuation: {
                tokenize: A
            },
            exit: q
        };
        function Z(D, h, z) {
            const j = this;
            return l;
            function l(h) {
                if (h === 62) {
                    const z = j.containerState;
                    if (!z.open) D.enter("blockQuote", {
                        _container: true
                    }), z.open = true;
                    return D.enter("blockQuotePrefix"), D.enter("blockQuoteMarker"), D.consume(h), D.exit("blockQuoteMarker"),
                    Z;
                }
                return z(h);
            }
            function Z(z) {
                if ((0, F.markdownSpace)(z)) return D.enter("blockQuotePrefixWhitespace"), D.consume(z),
                D.exit("blockQuotePrefixWhitespace"), D.exit("blockQuotePrefix"), h;
                return D.exit("blockQuotePrefix"), h(z);
            }
        }
        function A(D, h, z) {
            return (0, j.factorySpace)(D, D.attempt(l, h, z), "linePrefix", this.parser.constructs.disable.null.includes("codeIndented") ? void 0 : 4);
        }
        function q(D) {
            D.exit("blockQuote");
        }
        z.blockQuote = l;
    }, {
        "micromark-factory-space": 88,
        "micromark-util-character": 91
    } ],
    68: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.characterEscape = void 0;
        var j = D("micromark-util-character");
        const F = {
            name: "characterEscape",
            tokenize: l
        };
        function l(D, h, z) {
            return F;
            function F(h) {
                return D.enter("characterEscape"), D.enter("escapeMarker"), D.consume(h), D.exit("escapeMarker"),
                l;
            }
            function l(F) {
                if ((0, j.asciiPunctuation)(F)) return D.enter("characterEscapeValue"), D.consume(F),
                D.exit("characterEscapeValue"), D.exit("characterEscape"), h;
                return z(F);
            }
        }
        z.characterEscape = F;
    }, {
        "micromark-util-character": 91
    } ],
    69: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.characterReference = void 0;
        var j = D("decode-named-character-reference"), F = D("micromark-util-character");
        const l = {
            name: "characterReference",
            tokenize: Z
        };
        function Z(D, h, z) {
            const l = this;
            let Z = 0, A, q;
            return Q;
            function Q(h) {
                return D.enter("characterReference"), D.enter("characterReferenceMarker"), D.consume(h),
                D.exit("characterReferenceMarker"), I;
            }
            function I(h) {
                if (h === 35) return D.enter("characterReferenceMarkerNumeric"), D.consume(h), D.exit("characterReferenceMarkerNumeric"),
                E;
                return D.enter("characterReferenceValue"), A = 31, q = F.asciiAlphanumeric, X(h);
            }
            function E(h) {
                if (h === 88 || h === 120) return D.enter("characterReferenceMarkerHexadecimal"),
                D.consume(h), D.exit("characterReferenceMarkerHexadecimal"), D.enter("characterReferenceValue"),
                A = 6, q = F.asciiHexDigit, X;
                return D.enter("characterReferenceValue"), A = 7, q = F.asciiDigit, X(h);
            }
            function X(Q) {
                let I;
                if (Q === 59 && Z) {
                    if (I = D.exit("characterReferenceValue"), q === F.asciiAlphanumeric && !(0, j.decodeNamedCharacterReference)(l.sliceSerialize(I))) return z(Q);
                    return D.enter("characterReferenceMarker"), D.consume(Q), D.exit("characterReferenceMarker"),
                    D.exit("characterReference"), h;
                }
                if (q(Q) && Z++ < A) return D.consume(Q), X;
                return z(Q);
            }
        }
        z.characterReference = l;
    }, {
        "decode-named-character-reference": 4,
        "micromark-util-character": 91
    } ],
    70: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.codeFenced = void 0;
        var j = D("micromark-factory-space"), F = D("micromark-util-character");
        const l = {
            name: "codeFenced",
            tokenize: Z,
            concrete: true
        };
        function Z(D, h, z) {
            const l = this, Z = {
                tokenize: H,
                partial: true
            }, A = {
                tokenize: d,
                partial: true
            }, q = this.events[this.events.length - 1], Q = q && q[1].type === "linePrefix" ? q[2].sliceSerialize(q[1], true).length : 0;
            let I = 0, E;
            return X;
            function X(h) {
                return D.enter("codeFenced"), D.enter("codeFencedFence"), D.enter("codeFencedFenceSequence"),
                E = h, f(h);
            }
            function f(h) {
                if (h === E) return D.consume(h), I++, f;
                return D.exit("codeFencedFenceSequence"), I < 3 ? z(h) : (0, j.factorySpace)(D, s, "whitespace")(h);
            }
            function s(h) {
                if (h === null || (0, F.markdownLineEnding)(h)) return n(h);
                return D.enter("codeFencedFenceInfo"), D.enter("chunkString", {
                    contentType: "string"
                }), L(h);
            }
            function L(h) {
                if (h === null || (0, F.markdownLineEndingOrSpace)(h)) return D.exit("chunkString"),
                D.exit("codeFencedFenceInfo"), (0, j.factorySpace)(D, P, "whitespace")(h);
                if (h === 96 && h === E) return z(h);
                return D.consume(h), L;
            }
            function P(h) {
                if (h === null || (0, F.markdownLineEnding)(h)) return n(h);
                return D.enter("codeFencedFenceMeta"), D.enter("chunkString", {
                    contentType: "string"
                }), x(h);
            }
            function x(h) {
                if (h === null || (0, F.markdownLineEnding)(h)) return D.exit("chunkString"), D.exit("codeFencedFenceMeta"),
                n(h);
                if (h === 96 && h === E) return z(h);
                return D.consume(h), x;
            }
            function n(z) {
                return D.exit("codeFencedFence"), l.interrupt ? h(z) : w(z);
            }
            function w(h) {
                if (h === null) return a(h);
                if ((0, F.markdownLineEnding)(h)) return D.attempt(A, D.attempt(Z, a, Q ? (0, j.factorySpace)(D, w, "linePrefix", Q + 1) : w), a)(h);
                return D.enter("codeFlowValue"), J(h);
            }
            function J(h) {
                if (h === null || (0, F.markdownLineEnding)(h)) return D.exit("codeFlowValue"),
                w(h);
                return D.consume(h), J;
            }
            function a(z) {
                return D.exit("codeFenced"), h(z);
            }
            function d(D, h, z) {
                const j = this;
                return F;
                function F(h) {
                    return D.enter("lineEnding"), D.consume(h), D.exit("lineEnding"), l;
                }
                function l(D) {
                    return j.parser.lazy[j.now().line] ? z(D) : h(D);
                }
            }
            function H(D, h, z) {
                let l = 0;
                return (0, j.factorySpace)(D, Z, "linePrefix", this.parser.constructs.disable.null.includes("codeIndented") ? void 0 : 4);
                function Z(h) {
                    return D.enter("codeFencedFence"), D.enter("codeFencedFenceSequence"), A(h);
                }
                function A(h) {
                    if (h === E) return D.consume(h), l++, A;
                    if (l < I) return z(h);
                    return D.exit("codeFencedFenceSequence"), (0, j.factorySpace)(D, q, "whitespace")(h);
                }
                function q(j) {
                    if (j === null || (0, F.markdownLineEnding)(j)) return D.exit("codeFencedFence"),
                    h(j);
                    return z(j);
                }
            }
        }
        z.codeFenced = l;
    }, {
        "micromark-factory-space": 88,
        "micromark-util-character": 91
    } ],
    71: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.codeIndented = void 0;
        var j = D("micromark-factory-space"), F = D("micromark-util-character");
        const l = {
            name: "codeIndented",
            tokenize: A
        };
        z.codeIndented = l;
        const Z = {
            tokenize: q,
            partial: true
        };
        function A(D, h, z) {
            const l = this;
            return A;
            function A(h) {
                return D.enter("codeIndented"), (0, j.factorySpace)(D, q, "linePrefix", 4 + 1)(h);
            }
            function q(D) {
                const h = l.events[l.events.length - 1];
                return h && h[1].type === "linePrefix" && h[2].sliceSerialize(h[1], true).length >= 4 ? Q(D) : z(D);
            }
            function Q(h) {
                if (h === null) return E(h);
                if ((0, F.markdownLineEnding)(h)) return D.attempt(Z, Q, E)(h);
                return D.enter("codeFlowValue"), I(h);
            }
            function I(h) {
                if (h === null || (0, F.markdownLineEnding)(h)) return D.exit("codeFlowValue"),
                Q(h);
                return D.consume(h), I;
            }
            function E(z) {
                return D.exit("codeIndented"), h(z);
            }
        }
        function q(D, h, z) {
            const l = this;
            return Z;
            function Z(h) {
                if (l.parser.lazy[l.now().line]) return z(h);
                if ((0, F.markdownLineEnding)(h)) return D.enter("lineEnding"), D.consume(h), D.exit("lineEnding"),
                Z;
                return (0, j.factorySpace)(D, A, "linePrefix", 4 + 1)(h);
            }
            function A(D) {
                const j = l.events[l.events.length - 1];
                return j && j[1].type === "linePrefix" && j[2].sliceSerialize(j[1], true).length >= 4 ? h(D) : (0,
                F.markdownLineEnding)(D) ? Z(D) : z(D);
            }
        }
    }, {
        "micromark-factory-space": 88,
        "micromark-util-character": 91
    } ],
    72: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.codeText = void 0;
        var j = D("micromark-util-character");
        const F = {
            name: "codeText",
            tokenize: A,
            resolve: l,
            previous: Z
        };
        function l(D) {
            let h = D.length - 4, z = 3, j, F;
            if ((D[z][1].type === "lineEnding" || D[z][1].type === "space") && (D[h][1].type === "lineEnding" || D[h][1].type === "space")) {
                j = z;
                while (++j < h) if (D[j][1].type === "codeTextData") {
                    D[z][1].type = "codeTextPadding", D[h][1].type = "codeTextPadding", z += 2, h -= 2;
                    break;
                }
            }
            j = z - 1, h++;
            while (++j <= h) if (F === void 0) {
                if (j !== h && D[j][1].type !== "lineEnding") F = j;
            } else if (j === h || D[j][1].type === "lineEnding") {
                if (D[F][1].type = "codeTextData", j !== F + 2) D[F][1].end = D[j - 1][1].end, D.splice(F + 2, j - F - 2),
                h -= j - F - 2, j = F + 2;
                F = void 0;
            }
            return D;
        }
        function Z(D) {
            return D !== 96 || this.events[this.events.length - 1][1].type === "characterEscape";
        }
        function A(D, h, z) {
            const F = this;
            let l = 0, Z, A;
            return q;
            function q(h) {
                return D.enter("codeText"), D.enter("codeTextSequence"), Q(h);
            }
            function Q(h) {
                if (h === 96) return D.consume(h), l++, Q;
                return D.exit("codeTextSequence"), I(h);
            }
            function I(h) {
                if (h === null) return z(h);
                if (h === 96) return A = D.enter("codeTextSequence"), Z = 0, X(h);
                if (h === 32) return D.enter("space"), D.consume(h), D.exit("space"), I;
                if ((0, j.markdownLineEnding)(h)) return D.enter("lineEnding"), D.consume(h), D.exit("lineEnding"),
                I;
                return D.enter("codeTextData"), E(h);
            }
            function E(h) {
                if (h === null || h === 32 || h === 96 || (0, j.markdownLineEnding)(h)) return D.exit("codeTextData"),
                I(h);
                return D.consume(h), E;
            }
            function X(z) {
                if (z === 96) return D.consume(z), Z++, X;
                if (Z === l) return D.exit("codeTextSequence"), D.exit("codeText"), h(z);
                return A.type = "codeTextData", E(z);
            }
        }
        z.codeText = F;
    }, {
        "micromark-util-character": 91
    } ],
    73: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.content = void 0;
        var j = D("micromark-factory-space"), F = D("micromark-util-character"), l = D("micromark-util-subtokenize");
        const Z = {
            tokenize: Q,
            resolve: q
        };
        z.content = Z;
        const A = {
            tokenize: I,
            partial: true
        };
        function q(D) {
            return (0, l.subtokenize)(D), D;
        }
        function Q(D, h) {
            let z;
            return j;
            function j(h) {
                return D.enter("content"), z = D.enter("chunkContent", {
                    contentType: "content"
                }), l(h);
            }
            function l(h) {
                if (h === null) return Z(h);
                if ((0, F.markdownLineEnding)(h)) return D.check(A, q, Z)(h);
                return D.consume(h), l;
            }
            function Z(z) {
                return D.exit("chunkContent"), D.exit("content"), h(z);
            }
            function q(h) {
                return D.consume(h), D.exit("chunkContent"), z.next = D.enter("chunkContent", {
                    contentType: "content",
                    previous: z
                }), z = z.next, l;
            }
        }
        function I(D, h, z) {
            const l = this;
            return Z;
            function Z(h) {
                return D.exit("chunkContent"), D.enter("lineEnding"), D.consume(h), D.exit("lineEnding"),
                (0, j.factorySpace)(D, A, "linePrefix");
            }
            function A(j) {
                if (j === null || (0, F.markdownLineEnding)(j)) return z(j);
                const Z = l.events[l.events.length - 1];
                if (!l.parser.constructs.disable.null.includes("codeIndented") && Z && Z[1].type === "linePrefix" && Z[2].sliceSerialize(Z[1], true).length >= 4) return h(j);
                return D.interrupt(l.parser.constructs.flow, z, h)(j);
            }
        }
    }, {
        "micromark-factory-space": 88,
        "micromark-util-character": 91,
        "micromark-util-subtokenize": 101
    } ],
    74: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.definition = void 0;
        var j = D("micromark-factory-destination"), F = D("micromark-factory-label"), l = D("micromark-factory-space"), Z = D("micromark-factory-title"), A = D("micromark-factory-whitespace"), q = D("micromark-util-normalize-identifier"), Q = D("micromark-util-character");
        const I = {
            name: "definition",
            tokenize: X
        };
        z.definition = I;
        const E = {
            tokenize: f,
            partial: true
        };
        function X(D, h, z) {
            const Z = this;
            let I;
            return X;
            function X(h) {
                return D.enter("definition"), F.factoryLabel.call(Z, D, f, z, "definitionLabel", "definitionLabelMarker", "definitionLabelString")(h);
            }
            function f(h) {
                if (I = (0, q.normalizeIdentifier)(Z.sliceSerialize(Z.events[Z.events.length - 1][1]).slice(1, -1)),
                h === 58) return D.enter("definitionMarker"), D.consume(h), D.exit("definitionMarker"),
                (0, A.factoryWhitespace)(D, (0, j.factoryDestination)(D, D.attempt(E, (0, l.factorySpace)(D, s, "whitespace"), (0,
                l.factorySpace)(D, s, "whitespace")), z, "definitionDestination", "definitionDestinationLiteral", "definitionDestinationLiteralMarker", "definitionDestinationRaw", "definitionDestinationString"));
                return z(h);
            }
            function s(j) {
                if (j === null || (0, Q.markdownLineEnding)(j)) {
                    if (D.exit("definition"), !Z.parser.defined.includes(I)) Z.parser.defined.push(I);
                    return h(j);
                }
                return z(j);
            }
        }
        function f(D, h, z) {
            return j;
            function j(h) {
                return (0, Q.markdownLineEndingOrSpace)(h) ? (0, A.factoryWhitespace)(D, F)(h) : z(h);
            }
            function F(h) {
                if (h === 34 || h === 39 || h === 40) return (0, Z.factoryTitle)(D, (0, l.factorySpace)(D, q, "whitespace"), z, "definitionTitle", "definitionTitleMarker", "definitionTitleString")(h);
                return z(h);
            }
            function q(D) {
                return D === null || (0, Q.markdownLineEnding)(D) ? h(D) : z(D);
            }
        }
    }, {
        "micromark-factory-destination": 86,
        "micromark-factory-label": 87,
        "micromark-factory-space": 88,
        "micromark-factory-title": 89,
        "micromark-factory-whitespace": 90,
        "micromark-util-character": 91,
        "micromark-util-normalize-identifier": 99
    } ],
    75: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.hardBreakEscape = void 0;
        var j = D("micromark-util-character");
        const F = {
            name: "hardBreakEscape",
            tokenize: l
        };
        function l(D, h, z) {
            return F;
            function F(h) {
                return D.enter("hardBreakEscape"), D.enter("escapeMarker"), D.consume(h), l;
            }
            function l(F) {
                if ((0, j.markdownLineEnding)(F)) return D.exit("escapeMarker"), D.exit("hardBreakEscape"),
                h(F);
                return z(F);
            }
        }
        z.hardBreakEscape = F;
    }, {
        "micromark-util-character": 91
    } ],
    76: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.headingAtx = void 0;
        var j = D("micromark-factory-space"), F = D("micromark-util-character"), l = D("micromark-util-chunked");
        const Z = {
            name: "headingAtx",
            tokenize: q,
            resolve: A
        };
        function A(D, h) {
            let z = D.length - 2, j = 3, F, Z;
            if (D[j][1].type === "whitespace") j += 2;
            if (z - 2 > j && D[z][1].type === "whitespace") z -= 2;
            if (D[z][1].type === "atxHeadingSequence" && (j === z - 1 || z - 4 > j && D[z - 2][1].type === "whitespace")) z -= j + 1 === z ? 2 : 4;
            if (z > j) F = {
                type: "atxHeadingText",
                start: D[j][1].start,
                end: D[z][1].end
            }, Z = {
                type: "chunkText",
                start: D[j][1].start,
                end: D[z][1].end,
                contentType: "text"
            }, (0, l.splice)(D, j, z - j + 1, [ [ "enter", F, h ], [ "enter", Z, h ], [ "exit", Z, h ], [ "exit", F, h ] ]);
            return D;
        }
        function q(D, h, z) {
            const l = this;
            let Z = 0;
            return A;
            function A(h) {
                return D.enter("atxHeading"), D.enter("atxHeadingSequence"), q(h);
            }
            function q(j) {
                if (j === 35 && Z++ < 6) return D.consume(j), q;
                if (j === null || (0, F.markdownLineEndingOrSpace)(j)) return D.exit("atxHeadingSequence"),
                l.interrupt ? h(j) : Q(j);
                return z(j);
            }
            function Q(z) {
                if (z === 35) return D.enter("atxHeadingSequence"), I(z);
                if (z === null || (0, F.markdownLineEnding)(z)) return D.exit("atxHeading"), h(z);
                if ((0, F.markdownSpace)(z)) return (0, j.factorySpace)(D, Q, "whitespace")(z);
                return D.enter("atxHeadingText"), E(z);
            }
            function I(h) {
                if (h === 35) return D.consume(h), I;
                return D.exit("atxHeadingSequence"), Q(h);
            }
            function E(h) {
                if (h === null || h === 35 || (0, F.markdownLineEndingOrSpace)(h)) return D.exit("atxHeadingText"),
                Q(h);
                return D.consume(h), E;
            }
        }
        z.headingAtx = Z;
    }, {
        "micromark-factory-space": 88,
        "micromark-util-character": 91,
        "micromark-util-chunked": 93
    } ],
    77: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.htmlFlow = void 0;
        var j = D("micromark-util-character"), F = D("micromark-util-html-tag-name"), l = D("iG");
        const Z = {
            name: "htmlFlow",
            tokenize: Q,
            resolveTo: q,
            concrete: true
        };
        z.htmlFlow = Z;
        const A = {
            tokenize: I,
            partial: true
        };
        function q(D) {
            let h = D.length;
            while (h--) if (D[h][0] === "enter" && D[h][1].type === "htmlFlow") break;
            if (h > 1 && D[h - 2][1].type === "linePrefix") D[h][1].start = D[h - 2][1].start,
            D[h + 1][1].start = D[h - 2][1].start, D.splice(h - 2, 2);
            return D;
        }
        function Q(D, h, z) {
            const l = this;
            let Z, q, Q, I, E;
            return X;
            function X(h) {
                return D.enter("htmlFlow"), D.enter("htmlFlowData"), D.consume(h), f;
            }
            function f(F) {
                if (F === 33) return D.consume(F), s;
                if (F === 47) return D.consume(F), x;
                if (F === 63) return D.consume(F), Z = 3, l.interrupt ? h : W;
                if ((0, j.asciiAlpha)(F)) return D.consume(F), Q = String.fromCharCode(F), q = true,
                n;
                return z(F);
            }
            function s(F) {
                if (F === 45) return D.consume(F), Z = 2, L;
                if (F === 91) return D.consume(F), Z = 5, Q = "CDATA[", I = 0, P;
                if ((0, j.asciiAlpha)(F)) return D.consume(F), Z = 4, l.interrupt ? h : W;
                return z(F);
            }
            function L(j) {
                if (j === 45) return D.consume(j), l.interrupt ? h : W;
                return z(j);
            }
            function P(j) {
                if (j === Q.charCodeAt(I++)) return D.consume(j), I === Q.length ? l.interrupt ? h : v : P;
                return z(j);
            }
            function x(h) {
                if ((0, j.asciiAlpha)(h)) return D.consume(h), Q = String.fromCharCode(h), n;
                return z(h);
            }
            function n(A) {
                if (A === null || A === 47 || A === 62 || (0, j.markdownLineEndingOrSpace)(A)) {
                    if (A !== 47 && q && F.htmlRawNames.includes(Q.toLowerCase())) return Z = 1, l.interrupt ? h(A) : v(A);
                    if (F.htmlBlockNames.includes(Q.toLowerCase())) {
                        if (Z = 6, A === 47) return D.consume(A), w;
                        return l.interrupt ? h(A) : v(A);
                    }
                    return Z = 7, l.interrupt && !l.parser.lazy[l.now().line] ? z(A) : q ? a(A) : J(A);
                }
                if (A === 45 || (0, j.asciiAlphanumeric)(A)) return D.consume(A), Q += String.fromCharCode(A),
                n;
                return z(A);
            }
            function w(j) {
                if (j === 62) return D.consume(j), l.interrupt ? h : v;
                return z(j);
            }
            function J(h) {
                if ((0, j.markdownSpace)(h)) return D.consume(h), J;
                return T(h);
            }
            function a(h) {
                if (h === 47) return D.consume(h), T;
                if (h === 58 || h === 95 || (0, j.asciiAlpha)(h)) return D.consume(h), d;
                if ((0, j.markdownSpace)(h)) return D.consume(h), a;
                return T(h);
            }
            function d(h) {
                if (h === 45 || h === 46 || h === 58 || h === 95 || (0, j.asciiAlphanumeric)(h)) return D.consume(h),
                d;
                return H(h);
            }
            function H(h) {
                if (h === 61) return D.consume(h), K;
                if ((0, j.markdownSpace)(h)) return D.consume(h), H;
                return a(h);
            }
            function K(h) {
                if (h === null || h === 60 || h === 61 || h === 62 || h === 96) return z(h);
                if (h === 34 || h === 39) return D.consume(h), E = h, c;
                if ((0, j.markdownSpace)(h)) return D.consume(h), K;
                return E = null, M(h);
            }
            function c(h) {
                if (h === null || (0, j.markdownLineEnding)(h)) return z(h);
                if (h === E) return D.consume(h), S;
                return D.consume(h), c;
            }
            function M(h) {
                if (h === null || h === 34 || h === 39 || h === 60 || h === 61 || h === 62 || h === 96 || (0,
                j.markdownLineEndingOrSpace)(h)) return H(h);
                return D.consume(h), M;
            }
            function S(D) {
                if (D === 47 || D === 62 || (0, j.markdownSpace)(D)) return a(D);
                return z(D);
            }
            function T(h) {
                if (h === 62) return D.consume(h), e;
                return z(h);
            }
            function e(h) {
                if ((0, j.markdownSpace)(h)) return D.consume(h), e;
                return h === null || (0, j.markdownLineEnding)(h) ? v(h) : z(h);
            }
            function v(h) {
                if (h === 45 && Z === 2) return D.consume(h), t;
                if (h === 60 && Z === 1) return D.consume(h), C;
                if (h === 62 && Z === 4) return D.consume(h), U;
                if (h === 63 && Z === 3) return D.consume(h), W;
                if (h === 93 && Z === 5) return D.consume(h), k;
                if ((0, j.markdownLineEnding)(h) && (Z === 6 || Z === 7)) return D.check(A, U, m)(h);
                if (h === null || (0, j.markdownLineEnding)(h)) return m(h);
                return D.consume(h), v;
            }
            function m(h) {
                return D.exit("htmlFlowData"), G(h);
            }
            function G(h) {
                if (h === null) return p(h);
                if ((0, j.markdownLineEnding)(h)) return D.attempt({
                    tokenize: r,
                    partial: true
                }, G, p)(h);
                return D.enter("htmlFlowData"), v(h);
            }
            function r(D, h, z) {
                return j;
                function j(h) {
                    return D.enter("lineEnding"), D.consume(h), D.exit("lineEnding"), F;
                }
                function F(D) {
                    return l.parser.lazy[l.now().line] ? z(D) : h(D);
                }
            }
            function t(h) {
                if (h === 45) return D.consume(h), W;
                return v(h);
            }
            function C(h) {
                if (h === 47) return D.consume(h), Q = "", y;
                return v(h);
            }
            function y(h) {
                if (h === 62 && F.htmlRawNames.includes(Q.toLowerCase())) return D.consume(h), U;
                if ((0, j.asciiAlpha)(h) && Q.length < 8) return D.consume(h), Q += String.fromCharCode(h),
                y;
                return v(h);
            }
            function k(h) {
                if (h === 93) return D.consume(h), W;
                return v(h);
            }
            function W(h) {
                if (h === 62) return D.consume(h), U;
                if (h === 45 && Z === 2) return D.consume(h), W;
                return v(h);
            }
            function U(h) {
                if (h === null || (0, j.markdownLineEnding)(h)) return D.exit("htmlFlowData"), p(h);
                return D.consume(h), U;
            }
            function p(z) {
                return D.exit("htmlFlow"), h(z);
            }
        }
        function I(D, h, z) {
            return j;
            function j(j) {
                return D.exit("htmlFlowData"), D.enter("lineEndingBlank"), D.consume(j), D.exit("lineEndingBlank"),
                D.attempt(l.blankLine, h, z);
            }
        }
    }, {
        iG: 66,
        "micromark-util-character": 91,
        "micromark-util-html-tag-name": 98
    } ],
    78: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.htmlText = void 0;
        var j = D("micromark-factory-space"), F = D("micromark-util-character");
        const l = {
            name: "htmlText",
            tokenize: Z
        };
        function Z(D, h, z) {
            const l = this;
            let Z, A, q, Q;
            return I;
            function I(h) {
                return D.enter("htmlText"), D.enter("htmlTextData"), D.consume(h), E;
            }
            function E(h) {
                if (h === 33) return D.consume(h), X;
                if (h === 47) return D.consume(h), c;
                if (h === 63) return D.consume(h), H;
                if ((0, F.asciiAlpha)(h)) return D.consume(h), T;
                return z(h);
            }
            function X(h) {
                if (h === 45) return D.consume(h), f;
                if (h === 91) return D.consume(h), A = "CDATA[", q = 0, n;
                if ((0, F.asciiAlpha)(h)) return D.consume(h), d;
                return z(h);
            }
            function f(h) {
                if (h === 45) return D.consume(h), s;
                return z(h);
            }
            function s(h) {
                if (h === null || h === 62) return z(h);
                if (h === 45) return D.consume(h), L;
                return P(h);
            }
            function L(D) {
                if (D === null || D === 62) return z(D);
                return P(D);
            }
            function P(h) {
                if (h === null) return z(h);
                if (h === 45) return D.consume(h), x;
                if ((0, F.markdownLineEnding)(h)) return Q = P, y(h);
                return D.consume(h), P;
            }
            function x(h) {
                if (h === 45) return D.consume(h), W;
                return P(h);
            }
            function n(h) {
                if (h === A.charCodeAt(q++)) return D.consume(h), q === A.length ? w : n;
                return z(h);
            }
            function w(h) {
                if (h === null) return z(h);
                if (h === 93) return D.consume(h), J;
                if ((0, F.markdownLineEnding)(h)) return Q = w, y(h);
                return D.consume(h), w;
            }
            function J(h) {
                if (h === 93) return D.consume(h), a;
                return w(h);
            }
            function a(h) {
                if (h === 62) return W(h);
                if (h === 93) return D.consume(h), a;
                return w(h);
            }
            function d(h) {
                if (h === null || h === 62) return W(h);
                if ((0, F.markdownLineEnding)(h)) return Q = d, y(h);
                return D.consume(h), d;
            }
            function H(h) {
                if (h === null) return z(h);
                if (h === 63) return D.consume(h), K;
                if ((0, F.markdownLineEnding)(h)) return Q = H, y(h);
                return D.consume(h), H;
            }
            function K(D) {
                return D === 62 ? W(D) : H(D);
            }
            function c(h) {
                if ((0, F.asciiAlpha)(h)) return D.consume(h), M;
                return z(h);
            }
            function M(h) {
                if (h === 45 || (0, F.asciiAlphanumeric)(h)) return D.consume(h), M;
                return S(h);
            }
            function S(h) {
                if ((0, F.markdownLineEnding)(h)) return Q = S, y(h);
                if ((0, F.markdownSpace)(h)) return D.consume(h), S;
                return W(h);
            }
            function T(h) {
                if (h === 45 || (0, F.asciiAlphanumeric)(h)) return D.consume(h), T;
                if (h === 47 || h === 62 || (0, F.markdownLineEndingOrSpace)(h)) return e(h);
                return z(h);
            }
            function e(h) {
                if (h === 47) return D.consume(h), W;
                if (h === 58 || h === 95 || (0, F.asciiAlpha)(h)) return D.consume(h), v;
                if ((0, F.markdownLineEnding)(h)) return Q = e, y(h);
                if ((0, F.markdownSpace)(h)) return D.consume(h), e;
                return W(h);
            }
            function v(h) {
                if (h === 45 || h === 46 || h === 58 || h === 95 || (0, F.asciiAlphanumeric)(h)) return D.consume(h),
                v;
                return m(h);
            }
            function m(h) {
                if (h === 61) return D.consume(h), G;
                if ((0, F.markdownLineEnding)(h)) return Q = m, y(h);
                if ((0, F.markdownSpace)(h)) return D.consume(h), m;
                return e(h);
            }
            function G(h) {
                if (h === null || h === 60 || h === 61 || h === 62 || h === 96) return z(h);
                if (h === 34 || h === 39) return D.consume(h), Z = h, r;
                if ((0, F.markdownLineEnding)(h)) return Q = G, y(h);
                if ((0, F.markdownSpace)(h)) return D.consume(h), G;
                return D.consume(h), Z = void 0, C;
            }
            function r(h) {
                if (h === Z) return D.consume(h), t;
                if (h === null) return z(h);
                if ((0, F.markdownLineEnding)(h)) return Q = r, y(h);
                return D.consume(h), r;
            }
            function t(D) {
                if (D === 62 || D === 47 || (0, F.markdownLineEndingOrSpace)(D)) return e(D);
                return z(D);
            }
            function C(h) {
                if (h === null || h === 34 || h === 39 || h === 60 || h === 61 || h === 96) return z(h);
                if (h === 62 || (0, F.markdownLineEndingOrSpace)(h)) return e(h);
                return D.consume(h), C;
            }
            function y(h) {
                return D.exit("htmlTextData"), D.enter("lineEnding"), D.consume(h), D.exit("lineEnding"),
                (0, j.factorySpace)(D, k, "linePrefix", l.parser.constructs.disable.null.includes("codeIndented") ? void 0 : 4);
            }
            function k(h) {
                return D.enter("htmlTextData"), Q(h);
            }
            function W(j) {
                if (j === 62) return D.consume(j), D.exit("htmlTextData"), D.exit("htmlText"), h;
                return z(j);
            }
        }
        z.htmlText = l;
    }, {
        "micromark-factory-space": 88,
        "micromark-util-character": 91
    } ],
    79: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.labelEnd = void 0;
        var j = D("micromark-factory-destination"), F = D("micromark-factory-label"), l = D("micromark-factory-title"), Z = D("micromark-factory-whitespace"), A = D("micromark-util-character"), q = D("micromark-util-chunked"), Q = D("micromark-util-normalize-identifier"), I = D("micromark-util-resolve-all");
        const E = {
            name: "labelEnd",
            tokenize: x,
            resolveTo: P,
            resolveAll: L
        };
        z.labelEnd = E;
        const X = {
            tokenize: n
        }, f = {
            tokenize: w
        }, s = {
            tokenize: J
        };
        function L(D) {
            let h = -1, z;
            while (++h < D.length) if (z = D[h][1], z.type === "labelImage" || z.type === "labelLink" || z.type === "labelEnd") D.splice(h + 1, z.type === "labelImage" ? 4 : 2),
            z.type = "data", h++;
            return D;
        }
        function P(D, h) {
            let z = D.length, j = 0, F, l, Z, A;
            while (z--) if (F = D[z][1], l) {
                if (F.type === "link" || F.type === "labelLink" && F._inactive) break;
                if (D[z][0] === "enter" && F.type === "labelLink") F._inactive = true;
            } else if (Z) {
                if (D[z][0] === "enter" && (F.type === "labelImage" || F.type === "labelLink") && !F._balanced) if (l = z,
                F.type !== "labelLink") {
                    j = 2;
                    break;
                }
            } else if (F.type === "labelEnd") Z = z;
            const Q = {
                type: D[l][1].type === "labelLink" ? "link" : "image",
                start: Object.assign({}, D[l][1].start),
                end: Object.assign({}, D[D.length - 1][1].end)
            }, E = {
                type: "label",
                start: Object.assign({}, D[l][1].start),
                end: Object.assign({}, D[Z][1].end)
            }, X = {
                type: "labelText",
                start: Object.assign({}, D[l + j + 2][1].end),
                end: Object.assign({}, D[Z - 2][1].start)
            };
            return A = [ [ "enter", Q, h ], [ "enter", E, h ] ], A = (0, q.push)(A, D.slice(l + 1, l + j + 3)),
            A = (0, q.push)(A, [ [ "enter", X, h ] ]), A = (0, q.push)(A, (0, I.resolveAll)(h.parser.constructs.insideSpan.null, D.slice(l + j + 4, Z - 3), h)),
            A = (0, q.push)(A, [ [ "exit", X, h ], D[Z - 2], D[Z - 1], [ "exit", E, h ] ]),
            A = (0, q.push)(A, D.slice(Z + 1)), A = (0, q.push)(A, [ [ "exit", Q, h ] ]), (0,
            q.splice)(D, l, D.length, A), D;
        }
        function x(D, h, z) {
            const j = this;
            let F = j.events.length, l, Z;
            while (F--) if ((j.events[F][1].type === "labelImage" || j.events[F][1].type === "labelLink") && !j.events[F][1]._balanced) {
                l = j.events[F][1];
                break;
            }
            return A;
            function A(h) {
                if (!l) return z(h);
                if (l._inactive) return I(h);
                return Z = j.parser.defined.includes((0, Q.normalizeIdentifier)(j.sliceSerialize({
                    start: l.end,
                    end: j.now()
                }))), D.enter("labelEnd"), D.enter("labelMarker"), D.consume(h), D.exit("labelMarker"),
                D.exit("labelEnd"), q;
            }
            function q(z) {
                if (z === 40) return D.attempt(X, h, Z ? h : I)(z);
                if (z === 91) return D.attempt(f, h, Z ? D.attempt(s, h, I) : I)(z);
                return Z ? h(z) : I(z);
            }
            function I(D) {
                return l._balanced = true, z(D);
            }
        }
        function n(D, h, z) {
            return F;
            function F(h) {
                return D.enter("resource"), D.enter("resourceMarker"), D.consume(h), D.exit("resourceMarker"),
                (0, Z.factoryWhitespace)(D, q);
            }
            function q(h) {
                if (h === 41) return E(h);
                return (0, j.factoryDestination)(D, Q, z, "resourceDestination", "resourceDestinationLiteral", "resourceDestinationLiteralMarker", "resourceDestinationRaw", "resourceDestinationString", 32)(h);
            }
            function Q(h) {
                return (0, A.markdownLineEndingOrSpace)(h) ? (0, Z.factoryWhitespace)(D, I)(h) : E(h);
            }
            function I(h) {
                if (h === 34 || h === 39 || h === 40) return (0, l.factoryTitle)(D, (0, Z.factoryWhitespace)(D, E), z, "resourceTitle", "resourceTitleMarker", "resourceTitleString")(h);
                return E(h);
            }
            function E(j) {
                if (j === 41) return D.enter("resourceMarker"), D.consume(j), D.exit("resourceMarker"),
                D.exit("resource"), h;
                return z(j);
            }
        }
        function w(D, h, z) {
            const j = this;
            return l;
            function l(h) {
                return F.factoryLabel.call(j, D, Z, z, "reference", "referenceMarker", "referenceString")(h);
            }
            function Z(D) {
                return j.parser.defined.includes((0, Q.normalizeIdentifier)(j.sliceSerialize(j.events[j.events.length - 1][1]).slice(1, -1))) ? h(D) : z(D);
            }
        }
        function J(D, h, z) {
            return j;
            function j(h) {
                return D.enter("reference"), D.enter("referenceMarker"), D.consume(h), D.exit("referenceMarker"),
                F;
            }
            function F(j) {
                if (j === 93) return D.enter("referenceMarker"), D.consume(j), D.exit("referenceMarker"),
                D.exit("reference"), h;
                return z(j);
            }
        }
    }, {
        "micromark-factory-destination": 86,
        "micromark-factory-label": 87,
        "micromark-factory-title": 89,
        "micromark-factory-whitespace": 90,
        "micromark-util-character": 91,
        "micromark-util-chunked": 93,
        "micromark-util-normalize-identifier": 99,
        "micromark-util-resolve-all": 100
    } ],
    80: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.labelStartImage = void 0;
        var j = D("d1");
        const F = {
            name: "labelStartImage",
            tokenize: l,
            resolveAll: j.labelEnd.resolveAll
        };
        function l(D, h, z) {
            const j = this;
            return F;
            function F(h) {
                return D.enter("labelImage"), D.enter("labelImageMarker"), D.consume(h), D.exit("labelImageMarker"),
                l;
            }
            function l(h) {
                if (h === 91) return D.enter("labelMarker"), D.consume(h), D.exit("labelMarker"),
                D.exit("labelImage"), Z;
                return z(h);
            }
            function Z(D) {
                return D === 94 && "_hiddenFootnoteSupport" in j.parser.constructs ? z(D) : h(D);
            }
        }
        z.labelStartImage = F;
    }, {
        d1: 79
    } ],
    81: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.labelStartLink = void 0;
        var j = D("d1");
        const F = {
            name: "labelStartLink",
            tokenize: l,
            resolveAll: j.labelEnd.resolveAll
        };
        function l(D, h, z) {
            const j = this;
            return F;
            function F(h) {
                return D.enter("labelLink"), D.enter("labelMarker"), D.consume(h), D.exit("labelMarker"),
                D.exit("labelLink"), l;
            }
            function l(D) {
                return D === 94 && "_hiddenFootnoteSupport" in j.parser.constructs ? z(D) : h(D);
            }
        }
        z.labelStartLink = F;
    }, {
        d1: 79
    } ],
    82: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.lineEnding = void 0;
        var j = D("micromark-factory-space"), F = D("micromark-util-character");
        const l = {
            name: "lineEnding",
            tokenize: Z
        };
        function Z(D, h) {
            return z;
            function z(z) {
                return D.enter("lineEnding"), D.consume(z), D.exit("lineEnding"), (0, j.factorySpace)(D, h, "linePrefix");
            }
        }
        z.lineEnding = l;
    }, {
        "micromark-factory-space": 88,
        "micromark-util-character": 91
    } ],
    83: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.list = void 0;
        var j = D("micromark-factory-space"), F = D("micromark-util-character"), l = D("iG"), Z = D("k7");
        const A = {
            name: "list",
            tokenize: I,
            continuation: {
                tokenize: E
            },
            exit: f
        };
        z.list = A;
        const q = {
            tokenize: s,
            partial: true
        }, Q = {
            tokenize: X,
            partial: true
        };
        function I(D, h, z) {
            const j = this, A = j.events[j.events.length - 1];
            let Q = A && A[1].type === "linePrefix" ? A[2].sliceSerialize(A[1], true).length : 0, I = 0;
            return E;
            function E(h) {
                const l = j.containerState.type || (h === 42 || h === 43 || h === 45 ? "listUnordered" : "listOrdered");
                if (l === "listUnordered" ? !j.containerState.marker || h === j.containerState.marker : (0,
                F.asciiDigit)(h)) {
                    if (!j.containerState.type) j.containerState.type = l, D.enter(l, {
                        _container: true
                    });
                    if (l === "listUnordered") return D.enter("listItemPrefix"), h === 42 || h === 45 ? D.check(Z.thematicBreak, z, f)(h) : f(h);
                    if (!j.interrupt || h === 49) return D.enter("listItemPrefix"), D.enter("listItemValue"),
                    X(h);
                }
                return z(h);
            }
            function X(h) {
                if ((0, F.asciiDigit)(h) && ++I < 10) return D.consume(h), X;
                if ((!j.interrupt || I < 2) && (j.containerState.marker ? h === j.containerState.marker : h === 41 || h === 46)) return D.exit("listItemValue"),
                f(h);
                return z(h);
            }
            function f(h) {
                return D.enter("listItemMarker"), D.consume(h), D.exit("listItemMarker"), j.containerState.marker = j.containerState.marker || h,
                D.check(l.blankLine, j.interrupt ? z : s, D.attempt(q, P, L));
            }
            function s(D) {
                return j.containerState.initialBlankLine = true, Q++, P(D);
            }
            function L(h) {
                if ((0, F.markdownSpace)(h)) return D.enter("listItemPrefixWhitespace"), D.consume(h),
                D.exit("listItemPrefixWhitespace"), P;
                return z(h);
            }
            function P(z) {
                return j.containerState.size = Q + j.sliceSerialize(D.exit("listItemPrefix"), true).length,
                h(z);
            }
        }
        function E(D, h, z) {
            const Z = this;
            return Z.containerState._closeFlow = void 0, D.check(l.blankLine, q, I);
            function q(z) {
                return Z.containerState.furtherBlankLines = Z.containerState.furtherBlankLines || Z.containerState.initialBlankLine,
                (0, j.factorySpace)(D, h, "listItemIndent", Z.containerState.size + 1)(z);
            }
            function I(z) {
                if (Z.containerState.furtherBlankLines || !(0, F.markdownSpace)(z)) return Z.containerState.furtherBlankLines = void 0,
                Z.containerState.initialBlankLine = void 0, E(z);
                return Z.containerState.furtherBlankLines = void 0, Z.containerState.initialBlankLine = void 0,
                D.attempt(Q, h, E)(z);
            }
            function E(F) {
                return Z.containerState._closeFlow = true, Z.interrupt = void 0, (0, j.factorySpace)(D, D.attempt(A, h, z), "linePrefix", Z.parser.constructs.disable.null.includes("codeIndented") ? void 0 : 4)(F);
            }
        }
        function X(D, h, z) {
            const F = this;
            return (0, j.factorySpace)(D, l, "listItemIndent", F.containerState.size + 1);
            function l(D) {
                const j = F.events[F.events.length - 1];
                return j && j[1].type === "listItemIndent" && j[2].sliceSerialize(j[1], true).length === F.containerState.size ? h(D) : z(D);
            }
        }
        function f(D) {
            D.exit(this.containerState.type);
        }
        function s(D, h, z) {
            const l = this;
            return (0, j.factorySpace)(D, Z, "listItemPrefixWhitespace", l.parser.constructs.disable.null.includes("codeIndented") ? void 0 : 4 + 1);
            function Z(D) {
                const j = l.events[l.events.length - 1];
                return !(0, F.markdownSpace)(D) && j && j[1].type === "listItemPrefixWhitespace" ? h(D) : z(D);
            }
        }
    }, {
        iG: 66,
        k7: 85,
        "micromark-factory-space": 88,
        "micromark-util-character": 91
    } ],
    84: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.setextUnderline = void 0;
        var j = D("micromark-factory-space"), F = D("micromark-util-character");
        const l = {
            name: "setextUnderline",
            tokenize: A,
            resolveTo: Z
        };
        function Z(D, h) {
            let z = D.length, j, F, l;
            while (z--) if (D[z][0] === "enter") {
                if (D[z][1].type === "content") {
                    j = z;
                    break;
                }
                if (D[z][1].type === "paragraph") F = z;
            } else {
                if (D[z][1].type === "content") D.splice(z, 1);
                if (!l && D[z][1].type === "definition") l = z;
            }
            const Z = {
                type: "setextHeading",
                start: Object.assign({}, D[F][1].start),
                end: Object.assign({}, D[D.length - 1][1].end)
            };
            if (D[F][1].type = "setextHeadingText", l) D.splice(F, 0, [ "enter", Z, h ]), D.splice(l + 1, 0, [ "exit", D[j][1], h ]),
            D[j][1].end = Object.assign({}, D[l][1].end); else D[j][1] = Z;
            return D.push([ "exit", Z, h ]), D;
        }
        function A(D, h, z) {
            const l = this;
            let Z = l.events.length, A, q;
            while (Z--) if (l.events[Z][1].type !== "lineEnding" && l.events[Z][1].type !== "linePrefix" && l.events[Z][1].type !== "content") {
                q = l.events[Z][1].type === "paragraph";
                break;
            }
            return Q;
            function Q(h) {
                if (!l.parser.lazy[l.now().line] && (l.interrupt || q)) return D.enter("setextHeadingLine"),
                D.enter("setextHeadingLineSequence"), A = h, I(h);
                return z(h);
            }
            function I(h) {
                if (h === A) return D.consume(h), I;
                return D.exit("setextHeadingLineSequence"), (0, j.factorySpace)(D, E, "lineSuffix")(h);
            }
            function E(j) {
                if (j === null || (0, F.markdownLineEnding)(j)) return D.exit("setextHeadingLine"),
                h(j);
                return z(j);
            }
        }
        z.setextUnderline = l;
    }, {
        "micromark-factory-space": 88,
        "micromark-util-character": 91
    } ],
    85: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.thematicBreak = void 0;
        var j = D("micromark-factory-space"), F = D("micromark-util-character");
        const l = {
            name: "thematicBreak",
            tokenize: Z
        };
        function Z(D, h, z) {
            let l = 0, Z;
            return A;
            function A(h) {
                return D.enter("thematicBreak"), Z = h, q(h);
            }
            function q(A) {
                if (A === Z) return D.enter("thematicBreakSequence"), Q(A);
                if ((0, F.markdownSpace)(A)) return (0, j.factorySpace)(D, q, "whitespace")(A);
                if (l < 3 || A !== null && !(0, F.markdownLineEnding)(A)) return z(A);
                return D.exit("thematicBreak"), h(A);
            }
            function Q(h) {
                if (h === Z) return D.consume(h), l++, Q;
                return D.exit("thematicBreakSequence"), q(h);
            }
        }
        z.thematicBreak = l;
    }, {
        "micromark-factory-space": 88,
        "micromark-util-character": 91
    } ],
    86: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.factoryDestination = F;
        var j = D("micromark-util-character");
        function F(D, h, z, F, l, Z, A, q, Q) {
            const I = Q || Number.POSITIVE_INFINITY;
            let E = 0;
            return X;
            function X(h) {
                if (h === 60) return D.enter(F), D.enter(l), D.enter(Z), D.consume(h), D.exit(Z),
                f;
                if (h === null || h === 41 || (0, j.asciiControl)(h)) return z(h);
                return D.enter(F), D.enter(A), D.enter(q), D.enter("chunkString", {
                    contentType: "string"
                }), P(h);
            }
            function f(z) {
                if (z === 62) return D.enter(Z), D.consume(z), D.exit(Z), D.exit(l), D.exit(F),
                h;
                return D.enter(q), D.enter("chunkString", {
                    contentType: "string"
                }), s(z);
            }
            function s(h) {
                if (h === 62) return D.exit("chunkString"), D.exit(q), f(h);
                if (h === null || h === 60 || (0, j.markdownLineEnding)(h)) return z(h);
                return D.consume(h), h === 92 ? L : s;
            }
            function L(h) {
                if (h === 60 || h === 62 || h === 92) return D.consume(h), s;
                return s(h);
            }
            function P(l) {
                if (l === 40) {
                    if (++E > I) return z(l);
                    return D.consume(l), P;
                }
                if (l === 41) {
                    if (!E--) return D.exit("chunkString"), D.exit(q), D.exit(A), D.exit(F), h(l);
                    return D.consume(l), P;
                }
                if (l === null || (0, j.markdownLineEndingOrSpace)(l)) {
                    if (E) return z(l);
                    return D.exit("chunkString"), D.exit(q), D.exit(A), D.exit(F), h(l);
                }
                if ((0, j.asciiControl)(l)) return z(l);
                return D.consume(l), l === 92 ? x : P;
            }
            function x(h) {
                if (h === 40 || h === 41 || h === 92) return D.consume(h), P;
                return P(h);
            }
        }
    }, {
        "micromark-util-character": 91
    } ],
    87: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.factoryLabel = F;
        var j = D("micromark-util-character");
        function F(D, h, z, F, l, Z) {
            const A = this;
            let q = 0, Q;
            return I;
            function I(h) {
                return D.enter(F), D.enter(l), D.consume(h), D.exit(l), D.enter(Z), E;
            }
            function E(I) {
                if (I === null || I === 91 || I === 93 && !Q || I === 94 && !q && "_hiddenFootnoteSupport" in A.parser.constructs || q > 999) return z(I);
                if (I === 93) return D.exit(Z), D.enter(l), D.consume(I), D.exit(l), D.exit(F),
                h;
                if ((0, j.markdownLineEnding)(I)) return D.enter("lineEnding"), D.consume(I), D.exit("lineEnding"),
                E;
                return D.enter("chunkString", {
                    contentType: "string"
                }), X(I);
            }
            function X(h) {
                if (h === null || h === 91 || h === 93 || (0, j.markdownLineEnding)(h) || q++ > 999) return D.exit("chunkString"),
                E(h);
                return D.consume(h), Q = Q || !(0, j.markdownSpace)(h), h === 92 ? f : X;
            }
            function f(h) {
                if (h === 91 || h === 92 || h === 93) return D.consume(h), q++, X;
                return X(h);
            }
        }
    }, {
        "micromark-util-character": 91
    } ],
    88: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.factorySpace = F;
        var j = D("micromark-util-character");
        function F(D, h, z, F) {
            const l = F ? F - 1 : Number.POSITIVE_INFINITY;
            let Z = 0;
            return A;
            function A(F) {
                if ((0, j.markdownSpace)(F)) return D.enter(z), q(F);
                return h(F);
            }
            function q(F) {
                if ((0, j.markdownSpace)(F) && Z++ < l) return D.consume(F), q;
                return D.exit(z), h(F);
            }
        }
    }, {
        "micromark-util-character": 91
    } ],
    89: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.factoryTitle = l;
        var j = D("micromark-factory-space"), F = D("micromark-util-character");
        function l(D, h, z, l, Z, A) {
            let q;
            return Q;
            function Q(h) {
                return D.enter(l), D.enter(Z), D.consume(h), D.exit(Z), q = h === 40 ? 41 : h, I;
            }
            function I(z) {
                if (z === q) return D.enter(Z), D.consume(z), D.exit(Z), D.exit(l), h;
                return D.enter(A), E(z);
            }
            function E(h) {
                if (h === q) return D.exit(A), I(q);
                if (h === null) return z(h);
                if ((0, F.markdownLineEnding)(h)) return D.enter("lineEnding"), D.consume(h), D.exit("lineEnding"),
                (0, j.factorySpace)(D, E, "linePrefix");
                return D.enter("chunkString", {
                    contentType: "string"
                }), X(h);
            }
            function X(h) {
                if (h === q || h === null || (0, F.markdownLineEnding)(h)) return D.exit("chunkString"),
                E(h);
                return D.consume(h), h === 92 ? f : X;
            }
            function f(h) {
                if (h === q || h === 92) return D.consume(h), X;
                return X(h);
            }
        }
    }, {
        "micromark-factory-space": 88,
        "micromark-util-character": 91
    } ],
    90: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.factoryWhitespace = l;
        var j = D("micromark-factory-space"), F = D("micromark-util-character");
        function l(D, h) {
            let z;
            return l;
            function l(Z) {
                if ((0, F.markdownLineEnding)(Z)) return D.enter("lineEnding"), D.consume(Z), D.exit("lineEnding"),
                z = true, l;
                if ((0, F.markdownSpace)(Z)) return (0, j.factorySpace)(D, l, z ? "linePrefix" : "lineSuffix")(Z);
                return h(Z);
            }
        }
    }, {
        "micromark-factory-space": 88,
        "micromark-util-character": 91
    } ],
    91: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.asciiAtext = z.asciiAlphanumeric = z.asciiAlpha = void 0, z.asciiControl = I,
        z.asciiPunctuation = z.asciiHexDigit = z.asciiDigit = void 0, z.markdownLineEnding = X,
        z.markdownLineEndingOrSpace = E, z.markdownSpace = f, z.unicodeWhitespace = z.unicodePunctuation = void 0;
        var j = D("0b");
        const F = P(/[A-Za-z]/);
        z.asciiAlpha = F;
        const l = P(/\d/);
        z.asciiDigit = l;
        const Z = P(/[\dA-Fa-f]/);
        z.asciiHexDigit = Z;
        const A = P(/[\dA-Za-z]/);
        z.asciiAlphanumeric = A;
        const q = P(/[!-/:-@[-`{-~]/);
        z.asciiPunctuation = q;
        const Q = P(/[#-'*+\--9=?A-Z^-~]/);
        function I(D) {
            return D !== null && (D < 32 || D === 127);
        }
        function E(D) {
            return D !== null && (D < 0 || D === 32);
        }
        function X(D) {
            return D !== null && D < -2;
        }
        function f(D) {
            return D === -2 || D === -1 || D === 32;
        }
        z.asciiAtext = Q;
        const s = P(/\s/);
        z.unicodeWhitespace = s;
        const L = P(j.unicodePunctuationRegex);
        function P(D) {
            return h;
            function h(h) {
                return h !== null && D.test(String.fromCharCode(h));
            }
        }
        z.unicodePunctuation = L;
    }, {
        "0b": 92
    } ],
    92: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.unicodePunctuationRegex = void 0;
        const j = /[!-/:-@[-`{-~\u00A1\u00A7\u00AB\u00B6\u00B7\u00BB\u00BF\u037E\u0387\u055A-\u055F\u0589\u058A\u05BE\u05C0\u05C3\u05C6\u05F3\u05F4\u0609\u060A\u060C\u060D\u061B\u061E\u061F\u066A-\u066D\u06D4\u0700-\u070D\u07F7-\u07F9\u0830-\u083E\u085E\u0964\u0965\u0970\u09FD\u0A76\u0AF0\u0C77\u0C84\u0DF4\u0E4F\u0E5A\u0E5B\u0F04-\u0F12\u0F14\u0F3A-\u0F3D\u0F85\u0FD0-\u0FD4\u0FD9\u0FDA\u104A-\u104F\u10FB\u1360-\u1368\u1400\u166E\u169B\u169C\u16EB-\u16ED\u1735\u1736\u17D4-\u17D6\u17D8-\u17DA\u1800-\u180A\u1944\u1945\u1A1E\u1A1F\u1AA0-\u1AA6\u1AA8-\u1AAD\u1B5A-\u1B60\u1BFC-\u1BFF\u1C3B-\u1C3F\u1C7E\u1C7F\u1CC0-\u1CC7\u1CD3\u2010-\u2027\u2030-\u2043\u2045-\u2051\u2053-\u205E\u207D\u207E\u208D\u208E\u2308-\u230B\u2329\u232A\u2768-\u2775\u27C5\u27C6\u27E6-\u27EF\u2983-\u2998\u29D8-\u29DB\u29FC\u29FD\u2CF9-\u2CFC\u2CFE\u2CFF\u2D70\u2E00-\u2E2E\u2E30-\u2E4F\u2E52\u3001-\u3003\u3008-\u3011\u3014-\u301F\u3030\u303D\u30A0\u30FB\uA4FE\uA4FF\uA60D-\uA60F\uA673\uA67E\uA6F2-\uA6F7\uA874-\uA877\uA8CE\uA8CF\uA8F8-\uA8FA\uA8FC\uA92E\uA92F\uA95F\uA9C1-\uA9CD\uA9DE\uA9DF\uAA5C-\uAA5F\uAADE\uAADF\uAAF0\uAAF1\uABEB\uFD3E\uFD3F\uFE10-\uFE19\uFE30-\uFE52\uFE54-\uFE61\uFE63\uFE68\uFE6A\uFE6B\uFF01-\uFF03\uFF05-\uFF0A\uFF0C-\uFF0F\uFF1A\uFF1B\uFF1F\uFF20\uFF3B-\uFF3D\uFF3F\uFF5B\uFF5D\uFF5F-\uFF65]/;
        z.unicodePunctuationRegex = j;
    }, {} ],
    93: [ function(D, h, z) {
        "use strict";
        function j(D, h, z, j) {
            const F = D.length;
            let l = 0, Z;
            if (h < 0) h = -h > F ? 0 : F + h; else h = h > F ? F : h;
            if (z = z > 0 ? z : 0, j.length < 1e4) Z = Array.from(j), Z.unshift(h, z), [].splice.apply(D, Z); else {
                if (z) [].splice.apply(D, [ h, z ]);
                while (l < j.length) Z = j.slice(l, l + 1e4), Z.unshift(h, 0), [].splice.apply(D, Z),
                l += 1e4, h += 1e4;
            }
        }
        function F(D, h) {
            if (D.length > 0) return j(D, D.length, 0, h), D;
            return h;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.push = F, z.splice = j;
    }, {} ],
    94: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.classifyCharacter = F;
        var j = D("micromark-util-character");
        function F(D) {
            if (D === null || (0, j.markdownLineEndingOrSpace)(D) || (0, j.unicodeWhitespace)(D)) return 1;
            if ((0, j.unicodePunctuation)(D)) return 2;
        }
    }, {
        "micromark-util-character": 91
    } ],
    95: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.combineExtensions = l, z.combineHtmlExtensions = q;
        var j = D("micromark-util-chunked");
        const F = {}.hasOwnProperty;
        function l(D) {
            const h = {};
            let z = -1;
            while (++z < D.length) Z(h, D[z]);
            return h;
        }
        function Z(D, h) {
            let z;
            for (z in h) {
                const j = F.call(D, z) ? D[z] : void 0, l = j || (D[z] = {}), Z = h[z];
                let q;
                for (q in Z) {
                    if (!F.call(l, q)) l[q] = [];
                    const D = Z[q];
                    A(l[q], Array.isArray(D) ? D : D ? [ D ] : []);
                }
            }
        }
        function A(D, h) {
            let z = -1;
            const F = [];
            while (++z < h.length) (h[z].add === "after" ? D : F).push(h[z]);
            (0, j.splice)(D, 0, 0, F);
        }
        function q(D) {
            const h = {};
            let z = -1;
            while (++z < D.length) Q(h, D[z]);
            return h;
        }
        function Q(D, h) {
            let z;
            for (z in h) {
                const j = F.call(D, z) ? D[z] : void 0, l = j || (D[z] = {}), Z = h[z];
                let A;
                if (Z) for (A in Z) l[A] = Z[A];
            }
        }
    }, {
        "micromark-util-chunked": 93
    } ],
    96: [ function(D, h, z) {
        "use strict";
        function j(D, h) {
            const z = Number.parseInt(D, h);
            if (z < 9 || z === 11 || z > 13 && z < 32 || z > 126 && z < 160 || z > 55295 && z < 57344 || z > 64975 && z < 65008 || (z & 65535) === 65535 || (z & 65535) === 65534 || z > 1114111) return "�";
            return String.fromCharCode(z);
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.decodeNumericCharacterReference = j;
    }, {} ],
    97: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.decodeString = Z;
        var j = D("decode-named-character-reference"), F = D("micromark-util-decode-numeric-character-reference");
        const l = /\\([!-/:-@[-`{-~])|&(#(?:\d{1,7}|x[\da-f]{1,6})|[\da-z]{1,31});/gi;
        function Z(D) {
            return D.replace(l, A);
        }
        function A(D, h, z) {
            if (h) return h;
            const l = z.charCodeAt(0);
            if (l === 35) {
                const D = z.charCodeAt(1), h = D === 120 || D === 88;
                return (0, F.decodeNumericCharacterReference)(z.slice(h ? 2 : 1), h ? 16 : 10);
            }
            return (0, j.decodeNamedCharacterReference)(z) || D;
        }
    }, {
        "decode-named-character-reference": 4,
        "micromark-util-decode-numeric-character-reference": 96
    } ],
    98: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.htmlRawNames = z.htmlBlockNames = void 0;
        const j = [ "address", "article", "aside", "base", "basefont", "blockquote", "body", "caption", "center", "col", "colgroup", "dd", "details", "dialog", "dir", "div", "dl", "dt", "fieldset", "figcaption", "figure", "footer", "form", "frame", "frameset", "h1", "h2", "h3", "h4", "h5", "h6", "head", "header", "hr", "html", "iframe", "legend", "li", "link", "main", "menu", "menuitem", "nav", "noframes", "ol", "optgroup", "option", "p", "param", "section", "summary", "table", "tbody", "td", "tfoot", "th", "thead", "title", "tr", "track", "ul" ];
        z.htmlBlockNames = j;
        const F = [ "pre", "script", "style", "textarea" ];
        z.htmlRawNames = F;
    }, {} ],
    99: [ function(D, h, z) {
        "use strict";
        function j(D) {
            return D.replace(/[\t\n\r ]+/g, " ").replace(/^ | $/g, "").toLowerCase().toUpperCase();
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.normalizeIdentifier = j;
    }, {} ],
    100: [ function(D, h, z) {
        "use strict";
        function j(D, h, z) {
            const j = [];
            let F = -1;
            while (++F < D.length) {
                const l = D[F].resolveAll;
                if (l && !j.includes(l)) h = l(h, z), j.push(l);
            }
            return h;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.resolveAll = j;
    }, {} ],
    101: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.subtokenize = F;
        var j = D("micromark-util-chunked");
        function F(D) {
            const h = {};
            let z = -1, F, Z, A, q, Q, I, E;
            while (++z < D.length) {
                while (z in h) z = h[z];
                if (F = D[z], z && F[1].type === "chunkFlow" && D[z - 1][1].type === "listItemPrefix") {
                    if (I = F[1]._tokenizer.events, A = 0, A < I.length && I[A][1].type === "lineEndingBlank") A += 2;
                    if (A < I.length && I[A][1].type === "content") while (++A < I.length) {
                        if (I[A][1].type === "content") break;
                        if (I[A][1].type === "chunkText") I[A][1]._isInFirstContentOfListItem = true, A++;
                    }
                }
                if (F[0] === "enter") {
                    if (F[1].contentType) Object.assign(h, l(D, z)), z = h[z], E = true;
                } else if (F[1]._container) {
                    A = z, Z = void 0;
                    while (A--) if (q = D[A], q[1].type === "lineEnding" || q[1].type === "lineEndingBlank") {
                        if (q[0] === "enter") {
                            if (Z) D[Z][1].type = "lineEndingBlank";
                            q[1].type = "lineEnding", Z = A;
                        }
                    } else break;
                    if (Z) F[1].end = Object.assign({}, D[Z][1].start), Q = D.slice(Z, z), Q.unshift(F),
                    (0, j.splice)(D, Z, z - Z + 1, Q);
                }
            }
            return !E;
        }
        function l(D, h) {
            const z = D[h][1], F = D[h][2];
            let l = h - 1;
            const Z = [], A = z._tokenizer || F.parser[z.contentType](z.start), q = A.events, Q = [], I = {};
            let E, X, f = -1, s = z, L = 0, P = 0;
            const x = [ P ];
            while (s) {
                while (D[++l][1] !== s) ;
                if (Z.push(l), !s._tokenizer) {
                    if (E = F.sliceStream(s), !s.next) E.push(null);
                    if (X) A.defineSkip(s.start);
                    if (s._isInFirstContentOfListItem) A._gfmTasklistFirstContentOfListItem = true;
                    if (A.write(E), s._isInFirstContentOfListItem) A._gfmTasklistFirstContentOfListItem = void 0;
                }
                X = s, s = s.next;
            }
            s = z;
            while (++f < q.length) if (q[f][0] === "exit" && q[f - 1][0] === "enter" && q[f][1].type === q[f - 1][1].type && q[f][1].start.line !== q[f][1].end.line) P = f + 1,
            x.push(P), s._tokenizer = void 0, s.previous = void 0, s = s.next;
            if (A.events = [], s) s._tokenizer = void 0, s.previous = void 0; else x.pop();
            f = x.length;
            while (f--) {
                const h = q.slice(x[f], x[f + 1]), z = Z.pop();
                Q.unshift([ z, z + h.length - 1 ]), (0, j.splice)(D, z, 2, h);
            }
            f = -1;
            while (++f < Q.length) I[L + Q[f][0]] = L + Q[f][1], L += Q[f][1] - Q[f][0] - 1;
            return I;
        }
    }, {
        "micromark-util-chunked": 93
    } ],
    102: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.text = z.string = z.insideSpan = z.flowInitial = z.flow = z.document = z.disable = z.contentInitial = z.attentionMarkers = void 0;
        var j = D("micromark-core-commonmark"), F = D("Ws");
        const l = {
            [42]: j.list,
            [43]: j.list,
            [45]: j.list,
            [48]: j.list,
            [49]: j.list,
            [50]: j.list,
            [51]: j.list,
            [52]: j.list,
            [53]: j.list,
            [54]: j.list,
            [55]: j.list,
            [56]: j.list,
            [57]: j.list,
            [62]: j.blockQuote
        };
        z.document = l;
        const Z = {
            [91]: j.definition
        };
        z.contentInitial = Z;
        const A = {
            [-2]: j.codeIndented,
            [-1]: j.codeIndented,
            [32]: j.codeIndented
        };
        z.flowInitial = A;
        const q = {
            [35]: j.headingAtx,
            [42]: j.thematicBreak,
            [45]: [ j.setextUnderline, j.thematicBreak ],
            [60]: j.htmlFlow,
            [61]: j.setextUnderline,
            [95]: j.thematicBreak,
            [96]: j.codeFenced,
            [126]: j.codeFenced
        };
        z.flow = q;
        const Q = {
            [38]: j.characterReference,
            [92]: j.characterEscape
        };
        z.string = Q;
        const I = {
            [-5]: j.lineEnding,
            [-4]: j.lineEnding,
            [-3]: j.lineEnding,
            [33]: j.labelStartImage,
            [38]: j.characterReference,
            [42]: j.attention,
            [60]: [ j.autolink, j.htmlText ],
            [91]: j.labelStartLink,
            [92]: [ j.hardBreakEscape, j.characterEscape ],
            [93]: j.labelEnd,
            [95]: j.attention,
            [96]: j.codeText
        };
        z.text = I;
        const E = {
            null: [ j.attention, F.resolver ]
        };
        z.insideSpan = E;
        const X = {
            null: [ 42, 95 ]
        };
        z.attentionMarkers = X;
        const f = {
            null: []
        };
        z.disable = f;
    }, {
        Ws: 107,
        "micromark-core-commonmark": 63
    } ],
    103: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.createTokenizer = Z;
        var j = D("micromark-util-character"), F = D("micromark-util-chunked"), l = D("micromark-util-resolve-all");
        function Z(D, h, z) {
            let Z = Object.assign(z ? Object.assign({}, z) : {
                line: 1,
                column: 1,
                offset: 0
            }, {
                _index: 0,
                _bufferIndex: -1
            });
            const Q = {}, I = [];
            let E = [], X = [], f = true;
            const s = {
                consume: c,
                enter: M,
                exit: S,
                attempt: v(T),
                check: v(e),
                interrupt: v(e, {
                    interrupt: true
                })
            }, L = {
                previous: null,
                code: null,
                containerState: {},
                events: [],
                parser: D,
                sliceStream: J,
                sliceSerialize: w,
                now: a,
                defineSkip: d,
                write: n
            };
            let P = h.tokenize.call(L, s), x;
            if (h.resolveAll) I.push(h);
            return L;
            function n(D) {
                if (E = (0, F.push)(E, D), H(), E[E.length - 1] !== null) return [];
                return m(h, 0), L.events = (0, l.resolveAll)(I, L.events, L), L.events;
            }
            function w(D, h) {
                return q(J(D), h);
            }
            function J(D) {
                return A(E, D);
            }
            function a() {
                return Object.assign({}, Z);
            }
            function d(D) {
                Q[D.line] = D.column, r();
            }
            function H() {
                let D;
                while (Z._index < E.length) {
                    const h = E[Z._index];
                    if (typeof h === "string") {
                        if (D = Z._index, Z._bufferIndex < 0) Z._bufferIndex = 0;
                        while (Z._index === D && Z._bufferIndex < h.length) K(h.charCodeAt(Z._bufferIndex));
                    } else K(h);
                }
            }
            function K(D) {
                f = void 0, x = D, P = P(D);
            }
            function c(D) {
                if ((0, j.markdownLineEnding)(D)) Z.line++, Z.column = 1, Z.offset += D === -3 ? 2 : 1,
                r(); else if (D !== -1) Z.column++, Z.offset++;
                if (Z._bufferIndex < 0) Z._index++; else if (Z._bufferIndex++, Z._bufferIndex === E[Z._index].length) Z._bufferIndex = -1,
                Z._index++;
                L.previous = D, f = true;
            }
            function M(D, h) {
                const z = h || {};
                return z.type = D, z.start = a(), L.events.push([ "enter", z, L ]), X.push(z), z;
            }
            function S(D) {
                const h = X.pop();
                return h.end = a(), L.events.push([ "exit", h, L ]), h;
            }
            function T(D, h) {
                m(D, h.from);
            }
            function e(D, h) {
                h.restore();
            }
            function v(D, h) {
                return z;
                function z(z, j, F) {
                    let l, Z, A, q;
                    return Array.isArray(z) ? I(z) : "tokenize" in z ? I([ z ]) : Q(z);
                    function Q(D) {
                        return h;
                        function h(h) {
                            const z = h !== null && D[h], j = h !== null && D.null, F = [ ...Array.isArray(z) ? z : z ? [ z ] : [], ...Array.isArray(j) ? j : j ? [ j ] : [] ];
                            return I(F)(h);
                        }
                    }
                    function I(D) {
                        if (l = D, Z = 0, D.length === 0) return F;
                        return E(D[Z]);
                    }
                    function E(D) {
                        return z;
                        function z(z) {
                            if (q = G(), A = D, !D.partial) L.currentConstruct = D;
                            if (D.name && L.parser.constructs.disable.null.includes(D.name)) return P(z);
                            return D.tokenize.call(h ? Object.assign(Object.create(L), h) : L, s, X, P)(z);
                        }
                    }
                    function X(h) {
                        return f = true, D(A, q), j;
                    }
                    function P(D) {
                        if (f = true, q.restore(), ++Z < l.length) return E(l[Z]);
                        return F;
                    }
                }
            }
            function m(D, h) {
                if (D.resolveAll && !I.includes(D)) I.push(D);
                if (D.resolve) (0, F.splice)(L.events, h, L.events.length - h, D.resolve(L.events.slice(h), L));
                if (D.resolveTo) L.events = D.resolveTo(L.events, L);
            }
            function G() {
                const D = a(), h = L.previous, z = L.currentConstruct, j = L.events.length, F = Array.from(X);
                return {
                    restore: l,
                    from: j
                };
                function l() {
                    Z = D, L.previous = h, L.currentConstruct = z, L.events.length = j, X = F, r();
                }
            }
            function r() {
                if (Z.line in Q && Z.column < 2) Z.column = Q[Z.line], Z.offset += Q[Z.line] - 1;
            }
        }
        function A(D, h) {
            const z = h.start._index, j = h.start._bufferIndex, F = h.end._index, l = h.end._bufferIndex;
            let Z;
            if (z === F) Z = [ D[z].slice(j, l) ]; else {
                if (Z = D.slice(z, F), j > -1) Z[0] = Z[0].slice(j);
                if (l > 0) Z.push(D[F].slice(0, l));
            }
            return Z;
        }
        function q(D, h) {
            let z = -1;
            const j = [];
            let F;
            while (++z < D.length) {
                const l = D[z];
                let Z;
                if (typeof l === "string") Z = l; else switch (l) {
                  case -5:
                    Z = "\r";
                    break;

                  case -4:
                    Z = "\n";
                    break;

                  case -3:
                    Z = "\r" + "\n";
                    break;

                  case -2:
                    Z = h ? " " : "\t";
                    break;

                  case -1:
                    if (!h && F) continue;
                    Z = " ";
                    break;

                  default:
                    Z = String.fromCharCode(l);
                }
                F = l === -2, j.push(Z);
            }
            return j.join("");
        }
    }, {
        "micromark-util-character": 91,
        "micromark-util-chunked": 93,
        "micromark-util-resolve-all": 100
    } ],
    104: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.content = void 0;
        var j = D("micromark-factory-space"), F = D("micromark-util-character");
        const l = {
            tokenize: Z
        };
        function Z(D) {
            const h = D.attempt(this.parser.constructs.contentInitial, l, Z);
            let z;
            return h;
            function l(z) {
                if (z === null) return void D.consume(z);
                return D.enter("lineEnding"), D.consume(z), D.exit("lineEnding"), (0, j.factorySpace)(D, h, "linePrefix");
            }
            function Z(h) {
                return D.enter("paragraph"), A(h);
            }
            function A(h) {
                const j = D.enter("chunkText", {
                    contentType: "text",
                    previous: z
                });
                if (z) z.next = j;
                return z = j, q(h);
            }
            function q(h) {
                if (h === null) return D.exit("chunkText"), D.exit("paragraph"), void D.consume(h);
                if ((0, F.markdownLineEnding)(h)) return D.consume(h), D.exit("chunkText"), A;
                return D.consume(h), q;
            }
        }
        z.content = l;
    }, {
        "micromark-factory-space": 88,
        "micromark-util-character": 91
    } ],
    105: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.document = void 0;
        var j = D("micromark-factory-space"), F = D("micromark-util-character"), l = D("micromark-util-chunked");
        const Z = {
            tokenize: q
        };
        z.document = Z;
        const A = {
            tokenize: Q
        };
        function q(D) {
            const h = this, z = [];
            let j = 0, Z, q, Q;
            return I;
            function I(F) {
                if (j < z.length) {
                    const l = z[j];
                    return h.containerState = l[1], D.attempt(l[0].continuation, E, X)(F);
                }
                return X(F);
            }
            function E(D) {
                if (j++, h.containerState._closeFlow) {
                    if (h.containerState._closeFlow = void 0, Z) a();
                    const z = h.events.length;
                    let F = z, A;
                    while (F--) if (h.events[F][0] === "exit" && h.events[F][1].type === "chunkFlow") {
                        A = h.events[F][1].end;
                        break;
                    }
                    J(j);
                    let q = z;
                    while (q < h.events.length) h.events[q][1].end = Object.assign({}, A), q++;
                    return (0, l.splice)(h.events, F + 1, 0, h.events.slice(z)), h.events.length = q,
                    X(D);
                }
                return I(D);
            }
            function X(F) {
                if (j === z.length) {
                    if (!Z) return L(F);
                    if (Z.currentConstruct && Z.currentConstruct.concrete) return x(F);
                    h.interrupt = Boolean(Z.currentConstruct && !Z._gfmTableDynamicInterruptHack);
                }
                return h.containerState = {}, D.check(A, f, s)(F);
            }
            function f(D) {
                if (Z) a();
                return J(j), L(D);
            }
            function s(D) {
                return h.parser.lazy[h.now().line] = j !== z.length, Q = h.now().offset, x(D);
            }
            function L(z) {
                return h.containerState = {}, D.attempt(A, P, x)(z);
            }
            function P(D) {
                return j++, z.push([ h.currentConstruct, h.containerState ]), L(D);
            }
            function x(z) {
                if (z === null) {
                    if (Z) a();
                    return J(0), void D.consume(z);
                }
                return Z = Z || h.parser.flow(h.now()), D.enter("chunkFlow", {
                    contentType: "flow",
                    previous: q,
                    _tokenizer: Z
                }), n(z);
            }
            function n(z) {
                if (z === null) return w(D.exit("chunkFlow"), true), J(0), void D.consume(z);
                if ((0, F.markdownLineEnding)(z)) return D.consume(z), w(D.exit("chunkFlow")), j = 0,
                h.interrupt = void 0, I;
                return D.consume(z), n;
            }
            function w(D, z) {
                const F = h.sliceStream(D);
                if (z) F.push(null);
                if (D.previous = q, q) q.next = D;
                if (q = D, Z.defineSkip(D.start), Z.write(F), h.parser.lazy[D.start.line]) {
                    let D = Z.events.length;
                    while (D--) if (Z.events[D][1].start.offset < Q && (!Z.events[D][1].end || Z.events[D][1].end.offset > Q)) return;
                    const z = h.events.length;
                    let F = z, A, q;
                    while (F--) if (h.events[F][0] === "exit" && h.events[F][1].type === "chunkFlow") {
                        if (A) {
                            q = h.events[F][1].end;
                            break;
                        }
                        A = true;
                    }
                    J(j), D = z;
                    while (D < h.events.length) h.events[D][1].end = Object.assign({}, q), D++;
                    (0, l.splice)(h.events, F + 1, 0, h.events.slice(z)), h.events.length = D;
                }
            }
            function J(j) {
                let F = z.length;
                while (F-- > j) {
                    const j = z[F];
                    h.containerState = j[1], j[0].exit.call(h, D);
                }
                z.length = j;
            }
            function a() {
                Z.write([ null ]), q = void 0, Z = void 0, h.containerState._closeFlow = void 0;
            }
        }
        function Q(D, h, z) {
            return (0, j.factorySpace)(D, D.attempt(this.parser.constructs.document, h, z), "linePrefix", this.parser.constructs.disable.null.includes("codeIndented") ? void 0 : 4);
        }
    }, {
        "micromark-factory-space": 88,
        "micromark-util-character": 91,
        "micromark-util-chunked": 93
    } ],
    106: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.flow = void 0;
        var j = D("micromark-core-commonmark"), F = D("micromark-factory-space"), l = D("micromark-util-character");
        const Z = {
            tokenize: A
        };
        function A(D) {
            const h = this, z = D.attempt(j.blankLine, l, D.attempt(this.parser.constructs.flowInitial, Z, (0,
            F.factorySpace)(D, D.attempt(this.parser.constructs.flow, Z, D.attempt(j.content, Z)), "linePrefix")));
            return z;
            function l(j) {
                if (j === null) return void D.consume(j);
                return D.enter("lineEndingBlank"), D.consume(j), D.exit("lineEndingBlank"), h.currentConstruct = void 0,
                z;
            }
            function Z(j) {
                if (j === null) return void D.consume(j);
                return D.enter("lineEnding"), D.consume(j), D.exit("lineEnding"), h.currentConstruct = void 0,
                z;
            }
        }
        z.flow = Z;
    }, {
        "micromark-core-commonmark": 63,
        "micromark-factory-space": 88,
        "micromark-util-character": 91
    } ],
    107: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.text = z.string = z.resolver = void 0;
        const j = {
            resolveAll: A()
        };
        z.resolver = j;
        const F = Z("string");
        z.string = F;
        const l = Z("text");
        function Z(D) {
            return {
                tokenize: h,
                resolveAll: A(D === "text" ? q : void 0)
            };
            function h(h) {
                const z = this, j = this.parser.constructs[D], F = h.attempt(j, l, Z);
                return l;
                function l(D) {
                    return q(D) ? F(D) : Z(D);
                }
                function Z(D) {
                    if (D === null) return void h.consume(D);
                    return h.enter("data"), h.consume(D), A;
                }
                function A(D) {
                    if (q(D)) return h.exit("data"), F(D);
                    return h.consume(D), A;
                }
                function q(D) {
                    if (D === null) return true;
                    const h = j[D];
                    let F = -1;
                    if (h) while (++F < h.length) {
                        const D = h[F];
                        if (!D.previous || D.previous.call(z, z.previous)) return true;
                    }
                    return false;
                }
            }
        }
        function A(D) {
            return h;
            function h(h, z) {
                let j = -1, F;
                while (++j <= h.length) if (F === void 0) {
                    if (h[j] && h[j][1].type === "data") F = j, j++;
                } else if (!h[j] || h[j][1].type !== "data") {
                    if (j !== F + 2) h[F][1].end = h[j - 1][1].end, h.splice(F + 2, j - F - 2), j = F + 2;
                    F = void 0;
                }
                return D ? D(h, z) : h;
            }
        }
        function q(D, h) {
            let z = 0;
            while (++z <= D.length) if ((z === D.length || D[z][1].type === "lineEnding") && D[z - 1][1].type === "data") {
                const j = D[z - 1][1], F = h.sliceStream(j);
                let l = F.length, Z = -1, A = 0, q;
                while (l--) {
                    const D = F[l];
                    if (typeof D === "string") {
                        Z = D.length;
                        while (D.charCodeAt(Z - 1) === 32) A++, Z--;
                        if (Z) break;
                        Z = -1;
                    } else if (D === -2) q = true, A++; else if (D === -1) ; else {
                        l++;
                        break;
                    }
                }
                if (A) {
                    const F = {
                        type: z === D.length || q || A < 2 ? "lineSuffix" : "hardBreakTrailing",
                        start: {
                            line: j.end.line,
                            column: j.end.column - A,
                            offset: j.end.offset - A,
                            _index: j.start._index + l,
                            _bufferIndex: l ? Z : j.start._bufferIndex + Z
                        },
                        end: Object.assign({}, j.end)
                    };
                    if (j.end = Object.assign({}, F.start), j.start.offset === j.end.offset) Object.assign(j, F); else D.splice(z, 0, [ "enter", F, h ], [ "exit", F, h ]),
                    z += 2;
                }
                z++;
            }
            return D;
        }
        z.text = l;
    }, {} ],
    108: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.parse = X;
        var j = D("micromark-util-combine-extensions"), F = D("1I"), l = D("w8"), Z = D("JH"), A = D("Ws"), q = D("vh"), Q = E(D("5m"));
        function I(D) {
            if (typeof WeakMap !== "function") return null;
            var h = new WeakMap, z = new WeakMap;
            return (I = function(D) {
                return D ? z : h;
            })(D);
        }
        function E(D, h) {
            if (!h && D && D.__esModule) return D;
            if (D === null || typeof D !== "object" && typeof D !== "function") return {
                default: D
            };
            var z = I(h);
            if (z && z.has(D)) return z.get(D);
            var j = {}, F = Object.defineProperty && Object.getOwnPropertyDescriptor;
            for (var l in D) if (l !== "default" && Object.prototype.hasOwnProperty.call(D, l)) {
                var Z = F ? Object.getOwnPropertyDescriptor(D, l) : null;
                if (Z && (Z.get || Z.set)) Object.defineProperty(j, l, Z); else j[l] = D[l];
            }
            if (j.default = D, z) z.set(D, j);
            return j;
        }
        function X(D = {}) {
            const h = (0, j.combineExtensions)([ Q ].concat(D.extensions || [])), z = {
                defined: [],
                lazy: {},
                constructs: h,
                content: I(F.content),
                document: I(l.document),
                flow: I(Z.flow),
                string: I(A.string),
                text: I(A.text)
            };
            return z;
            function I(D) {
                return h;
                function h(h) {
                    return (0, q.createTokenizer)(z, D, h);
                }
            }
        }
    }, {
        "5m": 102,
        vh: 103,
        "1I": 104,
        w8: 105,
        JH: 106,
        Ws: 107,
        "micromark-util-combine-extensions": 95
    } ],
    109: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.postprocess = F;
        var j = D("micromark-util-subtokenize");
        function F(D) {
            while (!(0, j.subtokenize)(D)) ;
            return D;
        }
    }, {
        "micromark-util-subtokenize": 101
    } ],
    110: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.preprocess = F;
        const j = /[\0\t\n\r]/g;
        function F() {
            let D = 1, h = "", z = true, F;
            return l;
            function l(l, Z, A) {
                const q = [];
                let Q, I, E, X, f;
                if (l = h + l.toString(Z), E = 0, h = "", z) {
                    if (l.charCodeAt(0) === 65279) E++;
                    z = void 0;
                }
                while (E < l.length) {
                    if (j.lastIndex = E, Q = j.exec(l), X = Q && Q.index !== void 0 ? Q.index : l.length,
                    f = l.charCodeAt(X), !Q) {
                        h = l.slice(E);
                        break;
                    }
                    if (f === 10 && E === X && F) q.push(-3), F = void 0; else {
                        if (F) q.push(-5), F = void 0;
                        if (E < X) q.push(l.slice(E, X)), D += X - E;
                        switch (f) {
                          case 0:
                            q.push(65533), D++;
                            break;

                          case 9:
                            I = Math.ceil(D / 4) * 4, q.push(-2);
                            while (D++ < I) q.push(-1);
                            break;

                          case 10:
                            q.push(-4), D = 1;
                            break;

                          default:
                            F = true, D = 1;
                        }
                    }
                    E = X + 1;
                }
                if (A) {
                    if (F) q.push(-5);
                    if (h) q.push(h);
                    q.push(null);
                }
                return q;
            }
        }
    }, {} ],
    111: [ function(D, h, z) {
        "use strict";
        h.exports = () => {
            const D = {};
            return D.promise = new Promise(((h, z) => {
                D.resolve = h, D.reject = z;
            })), D;
        };
    }, {} ],
    112: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.TimeoutError = z.AbortError = void 0, z.default = A;
        class j extends Error {
            constructor(D) {
                super(D), this.name = "TimeoutError";
            }
        }
        z.TimeoutError = j;
        class F extends Error {
            constructor(D) {
                super(), this.name = "AbortError", this.message = D;
            }
        }
        z.AbortError = F;
        const l = D => globalThis.DOMException === void 0 ? new F(D) : new DOMException(D), Z = D => {
            const h = D.reason === void 0 ? l("This operation was aborted.") : D.reason;
            return h instanceof Error ? h : l(h);
        };
        function A(D, h) {
            const {milliseconds: z, fallback: F, message: l, customTimers: A = {
                setTimeout: setTimeout,
                clearTimeout: clearTimeout
            }} = h;
            let q;
            const Q = new Promise(((Q, I) => {
                if (typeof z !== "number" || Math.sign(z) !== 1) throw new TypeError(`Expected \`milliseconds\` to be a positive number, got \`${z}\``);
                if (z === Number.POSITIVE_INFINITY) return void Q(D);
                if (h.signal) {
                    const {signal: D} = h;
                    if (D.aborted) I(Z(D));
                    D.addEventListener("abort", (() => {
                        I(Z(D));
                    }));
                }
                q = A.setTimeout.call(void 0, (() => {
                    if (F) {
                        try {
                            Q(F());
                        } catch (D) {
                            I(D);
                        }
                        return;
                    }
                    if (typeof D.cancel === "function") D.cancel();
                    if (l === false) Q(); else if (l instanceof Error) I(l); else {
                        const D = l ?? `Promise timed out after ${z} milliseconds`;
                        I(new j(D));
                    }
                }), z), (async () => {
                    try {
                        Q(await D);
                    } catch (D) {
                        I(D);
                    } finally {
                        A.clearTimeout.call(void 0, q);
                    }
                })();
            }));
            return Q.clear = () => {
                A.clearTimeout.call(void 0, q), q = void 0;
            }, Q;
        }
    }, {} ],
    113: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.default = void 0;
        var j = F(D("k8"));
        function F(D) {
            return D && D.__esModule ? D : {
                default: D
            };
        }
        var l = j.default;
        z.default = l;
    }, {
        k8: 114
    } ],
    114: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.default = F;
        var j = D("mdast-util-from-markdown");
        function F(D) {
            const h = h => {
                const z = this.data("settings");
                return (0, j.fromMarkdown)(h, Object.assign({}, z, D, {
                    extensions: this.data("micromarkExtensions") || [],
                    mdastExtensions: this.data("fromMarkdownExtensions") || []
                }));
            };
            Object.assign(this, {
                Parser: h
            });
        }
    }, {
        "mdast-util-from-markdown": 11
    } ],
    115: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.default = void 0;
        var j = F(D("k8"));
        function F(D) {
            return D && D.__esModule ? D : {
                default: D
            };
        }
        var l = j.default;
        z.default = l;
    }, {
        k8: 116
    } ],
    116: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.default = F;
        var j = D("mdast-util-to-markdown");
        function F(D) {
            const h = h => {
                const z = this.data("settings");
                return (0, j.toMarkdown)(h, Object.assign({}, z, D, {
                    extensions: this.data("toMarkdownExtensions") || []
                }));
            };
            Object.assign(this, {
                Compiler: h
            });
        }
    }, {
        "mdast-util-to-markdown": 15
    } ],
    117: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.remark = void 0;
        var j = D("unified"), F = Z(D("remark-parse")), l = Z(D("remark-stringify"));
        function Z(D) {
            return D && D.__esModule ? D : {
                default: D
            };
        }
        const A = (0, j.unified)().use(F.default).use(l.default).freeze();
        z.remark = A;
    }, {
        "remark-parse": 113,
        "remark-stringify": 115,
        unified: 120
    } ],
    118: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.default = l;
        const j = {
            heading: Q,
            text: q,
            inlineCode: q,
            image: A,
            imageReference: A,
            break: E,
            blockquote: I,
            list: I,
            listItem: I,
            strong: I,
            emphasis: I,
            delete: I,
            link: I,
            linkReference: I,
            code: X,
            thematicBreak: X,
            html: X,
            table: X,
            tableCell: X,
            definition: X,
            yaml: X,
            toml: X,
            footnoteReference: X,
            footnoteDefinition: X
        }, F = {}.hasOwnProperty;
        function l(D = {}) {
            const h = Object.assign({}, j), z = D.remove || [], l = D.keep || [];
            let A = -1;
            while (++A < z.length) {
                const D = z[A];
                if (Array.isArray(D)) h[D[0]] = D[1]; else h[D] = X;
            }
            let q = {};
            if (l.length === 0) q = h; else {
                let D;
                for (D in h) if (!l.includes(D)) q[D] = h[D];
                A = -1;
                while (++A < l.length) if (D = l[A], !F.call(h, D)) throw new Error("Invalid `keep` option: No modifier is defined for node type `" + D + "`");
            }
            return Q;
            function Q(D) {
                const h = D.type;
                let z = D;
                if (h in q) {
                    const D = q[h];
                    if (D) z = D(z);
                }
                if (z = Array.isArray(z) ? I(z) : z, "children" in z) z.children = I(z.children);
                return z;
            }
            function I(D) {
                let h = -1;
                const z = [];
                while (++h < D.length) {
                    const j = Q(D[h]);
                    if (Array.isArray(j)) z.push(...j.flatMap((D => Q(D)))); else z.push(j);
                }
                return Z(z);
            }
        }
        function Z(D) {
            let h = -1;
            const z = [];
            let j;
            while (++h < D.length) {
                const F = D[h];
                if (j && F.type === j.type && "value" in F) j.value += F.value; else z.push(F),
                j = F;
            }
            return z;
        }
        function A(D) {
            const h = "title" in D ? D.title : "";
            return {
                type: "text",
                value: D.alt || h || ""
            };
        }
        function q(D) {
            return {
                type: "text",
                value: D.value
            };
        }
        function Q(D) {
            return {
                type: "paragraph",
                children: D.children
            };
        }
        function I(D) {
            return D.children || [];
        }
        function E() {
            return {
                type: "text",
                value: "\n"
            };
        }
        function X() {
            return {
                type: "text",
                value: ""
            };
        }
    }, {} ],
    119: [ function(D, h, z) {
        "use strict";
        function j() {
            const D = [], h = {
                run: z,
                use: j
            };
            return h;
            function z(...h) {
                let z = -1;
                const j = h.pop();
                if (typeof j !== "function") throw new TypeError("Expected function as last argument, not " + j);
                function l(Z, ...A) {
                    const q = D[++z];
                    let Q = -1;
                    if (Z) return void j(Z);
                    while (++Q < h.length) if (A[Q] === null || A[Q] === void 0) A[Q] = h[Q];
                    if (h = A, q) F(q, l)(...A); else j(null, ...A);
                }
                l(null, ...h);
            }
            function j(z) {
                if (typeof z !== "function") throw new TypeError("Expected `middelware` to be a function, not " + z);
                return D.push(z), h;
            }
        }
        function F(D, h) {
            let z;
            return j;
            function j(...h) {
                const j = D.length > h.length;
                let Z;
                if (j) h.push(F);
                try {
                    Z = D.apply(this, h);
                } catch (D) {
                    const h = D;
                    if (j && z) throw h;
                    return F(h);
                }
                if (!j) if (Z instanceof Promise) Z.then(l, F); else if (Z instanceof Error) F(Z); else l(Z);
            }
            function F(D, ...j) {
                if (!z) z = true, h(D, ...j);
            }
            function l(D) {
                F(null, D);
            }
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.trough = j, z.wrap = F;
    }, {} ],
    120: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), Object.defineProperty(z, "unified", {
            enumerable: true,
            get: function() {
                return j.unified;
            }
        });
        var j = D("k8");
    }, {
        k8: 121
    } ],
    121: [ function(D, h, z) {
        (function(h) {
            (function() {
                "use strict";
                Object.defineProperty(z, "__esModule", {
                    value: true
                }), z.unified = void 0;
                var h = D("bail"), j = q(D("is-buffer")), F = q(D("extend")), l = q(D("is-plain-obj")), Z = D("trough"), A = D("vfile");
                function q(D) {
                    return D && D.__esModule ? D : {
                        default: D
                    };
                }
                const Q = E().freeze();
                z.unified = Q;
                const I = {}.hasOwnProperty;
                function E() {
                    const D = (0, Z.trough)(), z = [];
                    let j = {}, A, q = -1;
                    return Q.data = f, Q.Parser = void 0, Q.Compiler = void 0, Q.freeze = J, Q.attachers = z,
                    Q.use = d, Q.parse = H, Q.stringify = K, Q.run = c, Q.runSync = M, Q.process = S,
                    Q.processSync = T, Q;
                    function Q() {
                        const D = E();
                        let h = -1;
                        while (++h < z.length) D.use(...z[h]);
                        return D.data((0, F.default)(true, {}, j)), D;
                    }
                    function f(D, h) {
                        if (typeof D === "string") {
                            if (arguments.length === 2) return P("data", A), j[D] = h, Q;
                            return I.call(j, D) && j[D] || null;
                        }
                        if (D) return P("data", A), j = D, Q;
                        return j;
                    }
                    function J() {
                        if (A) return Q;
                        while (++q < z.length) {
                            const [h, ...j] = z[q];
                            if (j[0] === false) continue;
                            if (j[0] === true) j[0] = void 0;
                            const F = h.call(Q, ...j);
                            if (typeof F === "function") D.use(F);
                        }
                        return A = true, q = Number.POSITIVE_INFINITY, Q;
                    }
                    function d(D, ...h) {
                        let Z;
                        if (P("use", A), D === null || D === void 0) ; else if (typeof D === "function") X(D, ...h); else if (typeof D === "object") if (Array.isArray(D)) E(D); else I(D); else throw new TypeError("Expected usable value, not `" + D + "`");
                        if (Z) j.settings = Object.assign(j.settings || {}, Z);
                        return Q;
                        function q(D) {
                            if (typeof D === "function") X(D); else if (typeof D === "object") if (Array.isArray(D)) {
                                const [h, ...z] = D;
                                X(h, ...z);
                            } else I(D); else throw new TypeError("Expected usable value, not `" + D + "`");
                        }
                        function I(D) {
                            if (E(D.plugins), D.settings) Z = Object.assign(Z || {}, D.settings);
                        }
                        function E(D) {
                            let h = -1;
                            if (D === null || D === void 0) ; else if (Array.isArray(D)) while (++h < D.length) {
                                const z = D[h];
                                q(z);
                            } else throw new TypeError("Expected a list of plugins, not `" + D + "`");
                        }
                        function X(D, h) {
                            let j = -1, Z;
                            while (++j < z.length) if (z[j][0] === D) {
                                Z = z[j];
                                break;
                            }
                            if (Z) {
                                if ((0, l.default)(Z[1]) && (0, l.default)(h)) h = (0, F.default)(true, Z[1], h);
                                Z[1] = h;
                            } else z.push([ ...arguments ]);
                        }
                    }
                    function H(D) {
                        Q.freeze();
                        const h = w(D), z = Q.Parser;
                        if (s("parse", z), X(z, "parse")) return new z(String(h), h).parse();
                        return z(String(h), h);
                    }
                    function K(D, h) {
                        Q.freeze();
                        const z = w(h), j = Q.Compiler;
                        if (L("stringify", j), x(D), X(j, "compile")) return new j(D, z).compile();
                        return j(D, z);
                    }
                    function c(h, z, j) {
                        if (x(h), Q.freeze(), !j && typeof z === "function") j = z, z = void 0;
                        if (!j) return new Promise(F);
                        function F(F, l) {
                            function Z(D, z, Z) {
                                if (z = z || h, D) l(D); else if (F) F(z); else j(null, z, Z);
                            }
                            D.run(h, w(z), Z);
                        }
                        F(null, j);
                    }
                    function M(D, z) {
                        let j, F;
                        return Q.run(D, z, l), n("runSync", "run", F), j;
                        function l(D, z) {
                            (0, h.bail)(D), j = z, F = true;
                        }
                    }
                    function S(D, h) {
                        if (Q.freeze(), s("process", Q.Parser), L("process", Q.Compiler), !h) return new Promise(z);
                        function z(z, j) {
                            const F = w(D);
                            function l(D, F) {
                                if (D || !F) j(D); else if (z) z(F); else h(null, F);
                            }
                            Q.run(Q.parse(F), F, ((D, h, z) => {
                                if (D || !h || !z) l(D); else {
                                    const j = Q.stringify(h, z);
                                    if (j === void 0 || j === null) ; else if (a(j)) z.value = j; else z.result = j;
                                    l(D, z);
                                }
                            }));
                        }
                        z(null, h);
                    }
                    function T(D) {
                        let z;
                        Q.freeze(), s("processSync", Q.Parser), L("processSync", Q.Compiler);
                        const j = w(D);
                        return Q.process(j, F), n("processSync", "process", z), j;
                        function F(D) {
                            z = true, (0, h.bail)(D);
                        }
                    }
                }
                function X(D, h) {
                    return typeof D === "function" && D.prototype && (f(D.prototype) || h in D.prototype);
                }
                function f(D) {
                    let h;
                    for (h in D) if (I.call(D, h)) return true;
                    return false;
                }
                function s(D, h) {
                    if (typeof h !== "function") throw new TypeError("Cannot `" + D + "` without `Parser`");
                }
                function L(D, h) {
                    if (typeof h !== "function") throw new TypeError("Cannot `" + D + "` without `Compiler`");
                }
                function P(D, h) {
                    if (h) throw new Error("Cannot call `" + D + "` on a frozen processor.\nCreate a new processor first, by calling it: use `processor()` instead of `processor`.");
                }
                function x(D) {
                    if (!(0, l.default)(D) || typeof D.type !== "string") throw new TypeError("Expected node, got `" + D + "`");
                }
                function n(D, h, z) {
                    if (!z) throw new Error("`" + D + "` finished async. Use `" + h + "` instead");
                }
                function w(D) {
                    return J(D) ? D : new A.VFile(D);
                }
                function J(D) {
                    return Boolean(D && typeof D === "object" && "message" in D && "messages" in D);
                }
                function a(D) {
                    return typeof D === "string" || (0, j.default)(D);
                }
            }).call(this);
        }).call(this, D("_process"));
    }, {
        _process: 1,
        bail: 2,
        extend: 7,
        "is-buffer": 122,
        "is-plain-obj": 8,
        trough: 119,
        vfile: 145
    } ],
    122: [ function(D, h, z) {
        "use strict";
        h.exports = function D(h) {
            return h != null && h.constructor != null && typeof h.constructor.isBuffer === "function" && h.constructor.isBuffer(h);
        };
    }, {} ],
    123: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.is = z.convert = void 0;
        const j = function D(h, z, j, l, Z) {
            const A = F(z);
            if (j !== void 0 && j !== null && (typeof j !== "number" || j < 0 || j === Number.POSITIVE_INFINITY)) throw new Error("Expected positive finite index");
            if (l !== void 0 && l !== null && (!D(l) || !l.children)) throw new Error("Expected parent node");
            if ((l === void 0 || l === null) !== (j === void 0 || j === null)) throw new Error("Expected both parent and index");
            return h && h.type && typeof h.type === "string" ? Boolean(A.call(Z, h, j, l)) : false;
        };
        z.is = j;
        const F = function(D) {
            if (D === void 0 || D === null) return Q;
            if (typeof D === "string") return A(D);
            if (typeof D === "object") return Array.isArray(D) ? l(D) : Z(D);
            if (typeof D === "function") return q(D);
            throw new Error("Expected function, string, or object as test");
        };
        function l(D) {
            const h = [];
            let z = -1;
            while (++z < D.length) h[z] = F(D[z]);
            return q(j);
            function j(...D) {
                let z = -1;
                while (++z < h.length) if (h[z].call(this, ...D)) return true;
                return false;
            }
        }
        function Z(D) {
            return q(h);
            function h(h) {
                let z;
                for (z in D) if (h[z] !== D[z]) return false;
                return true;
            }
        }
        function A(D) {
            return q(h);
            function h(h) {
                return h && h.type === D;
            }
        }
        function q(D) {
            return h;
            function h(...h) {
                return Boolean(D.call(this, ...h));
            }
        }
        function Q() {
            return true;
        }
        z.convert = F;
    }, {} ],
    124: [ function(D, h, z) {
        "use strict";
        function j(D) {
            if (!D || typeof D !== "object") return "";
            if ("position" in D || "type" in D) return l(D.position);
            if ("start" in D || "end" in D) return l(D);
            if ("line" in D || "column" in D) return F(D);
            return "";
        }
        function F(D) {
            return Z(D && D.line) + ":" + Z(D && D.column);
        }
        function l(D) {
            return F(D && D.start) + "-" + F(D && D.end);
        }
        function Z(D) {
            return D && typeof D === "number" ? D : 1;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.stringifyPosition = j;
    }, {} ],
    125: [ function(D, h, z) {
        "use strict";
        function j(D) {
            return D;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.color = j;
    }, {} ],
    126: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.visitParents = z.SKIP = z.EXIT = z.CONTINUE = void 0;
        var j = D("unist-util-is"), F = D("Ro");
        const l = true;
        z.CONTINUE = l;
        const Z = "skip";
        z.SKIP = Z;
        const A = false;
        z.EXIT = A;
        const q = function(D, h, z, l) {
            if (typeof h === "function" && typeof z !== "function") l = z, z = h, h = null;
            const q = (0, j.convert)(h), I = l ? -1 : 1;
            function E(D, j, X) {
                const f = typeof D === "object" && D !== null ? D : {};
                let s;
                if (typeof f.type === "string") s = typeof f.tagName === "string" ? f.tagName : typeof f.name === "string" ? f.name : void 0,
                Object.defineProperty(L, "name", {
                    value: "node (" + (0, F.color)(f.type + (s ? "<" + s + ">" : "")) + ")"
                });
                return L;
                function L() {
                    let F = [], f, s, L;
                    if (!h || q(D, j, X[X.length - 1] || null)) if (F = Q(z(D, X)), F[0] === A) return F;
                    if (D.children && F[0] !== Z) {
                        s = (l ? D.children.length : -1) + I, L = X.concat(D);
                        while (s > -1 && s < D.children.length) {
                            if (f = E(D.children[s], s, L)(), f[0] === A) return f;
                            s = typeof f[1] === "number" ? f[1] : s + I;
                        }
                    }
                    return F;
                }
            }
            E(D, null, [])();
        };
        function Q(D) {
            if (Array.isArray(D)) return D;
            if (typeof D === "number") return [ l, D ];
            return [ D ];
        }
        z.visitParents = q;
    }, {
        Ro: 125,
        "unist-util-is": 123
    } ],
    127: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), Object.defineProperty(z, "CONTINUE", {
            enumerable: true,
            get: function() {
                return j.CONTINUE;
            }
        }), Object.defineProperty(z, "EXIT", {
            enumerable: true,
            get: function() {
                return j.EXIT;
            }
        }), Object.defineProperty(z, "SKIP", {
            enumerable: true,
            get: function() {
                return j.SKIP;
            }
        }), z.visit = void 0;
        var j = D("unist-util-visit-parents");
        const F = function(D, h, z, F) {
            if (typeof h === "function" && typeof z !== "function") F = z, z = h, h = null;
            function l(D, h) {
                const j = h[h.length - 1];
                return z(D, j ? j.children.indexOf(D) : null, j);
            }
            (0, j.visitParents)(D, h, l, F);
        };
        z.visit = F;
    }, {
        "unist-util-visit-parents": 126
    } ],
    128: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), Object.defineProperty(z, "NIL", {
            enumerable: true,
            get: function() {
                return A.default;
            }
        }), Object.defineProperty(z, "parse", {
            enumerable: true,
            get: function() {
                return E.default;
            }
        }), Object.defineProperty(z, "stringify", {
            enumerable: true,
            get: function() {
                return I.default;
            }
        }), Object.defineProperty(z, "v1", {
            enumerable: true,
            get: function() {
                return j.default;
            }
        }), Object.defineProperty(z, "v3", {
            enumerable: true,
            get: function() {
                return F.default;
            }
        }), Object.defineProperty(z, "v4", {
            enumerable: true,
            get: function() {
                return l.default;
            }
        }), Object.defineProperty(z, "v5", {
            enumerable: true,
            get: function() {
                return Z.default;
            }
        }), Object.defineProperty(z, "validate", {
            enumerable: true,
            get: function() {
                return Q.default;
            }
        }), Object.defineProperty(z, "version", {
            enumerable: true,
            get: function() {
                return q.default;
            }
        });
        var j = X(D("Y5")), F = X(D("4P")), l = X(D("ti")), Z = X(D("QH")), A = X(D("9n")), q = X(D("PD")), Q = X(D("p0")), I = X(D("Jc")), E = X(D("Ui"));
        function X(D) {
            return D && D.__esModule ? D : {
                default: D
            };
        }
    }, {
        "9n": 131,
        Ui: 132,
        Jc: 136,
        Y5: 137,
        "4P": 138,
        ti: 140,
        QH: 141,
        p0: 142,
        PD: 143
    } ],
    129: [ function(D, h, z) {
        "use strict";
        function j(D) {
            if (typeof D === "string") {
                const h = unescape(encodeURIComponent(D));
                D = new Uint8Array(h.length);
                for (let z = 0; z < h.length; ++z) D[z] = h.charCodeAt(z);
            }
            return F(Z(A(D), D.length * 8));
        }
        function F(D) {
            const h = [], z = D.length * 32, j = "0123456789abcdef";
            for (let F = 0; F < z; F += 8) {
                const z = D[F >> 5] >>> F % 32 & 255, l = parseInt(j.charAt(z >>> 4 & 15) + j.charAt(z & 15), 16);
                h.push(l);
            }
            return h;
        }
        function l(D) {
            return (D + 64 >>> 9 << 4) + 14 + 1;
        }
        function Z(D, h) {
            D[h >> 5] |= 128 << h % 32, D[l(h) - 1] = h;
            let z = 1732584193, j = -271733879, F = -1732584194, Z = 271733878;
            for (let h = 0; h < D.length; h += 16) {
                const l = z, A = j, Q = F, I = Z;
                z = E(z, j, F, Z, D[h], 7, -680876936), Z = E(Z, z, j, F, D[h + 1], 12, -389564586),
                F = E(F, Z, z, j, D[h + 2], 17, 606105819), j = E(j, F, Z, z, D[h + 3], 22, -1044525330),
                z = E(z, j, F, Z, D[h + 4], 7, -176418897), Z = E(Z, z, j, F, D[h + 5], 12, 1200080426),
                F = E(F, Z, z, j, D[h + 6], 17, -1473231341), j = E(j, F, Z, z, D[h + 7], 22, -45705983),
                z = E(z, j, F, Z, D[h + 8], 7, 1770035416), Z = E(Z, z, j, F, D[h + 9], 12, -1958414417),
                F = E(F, Z, z, j, D[h + 10], 17, -42063), j = E(j, F, Z, z, D[h + 11], 22, -1990404162),
                z = E(z, j, F, Z, D[h + 12], 7, 1804603682), Z = E(Z, z, j, F, D[h + 13], 12, -40341101),
                F = E(F, Z, z, j, D[h + 14], 17, -1502002290), j = E(j, F, Z, z, D[h + 15], 22, 1236535329),
                z = X(z, j, F, Z, D[h + 1], 5, -165796510), Z = X(Z, z, j, F, D[h + 6], 9, -1069501632),
                F = X(F, Z, z, j, D[h + 11], 14, 643717713), j = X(j, F, Z, z, D[h], 20, -373897302),
                z = X(z, j, F, Z, D[h + 5], 5, -701558691), Z = X(Z, z, j, F, D[h + 10], 9, 38016083),
                F = X(F, Z, z, j, D[h + 15], 14, -660478335), j = X(j, F, Z, z, D[h + 4], 20, -405537848),
                z = X(z, j, F, Z, D[h + 9], 5, 568446438), Z = X(Z, z, j, F, D[h + 14], 9, -1019803690),
                F = X(F, Z, z, j, D[h + 3], 14, -187363961), j = X(j, F, Z, z, D[h + 8], 20, 1163531501),
                z = X(z, j, F, Z, D[h + 13], 5, -1444681467), Z = X(Z, z, j, F, D[h + 2], 9, -51403784),
                F = X(F, Z, z, j, D[h + 7], 14, 1735328473), j = X(j, F, Z, z, D[h + 12], 20, -1926607734),
                z = f(z, j, F, Z, D[h + 5], 4, -378558), Z = f(Z, z, j, F, D[h + 8], 11, -2022574463),
                F = f(F, Z, z, j, D[h + 11], 16, 1839030562), j = f(j, F, Z, z, D[h + 14], 23, -35309556),
                z = f(z, j, F, Z, D[h + 1], 4, -1530992060), Z = f(Z, z, j, F, D[h + 4], 11, 1272893353),
                F = f(F, Z, z, j, D[h + 7], 16, -155497632), j = f(j, F, Z, z, D[h + 10], 23, -1094730640),
                z = f(z, j, F, Z, D[h + 13], 4, 681279174), Z = f(Z, z, j, F, D[h], 11, -358537222),
                F = f(F, Z, z, j, D[h + 3], 16, -722521979), j = f(j, F, Z, z, D[h + 6], 23, 76029189),
                z = f(z, j, F, Z, D[h + 9], 4, -640364487), Z = f(Z, z, j, F, D[h + 12], 11, -421815835),
                F = f(F, Z, z, j, D[h + 15], 16, 530742520), j = f(j, F, Z, z, D[h + 2], 23, -995338651),
                z = s(z, j, F, Z, D[h], 6, -198630844), Z = s(Z, z, j, F, D[h + 7], 10, 1126891415),
                F = s(F, Z, z, j, D[h + 14], 15, -1416354905), j = s(j, F, Z, z, D[h + 5], 21, -57434055),
                z = s(z, j, F, Z, D[h + 12], 6, 1700485571), Z = s(Z, z, j, F, D[h + 3], 10, -1894986606),
                F = s(F, Z, z, j, D[h + 10], 15, -1051523), j = s(j, F, Z, z, D[h + 1], 21, -2054922799),
                z = s(z, j, F, Z, D[h + 8], 6, 1873313359), Z = s(Z, z, j, F, D[h + 15], 10, -30611744),
                F = s(F, Z, z, j, D[h + 6], 15, -1560198380), j = s(j, F, Z, z, D[h + 13], 21, 1309151649),
                z = s(z, j, F, Z, D[h + 4], 6, -145523070), Z = s(Z, z, j, F, D[h + 11], 10, -1120210379),
                F = s(F, Z, z, j, D[h + 2], 15, 718787259), j = s(j, F, Z, z, D[h + 9], 21, -343485551),
                z = q(z, l), j = q(j, A), F = q(F, Q), Z = q(Z, I);
            }
            return [ z, j, F, Z ];
        }
        function A(D) {
            if (D.length === 0) return [];
            const h = D.length * 8, z = new Uint32Array(l(h));
            for (let j = 0; j < h; j += 8) z[j >> 5] |= (D[j / 8] & 255) << j % 32;
            return z;
        }
        function q(D, h) {
            const z = (D & 65535) + (h & 65535), j = (D >> 16) + (h >> 16) + (z >> 16);
            return j << 16 | z & 65535;
        }
        function Q(D, h) {
            return D << h | D >>> 32 - h;
        }
        function I(D, h, z, j, F, l) {
            return q(Q(q(q(h, D), q(j, l)), F), z);
        }
        function E(D, h, z, j, F, l, Z) {
            return I(h & z | ~h & j, D, h, F, l, Z);
        }
        function X(D, h, z, j, F, l, Z) {
            return I(h & j | z & ~j, D, h, F, l, Z);
        }
        function f(D, h, z, j, F, l, Z) {
            return I(h ^ z ^ j, D, h, F, l, Z);
        }
        function s(D, h, z, j, F, l, Z) {
            return I(z ^ (h | ~j), D, h, F, l, Z);
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.default = void 0;
        var L = j;
        z.default = L;
    }, {} ],
    130: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.default = void 0;
        const j = typeof crypto !== "undefined" && crypto.randomUUID && crypto.randomUUID.bind(crypto);
        var F = {
            randomUUID: j
        };
        z.default = F;
    }, {} ],
    131: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.default = void 0;
        var j = "00000000-0000-0000-0000-000000000000";
        z.default = j;
    }, {} ],
    132: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.default = void 0;
        var j = F(D("p0"));
        function F(D) {
            return D && D.__esModule ? D : {
                default: D
            };
        }
        function l(D) {
            if (!(0, j.default)(D)) throw TypeError("Invalid UUID");
            let h;
            const z = new Uint8Array(16);
            return z[0] = (h = parseInt(D.slice(0, 8), 16)) >>> 24, z[1] = h >>> 16 & 255, z[2] = h >>> 8 & 255,
            z[3] = h & 255, z[4] = (h = parseInt(D.slice(9, 13), 16)) >>> 8, z[5] = h & 255,
            z[6] = (h = parseInt(D.slice(14, 18), 16)) >>> 8, z[7] = h & 255, z[8] = (h = parseInt(D.slice(19, 23), 16)) >>> 8,
            z[9] = h & 255, z[10] = (h = parseInt(D.slice(24, 36), 16)) / 1099511627776 & 255,
            z[11] = h / 4294967296 & 255, z[12] = h >>> 24 & 255, z[13] = h >>> 16 & 255, z[14] = h >>> 8 & 255,
            z[15] = h & 255, z;
        }
        var Z = l;
        z.default = Z;
    }, {
        p0: 142
    } ],
    133: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.default = void 0;
        var j = /^(?:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}|00000000-0000-0000-0000-000000000000)$/i;
        z.default = j;
    }, {} ],
    134: [ function(D, h, z) {
        "use strict";
        let j;
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.default = l;
        const F = new Uint8Array(16);
        function l() {
            if (!j) if (j = typeof crypto !== "undefined" && crypto.getRandomValues && crypto.getRandomValues.bind(crypto),
            !j) throw new Error("crypto.getRandomValues() not supported. See https://github.com/uuidjs/uuid#getrandomvalues-not-supported");
            return j(F);
        }
    }, {} ],
    135: [ function(D, h, z) {
        "use strict";
        function j(D, h, z, j) {
            switch (D) {
              case 0:
                return h & z ^ ~h & j;

              case 1:
                return h ^ z ^ j;

              case 2:
                return h & z ^ h & j ^ z & j;

              case 3:
                return h ^ z ^ j;
            }
        }
        function F(D, h) {
            return D << h | D >>> 32 - h;
        }
        function l(D) {
            const h = [ 1518500249, 1859775393, 2400959708, 3395469782 ], z = [ 1732584193, 4023233417, 2562383102, 271733878, 3285377520 ];
            if (typeof D === "string") {
                const h = unescape(encodeURIComponent(D));
                D = [];
                for (let z = 0; z < h.length; ++z) D.push(h.charCodeAt(z));
            } else if (!Array.isArray(D)) D = Array.prototype.slice.call(D);
            D.push(128);
            const l = D.length / 4 + 2, Z = Math.ceil(l / 16), A = new Array(Z);
            for (let h = 0; h < Z; ++h) {
                const z = new Uint32Array(16);
                for (let j = 0; j < 16; ++j) z[j] = D[h * 64 + j * 4] << 24 | D[h * 64 + j * 4 + 1] << 16 | D[h * 64 + j * 4 + 2] << 8 | D[h * 64 + j * 4 + 3];
                A[h] = z;
            }
            A[Z - 1][14] = (D.length - 1) * 8 / Math.pow(2, 32), A[Z - 1][14] = Math.floor(A[Z - 1][14]),
            A[Z - 1][15] = (D.length - 1) * 8 & 4294967295;
            for (let D = 0; D < Z; ++D) {
                const l = new Uint32Array(80);
                for (let h = 0; h < 16; ++h) l[h] = A[D][h];
                for (let D = 16; D < 80; ++D) l[D] = F(l[D - 3] ^ l[D - 8] ^ l[D - 14] ^ l[D - 16], 1);
                let Z = z[0], q = z[1], Q = z[2], I = z[3], E = z[4];
                for (let D = 0; D < 80; ++D) {
                    const z = Math.floor(D / 20), A = F(Z, 5) + j(z, q, Q, I) + E + h[z] + l[D] >>> 0;
                    E = I, I = Q, Q = F(q, 30) >>> 0, q = Z, Z = A;
                }
                z[0] = z[0] + Z >>> 0, z[1] = z[1] + q >>> 0, z[2] = z[2] + Q >>> 0, z[3] = z[3] + I >>> 0,
                z[4] = z[4] + E >>> 0;
            }
            return [ z[0] >> 24 & 255, z[0] >> 16 & 255, z[0] >> 8 & 255, z[0] & 255, z[1] >> 24 & 255, z[1] >> 16 & 255, z[1] >> 8 & 255, z[1] & 255, z[2] >> 24 & 255, z[2] >> 16 & 255, z[2] >> 8 & 255, z[2] & 255, z[3] >> 24 & 255, z[3] >> 16 & 255, z[3] >> 8 & 255, z[3] & 255, z[4] >> 24 & 255, z[4] >> 16 & 255, z[4] >> 8 & 255, z[4] & 255 ];
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.default = void 0;
        var Z = l;
        z.default = Z;
    }, {} ],
    136: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.default = void 0, z.unsafeStringify = Z;
        var j = F(D("p0"));
        function F(D) {
            return D && D.__esModule ? D : {
                default: D
            };
        }
        const l = [];
        for (let D = 0; D < 256; ++D) l.push((D + 256).toString(16).slice(1));
        function Z(D, h = 0) {
            return (l[D[h + 0]] + l[D[h + 1]] + l[D[h + 2]] + l[D[h + 3]] + "-" + l[D[h + 4]] + l[D[h + 5]] + "-" + l[D[h + 6]] + l[D[h + 7]] + "-" + l[D[h + 8]] + l[D[h + 9]] + "-" + l[D[h + 10]] + l[D[h + 11]] + l[D[h + 12]] + l[D[h + 13]] + l[D[h + 14]] + l[D[h + 15]]).toLowerCase();
        }
        function A(D, h = 0) {
            const z = Z(D, h);
            if (!(0, j.default)(z)) throw TypeError("Stringified UUID is invalid");
            return z;
        }
        var q = A;
        z.default = q;
    }, {
        p0: 142
    } ],
    137: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.default = void 0;
        var j = l(D("O4")), F = D("Jc");
        function l(D) {
            return D && D.__esModule ? D : {
                default: D
            };
        }
        let Z, A, q = 0, Q = 0;
        function I(D, h, z) {
            let l = h && z || 0;
            const I = h || new Array(16);
            D = D || {};
            let E = D.node || Z, X = D.clockseq !== void 0 ? D.clockseq : A;
            if (E == null || X == null) {
                const h = D.random || (D.rng || j.default)();
                if (E == null) E = Z = [ h[0] | 1, h[1], h[2], h[3], h[4], h[5] ];
                if (X == null) X = A = (h[6] << 8 | h[7]) & 16383;
            }
            let f = D.msecs !== void 0 ? D.msecs : Date.now(), s = D.nsecs !== void 0 ? D.nsecs : Q + 1;
            const L = f - q + (s - Q) / 1e4;
            if (L < 0 && D.clockseq === void 0) X = X + 1 & 16383;
            if ((L < 0 || f > q) && D.nsecs === void 0) s = 0;
            if (s >= 1e4) throw new Error("uuid.v1(): Can't create more than 10M uuids/sec");
            q = f, Q = s, A = X, f += 122192928e5;
            const P = ((f & 268435455) * 1e4 + s) % 4294967296;
            I[l++] = P >>> 24 & 255, I[l++] = P >>> 16 & 255, I[l++] = P >>> 8 & 255, I[l++] = P & 255;
            const x = f / 4294967296 * 1e4 & 268435455;
            I[l++] = x >>> 8 & 255, I[l++] = x & 255, I[l++] = x >>> 24 & 15 | 16, I[l++] = x >>> 16 & 255,
            I[l++] = X >>> 8 | 128, I[l++] = X & 255;
            for (let D = 0; D < 6; ++D) I[l + D] = E[D];
            return h || (0, F.unsafeStringify)(I);
        }
        var E = I;
        z.default = E;
    }, {
        O4: 134,
        Jc: 136
    } ],
    138: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.default = void 0;
        var j = l(D("PT")), F = l(D("NO"));
        function l(D) {
            return D && D.__esModule ? D : {
                default: D
            };
        }
        const Z = (0, j.default)("v3", 48, F.default);
        var A = Z;
        z.default = A;
    }, {
        NO: 129,
        PT: 139
    } ],
    139: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.URL = z.DNS = void 0, z.default = Q;
        var j = D("Jc"), F = l(D("Ui"));
        function l(D) {
            return D && D.__esModule ? D : {
                default: D
            };
        }
        function Z(D) {
            D = unescape(encodeURIComponent(D));
            const h = [];
            for (let z = 0; z < D.length; ++z) h.push(D.charCodeAt(z));
            return h;
        }
        const A = "6ba7b810-9dad-11d1-80b4-00c04fd430c8";
        z.DNS = A;
        const q = "6ba7b811-9dad-11d1-80b4-00c04fd430c8";
        function Q(D, h, z) {
            function l(D, l, A, q) {
                var Q;
                if (typeof D === "string") D = Z(D);
                if (typeof l === "string") l = (0, F.default)(l);
                if (((Q = l) === null || Q === void 0 ? void 0 : Q.length) !== 16) throw TypeError("Namespace must be array-like (16 iterable integer values, 0-255)");
                let I = new Uint8Array(16 + D.length);
                if (I.set(l), I.set(D, l.length), I = z(I), I[6] = I[6] & 15 | h, I[8] = I[8] & 63 | 128,
                A) {
                    q = q || 0;
                    for (let D = 0; D < 16; ++D) A[q + D] = I[D];
                    return A;
                }
                return (0, j.unsafeStringify)(I);
            }
            try {
                l.name = D;
            } catch (D) {}
            return l.DNS = A, l.URL = q, l;
        }
        z.URL = q;
    }, {
        Ui: 132,
        Jc: 136
    } ],
    140: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.default = void 0;
        var j = Z(D("iD")), F = Z(D("O4")), l = D("Jc");
        function Z(D) {
            return D && D.__esModule ? D : {
                default: D
            };
        }
        function A(D, h, z) {
            if (j.default.randomUUID && !h && !D) return j.default.randomUUID();
            D = D || {};
            const Z = D.random || (D.rng || F.default)();
            if (Z[6] = Z[6] & 15 | 64, Z[8] = Z[8] & 63 | 128, h) {
                z = z || 0;
                for (let D = 0; D < 16; ++D) h[z + D] = Z[D];
                return h;
            }
            return (0, l.unsafeStringify)(Z);
        }
        var q = A;
        z.default = q;
    }, {
        iD: 130,
        O4: 134,
        Jc: 136
    } ],
    141: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.default = void 0;
        var j = l(D("PT")), F = l(D("ll"));
        function l(D) {
            return D && D.__esModule ? D : {
                default: D
            };
        }
        const Z = (0, j.default)("v5", 80, F.default);
        var A = Z;
        z.default = A;
    }, {
        ll: 135,
        PT: 139
    } ],
    142: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.default = void 0;
        var j = F(D("y0"));
        function F(D) {
            return D && D.__esModule ? D : {
                default: D
            };
        }
        function l(D) {
            return typeof D === "string" && j.default.test(D);
        }
        var Z = l;
        z.default = Z;
    }, {
        y0: 133
    } ],
    143: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.default = void 0;
        var j = F(D("p0"));
        function F(D) {
            return D && D.__esModule ? D : {
                default: D
            };
        }
        function l(D) {
            if (!(0, j.default)(D)) throw TypeError("Invalid UUID");
            return parseInt(D.slice(14, 15), 16);
        }
        var Z = l;
        z.default = Z;
    }, {
        p0: 142
    } ],
    144: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.VFileMessage = void 0;
        var j = D("unist-util-stringify-position");
        class F extends Error {
            constructor(D, h, z) {
                const F = [ null, null ];
                let l = {
                    start: {
                        line: null,
                        column: null
                    },
                    end: {
                        line: null,
                        column: null
                    }
                };
                if (super(), typeof h === "string") z = h, h = void 0;
                if (typeof z === "string") {
                    const D = z.indexOf(":");
                    if (D === -1) F[1] = z; else F[0] = z.slice(0, D), F[1] = z.slice(D + 1);
                }
                if (h) if ("type" in h || "position" in h) {
                    if (h.position) l = h.position;
                } else if ("start" in h || "end" in h) l = h; else if ("line" in h || "column" in h) l.start = h;
                if (this.name = (0, j.stringifyPosition)(h) || "1:1", this.message = typeof D === "object" ? D.message : D,
                this.stack = "", typeof D === "object" && D.stack) this.stack = D.stack;
                this.reason = this.message, this.fatal, this.line = l.start.line, this.column = l.start.column,
                this.position = l, this.source = F[0], this.ruleId = F[1], this.file, this.actual,
                this.expected, this.url, this.note;
            }
        }
        z.VFileMessage = F, F.prototype.file = "", F.prototype.name = "", F.prototype.reason = "",
        F.prototype.message = "", F.prototype.stack = "", F.prototype.fatal = null, F.prototype.column = null,
        F.prototype.line = null, F.prototype.source = null, F.prototype.ruleId = null, F.prototype.position = null;
    }, {
        "unist-util-stringify-position": 124
    } ],
    145: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), Object.defineProperty(z, "VFile", {
            enumerable: true,
            get: function() {
                return j.VFile;
            }
        });
        var j = D("k8");
    }, {
        k8: 146
    } ],
    146: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.VFile = void 0;
        var j = q(D("is-buffer")), F = D("vfile-message"), l = D("jX"), Z = D("Qo"), A = D("gs");
        function q(D) {
            return D && D.__esModule ? D : {
                default: D
            };
        }
        const Q = [ "history", "path", "basename", "stem", "extname", "dirname" ];
        class I {
            constructor(D) {
                let h;
                if (!D) h = {}; else if (typeof D === "string" || (0, j.default)(D)) h = {
                    value: D
                }; else if ((0, A.isUrl)(D)) h = {
                    path: D
                }; else h = D;
                this.data = {}, this.messages = [], this.history = [], this.cwd = Z.proc.cwd(),
                this.value, this.stored, this.result, this.map;
                let z = -1, F;
                while (++z < Q.length) {
                    const D = Q[z];
                    if (D in h && h[D] !== void 0) this[D] = D === "history" ? [ ...h[D] ] : h[D];
                }
                for (F in h) if (!Q.includes(F)) this[F] = h[F];
            }
            get path() {
                return this.history[this.history.length - 1];
            }
            set path(D) {
                if ((0, A.isUrl)(D)) D = (0, A.urlToPath)(D);
                if (X(D, "path"), this.path !== D) this.history.push(D);
            }
            get dirname() {
                return typeof this.path === "string" ? l.path.dirname(this.path) : void 0;
            }
            set dirname(D) {
                f(this.basename, "dirname"), this.path = l.path.join(D || "", this.basename);
            }
            get basename() {
                return typeof this.path === "string" ? l.path.basename(this.path) : void 0;
            }
            set basename(D) {
                X(D, "basename"), E(D, "basename"), this.path = l.path.join(this.dirname || "", D);
            }
            get extname() {
                return typeof this.path === "string" ? l.path.extname(this.path) : void 0;
            }
            set extname(D) {
                if (E(D, "extname"), f(this.dirname, "extname"), D) {
                    if (D.charCodeAt(0) !== 46) throw new Error("`extname` must start with `.`");
                    if (D.includes(".", 1)) throw new Error("`extname` cannot contain multiple dots");
                }
                this.path = l.path.join(this.dirname, this.stem + (D || ""));
            }
            get stem() {
                return typeof this.path === "string" ? l.path.basename(this.path, this.extname) : void 0;
            }
            set stem(D) {
                X(D, "stem"), E(D, "stem"), this.path = l.path.join(this.dirname || "", D + (this.extname || ""));
            }
            toString(D) {
                return (this.value || "").toString(D);
            }
            message(D, h, z) {
                const j = new F.VFileMessage(D, h, z);
                if (this.path) j.name = this.path + ":" + j.name, j.file = this.path;
                return j.fatal = false, this.messages.push(j), j;
            }
            info(D, h, z) {
                const j = this.message(D, h, z);
                return j.fatal = null, j;
            }
            fail(D, h, z) {
                const j = this.message(D, h, z);
                throw j.fatal = true, j;
            }
        }
        function E(D, h) {
            if (D && D.includes(l.path.sep)) throw new Error("`" + h + "` cannot be a path: did not expect `" + l.path.sep + "`");
        }
        function X(D, h) {
            if (!D) throw new Error("`" + h + "` cannot be empty");
        }
        function f(D, h) {
            if (!D) throw new Error("Setting `" + h + "` requires `path` to be set too");
        }
        z.VFile = I;
    }, {
        jX: 147,
        Qo: 148,
        gs: 149,
        "is-buffer": 151,
        "vfile-message": 144
    } ],
    147: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.path = void 0;
        const j = {
            basename: F,
            dirname: l,
            extname: Z,
            join: A,
            sep: "/"
        };
        function F(D, h) {
            if (h !== void 0 && typeof h !== "string") throw new TypeError('"ext" argument must be a string');
            I(D);
            let z = 0, j = -1, F = D.length, l;
            if (h === void 0 || h.length === 0 || h.length > D.length) {
                while (F--) if (D.charCodeAt(F) === 47) {
                    if (l) {
                        z = F + 1;
                        break;
                    }
                } else if (j < 0) l = true, j = F + 1;
                return j < 0 ? "" : D.slice(z, j);
            }
            if (h === D) return "";
            let Z = -1, A = h.length - 1;
            while (F--) if (D.charCodeAt(F) === 47) {
                if (l) {
                    z = F + 1;
                    break;
                }
            } else {
                if (Z < 0) l = true, Z = F + 1;
                if (A > -1) if (D.charCodeAt(F) === h.charCodeAt(A--)) {
                    if (A < 0) j = F;
                } else A = -1, j = Z;
            }
            if (z === j) j = Z; else if (j < 0) j = D.length;
            return D.slice(z, j);
        }
        function l(D) {
            if (I(D), D.length === 0) return ".";
            let h = -1, z = D.length, j;
            while (--z) if (D.charCodeAt(z) === 47) {
                if (j) {
                    h = z;
                    break;
                }
            } else if (!j) j = true;
            return h < 0 ? D.charCodeAt(0) === 47 ? "/" : "." : h === 1 && D.charCodeAt(0) === 47 ? "//" : D.slice(0, h);
        }
        function Z(D) {
            I(D);
            let h = D.length, z = -1, j = 0, F = -1, l = 0, Z;
            while (h--) {
                const A = D.charCodeAt(h);
                if (A === 47) {
                    if (Z) {
                        j = h + 1;
                        break;
                    }
                    continue;
                }
                if (z < 0) Z = true, z = h + 1;
                if (A === 46) {
                    if (F < 0) F = h; else if (l !== 1) l = 1;
                } else if (F > -1) l = -1;
            }
            if (F < 0 || z < 0 || l === 0 || l === 1 && F === z - 1 && F === j + 1) return "";
            return D.slice(F, z);
        }
        function A(...D) {
            let h = -1, z;
            while (++h < D.length) if (I(D[h]), D[h]) z = z === void 0 ? D[h] : z + "/" + D[h];
            return z === void 0 ? "." : q(z);
        }
        function q(D) {
            I(D);
            const h = D.charCodeAt(0) === 47;
            let z = Q(D, !h);
            if (z.length === 0 && !h) z = ".";
            if (z.length > 0 && D.charCodeAt(D.length - 1) === 47) z += "/";
            return h ? "/" + z : z;
        }
        function Q(D, h) {
            let z = "", j = 0, F = -1, l = 0, Z = -1, A, q;
            while (++Z <= D.length) {
                if (Z < D.length) A = D.charCodeAt(Z); else if (A === 47) break; else A = 47;
                if (A === 47) {
                    if (F === Z - 1 || l === 1) ; else if (F !== Z - 1 && l === 2) {
                        if (z.length < 2 || j !== 2 || z.charCodeAt(z.length - 1) !== 46 || z.charCodeAt(z.length - 2) !== 46) if (z.length > 2) {
                            if (q = z.lastIndexOf("/"), q !== z.length - 1) {
                                if (q < 0) z = "", j = 0; else z = z.slice(0, q), j = z.length - 1 - z.lastIndexOf("/");
                                F = Z, l = 0;
                                continue;
                            }
                        } else if (z.length > 0) {
                            z = "", j = 0, F = Z, l = 0;
                            continue;
                        }
                        if (h) z = z.length > 0 ? z + "/.." : "..", j = 2;
                    } else {
                        if (z.length > 0) z += "/" + D.slice(F + 1, Z); else z = D.slice(F + 1, Z);
                        j = Z - F - 1;
                    }
                    F = Z, l = 0;
                } else if (A === 46 && l > -1) l++; else l = -1;
            }
            return z;
        }
        function I(D) {
            if (typeof D !== "string") throw new TypeError("Path must be a string. Received " + JSON.stringify(D));
        }
        z.path = j;
    }, {} ],
    148: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.proc = void 0;
        const j = {
            cwd: F
        };
        function F() {
            return "/";
        }
        z.proc = j;
    }, {} ],
    149: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), Object.defineProperty(z, "isUrl", {
            enumerable: true,
            get: function() {
                return j.isUrl;
            }
        }), z.urlToPath = F;
        var j = D("UG");
        function F(D) {
            if (typeof D === "string") D = new URL(D); else if (!(0, j.isUrl)(D)) {
                const h = new TypeError('The "path" argument must be of type string or an instance of URL. Received `' + D + "`");
                throw h.code = "ERR_INVALID_ARG_TYPE", h;
            }
            if (D.protocol !== "file:") {
                const D = new TypeError("The URL must be of scheme file");
                throw D.code = "ERR_INVALID_URL_SCHEME", D;
            }
            return l(D);
        }
        function l(D) {
            if (D.hostname !== "") {
                const D = new TypeError('File URL host must be "localhost" or empty on darwin');
                throw D.code = "ERR_INVALID_FILE_URL_HOST", D;
            }
            const h = D.pathname;
            let z = -1;
            while (++z < h.length) if (h.charCodeAt(z) === 37 && h.charCodeAt(z + 1) === 50) {
                const D = h.charCodeAt(z + 2);
                if (D === 70 || D === 102) {
                    const D = new TypeError("File URL path must not include encoded / characters");
                    throw D.code = "ERR_INVALID_FILE_URL_PATH", D;
                }
            }
            return decodeURIComponent(h);
        }
    }, {
        UG: 150
    } ],
    150: [ function(D, h, z) {
        "use strict";
        function j(D) {
            return D !== null && typeof D === "object" && D.href && D.origin;
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.isUrl = j;
    }, {} ],
    151: [ function(D, h, z) {
        arguments[4][122][0].apply(z, arguments);
    }, {
        dup: 122
    } ],
    152: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.zwitch = F;
        const j = {}.hasOwnProperty;
        function F(D, h) {
            const z = h || {};
            function F(h, ...z) {
                let l = F.invalid;
                const Z = F.handlers;
                if (h && j.call(h, D)) {
                    const z = String(h[D]);
                    l = j.call(Z, z) ? Z[z] : F.unknown;
                }
                if (l) return l.call(this, h, ...z);
            }
            return F.handlers = z.handlers || {}, F.invalid = z.invalid, F.unknown = z.unknown,
            F;
        }
    }, {} ],
    153: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.Analytics = void 0, z.default = z.analytics = I;
        var j = D("uuid");
        const F = "https://www.google-analytics.com/mp/collect", l = "https://www.google-analytics.com/debug/mp/collect", Z = "cid", A = 100, q = 30;
        class Q {
            debug;
            measurement_id;
            api_secret;
            constructor(D, h, z = false) {
                this.measurement_id = D, this.api_secret = h, this.debug = z;
            }
            static async getOrCreateClientId() {
                const D = await chrome.storage.local.get(Z);
                let h = D[Z];
                if (!h) h = (0, j.v4)(), await chrome.storage.local.set({
                    [Z]: h
                });
                return h;
            }
            async getOrCreateSessionId() {
                let {sessionData: D} = await chrome.storage.session.get("sessionData");
                const h = Date.now();
                if (D && D.timestamp) {
                    const z = (h - D.timestamp) / 6e4;
                    if (z > q) D = null; else D.timestamp = h, await chrome.storage.session.set({
                        sessionData: D
                    });
                }
                if (!D) D = {
                    session_id: h.toString(),
                    timestamp: h.toString()
                }, await chrome.storage.session.set({
                    sessionData: D
                });
                return D.session_id;
            }
            async fireEvent(D, h = {}) {
                if (!h.session_id) h.session_id = await this.getOrCreateSessionId();
                if (!h.engagement_time_msec) h.engagement_time_msec = A;
                try {
                    const z = await fetch(`${this.debug ? l : F}?measurement_id=${this.measurement_id}&api_secret=${this.api_secret}`, {
                        method: "POST",
                        body: JSON.stringify({
                            client_id: await Q.getOrCreateClientId(),
                            events: [ {
                                name: D,
                                params: h
                            } ]
                        })
                    });
                    if (!this.debug) return;
                } catch (D) {}
            }
            async firePageViewEvent(D, h, z = {}) {
                return this.fireEvent("page_view", {
                    page_title: D,
                    page_location: h,
                    ...z
                });
            }
            async fireErrorEvent(D, h = {}) {
                return this.fireEvent("extension_error", {
                    ...D,
                    ...h
                });
            }
        }
        function I(D, h) {
            const z = new Q(D, h);
            z.fireEvent("run"), chrome.alarms.create(D, {
                periodInMinutes: 60
            }), chrome.alarms.onAlarm.addListener((() => {
                z.fireEvent("run");
            }));
        }
        z.Analytics = Q;
    }, {
        uuid: 128
    } ],
    154: [ function(D, h, z) {
        "use strict";
        var j = X(D("expiry-map")), F = D("zC"), l = D("RG"), Z = D("8D"), A = D("Gc"), q = D("7t"), Q = D("SD"), I = X(D("I9")), E = D("Rg");
        function X(D) {
            return D && D.__esModule ? D : {
                default: D
            };
        }
        const f = "cid", s = new j.default(30 * 1e3);
        async function L() {
            return new Promise((D => {
                chrome.tabs.query({}, (h => D(h)));
            }));
        }
        function P(D) {
            const h = new URL(D);
            return h.hostname;
        }
        async function x(D) {
            try {
                await chrome.scripting.executeScript({
                    target: {
                        tabId: D
                    },
                    files: [ "js/content-script.js" ]
                }), await chrome.scripting.executeScript({
                    target: {
                        tabId: D
                    },
                    files: [ "js/content-script-main.js" ],
                    world: "MAIN"
                });
            } catch (D) {}
        }
        function n(D) {
            for (let h = 0; h < l.SITES_REGEX.length; h += 1) {
                const z = new RegExp(l.SITES_REGEX[h]), j = z.test(D);
                if (j) return true;
            }
            return false;
        }
        async function w(D) {
            const h = D.url || "", z = D.id;
            if (h && z) {
                const D = P(h), j = n(D);
                if (j) x(z);
            }
        }
        async function J() {
            let D = false;
            try {
                D = !!await (0, Z.getAccessToken)();
            } catch (h) {
                D = false;
            }
            return D;
        }
        (0, I.default)("G-HVZS0VZV5B", "5KhNKowKS1eNDP0mBdW54w"), chrome.runtime.onConnect.addListener((D => {
            D.onDisconnect.addListener((() => {})), D.onMessage.addListener((async h => {
                const z = !!await (0, q.getSetting)(l.ChatGptSettingsKey.DEBUG);
                if (z) {
                    const h = await (0, q.getSetting)(l.ChatGptSettingsKey.RESPONSE_BEHAVIOR_TYPE);
                    switch (h) {
                      case l.ResponseBehaviorType.STUB_ANSWER:
                        for (let h = 0; h < l.STUB_RESPONSE.length; h += 1) (0, A.sendMessage)(D, l.ChatGptMessageType.ANSWER_TEXT_FROM_BG, {
                            answer: l.STUB_RESPONSE.slice(0, h)
                        }), await new Promise((D => setTimeout(D, 10)));
                        return await (0, A.sendMessage)(D, l.ChatGptMessageType.ANSWER_DONE_FROM_BG), void D.disconnect();

                      case l.ResponseBehaviorType.STUB_ERROR:
                        return void (0, A.sendMessage)(D, l.ChatGptMessageType.ANSWER_ERROR_FROM_BG, {
                            error: "STUB_ERROR"
                        });

                      case l.ResponseBehaviorType.STUB_UNAUTHORIZED:
                        return void (0, A.sendMessage)(D, l.ChatGptMessageType.ANSWER_ERROR_FROM_BG, {
                            error: "UNAUTHORIZED"
                        });

                      case l.ResponseBehaviorType.DEFAULT:
                      default:
                        break;
                    }
                }
                let j;
                try {
                    const D = await (0, Z.getAccessToken)();
                    j = new F.ChatGPTAPI({
                        sessionToken: D
                    }), await j.ensureAuth();
                } catch (h) {
                    return void (0, A.sendMessage)(D, l.ChatGptMessageType.ANSWER_ERROR_FROM_BG, {
                        error: "UNAUTHORIZED"
                    });
                }
                try {
                    const z = j.getConversation({
                        conversationId: h.data.conversationId,
                        parentMessageId: h.data.parentMessageId
                    });
                    await z.sendMessage(h.data.question, {
                        onProgress(D) {},
                        onConversationResponse(h) {
                            (0, A.sendMessage)(D, l.ChatGptMessageType.ANSWER_TEXT_FROM_BG, {
                                conversationResponse: h
                            });
                        }
                    }), (0, A.sendMessage)(D, l.ChatGptMessageType.ANSWER_DONE_FROM_BG), D.disconnect();
                } catch (h) {
                    (0, A.sendMessage)(D, l.ChatGptMessageType.ANSWER_ERROR_FROM_BG, {
                        error: h.message
                    }), D.disconnect(), Z.cache.delete(l.KEY_ACCESS_TOKEN);
                }
            }));
        })), chrome.tabs.onUpdated.addListener(((D, h, z) => {
            if (h.status == "complete") w(z);
        })), chrome.runtime.onInstalled.addListener((async D => {
            if (D.reason === chrome.runtime.OnInstalledReason.INSTALL) {
                const D = await L();
                D.forEach((D => {
                    w(D);
                }));
            }
            const h = [ {
                id: 1,
                action: {
                    type: "modifyHeaders",
                    responseHeaders: [ {
                        header: "X-Frame-Options",
                        operation: "remove"
                    } ],
                    requestHeaders: [ {
                        header: "Referer",
                        operation: "set",
                        value: "https://chatgpt.com/"
                    }, {
                        header: "Origin",
                        operation: "remove"
                    } ]
                },
                condition: {
                    domains: [ chrome.runtime.id ],
                    urlFilter: "|https://chatgpt.com/backend-api*",
                    resourceTypes: [ "xmlhttprequest" ]
                }
            }, {
                id: 2,
                action: {
                    type: "modifyHeaders",
                    responseHeaders: [ {
                        header: "X-Frame-Options",
                        operation: "remove"
                    } ],
                    requestHeaders: [ {
                        header: "Referer",
                        operation: "set",
                        value: "https://chatgpt.com/"
                    }, {
                        header: "Origin",
                        operation: "remove"
                    }, {
                        header: "sec-fetch-dest",
                        operation: "remove"
                    } ]
                },
                condition: {
                    domains: [ chrome.runtime.id ],
                    urlFilter: "|https://chatgpt.com/*",
                    resourceTypes: [ "xmlhttprequest", "sub_frame", "main_frame" ]
                }
            }, {
                id: 3,
                action: {
                    type: "modifyHeaders",
                    responseHeaders: [ {
                        header: "Content-Security-Policy",
                        operation: "remove"
                    } ]
                },
                condition: {
                    domains: [ chrome.runtime.id ],
                    urlFilter: "|https://chatgpt.com/*",
                    resourceTypes: [ "sub_frame" ]
                }
            } ];
            await chrome.declarativeNetRequest.updateDynamicRules({
                removeRuleIds: h.map((D => D.id)),
                addRules: h
            });
            try {
                chrome.contextMenus.create({
                    id: "gpt-search",
                    title: "Use selected text as ChatGPT prompt",
                    contexts: [ "selection" ]
                });
            } catch (D) {}
        })), chrome.omnibox.onInputEntered.addListener((D => {
            chrome.tabs.create({
                url: "https://chatgpt.com/"
            }, (h => {
                s.set(h === null || h === void 0 ? void 0 : h.id, D);
            }));
        })), chrome.omnibox.onInputChanged.addListener((async (D, h) => {
            const z = D.trim().toLowerCase(), j = await chrome.storage.local.get(l.CHAT_GPT_HISTORY_KEY);
            if (j[l.CHAT_GPT_HISTORY_KEY]) h(j[l.CHAT_GPT_HISTORY_KEY].filter((D => D.trim().toLowerCase().includes(z))).map((D => {
                let h = D;
                const j = h.toLowerCase().indexOf(z);
                if (j >= 0) {
                    const D = j + z.length;
                    h = `${h.slice(0, j)}<match>${h.slice(j, D)}</match>${h.slice(D)}`;
                }
                return {
                    content: D,
                    description: `${h}`
                };
            })));
        })), chrome.contextMenus.onClicked.addListener(((D, h) => {
            if (D.menuItemId === "gpt-search") chrome.tabs.create({
                url: "https://chatgpt.com/"
            }, (h => {
                s.set(h === null || h === void 0 ? void 0 : h.id, D.selectionText);
            }));
        })), chrome.alarms.create("authCheck", {
            periodInMinutes: 5
        }), chrome.alarms.create("tabCheck", {
            periodInMinutes: 1
        }), chrome.alarms.onAlarm.addListener((async D => {
            switch (D.name) {
              case "authCheck":
                if (!await (0, q.getSetting)(l.ChatGptSettingsKey.AUTO_REFRESH_SESSION)) return;
                let h;
                try {
                    const D = await (0, Z.getAccessToken)();
                    h = new F.ChatGPTAPI({
                        sessionToken: D
                    }), await h.ensureAuth();
                } catch (D) {
                    (0, Q.maybeOpenAndCloseChatGptTab)();
                }
                break;

              case "tabCheck":
                if (!await (0, q.getSetting)(l.ChatGptSettingsKey.KEEP_CHATGPT_PINNED)) return;
                (0, Q.maybePinChatGptTab)();
                break;

              default:
                throw new Error(`Bad alarm name:${D.name}`);
            }
        })), chrome.runtime.onMessage.addListener(((D, h, z) => {
            var j, F;
            switch (D.type) {
              case l.ChatGptMessageType.GET_PROMPT:
                z({
                    data: {
                        prompt: s.get((j = h.tab) === null || j === void 0 ? void 0 : j.id)
                    }
                });
                break;

              case l.ChatGptMessageType.OPEN_SETTINGS:
                break;

              case l.ChatGptMessageType.BURN_PROMPT:
                s.delete((F = h.tab) === null || F === void 0 ? void 0 : F.id);
                break;

              case l.ChatGptMessageType.TRACK_EVENT:
                break;

              case l.ChatGptMessageType.AUTH_STATUS_REQUEST:
                J().then((D => chrome.runtime.sendMessage({
                    type: l.ChatGptMessageType.AUTH_STATUS,
                    data: D
                })));
                break;

              case l.ChatGptMessageType.PIN_CHATGPT_TAB:
                (0, Q.maybePinChatGptTab)();
                break;

              default:
                break;
            }
        })), (0, E.init)();
    }, {
        I9: 153,
        zC: 155,
        RG: 156,
        Rg: 157,
        "8D": 159,
        Gc: 160,
        "7t": 161,
        SD: 162,
        "expiry-map": 6
    } ],
    155: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.ChatGPTConversation = z.ChatGPTAPI = void 0, z.markdownToText = L;
        var j = Q(D("expiry-map")), F = Q(D("p-timeout")), l = D("uuid"), Z = D("eventsource-parser"), A = D("remark"), q = Q(D("strip-markdown"));
        function Q(D) {
            return D && D.__esModule ? D : {
                default: D
            };
        }
        var I = class {
            constructor(D, h = {}) {
                this.conversationId = void 0, this.parentMessageId = void 0, this.api = D, this.conversationId = h.conversationId,
                this.parentMessageId = h.parentMessageId;
            }
            async sendMessage(D, h = {}) {
                const {onConversationResponse: z, ...j} = h;
                return this.api.sendMessage(D, {
                    ...j,
                    conversationId: this.conversationId,
                    parentMessageId: this.parentMessageId,
                    onConversationResponse: D => {
                        var h;
                        if (D.conversation_id) this.conversationId = D.conversation_id;
                        if ((h = D.message) == null ? void 0 : h.id) this.parentMessageId = D.message.id;
                        if (z) return z(D);
                    }
                });
            }
        }, E;
        z.ChatGPTConversation = I;
        var X = globalThis.fetch ?? async function D(...h) {
            if (!E) E = null;
            if (typeof (E == null ? void 0 : E.fetch) !== "function") throw new Error("Invalid undici installation; please make sure undici is installed correctly in your node_modules. Note that this package requires Node.js >= 16.8");
            return E.fetch(...h);
        };
        async function* f(D) {
            const h = D.getReader();
            try {
                while (true) {
                    const {done: D, value: z} = await h.read();
                    if (D) return;
                    yield z;
                }
            } finally {
                h.releaseLock();
            }
        }
        async function s(D, h) {
            const {onMessage: z, ...j} = h, F = await X(D, j);
            if (!F.ok) throw new Error(`ChatGPTAPI error ${F.status || F.statusText}`);
            const l = (0, Z.createParser)((D => {
                if (D.type === "event") z(D.data);
            }));
            if (!F.body.getReader) {
                const D = F.body;
                if (!D.on || !D.read) throw new Error('unsupported "fetch" implementation');
                D.on("readable", (() => {
                    let h;
                    while (null !== (h = D.read())) l.feed(h.toString());
                }));
            } else for await (const D of f(F.body)) {
                const h = (new TextDecoder).decode(D);
                l.feed(h);
            }
        }
        function L(D) {
            return (0, A.remark)().use(q.default).processSync(D ?? "").toString();
        }
        var P = "accessToken", x = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36", n = class {
            constructor(D) {
                const {sessionToken: h, markdown: z = true, apiBaseUrl: F = "https://chatgpt.com/api", backendApiBaseUrl: l = "https://chatgpt.com/backend-api", userAgent: Z = x, accessTokenTTL: A = 6e4} = D;
                if (this._sessionToken = h, this._markdown = !!z, this._apiBaseUrl = F, this._backendApiBaseUrl = l,
                this._userAgent = Z, this._accessTokenCache = new j.default(A), !this._sessionToken) throw new Error("ChatGPT invalid session token");
            }
            async sendMessage(D, h = {}) {
                const {conversationId: z, parentMessageId: j = (0, l.v4)(), timeoutMs: Z, onProgress: A, onConversationResponse: q} = h;
                let {abortSignal: Q} = h, I = null;
                if (Z && !Q) I = new AbortController, Q = I.signal;
                const E = await this.refreshAccessToken(), X = await this.getModelName(), f = {
                    action: "next",
                    messages: [ {
                        id: (0, l.v4)(),
                        role: "user",
                        content: {
                            content_type: "text",
                            parts: [ D ]
                        }
                    } ],
                    model: X,
                    parent_message_id: j
                };
                if (z) f.conversation_id = z;
                const P = `${this._backendApiBaseUrl}/conversation`;
                let x = "", n = null;
                const w = new Promise(((D, h) => {
                    s(P, {
                        method: "POST",
                        headers: {
                            Authorization: `Bearer ${E}`,
                            "Content-Type": "application/json",
                            "User-Agent": this._userAgent
                        },
                        body: JSON.stringify(f),
                        signal: Q,
                        onMessage: h => {
                            var z, j;
                            if (h === "[DONE]") {
                                if (n) this.hideConversation(n);
                                return D(x);
                            }
                            try {
                                const D = JSON.parse(h);
                                if ("conversation_id" in D) n = D.conversation_id;
                                if (q) q(D);
                                const F = D.message;
                                if (F) {
                                    let D = (j = (z = F == null ? void 0 : F.content) == null ? void 0 : z.parts) == null ? void 0 : j[0];
                                    if (D) {
                                        if (!this._markdown) D = L(D);
                                        if (x = D, A) A(D);
                                    }
                                }
                            } catch (D) {}
                        }
                    }).catch(h);
                }));
                if (Z) {
                    if (I) w.cancel = () => {
                        I.abort();
                    };
                    return (0, F.default)(w, {
                        milliseconds: Z,
                        message: "ChatGPT timed out waiting for response"
                    });
                } else return w;
            }
            async getIsAuthenticated() {
                try {
                    return await this.refreshAccessToken(), true;
                } catch (D) {
                    return false;
                }
            }
            async ensureAuth() {
                return await this.refreshAccessToken();
            }
            async hideConversation(D) {
                try {
                    const h = await X(`https://chatgpt.com/backend-api/conversation/${D}`, {
                        method: "PATCH",
                        headers: {
                            Authorization: `Bearer ${this._accessTokenCache.get(P)}`,
                            "Content-Type": "application/json",
                            "User-Agent": this._userAgent
                        },
                        body: JSON.stringify({
                            is_visible: false
                        })
                    }), z = await h.json();
                } catch (D) {}
            }
            async fetchModels() {
                const D = await X("https://chatgpt.com/backend-api/models", {
                    method: "GET",
                    headers: {
                        Authorization: `Bearer ${this._accessTokenCache.get(P)}`,
                        "Content-Type": "application/json",
                        "User-Agent": this._userAgent
                    }
                });
                return await D.json();
            }
            async getModelName() {
                try {
                    const D = await this.fetchModels();
                    return D.models[0].slug;
                } catch (D) {
                    return "text-davinci-002-render";
                }
            }
            async refreshAccessToken() {
                const D = this._accessTokenCache.get(P);
                if (D) return D;
                try {
                    const D = await X("https://chatgpt.com/api/auth/session", {
                        headers: {
                            cookie: `__Secure-next-auth.session-token=${this._sessionToken}`,
                            "user-agent": this._userAgent
                        }
                    }).then((D => {
                        if (!D.ok) throw new Error(`${D.status} ${D.statusText}`);
                        return D.json();
                    })), h = D == null ? void 0 : D.accessToken;
                    if (!h) throw new Error("Unauthorized");
                    const z = D == null ? void 0 : D.error;
                    if (z) if (z === "RefreshAccessTokenError") throw new Error("session token may have expired"); else throw new Error(z);
                    return this._accessTokenCache.set(P, h), h;
                } catch (D) {
                    throw new Error(`ChatGPT failed to refresh auth token. ${D.toString()}`);
                }
            }
            getConversation(D = {}) {
                return new I(this, D);
            }
        };
        z.ChatGPTAPI = n;
    }, {
        "eventsource-parser": 5,
        "expiry-map": 6,
        "p-timeout": 112,
        remark: 117,
        "strip-markdown": 118,
        uuid: 128
    } ],
    156: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.STUB_RESPONSE = z.SITES_REGEX = z.ResponseBehaviorType = z.QUICK_SUMMARIES = z.QUICK_REPLY_SUMMARIES = z.KEY_ACCESS_TOKEN = z.EMAIL_URGENCY_OPTIONS = z.EMAIL_TONE_OPTIONS = z.EMAIL_STYLE_OPTIONS = z.EMAIL_LENGTH_OPTIONS = z.ChatGptThreadState = z.ChatGptSettingsKey = z.ChatGptMessageType = z.CHAT_GPT_SETTINGS_KEY = z.CHAT_GPT_HISTORY_KEY = void 0;
        const j = "CHAT_GPT_HISTORY";
        z.CHAT_GPT_HISTORY_KEY = j;
        const F = "CHAT_GPT_SETTINGS_KEY";
        var l, Z, A, q;
        z.CHAT_GPT_SETTINGS_KEY = F, z.ChatGptSettingsKey = l, function(D) {
            D["ENABLE_CONTENT_SCRIPT"] = "ENABLE_CONTENT_SCRIPT", D["EAGER_SEARCH"] = "EAGER_SEARCH",
            D["SHORT_SEARCH_RESPONSES"] = "SHORT_SEARCH_RESPONSES", D["IFRAME_POPUP"] = "IFRAME_POPUP",
            D["DEBUG"] = "DEBUG", D["RESPONSE_BEHAVIOR_TYPE"] = "RESPONSE_BEHAVIOR_TYPE", D["AUTO_REFRESH_SESSION"] = "AUTO_REFRESH_SESSION",
            D["KEEP_CHATGPT_PINNED"] = "KEEP_CHATGPT_PINNED", D["ENABLE_EMAIL"] = "ENABLE_EMAIL",
            D["EMAIL_LENGTH"] = "EMAIL_LENGTH", D["EMAIL_STYLE"] = "EMAIL_STYLE", D["EMAIL_URGENCY"] = "EMAIL_URGENCY",
            D["EMAIL_TONE"] = "EMAIL_TONE";
        }(l || (z.ChatGptSettingsKey = l = {})), z.ChatGptThreadState = Z, function(D) {
            D[D["INITIAL"] = 0] = "INITIAL", D[D["UNAUTHORIZED"] = 1] = "UNAUTHORIZED", D[D["LOADING"] = 2] = "LOADING",
            D[D["SUCCESS_INFLIGHT"] = 3] = "SUCCESS_INFLIGHT", D[D["SUCCESS_COMPLETE"] = 4] = "SUCCESS_COMPLETE",
            D[D["ERROR"] = 5] = "ERROR";
        }(Z || (z.ChatGptThreadState = Z = {})), z.ChatGptMessageType = A, function(D) {
            D["SEND_PROMPT_FROM_CS"] = "SEND_PROMPT_FROM_CS", D["ANSWER_TEXT_FROM_BG"] = "ANSWER_FROM_BG",
            D["ANSWER_DONE_FROM_BG"] = "ANSWER_DONE_FROM_BG", D["ANSWER_ERROR_FROM_BG"] = "ANSWER_ERROR_FROM_BG",
            D["BURN_PROMPT"] = "BURN_PROMPT", D["GET_PROMPT"] = "GET_PROMPT", D["OPEN_SETTINGS"] = "OPEN_SETTINGS",
            D["TRACK_EVENT"] = "TRACK_EVENT", D["PIN_CHATGPT_TAB"] = "PIN_CHATGPT_TAB", D["AUTH_STATUS_REQUEST"] = "AUTH_STATUS_REQUEST",
            D["AUTH_STATUS"] = "AUTH_STATUS";
        }(A || (z.ChatGptMessageType = A = {})), z.ResponseBehaviorType = q, function(D) {
            D["DEFAULT"] = "DEFAULT", D["STUB_ANSWER"] = "STUB_ANSWER", D["STUB_ERROR"] = "STUB_ERROR",
            D["STUB_UNAUTHORIZED"] = "STUB_UNAUTHORIZED";
        }(q || (z.ResponseBehaviorType = q = {}));
        const Q = "accessToken";
        z.KEY_ACCESS_TOKEN = Q;
        const I = `\nThis is a stub response! This is a stub response! \nThis is a stub response! This is a stub response! \n\n\`\`\`\n// Here is some code:\nfunction foobar() {\n    return "baz";\n}\n\`\`\`\n\nThis is a stub response! This is a stub response! \nThis is a stub response! This is a stub response! \n`;
        z.STUB_RESPONSE = I;
        const E = [ "Brief", "Thorough" ];
        z.EMAIL_LENGTH_OPTIONS = E;
        const X = [ "Formal", "Casual" ];
        z.EMAIL_STYLE_OPTIONS = X;
        const f = [ "Urgent", "Non-urgent" ];
        z.EMAIL_URGENCY_OPTIONS = f;
        const s = [ "Appreciative", "Assertive", "Cheerful", "Critical", "Dry", "Friendly", "Humorous", "Inspirational", "Lighthearted", "Negative", "Persuasive", "Polite", "Positive", "Professional", "Serious", "Thankful" ];
        z.EMAIL_TONE_OPTIONS = s;
        const L = [ "It was nice meeting you" ];
        z.QUICK_SUMMARIES = L;
        const P = [ "Acknowledge the email and say thank you", "I'll look into it", "I don't understand, can you clarify?" ];
        z.QUICK_REPLY_SUMMARIES = P;
        const x = [ "^.*google.[a-z]+$", "^.*google.co.[a-z]+$", "^.*google.com.[a-z]+$", "^.*yahoo.co.[a-z]+$", "^.*yahoo.[a-z]+$", "^.*bing.[a-z]+$", "^.*duckduckgo.com$", "^.*search.brave.com$", "^.*ecosia.org$", "^.*presearch.com$", "^chatgpt.com$" ];
        z.SITES_REGEX = x;
    }, {} ],
    157: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.init = q;
        var j = D("z2"), F = D("RG");
        const l = "https://api.chatgpt-chrome.com/api/leakprevention/v2/check";
        function Z() {
            alert("Your prompt may have sensitive information inside. This message won't be shown again for this tab.");
        }
        async function A(D, h) {
            const z = await j.Analytics.getOrCreateClientId();
            D.cid = z;
            const F = await fetch(l, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(D)
            });
            if (F.ok) {
                const D = await F.json();
                if (D.verdict == "unsafe") if (h) {
                    const D = `shown_${h}`, z = await chrome.storage.session.get([ D ]);
                    if (!z[D]) await chrome.storage.session.set({
                        [D]: true
                    }), await chrome.scripting.executeScript({
                        target: {
                            tabId: h
                        },
                        func: Z
                    });
                }
            }
        }
        function q() {
            return chrome.runtime.onMessage.addListener(((D, h, z) => {
                if ((D === null || D === void 0 ? void 0 : D.type) == F.MSG_TYPE) {
                    var j;
                    const z = D.data;
                    A(z, (j = h.tab) === null || j === void 0 ? void 0 : j.id);
                }
            })), true;
        }
    }, {
        z2: 153,
        RG: 158
    } ],
    158: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.MSG_TYPE = void 0;
        const j = "leak_prevention_msg";
        z.MSG_TYPE = j;
    }, {} ],
    159: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.cache = void 0, z.fetchSSE = I, z.getAccessToken = X, z.getAnswer = f, z.streamAsyncIterable = E;
        var j = D("eventsource-parser"), F = q(D("expiry-map")), l = D("uuid"), Z = D("p2"), A = D("xS");
        function q(D) {
            return D && D.__esModule ? D : {
                default: D
            };
        }
        const Q = new F.default(10 * 1e3);
        async function I(D, h) {
            const {onMessage: z, ...F} = h, l = await fetch(D, F), Z = (0, j.createParser)((D => {
                if (D.type === "event") z(D.data);
            }));
            for await (const D of E(l.body)) {
                const h = (new TextDecoder).decode(D);
                Z.feed(h);
            }
        }
        async function* E(D) {
            const h = D.getReader();
            try {
                while (true) {
                    const {done: D, value: z} = await h.read();
                    if (D) return;
                    yield z;
                }
            } finally {
                h.releaseLock();
            }
        }
        async function X() {
            if (Q.get(Z.KEY_ACCESS_TOKEN)) return Q.get(Z.KEY_ACCESS_TOKEN);
            const D = await fetch("https://chatgpt.com/api/auth/session").then((D => D.json())).catch((() => ({})));
            if (!D.accessToken) throw new Error("UNAUTHORIZED");
            return Q.set(Z.KEY_ACCESS_TOKEN, D.accessToken), D.accessToken;
        }
        async function f(D, h) {
            const z = !!await (0, A.getSetting)(Z.ChatGptSettingsKey.DEBUG);
            if (z) {
                const D = await (0, A.getSetting)(Z.ChatGptSettingsKey.RESPONSE_BEHAVIOR_TYPE);
                switch (D) {
                  case Z.ResponseBehaviorType.STUB_ANSWER:
                    for (let D = 0; D < Z.STUB_RESPONSE.length; D += 1) h({
                        done: false,
                        answer: Z.STUB_RESPONSE.slice(0, D)
                    }), await new Promise((D => setTimeout(D, 10)));
                    return void h({
                        done: true
                    });

                  case Z.ResponseBehaviorType.STUB_ERROR:
                    throw new Error("STUB ERROR");

                  case Z.ResponseBehaviorType.STUB_UNAUTHORIZED:
                    throw new Error("UNAUTHORIZED");

                  case Z.ResponseBehaviorType.DEFAULT:
                  default:
                    break;
                }
            }
            const j = await X();
            let F = "text-davinci-002-render";
            try {
                const D = await fetch("https://chatgpt.com/backend-api/models", {
                    headers: {
                        Authorization: `Bearer ${j}`
                    }
                });
                if (D.ok) {
                    const h = await D.json();
                    F = h.models[0].slug;
                }
            } catch (D) {}
            const q = {
                action: "next",
                messages: [ {
                    id: (0, l.v4)(),
                    role: "user",
                    content: {
                        content_type: "text",
                        parts: [ D ]
                    }
                } ],
                model: F,
                parent_message_id: (0, l.v4)()
            };
            await I("https://chatgpt.com/backend-api/conversation", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${j}`
                },
                body: JSON.stringify(q),
                onMessage(D) {
                    if (D === "[DONE]") return void h({
                        done: true
                    });
                    let z = null;
                    try {
                        var j, F, l;
                        const h = JSON.parse(D);
                        z = (j = h.message) === null || j === void 0 ? void 0 : (F = j.content) === null || F === void 0 ? void 0 : (l = F.parts) === null || l === void 0 ? void 0 : l[0];
                    } catch (D) {}
                    if (z) h({
                        done: false,
                        answer: z
                    });
                }
            });
        }
        z.cache = Q;
    }, {
        p2: 156,
        xS: 161,
        "eventsource-parser": 5,
        "expiry-map": 6,
        uuid: 128
    } ],
    160: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.sendMessage = F, z.sendPromptFromContentScript = l;
        var j = D("p2");
        function F(D, h, z) {
            D.postMessage({
                messageType: h,
                data: z
            });
        }
        function l(D, h) {
            const z = chrome.runtime.connect();
            z.onMessage.addListener((D => h(D))), z.onDisconnect.addListener((() => {})), F(z, j.ChatGptMessageType.SEND_PROMPT_FROM_CS, {
                question: D
            });
        }
    }, {
        p2: 156
    } ],
    161: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.defaultSettings = void 0, z.getAllSettings = A, z.getSetting = q, z.updateAllSettings = Z,
        z.updateSetting = l;
        var j = D("p2");
        const F = {
            [j.ChatGptSettingsKey.ENABLE_CONTENT_SCRIPT]: true,
            [j.ChatGptSettingsKey.EAGER_SEARCH]: false,
            [j.ChatGptSettingsKey.SHORT_SEARCH_RESPONSES]: true,
            [j.ChatGptSettingsKey.IFRAME_POPUP]: false,
            [j.ChatGptSettingsKey.AUTO_REFRESH_SESSION]: true,
            [j.ChatGptSettingsKey.KEEP_CHATGPT_PINNED]: false,
            [j.ChatGptSettingsKey.DEBUG]: false,
            [j.ChatGptSettingsKey.RESPONSE_BEHAVIOR_TYPE]: j.ResponseBehaviorType.DEFAULT,
            [j.ChatGptSettingsKey.ENABLE_EMAIL]: false,
            [j.ChatGptSettingsKey.EMAIL_LENGTH]: "Brief",
            [j.ChatGptSettingsKey.EMAIL_STYLE]: "Formal",
            [j.ChatGptSettingsKey.EMAIL_URGENCY]: "Non-urgent",
            [j.ChatGptSettingsKey.EMAIL_TONE]: "Friendly"
        };
        async function l(D, h) {
            const z = await A();
            return z[D] = h, chrome.storage.local.set(z);
        }
        async function Z(D) {
            return chrome.storage.local.set({
                [j.CHAT_GPT_SETTINGS_KEY]: D
            });
        }
        async function A() {
            return chrome.storage.local.get(j.CHAT_GPT_SETTINGS_KEY).then((D => {
                if (D[j.CHAT_GPT_SETTINGS_KEY]) return {
                    ...F,
                    ...D[j.CHAT_GPT_SETTINGS_KEY]
                };
                return F;
            }));
        }
        async function q(D) {
            return chrome.storage.local.get(j.CHAT_GPT_SETTINGS_KEY).then((h => {
                if (!h[j.CHAT_GPT_SETTINGS_KEY]) return null;
                return h[j.CHAT_GPT_SETTINGS_KEY][D];
            }));
        }
        z.defaultSettings = F;
    }, {
        p2: 156
    } ],
    162: [ function(D, h, z) {
        "use strict";
        async function j() {
            const D = chrome.runtime.getManifest().options_ui.page;
            chrome.tabs.create({
                url: chrome.runtime.getURL(`${D}#/settings`)
            });
        }
        async function F() {
            const D = {
                active: true,
                lastFocusedWindow: true
            }, [h] = await chrome.tabs.query(D);
            return h;
        }
        async function l() {
            chrome.tabs.create({
                active: false,
                url: "https://chatgpt.com/"
            }, (D => {
                setTimeout((() => {
                    D.id && chrome.tabs.remove(D.id);
                }), 1e4);
            }));
        }
        async function Z() {
            const D = {
                url: "https://chatgpt.com/*",
                pinned: true,
                lastFocusedWindow: true
            }, h = await chrome.tabs.query(D);
            if (h.length === 0) chrome.tabs.create({
                url: "https://chatgpt.com/",
                pinned: true,
                active: false
            }); else chrome.tabs.reload(h[0].id);
        }
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.getCurrentTab = F, z.maybeOpenAndCloseChatGptTab = l, z.maybePinChatGptTab = Z,
        z.openSettings = j;
    }, {} ]
}, {}, [ 154 ]);