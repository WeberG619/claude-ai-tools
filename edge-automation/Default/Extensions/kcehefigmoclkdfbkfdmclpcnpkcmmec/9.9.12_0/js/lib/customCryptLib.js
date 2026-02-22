if (!Uint8Array.prototype.slice) {
  Object.defineProperty(Uint8Array.prototype, 'slice', {
    value: Array.prototype.slice,
  })
}

/**
 * Encode multi-byte Unicode string into utf-8 multiple single-byte characters
 * (BMP / basic multilingual plane only)
 *
 * Chars in range U+0080 - U+07FF are encoded in 2 chars, U+0800 - U+FFFF in 3 chars
 *
 * @return encoded string
 */
function encodeUTF8(input) {
  // use regular expressions & String.replace callback function for better efficiency
  // than procedural approaches
  var str = input.replace(
    /[\u0080-\u07ff]/g, // U+0080 - U+07FF => 2 bytes 110yyyyy, 10zzzzzz
    function (c) {
      var cc = c.charCodeAt(0)
      return String.fromCharCode(0xc0 | (cc >> 6), 0x80 | (cc & 0x3f))
    }
  )
  str = str.replace(
    /[\u0800-\uffff]/g, // U+0800 - U+FFFF => 3 bytes 1110xxxx, 10yyyyyy, 10zzzzzz
    function (c) {
      var cc = c.charCodeAt(0)
      return String.fromCharCode(
        0xe0 | (cc >> 12),
        0x80 | ((cc >> 6) & 0x3f),
        0x80 | (cc & 0x3f)
      )
    }
  )
  return str
}

/**
 * Decode utf-8 encoded string back into multi-byte Unicode characters
 *
 * @return decoded string
 */
function decodeUTF8(t) {
  var e = t.replace(/[\u00c0-\u00df][\u0080-\u00bf]/g, function (t) {
    var e = ((31 & t.charCodeAt(0)) << 6) | (63 & t.charCodeAt(1))
    return String.fromCharCode(e)
  })
  return (e = e.replace(
    /[\u00e0-\u00ef][\u0080-\u00bf][\u0080-\u00bf]/g,
    function (t) {
      var e =
        ((15 & t.charCodeAt(0)) << 12) |
        ((63 & t.charCodeAt(1)) << 6) |
        (63 & t.charCodeAt(2))
      return String.fromCharCode(e)
    }
  ))
}
function convertFromHex(hexStr) {
  var hexStrLength = hexStr.length

  // Convert
  var str = []
  for (var i = 0; i < hexStrLength; i += 2) {
    str[str.length] = String.fromCharCode(parseInt(hexStr.substr(i, 2), 16))
  }

  return str.join('')
}

var crypto_wrapper = {
  SHA1: function (input) {
    return asmCrypto.SHA1.hex(input)
  },
  SHA256: function (input) {
    return asmCrypto.SHA256.hex(input)
  },
  random: function (bytes) {
    var output = new Uint8Array(bytes)
    asmCrypto.getRandomValues(output)
    return asmCrypto.bytes_to_hex(output)
  },
  // openssl based key and iv generation
  createKeyAndIV: function (password, salt) {
    var data00 = password + convertFromHex(salt)
    var hashtarget = ''
    var result = ''
    var keymaterial = []
    var count = 1 //openssl rounds
    var miter = 3
    var loop = 0,
      key,
      iv
    keymaterial[loop++] = data00

    for (var j = 0; j < miter; j++) {
      if (j == 0) {
        result = data00
      } else {
        hashtarget = convertFromHex(result)
        hashtarget += data00
        result = hashtarget
      }
      for (var c = 0; c < count; c++) {
        result = md5(result)
      }
      keymaterial[loop++] = result
    }
    key = asmCrypto.hex_to_bytes(keymaterial[1] + keymaterial[2])
    iv = asmCrypto.hex_to_bytes(keymaterial[3])
    return { key: key, iv: iv, salt: salt }
  },
  aes_encrypt: function (context, input) {
    var key = context.key
    var iv = context.iv
    var blockSize = 16
    var originalInput = input

    try {
      var inputBytes = asmCrypto.string_to_bytes(encodeUTF8(input))

      var charDiv = blockSize - ((inputBytes.length + 1) % blockSize)
      var paddedInputBytes = new Uint8Array(inputBytes.length + charDiv + 1)
      paddedInputBytes.set(inputBytes)

      // PKCS5 paddding
      var idx = 0
      paddedInputBytes[inputBytes.length + idx++] = 10
      for (var c = 0; c < charDiv; c++) {
        paddedInputBytes[inputBytes.length + idx++] = charDiv
      }

      return asmCrypto.bytes_to_base64(
        asmCrypto.AES_CBC.encrypt(paddedInputBytes, key, null, iv)
      )
    } catch (e) {
      // any failure return original input
      return originalInput
    }
  },
  aes_decrypt: function (context, input) {
    var key = context.key
    var iv = context.iv
    var originalInput = input

    try {
      var plainBytes = asmCrypto.AES_CBC.decrypt(atob(input), key, null, iv)

      // remove pkcs5 padding
      var length = plainBytes.length
      plainBytes = plainBytes.slice(0, length - plainBytes[length - 1] - 1)

      var plainText = asmCrypto.bytes_to_string(plainBytes)
      return decodeUTF8(plainText)
    } catch (e) {
      // any failure return original input
      return originalInput
    }
  },
}

// returns MD5 of input string
function md5(input) {
  var i,
    output = []
  output[(input.length >> 2) - 1] = undefined
  for (i = 0; i < output.length; i += 1) {
    output[i] = 0
  }
  for (i = 0; i < input.length * 8; i += 8) {
    output[i >> 5] |= input.charCodeAt(i / 8) << i % 32
  }
  return MD5(output, input.length)
}

// returns sha256 of input string
function sha256(input) {
  return crypto_wrapper.SHA256(input)
}

function sha1(input) {
  return crypto_wrapper.SHA1(input)
}

var keyIVCache = {}
// creates key/iv for given password and salt
// returns an object with key, iv and salt
function createKeyAndIV(password, salt) {
  var cacheKey = password + salt
  if (!(cacheKey in keyIVCache)) {
    keyIVCache[cacheKey] = crypto_wrapper.createKeyAndIV(password, salt)
  }

  return keyIVCache[cacheKey]
}

function createRSApair() {
  crypt = new JSEncrypt({ default_key_size: 2048 })
  PublicPrivateKey = {
    PublicKey: crypt.getPublicKey(),
    PrivateKey: crypt.getPrivateKey(),
  }
  private_key = PublicPrivateKey.PrivateKey.replace(
    '-----BEGIN RSA PRIVATE KEY-----',
    ''
  )
    .replace('-----END RSA PRIVATE KEY-----', '')
    .replace(/(\r\n|\n|\r)/gm, '')
  public_key = PublicPrivateKey.PublicKey.replace(
    '-----BEGIN PUBLIC KEY-----',
    ''
  )
    .replace('-----END PUBLIC KEY-----', '')
    .replace(/(\r\n|\n|\r)/gm, '')
  return { public_key: public_key, private_key: private_key }
}

// encrypt plain text using given key/iv
function encrypt(context, input) {
  return crypto_wrapper.aes_encrypt(context, input)
}

// decrypt cipher text using given key/iv/salt
function decrypt(context, cipherText) {
  return crypto_wrapper.aes_decrypt(context, cipherText)
}

// create random salt 8 byte
function salt() {
  return crypto_wrapper.random(8)
}

function getEncryptedPasswordHash(password) {
  var context = createKeyAndIV(password, password)
  return sha256(encrypt(context, password))
}

function getServerPassword(inputPassword) {
  return getEncryptedPasswordHash(getEncryptedPasswordHash(inputPassword))
}

function encryptKey(password, plain, salt) {
  return encrypt(createKeyAndIV(password, salt || sha256(password)), plain)
}

function decryptKey(password, cipher, salt, verifyKey) {
  var saltArg = salt || sha256(password)
  var keyAndIV = createKeyAndIV(password, saltArg)
  var plain = decrypt(keyAndIV, cipher)
  if (verifyKey) {
    if (cipher != encrypt(keyAndIV, plain)) {
      // decryption failed
      return cipher
    }
  }
  return plain
}

function _verifyKey(key, cipher, salt) {
  try {
    return cipher != decryptKey(key, cipher, salt, true)
  } catch (e) {}
  return false
}

function encryptObject(password, object, fields) {
  var salt = object.id
  for (var i = 0; i < fields.length; i++) {
    var plain = object[fields[i]]
    // do not re-encrypt if it is already encrypted.
    if (plain && plain.toString().indexOf('ENC_') == -1)
      var cipher = encryptKey(password, plain, salt)
    else var cipher = plain
    if (cipher != plain) {
      object[fields[i]] = 'ENC_' + cipher
    }
  }
}

function decryptObject(password, object, fields, verifyKey) {
  var response = 0
  var salt = object.id
  for (var i = 0; i < fields.length; i++) {
    var cipher = object[fields[i]]
    if (cipher && cipher.length > 0) {
      if (cipher.indexOf('ENC_') == 0) {
        cipher = cipher.substr(4)
        if (password) {
          if (verifyKey) {
            if (!_verifyKey(password, cipher, salt)) {
              return 1 // decryption failed
            }
            verifyKey = false
          }
          var plain = decryptKey(password, cipher, salt)
          if (plain != cipher) {
            object[fields[i]] = plain
          } else {
            return 1 // decryption failed
          }
        } else {
          return 1 // decryption failed
        }
      } else if (password) {
        response = 2 // needs encryption
      }
    }
  }
  return response
}

// create random N byte string
function randomString(n) {
  var chars =
    '0123456789ABCDEFGHIJKLMNOPQRSTUVWXTZabcdefghiklmnopqrstuvwxyz!@#$%^&*(){}[]|\\/<>?,.;~'
  var pass = ''
  for (var i = 0; i < n; i++) {
    var rnum = Math.floor(Math.random() * chars.length)
    pass += chars.substring(rnum, rnum + 1)
  }
  return pass
}

// create random 16 byte string
function generateKey(size) {
  if (!size) {
    size = 16
  }
  return crypto_wrapper.random(size)
}

/*
 * JavaScript MD5 1.0.1
 * https://github.com/blueimp/JavaScript-MD5
 *
 * Copyright 2011, Sebastian Tschan
 * https://blueimp.net
 *
 * Licensed under the MIT license:
 * http://www.opensource.org/licenses/MIT
 *
 * Based on
 * A JavaScript implementation of the RSA Data Security, Inc. MD5 Message
 * Digest Algorithm, as defined in RFC 1321.
 * Version 2.2 Copyright (C) Paul Johnston 1999 - 2009
 * Other contributors: Greg Holt, Andrew Kepert, Ydnar, Lostinet
 * Distributed under the BSD License
 * See http://pajhome.org.uk/crypt/md5 for more info.
 */
function md5main(t) {
  'use strict'
  function e(t, e) {
    var n = (65535 & t) + (65535 & e)
    return (((t >> 16) + (e >> 16) + (n >> 16)) << 16) | (65535 & n)
  }
  function n(t, e) {
    return (t << e) | (t >>> (32 - e))
  }
  function r(t, r, i, o, s, a) {
    return e(n(e(e(r, t), e(o, a)), s), i)
  }
  function i(t, e, n, i, o, s, a) {
    return r((e & n) | (~e & i), t, e, o, s, a)
  }
  function o(t, e, n, i, o, s, a) {
    return r((e & i) | (n & ~i), t, e, o, s, a)
  }
  function s(t, e, n, i, o, s, a) {
    return r(e ^ n ^ i, t, e, o, s, a)
  }
  function a(t, e, n, i, o, s, a) {
    return r(n ^ (e | ~i), t, e, o, s, a)
  }
  function u(t, n) {
    ;(t[n >> 5] |= 128 << n % 32), (t[14 + (((n + 64) >>> 9) << 4)] = n)
    var r,
      u,
      c,
      l,
      h,
      f = 1732584193,
      d = -271733879,
      p = -1732584194,
      m = 271733878
    for (r = 0; r < t.length; r += 16)
      (u = f),
        (c = d),
        (l = p),
        (h = m),
        (d = a(
          (d = a(
            (d = a(
              (d = a(
                (d = s(
                  (d = s(
                    (d = s(
                      (d = s(
                        (d = o(
                          (d = o(
                            (d = o(
                              (d = o(
                                (d = i(
                                  (d = i(
                                    (d = i(
                                      (d = i(
                                        d,
                                        (p = i(
                                          p,
                                          (m = i(
                                            m,
                                            (f = i(
                                              f,
                                              d,
                                              p,
                                              m,
                                              t[r],
                                              7,
                                              -680876936
                                            )),
                                            d,
                                            p,
                                            t[r + 1],
                                            12,
                                            -389564586
                                          )),
                                          f,
                                          d,
                                          t[r + 2],
                                          17,
                                          606105819
                                        )),
                                        m,
                                        f,
                                        t[r + 3],
                                        22,
                                        -1044525330
                                      )),
                                      (p = i(
                                        p,
                                        (m = i(
                                          m,
                                          (f = i(
                                            f,
                                            d,
                                            p,
                                            m,
                                            t[r + 4],
                                            7,
                                            -176418897
                                          )),
                                          d,
                                          p,
                                          t[r + 5],
                                          12,
                                          1200080426
                                        )),
                                        f,
                                        d,
                                        t[r + 6],
                                        17,
                                        -1473231341
                                      )),
                                      m,
                                      f,
                                      t[r + 7],
                                      22,
                                      -45705983
                                    )),
                                    (p = i(
                                      p,
                                      (m = i(
                                        m,
                                        (f = i(
                                          f,
                                          d,
                                          p,
                                          m,
                                          t[r + 8],
                                          7,
                                          1770035416
                                        )),
                                        d,
                                        p,
                                        t[r + 9],
                                        12,
                                        -1958414417
                                      )),
                                      f,
                                      d,
                                      t[r + 10],
                                      17,
                                      -42063
                                    )),
                                    m,
                                    f,
                                    t[r + 11],
                                    22,
                                    -1990404162
                                  )),
                                  (p = i(
                                    p,
                                    (m = i(
                                      m,
                                      (f = i(
                                        f,
                                        d,
                                        p,
                                        m,
                                        t[r + 12],
                                        7,
                                        1804603682
                                      )),
                                      d,
                                      p,
                                      t[r + 13],
                                      12,
                                      -40341101
                                    )),
                                    f,
                                    d,
                                    t[r + 14],
                                    17,
                                    -1502002290
                                  )),
                                  m,
                                  f,
                                  t[r + 15],
                                  22,
                                  1236535329
                                )),
                                (p = o(
                                  p,
                                  (m = o(
                                    m,
                                    (f = o(
                                      f,
                                      d,
                                      p,
                                      m,
                                      t[r + 1],
                                      5,
                                      -165796510
                                    )),
                                    d,
                                    p,
                                    t[r + 6],
                                    9,
                                    -1069501632
                                  )),
                                  f,
                                  d,
                                  t[r + 11],
                                  14,
                                  643717713
                                )),
                                m,
                                f,
                                t[r],
                                20,
                                -373897302
                              )),
                              (p = o(
                                p,
                                (m = o(
                                  m,
                                  (f = o(f, d, p, m, t[r + 5], 5, -701558691)),
                                  d,
                                  p,
                                  t[r + 10],
                                  9,
                                  38016083
                                )),
                                f,
                                d,
                                t[r + 15],
                                14,
                                -660478335
                              )),
                              m,
                              f,
                              t[r + 4],
                              20,
                              -405537848
                            )),
                            (p = o(
                              p,
                              (m = o(
                                m,
                                (f = o(f, d, p, m, t[r + 9], 5, 568446438)),
                                d,
                                p,
                                t[r + 14],
                                9,
                                -1019803690
                              )),
                              f,
                              d,
                              t[r + 3],
                              14,
                              -187363961
                            )),
                            m,
                            f,
                            t[r + 8],
                            20,
                            1163531501
                          )),
                          (p = o(
                            p,
                            (m = o(
                              m,
                              (f = o(f, d, p, m, t[r + 13], 5, -1444681467)),
                              d,
                              p,
                              t[r + 2],
                              9,
                              -51403784
                            )),
                            f,
                            d,
                            t[r + 7],
                            14,
                            1735328473
                          )),
                          m,
                          f,
                          t[r + 12],
                          20,
                          -1926607734
                        )),
                        (p = s(
                          p,
                          (m = s(
                            m,
                            (f = s(f, d, p, m, t[r + 5], 4, -378558)),
                            d,
                            p,
                            t[r + 8],
                            11,
                            -2022574463
                          )),
                          f,
                          d,
                          t[r + 11],
                          16,
                          1839030562
                        )),
                        m,
                        f,
                        t[r + 14],
                        23,
                        -35309556
                      )),
                      (p = s(
                        p,
                        (m = s(
                          m,
                          (f = s(f, d, p, m, t[r + 1], 4, -1530992060)),
                          d,
                          p,
                          t[r + 4],
                          11,
                          1272893353
                        )),
                        f,
                        d,
                        t[r + 7],
                        16,
                        -155497632
                      )),
                      m,
                      f,
                      t[r + 10],
                      23,
                      -1094730640
                    )),
                    (p = s(
                      p,
                      (m = s(
                        m,
                        (f = s(f, d, p, m, t[r + 13], 4, 681279174)),
                        d,
                        p,
                        t[r],
                        11,
                        -358537222
                      )),
                      f,
                      d,
                      t[r + 3],
                      16,
                      -722521979
                    )),
                    m,
                    f,
                    t[r + 6],
                    23,
                    76029189
                  )),
                  (p = s(
                    p,
                    (m = s(
                      m,
                      (f = s(f, d, p, m, t[r + 9], 4, -640364487)),
                      d,
                      p,
                      t[r + 12],
                      11,
                      -421815835
                    )),
                    f,
                    d,
                    t[r + 15],
                    16,
                    530742520
                  )),
                  m,
                  f,
                  t[r + 2],
                  23,
                  -995338651
                )),
                (p = a(
                  p,
                  (m = a(
                    m,
                    (f = a(f, d, p, m, t[r], 6, -198630844)),
                    d,
                    p,
                    t[r + 7],
                    10,
                    1126891415
                  )),
                  f,
                  d,
                  t[r + 14],
                  15,
                  -1416354905
                )),
                m,
                f,
                t[r + 5],
                21,
                -57434055
              )),
              (p = a(
                p,
                (m = a(
                  m,
                  (f = a(f, d, p, m, t[r + 12], 6, 1700485571)),
                  d,
                  p,
                  t[r + 3],
                  10,
                  -1894986606
                )),
                f,
                d,
                t[r + 10],
                15,
                -1051523
              )),
              m,
              f,
              t[r + 1],
              21,
              -2054922799
            )),
            (p = a(
              p,
              (m = a(
                m,
                (f = a(f, d, p, m, t[r + 8], 6, 1873313359)),
                d,
                p,
                t[r + 15],
                10,
                -30611744
              )),
              f,
              d,
              t[r + 6],
              15,
              -1560198380
            )),
            m,
            f,
            t[r + 13],
            21,
            1309151649
          )),
          (p = a(
            p,
            (m = a(
              m,
              (f = a(f, d, p, m, t[r + 4], 6, -145523070)),
              d,
              p,
              t[r + 11],
              10,
              -1120210379
            )),
            f,
            d,
            t[r + 2],
            15,
            718787259
          )),
          m,
          f,
          t[r + 9],
          21,
          -343485551
        )),
        (f = e(f, u)),
        (d = e(d, c)),
        (p = e(p, l)),
        (m = e(m, h))
    return [f, d, p, m]
  }
  function c(t) {
    var e,
      n = ''
    for (e = 0; e < 32 * t.length; e += 8)
      n += String.fromCharCode((t[e >> 5] >>> e % 32) & 255)
    return n
  }
  function l(t) {
    var e,
      n,
      r = '0123456789abcdef',
      i = ''
    for (n = 0; n < t.length; n += 1)
      (e = t.charCodeAt(n)), (i += r.charAt((e >>> 4) & 15) + r.charAt(15 & e))
    return i
  }
  t.MD5 = function (t, e) {
    return l(c(u(t, 8 * e)))
  }
}
this,
  (function (t, e) {
    function n() {
      var t = Error.apply(this, arguments)
      ;(this.message = t.message), (this.stack = t.stack)
    }
    function r() {
      var t = Error.apply(this, arguments)
      ;(this.message = t.message), (this.stack = t.stack)
    }
    function i() {
      var t = Error.apply(this, arguments)
      ;(this.message = t.message), (this.stack = t.stack)
    }
    function o(t, e) {
      e = !!e
      for (
        var n = t.length, r = new Uint8Array(e ? 4 * n : n), i = 0, o = 0;
        n > i;
        i++
      ) {
        var s = t.charCodeAt(i)
        if (e && s >= 55296 && 56319 >= s) {
          if (++i >= n)
            throw new Error(
              'Malformed string, low surrogate expected at position ' + i
            )
          s = ((55296 ^ s) << 10) | 65536 | (56320 ^ t.charCodeAt(i))
        } else if (!e && s >>> 8)
          throw new Error('Wide characters are not allowed.')
        !e || 127 >= s
          ? (r[o++] = s)
          : 2047 >= s
          ? ((r[o++] = 192 | (s >> 6)), (r[o++] = 128 | (63 & s)))
          : 65535 >= s
          ? ((r[o++] = 224 | (s >> 12)),
            (r[o++] = 128 | ((s >> 6) & 63)),
            (r[o++] = 128 | (63 & s)))
          : ((r[o++] = 240 | (s >> 18)),
            (r[o++] = 128 | ((s >> 12) & 63)),
            (r[o++] = 128 | ((s >> 6) & 63)),
            (r[o++] = 128 | (63 & s)))
      }
      return r.subarray(0, o)
    }
    function s(t) {
      var e = t.length
      1 & e && ((t = '0' + t), e++)
      for (var n = new Uint8Array(e >> 1), r = 0; e > r; r += 2)
        n[r >> 1] = parseInt(t.substr(r, 2), 16)
      return n
    }
    function a(t) {
      return o(atob(t))
    }
    function u(t, e) {
      e = !!e
      for (var n = t.length, r = new Array(n), i = 0, o = 0; n > i; i++) {
        var s = t[i]
        if (!e || 128 > s) r[o++] = s
        else if (s >= 192 && 224 > s && n > i + 1)
          r[o++] = ((31 & s) << 6) | (63 & t[++i])
        else if (s >= 224 && 240 > s && n > i + 2)
          r[o++] = ((15 & s) << 12) | ((63 & t[++i]) << 6) | (63 & t[++i])
        else {
          if (!(s >= 240 && 248 > s && n > i + 3))
            throw new Error('Malformed UTF8 character at byte offset ' + i)
          var a =
            ((7 & s) << 18) |
            ((63 & t[++i]) << 12) |
            ((63 & t[++i]) << 6) |
            (63 & t[++i])
          65535 >= a
            ? (r[o++] = a)
            : ((a ^= 65536),
              (r[o++] = 55296 | (a >> 10)),
              (r[o++] = 56320 | (1023 & a)))
        }
      }
      var u = '',
        c = 16384
      for (i = 0; o > i; i += c)
        u += String.fromCharCode.apply(
          String,
          r.slice(i, o >= i + c ? i + c : o)
        )
      return u
    }
    function c(t) {
      for (var e = '', n = 0; n < t.length; n++) {
        var r = (255 & t[n]).toString(16)
        r.length < 2 && (e += '0'), (e += r)
      }
      return e
    }
    function l(t) {
      return btoa(u(t))
    }
    function h(t) {
      return (
        (t -= 1),
        (t |= t >>> 1),
        (t |= t >>> 2),
        (t |= t >>> 4),
        (t |= t >>> 8),
        (t |= t >>> 16) + 1
      )
    }
    function f(t) {
      return 'number' == typeof t
    }
    function d(t) {
      return 'string' == typeof t
    }
    function p(t) {
      return t instanceof ArrayBuffer
    }
    function m(t) {
      return t instanceof Uint8Array
    }
    function g(t) {
      return (
        t instanceof Int8Array ||
        t instanceof Uint8Array ||
        t instanceof Int16Array ||
        t instanceof Uint16Array ||
        t instanceof Int32Array ||
        t instanceof Uint32Array ||
        t instanceof Float32Array ||
        t instanceof Float64Array
      )
    }
    function y(t, e) {
      var n = e.heap,
        r = n ? n.byteLength : e.heapSize || 65536
      if (4095 & r || 0 >= r)
        throw new Error(
          'heap size must be a positive integer and a multiple of 4096'
        )
      return n || new t(new ArrayBuffer(r))
    }
    function v(t, e, n, r, i) {
      var o = t.length - e,
        s = i > o ? o : i
      return t.set(n.subarray(r, r + s), e), s
    }
    function b(t) {
      ;(t = t || {}),
        (this.heap = y(Uint8Array, t).subarray(Ge.HEAP_DATA)),
        (this.asm = t.asm || Ge(e, null, this.heap.buffer)),
        (this.mode = null),
        (this.key = null),
        this.reset(t)
    }
    function _(t) {
      if (void 0 !== t) {
        if (p(t) || m(t)) t = new Uint8Array(t)
        else {
          if (!d(t)) throw new TypeError('unexpected key type')
          t = o(t)
        }
        var e = t.length
        if (16 !== e && 24 !== e && 32 !== e) throw new r('illegal key size')
        var n = new DataView(t.buffer, t.byteOffset, t.byteLength)
        this.asm.set_key(
          e >> 2,
          n.getUint32(0),
          n.getUint32(4),
          n.getUint32(8),
          n.getUint32(12),
          e > 16 ? n.getUint32(16) : 0,
          e > 16 ? n.getUint32(20) : 0,
          e > 24 ? n.getUint32(24) : 0,
          e > 24 ? n.getUint32(28) : 0
        ),
          (this.key = t)
      } else if (!this.key) throw new Error('key is required')
    }
    function w(t) {
      if (void 0 !== t) {
        if (p(t) || m(t)) t = new Uint8Array(t)
        else {
          if (!d(t)) throw new TypeError('unexpected iv type')
          t = o(t)
        }
        if (16 !== t.length) throw new r('illegal iv size')
        var e = new DataView(t.buffer, t.byteOffset, t.byteLength)
        ;(this.iv = t),
          this.asm.set_iv(
            e.getUint32(0),
            e.getUint32(4),
            e.getUint32(8),
            e.getUint32(12)
          )
      } else (this.iv = null), this.asm.set_iv(0, 0, 0, 0)
    }
    function S(t) {
      this.padding = void 0 === t || !!t
    }
    function C(t) {
      return (
        (t = t || {}),
        (this.result = null),
        (this.pos = 0),
        (this.len = 0),
        _.call(this, t.key),
        this.hasOwnProperty('iv') && w.call(this, t.iv),
        this.hasOwnProperty('padding') && S.call(this, t.padding),
        this
      )
    }
    function E(t) {
      if ((d(t) && (t = o(t)), p(t) && (t = new Uint8Array(t)), !m(t)))
        throw new TypeError("data isn't of expected type")
      for (
        var e = this.asm,
          n = this.heap,
          r = Ge.ENC[this.mode],
          i = Ge.HEAP_DATA,
          s = this.pos,
          a = this.len,
          u = 0,
          c = t.length || 0,
          l = 0,
          h = 0,
          f = new Uint8Array((a + c) & -16);
        c > 0;

      )
        (a += h = v(n, s + a, t, u, c)),
          (u += h),
          (c -= h),
          (h = e.cipher(r, i + s, a)) && f.set(n.subarray(s, s + h), l),
          (l += h),
          a > h ? ((s += h), (a -= h)) : ((s = 0), (a = 0))
      return (this.result = f), (this.pos = s), (this.len = a), this
    }
    function M(t) {
      var e = null,
        n = 0
      void 0 !== t && (n = (e = E.call(this, t).result).length)
      var i = this.asm,
        o = this.heap,
        s = Ge.ENC[this.mode],
        a = Ge.HEAP_DATA,
        u = this.pos,
        c = this.len,
        l = 16 - (c % 16),
        h = c
      if (this.hasOwnProperty('padding')) {
        if (this.padding) {
          for (var f = 0; l > f; ++f) o[u + c + f] = l
          h = c += l
        } else if (c % 16)
          throw new r('data length must be a multiple of the block size')
      } else c += l
      var d = new Uint8Array(n + h)
      return (
        n && d.set(e),
        c && i.cipher(s, a + u, c),
        h && d.set(o.subarray(u, u + h), n),
        (this.result = d),
        (this.pos = 0),
        (this.len = 0),
        this
      )
    }
    function k(t) {
      if ((d(t) && (t = o(t)), p(t) && (t = new Uint8Array(t)), !m(t)))
        throw new TypeError("data isn't of expected type")
      var e = this.asm,
        n = this.heap,
        r = Ge.DEC[this.mode],
        i = Ge.HEAP_DATA,
        s = this.pos,
        a = this.len,
        u = 0,
        c = t.length || 0,
        l = 0,
        h = (a + c) & -16,
        f = 0,
        g = 0
      this.hasOwnProperty('padding') &&
        this.padding &&
        (h -= f = a + c - h || 16)
      for (var y = new Uint8Array(h); c > 0; )
        (a += g = v(n, s + a, t, u, c)),
          (u += g),
          (c -= g),
          (g = e.cipher(r, i + s, a - (c ? 0 : f))) &&
            y.set(n.subarray(s, s + g), l),
          (l += g),
          a > g ? ((s += g), (a -= g)) : ((s = 0), (a = 0))
      return (this.result = y), (this.pos = s), (this.len = a), this
    }
    function x(t) {
      var e = null,
        n = 0
      void 0 !== t && (n = (e = k.call(this, t).result).length)
      var o = this.asm,
        s = this.heap,
        a = Ge.DEC[this.mode],
        u = Ge.HEAP_DATA,
        c = this.pos,
        l = this.len,
        h = l
      if (l > 0) {
        if (l % 16) {
          if (this.hasOwnProperty('padding'))
            throw new r('data length must be a multiple of the block size')
          l += 16 - (l % 16)
        }
        if (
          (o.cipher(a, u + c, l),
          this.hasOwnProperty('padding') && this.padding)
        ) {
          var f = s[c + h - 1]
          if (1 > f || f > 16 || f > h) throw new i('bad padding')
          for (var d = 0, p = f; p > 1; p--) d |= f ^ s[c + h - p]
          if (d) throw new i('bad padding')
          h -= f
        }
      }
      var m = new Uint8Array(n + h)
      return (
        n > 0 && m.set(e),
        h > 0 && m.set(s.subarray(c, c + h), n),
        (this.result = m),
        (this.pos = 0),
        (this.len = 0),
        this
      )
    }
    function A(t) {
      ;(this.padding = !0),
        (this.iv = null),
        b.call(this, t),
        (this.mode = 'CBC')
    }
    function T(t) {
      A.call(this, t)
    }
    function I(t) {
      A.call(this, t)
    }
    function R(t) {
      ;(this.nonce = null),
        (this.counter = 0),
        (this.counterSize = 0),
        b.call(this, t),
        (this.mode = 'CTR')
    }
    function N(t) {
      R.call(this, t)
    }
    function D(t, e, n) {
      if (void 0 !== n) {
        if (8 > n || n > 48) throw new r('illegal counter size')
        this.counterSize = n
        var i = Math.pow(2, n) - 1
        this.asm.set_mask(0, 0, (i / 4294967296) | 0, 0 | i)
      } else
        (this.counterSize = n = 48), this.asm.set_mask(0, 0, 65535, 4294967295)
      if (void 0 === t) throw new Error('nonce is required')
      if (p(t) || m(t)) t = new Uint8Array(t)
      else {
        if (!d(t)) throw new TypeError('unexpected nonce type')
        t = o(t)
      }
      var s = t.length
      if (!s || s > 16) throw new r('illegal nonce size')
      this.nonce = t
      var a = new DataView(new ArrayBuffer(16))
      if (
        (new Uint8Array(a.buffer).set(t),
        this.asm.set_nonce(
          a.getUint32(0),
          a.getUint32(4),
          a.getUint32(8),
          a.getUint32(12)
        ),
        void 0 !== e)
      ) {
        if (!f(e)) throw new TypeError('unexpected counter type')
        if (0 > e || e >= Math.pow(2, n)) throw new r('illegal counter value')
        ;(this.counter = e),
          this.asm.set_counter(0, 0, (e / 4294967296) | 0, 0 | e)
      } else this.counter = e = 0
    }
    function P(t) {
      return (
        (t = t || {}),
        C.call(this, t),
        D.call(this, t.nonce, t.counter, t.counterSize),
        this
      )
    }
    function B(t) {
      for (
        var e = this.heap, n = this.asm, r = 0, i = t.length || 0, o = 0;
        i > 0;

      ) {
        for (r += o = v(e, 0, t, r, i), i -= o; 15 & o; ) e[o++] = 0
        n.mac(Ge.MAC.GCM, Ge.HEAP_DATA, o)
      }
    }
    function L(t) {
      ;(this.nonce = null),
        (this.adata = null),
        (this.iv = null),
        (this.counter = 1),
        (this.tagSize = 16),
        b.call(this, t),
        (this.mode = 'GCM')
    }
    function O(t) {
      L.call(this, t)
    }
    function q(t) {
      L.call(this, t)
    }
    function U(t) {
      ;(t = t || {}), C.call(this, t)
      var e = this.asm,
        n = this.heap
      e.gcm_init()
      var i = t.tagSize
      if (void 0 !== i) {
        if (!f(i)) throw new TypeError('tagSize must be a number')
        if (4 > i || i > 16) throw new r('illegal tagSize value')
        this.tagSize = i
      } else this.tagSize = 16
      var s = t.nonce
      if (void 0 === s) throw new Error('nonce is required')
      if (m(s) || p(s)) s = new Uint8Array(s)
      else {
        if (!d(s)) throw new TypeError('unexpected nonce type')
        s = o(s)
      }
      this.nonce = s
      var a = s.length || 0,
        u = new Uint8Array(16)
      12 !== a
        ? (B.call(this, s),
          (n[0] =
            n[1] =
            n[2] =
            n[3] =
            n[4] =
            n[5] =
            n[6] =
            n[7] =
            n[8] =
            n[9] =
            n[10] =
              0),
          (n[11] = a >>> 29),
          (n[12] = (a >>> 21) & 255),
          (n[13] = (a >>> 13) & 255),
          (n[14] = (a >>> 5) & 255),
          (n[15] = (a << 3) & 255),
          e.mac(Ge.MAC.GCM, Ge.HEAP_DATA, 16),
          e.get_iv(Ge.HEAP_DATA),
          e.set_iv(),
          u.set(n.subarray(0, 16)))
        : (u.set(s), (u[15] = 1))
      var c = new DataView(u.buffer)
      ;(this.gamma0 = c.getUint32(12)),
        e.set_nonce(c.getUint32(0), c.getUint32(4), c.getUint32(8), 0),
        e.set_mask(0, 0, 0, 4294967295)
      var l = t.adata
      if (null != l) {
        if (m(l) || p(l)) l = new Uint8Array(l)
        else {
          if (!d(l)) throw new TypeError('unexpected adata type')
          l = o(l)
        }
        if (l.length > tn) throw new r('illegal adata length')
        l.length ? ((this.adata = l), B.call(this, l)) : (this.adata = null)
      } else this.adata = null
      var h = t.counter
      if (void 0 !== h) {
        if (!f(h)) throw new TypeError('counter must be a number')
        if (1 > h || h > 4294967295)
          throw new RangeError('counter must be a positive 32-bit integer')
        ;(this.counter = h), e.set_counter(0, 0, 0, (this.gamma0 + h) | 0)
      } else (this.counter = 1), e.set_counter(0, 0, 0, (this.gamma0 + 1) | 0)
      var g = t.iv
      if (void 0 !== g) {
        if (!f(h)) throw new TypeError('counter must be a number')
        ;(this.iv = g), w.call(this, g)
      }
      return this
    }
    function j(t) {
      if ((d(t) && (t = o(t)), p(t) && (t = new Uint8Array(t)), !m(t)))
        throw new TypeError("data isn't of expected type")
      var e = 0,
        n = t.length || 0,
        r = this.asm,
        i = this.heap,
        s = this.counter,
        a = this.pos,
        u = this.len,
        c = 0,
        l = (u + n) & -16,
        h = 0
      if (((s - 1) << 4) + u + n > tn) throw new RangeError('counter overflow')
      for (var f = new Uint8Array(l); n > 0; )
        (u += h = v(i, a + u, t, e, n)),
          (e += h),
          (n -= h),
          (h = r.cipher(Ge.ENC.CTR, Ge.HEAP_DATA + a, u)),
          (h = r.mac(Ge.MAC.GCM, Ge.HEAP_DATA + a, h)) &&
            f.set(i.subarray(a, a + h), c),
          (s += h >>> 4),
          (c += h),
          u > h ? ((a += h), (u -= h)) : ((a = 0), (u = 0))
      return (
        (this.result = f),
        (this.counter = s),
        (this.pos = a),
        (this.len = u),
        this
      )
    }
    function F() {
      var t = this.asm,
        e = this.heap,
        n = this.counter,
        r = this.tagSize,
        i = this.adata,
        o = this.pos,
        s = this.len,
        a = new Uint8Array(s + r)
      t.cipher(Ge.ENC.CTR, Ge.HEAP_DATA + o, (s + 15) & -16),
        s && a.set(e.subarray(o, o + s))
      for (var u = s; 15 & u; u++) e[o + u] = 0
      t.mac(Ge.MAC.GCM, Ge.HEAP_DATA + o, u)
      var c = null !== i ? i.length : 0,
        l = ((n - 1) << 4) + s
      return (
        (e[0] = e[1] = e[2] = 0),
        (e[3] = c >>> 29),
        (e[4] = c >>> 21),
        (e[5] = (c >>> 13) & 255),
        (e[6] = (c >>> 5) & 255),
        (e[7] = (c << 3) & 255),
        (e[8] = e[9] = e[10] = 0),
        (e[11] = l >>> 29),
        (e[12] = (l >>> 21) & 255),
        (e[13] = (l >>> 13) & 255),
        (e[14] = (l >>> 5) & 255),
        (e[15] = (l << 3) & 255),
        t.mac(Ge.MAC.GCM, Ge.HEAP_DATA, 16),
        t.get_iv(Ge.HEAP_DATA),
        t.set_counter(0, 0, 0, this.gamma0),
        t.cipher(Ge.ENC.CTR, Ge.HEAP_DATA, 16),
        a.set(e.subarray(0, r), s),
        (this.result = a),
        (this.counter = 1),
        (this.pos = 0),
        (this.len = 0),
        this
      )
    }
    function H(t) {
      var e = j.call(this, t).result,
        n = F.call(this).result,
        r = new Uint8Array(e.length + n.length)
      return (
        e.length && r.set(e),
        n.length && r.set(n, e.length),
        (this.result = r),
        this
      )
    }
    function z(t) {
      if ((d(t) && (t = o(t)), p(t) && (t = new Uint8Array(t)), !m(t)))
        throw new TypeError("data isn't of expected type")
      var e = 0,
        n = t.length || 0,
        r = this.asm,
        i = this.heap,
        s = this.counter,
        a = this.tagSize,
        u = this.pos,
        c = this.len,
        l = 0,
        h = c + n > a ? (c + n - a) & -16 : 0,
        f = c + n - h,
        g = 0
      if (((s - 1) << 4) + c + n > tn) throw new RangeError('counter overflow')
      for (var y = new Uint8Array(h); n > f; )
        (c += g = v(i, u + c, t, e, n - f)),
          (e += g),
          (n -= g),
          (g = r.mac(Ge.MAC.GCM, Ge.HEAP_DATA + u, g)),
          (g = r.cipher(Ge.DEC.CTR, Ge.HEAP_DATA + u, g)) &&
            y.set(i.subarray(u, u + g), l),
          (s += g >>> 4),
          (l += g),
          (u = 0),
          (c = 0)
      return (
        n > 0 && (c += v(i, 0, t, e, n)),
        (this.result = y),
        (this.counter = s),
        (this.pos = u),
        (this.len = c),
        this
      )
    }
    function V() {
      var t = this.asm,
        e = this.heap,
        r = this.tagSize,
        o = this.adata,
        s = this.counter,
        a = this.pos,
        u = this.len,
        c = u - r
      if (r > u) throw new n('authentication tag not found')
      for (
        var l = new Uint8Array(c),
          h = new Uint8Array(e.subarray(a + c, a + u)),
          f = c;
        15 & f;
        f++
      )
        e[a + f] = 0
      t.mac(Ge.MAC.GCM, Ge.HEAP_DATA + a, f),
        t.cipher(Ge.DEC.CTR, Ge.HEAP_DATA + a, f),
        c && l.set(e.subarray(a, a + c))
      var d = null !== o ? o.length : 0,
        p = ((s - 1) << 4) + u - r
      ;(e[0] = e[1] = e[2] = 0),
        (e[3] = d >>> 29),
        (e[4] = d >>> 21),
        (e[5] = (d >>> 13) & 255),
        (e[6] = (d >>> 5) & 255),
        (e[7] = (d << 3) & 255),
        (e[8] = e[9] = e[10] = 0),
        (e[11] = p >>> 29),
        (e[12] = (p >>> 21) & 255),
        (e[13] = (p >>> 13) & 255),
        (e[14] = (p >>> 5) & 255),
        (e[15] = (p << 3) & 255),
        t.mac(Ge.MAC.GCM, Ge.HEAP_DATA, 16),
        t.get_iv(Ge.HEAP_DATA),
        t.set_counter(0, 0, 0, this.gamma0),
        t.cipher(Ge.ENC.CTR, Ge.HEAP_DATA, 16)
      var m = 0
      for (f = 0; r > f; ++f) m |= h[f] ^ e[f]
      if (m) throw new i('data integrity check failed')
      return (
        (this.result = l),
        (this.counter = 1),
        (this.pos = 0),
        (this.len = 0),
        this
      )
    }
    function K(t) {
      var e = z.call(this, t).result,
        n = V.call(this).result,
        r = new Uint8Array(e.length + n.length)
      return (
        e.length && r.set(e),
        n.length && r.set(n, e.length),
        (this.result = r),
        this
      )
    }
    function $(t, e, n, r) {
      if (void 0 === t) throw new SyntaxError('data required')
      if (void 0 === e) throw new SyntaxError('key required')
      return new A({
        heap: on,
        asm: sn,
        key: e,
        padding: n,
        iv: r,
      }).encrypt(t).result
    }
    function W(t, e, n, r) {
      if (void 0 === t) throw new SyntaxError('data required')
      if (void 0 === e) throw new SyntaxError('key required')
      return new A({
        heap: on,
        asm: sn,
        key: e,
        padding: n,
        iv: r,
      }).decrypt(t).result
    }
    function G(t, e, n, r, i) {
      if (void 0 === t) throw new SyntaxError('data required')
      if (void 0 === e) throw new SyntaxError('key required')
      if (void 0 === n) throw new SyntaxError('nonce required')
      return new L({
        heap: on,
        asm: sn,
        key: e,
        nonce: n,
        adata: r,
        tagSize: i,
      }).encrypt(t).result
    }
    function X(t, e, n, r, i) {
      if (void 0 === t) throw new SyntaxError('data required')
      if (void 0 === e) throw new SyntaxError('key required')
      if (void 0 === n) throw new SyntaxError('nonce required')
      return new L({
        heap: on,
        asm: sn,
        key: e,
        nonce: n,
        adata: r,
        tagSize: i,
      }).decrypt(t).result
    }
    function Y() {
      return (
        (this.result = null),
        (this.pos = 0),
        (this.len = 0),
        this.asm.reset(),
        this
      )
    }
    function J(t) {
      if (null !== this.result)
        throw new n('state must be reset before processing new data')
      if ((d(t) && (t = o(t)), p(t) && (t = new Uint8Array(t)), !m(t)))
        throw new TypeError("data isn't of expected type")
      for (
        var e = this.asm,
          r = this.heap,
          i = this.pos,
          s = this.len,
          a = 0,
          u = t.length,
          c = 0;
        u > 0;

      )
        (s += c = v(r, i + s, t, a, u)),
          (a += c),
          (u -= c),
          (i += c = e.process(i, s)),
          (s -= c) || (i = 0)
      return (this.pos = i), (this.len = s), this
    }
    function Z() {
      if (null !== this.result)
        throw new n('state must be reset before processing new data')
      return (
        this.asm.finish(this.pos, this.len, 0),
        (this.result = new Uint8Array(this.HASH_SIZE)),
        this.result.set(this.heap.subarray(0, this.HASH_SIZE)),
        (this.pos = 0),
        (this.len = 0),
        this
      )
    }
    function Q(t, e, n) {
      'use asm'
      var r = 0,
        i = 0,
        o = 0,
        s = 0,
        a = 0,
        u = 0,
        c = 0
      var l = 0,
        h = 0,
        f = 0,
        d = 0,
        p = 0,
        m = 0,
        g = 0,
        y = 0,
        v = 0,
        b = 0
      var _ = new t.Uint8Array(n)
      function w(t, e, n, u, c, l, h, f, d, p, m, g, y, v, b, _) {
        t = t | 0
        e = e | 0
        n = n | 0
        u = u | 0
        c = c | 0
        l = l | 0
        h = h | 0
        f = f | 0
        d = d | 0
        p = p | 0
        m = m | 0
        g = g | 0
        y = y | 0
        v = v | 0
        b = b | 0
        _ = _ | 0
        var w = 0,
          S = 0,
          C = 0,
          E = 0,
          M = 0,
          k = 0,
          x = 0,
          A = 0,
          T = 0,
          I = 0,
          R = 0,
          N = 0,
          D = 0,
          P = 0,
          B = 0,
          L = 0,
          O = 0,
          q = 0,
          U = 0,
          j = 0,
          F = 0,
          H = 0,
          z = 0,
          V = 0,
          K = 0,
          $ = 0,
          W = 0,
          G = 0,
          X = 0,
          Y = 0,
          J = 0,
          Z = 0,
          Q = 0,
          tt = 0,
          et = 0,
          nt = 0,
          rt = 0,
          it = 0,
          ot = 0,
          st = 0,
          at = 0,
          ut = 0,
          ct = 0,
          lt = 0,
          ht = 0,
          ft = 0,
          dt = 0,
          pt = 0,
          mt = 0,
          gt = 0,
          yt = 0,
          vt = 0,
          bt = 0,
          _t = 0,
          wt = 0,
          St = 0,
          Ct = 0,
          Et = 0,
          Mt = 0,
          kt = 0,
          xt = 0,
          At = 0,
          Tt = 0,
          It = 0,
          Rt = 0,
          Nt = 0,
          Dt = 0,
          Pt = 0,
          Bt = 0,
          Lt = 0,
          Ot = 0
        w = r
        S = i
        C = o
        E = s
        M = a
        x =
          (t +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (~S & E)) +
            1518500249) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        x =
          (e +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (~S & E)) +
            1518500249) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        x =
          (n +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (~S & E)) +
            1518500249) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        x =
          (u +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (~S & E)) +
            1518500249) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        x =
          (c +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (~S & E)) +
            1518500249) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        x =
          (l +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (~S & E)) +
            1518500249) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        x =
          (h +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (~S & E)) +
            1518500249) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        x =
          (f +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (~S & E)) +
            1518500249) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        x =
          (d +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (~S & E)) +
            1518500249) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        x =
          (p +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (~S & E)) +
            1518500249) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        x =
          (m +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (~S & E)) +
            1518500249) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        x =
          (g +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (~S & E)) +
            1518500249) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        x =
          (y +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (~S & E)) +
            1518500249) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        x =
          (v +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (~S & E)) +
            1518500249) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        x =
          (b +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (~S & E)) +
            1518500249) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        x =
          (_ +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (~S & E)) +
            1518500249) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = v ^ d ^ n ^ t
        A = (k << 1) | (k >>> 31)
        x =
          (A +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (~S & E)) +
            1518500249) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = b ^ p ^ u ^ e
        T = (k << 1) | (k >>> 31)
        x =
          (T +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (~S & E)) +
            1518500249) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = _ ^ m ^ c ^ n
        I = (k << 1) | (k >>> 31)
        x =
          (I +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (~S & E)) +
            1518500249) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = A ^ g ^ l ^ u
        R = (k << 1) | (k >>> 31)
        x =
          (R +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (~S & E)) +
            1518500249) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = T ^ y ^ h ^ c
        N = (k << 1) | (k >>> 31)
        x = (N + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) + 1859775393) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = I ^ v ^ f ^ l
        D = (k << 1) | (k >>> 31)
        x = (D + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) + 1859775393) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = R ^ b ^ d ^ h
        P = (k << 1) | (k >>> 31)
        x = (P + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) + 1859775393) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = N ^ _ ^ p ^ f
        B = (k << 1) | (k >>> 31)
        x = (B + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) + 1859775393) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = D ^ A ^ m ^ d
        L = (k << 1) | (k >>> 31)
        x = (L + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) + 1859775393) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = P ^ T ^ g ^ p
        O = (k << 1) | (k >>> 31)
        x = (O + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) + 1859775393) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = B ^ I ^ y ^ m
        q = (k << 1) | (k >>> 31)
        x = (q + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) + 1859775393) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = L ^ R ^ v ^ g
        U = (k << 1) | (k >>> 31)
        x = (U + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) + 1859775393) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = O ^ N ^ b ^ y
        j = (k << 1) | (k >>> 31)
        x = (j + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) + 1859775393) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = q ^ D ^ _ ^ v
        F = (k << 1) | (k >>> 31)
        x = (F + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) + 1859775393) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = U ^ P ^ A ^ b
        H = (k << 1) | (k >>> 31)
        x = (H + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) + 1859775393) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = j ^ B ^ T ^ _
        z = (k << 1) | (k >>> 31)
        x = (z + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) + 1859775393) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = F ^ L ^ I ^ A
        V = (k << 1) | (k >>> 31)
        x = (V + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) + 1859775393) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = H ^ O ^ R ^ T
        K = (k << 1) | (k >>> 31)
        x = (K + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) + 1859775393) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = z ^ q ^ N ^ I
        $ = (k << 1) | (k >>> 31)
        x = ($ + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) + 1859775393) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = V ^ U ^ D ^ R
        W = (k << 1) | (k >>> 31)
        x = (W + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) + 1859775393) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = K ^ j ^ P ^ N
        G = (k << 1) | (k >>> 31)
        x = (G + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) + 1859775393) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = $ ^ F ^ B ^ D
        X = (k << 1) | (k >>> 31)
        x = (X + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) + 1859775393) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = W ^ H ^ L ^ P
        Y = (k << 1) | (k >>> 31)
        x = (Y + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) + 1859775393) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = G ^ z ^ O ^ B
        J = (k << 1) | (k >>> 31)
        x = (J + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) + 1859775393) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = X ^ V ^ q ^ L
        Z = (k << 1) | (k >>> 31)
        x =
          (Z +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (S & E) | (C & E)) -
            1894007588) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = Y ^ K ^ U ^ O
        Q = (k << 1) | (k >>> 31)
        x =
          (Q +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (S & E) | (C & E)) -
            1894007588) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = J ^ $ ^ j ^ q
        tt = (k << 1) | (k >>> 31)
        x =
          (tt +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (S & E) | (C & E)) -
            1894007588) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = Z ^ W ^ F ^ U
        et = (k << 1) | (k >>> 31)
        x =
          (et +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (S & E) | (C & E)) -
            1894007588) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = Q ^ G ^ H ^ j
        nt = (k << 1) | (k >>> 31)
        x =
          (nt +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (S & E) | (C & E)) -
            1894007588) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = tt ^ X ^ z ^ F
        rt = (k << 1) | (k >>> 31)
        x =
          (rt +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (S & E) | (C & E)) -
            1894007588) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = et ^ Y ^ V ^ H
        it = (k << 1) | (k >>> 31)
        x =
          (it +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (S & E) | (C & E)) -
            1894007588) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = nt ^ J ^ K ^ z
        ot = (k << 1) | (k >>> 31)
        x =
          (ot +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (S & E) | (C & E)) -
            1894007588) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = rt ^ Z ^ $ ^ V
        st = (k << 1) | (k >>> 31)
        x =
          (st +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (S & E) | (C & E)) -
            1894007588) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = it ^ Q ^ W ^ K
        at = (k << 1) | (k >>> 31)
        x =
          (at +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (S & E) | (C & E)) -
            1894007588) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = ot ^ tt ^ G ^ $
        ut = (k << 1) | (k >>> 31)
        x =
          (ut +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (S & E) | (C & E)) -
            1894007588) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = st ^ et ^ X ^ W
        ct = (k << 1) | (k >>> 31)
        x =
          (ct +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (S & E) | (C & E)) -
            1894007588) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = at ^ nt ^ Y ^ G
        lt = (k << 1) | (k >>> 31)
        x =
          (lt +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (S & E) | (C & E)) -
            1894007588) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = ut ^ rt ^ J ^ X
        ht = (k << 1) | (k >>> 31)
        x =
          (ht +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (S & E) | (C & E)) -
            1894007588) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = ct ^ it ^ Z ^ Y
        ft = (k << 1) | (k >>> 31)
        x =
          (ft +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (S & E) | (C & E)) -
            1894007588) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = lt ^ ot ^ Q ^ J
        dt = (k << 1) | (k >>> 31)
        x =
          (dt +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (S & E) | (C & E)) -
            1894007588) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = ht ^ st ^ tt ^ Z
        pt = (k << 1) | (k >>> 31)
        x =
          (pt +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (S & E) | (C & E)) -
            1894007588) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = ft ^ at ^ et ^ Q
        mt = (k << 1) | (k >>> 31)
        x =
          (mt +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (S & E) | (C & E)) -
            1894007588) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = dt ^ ut ^ nt ^ tt
        gt = (k << 1) | (k >>> 31)
        x =
          (gt +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (S & E) | (C & E)) -
            1894007588) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = pt ^ ct ^ rt ^ et
        yt = (k << 1) | (k >>> 31)
        x =
          (yt +
            ((w << 5) | (w >>> 27)) +
            M +
            ((S & C) | (S & E) | (C & E)) -
            1894007588) |
          0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = mt ^ lt ^ it ^ nt
        vt = (k << 1) | (k >>> 31)
        x = (vt + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) - 899497514) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = gt ^ ht ^ ot ^ rt
        bt = (k << 1) | (k >>> 31)
        x = (bt + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) - 899497514) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = yt ^ ft ^ st ^ it
        _t = (k << 1) | (k >>> 31)
        x = (_t + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) - 899497514) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = vt ^ dt ^ at ^ ot
        wt = (k << 1) | (k >>> 31)
        x = (wt + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) - 899497514) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = bt ^ pt ^ ut ^ st
        St = (k << 1) | (k >>> 31)
        x = (St + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) - 899497514) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = _t ^ mt ^ ct ^ at
        Ct = (k << 1) | (k >>> 31)
        x = (Ct + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) - 899497514) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = wt ^ gt ^ lt ^ ut
        Et = (k << 1) | (k >>> 31)
        x = (Et + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) - 899497514) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = St ^ yt ^ ht ^ ct
        Mt = (k << 1) | (k >>> 31)
        x = (Mt + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) - 899497514) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = Ct ^ vt ^ ft ^ lt
        kt = (k << 1) | (k >>> 31)
        x = (kt + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) - 899497514) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = Et ^ bt ^ dt ^ ht
        xt = (k << 1) | (k >>> 31)
        x = (xt + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) - 899497514) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = Mt ^ _t ^ pt ^ ft
        At = (k << 1) | (k >>> 31)
        x = (At + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) - 899497514) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = kt ^ wt ^ mt ^ dt
        Tt = (k << 1) | (k >>> 31)
        x = (Tt + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) - 899497514) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = xt ^ St ^ gt ^ pt
        It = (k << 1) | (k >>> 31)
        x = (It + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) - 899497514) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = At ^ Ct ^ yt ^ mt
        Rt = (k << 1) | (k >>> 31)
        x = (Rt + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) - 899497514) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = Tt ^ Et ^ vt ^ gt
        Nt = (k << 1) | (k >>> 31)
        x = (Nt + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) - 899497514) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = It ^ Mt ^ bt ^ yt
        Dt = (k << 1) | (k >>> 31)
        x = (Dt + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) - 899497514) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = Rt ^ kt ^ _t ^ vt
        Pt = (k << 1) | (k >>> 31)
        x = (Pt + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) - 899497514) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = Nt ^ xt ^ wt ^ bt
        Bt = (k << 1) | (k >>> 31)
        x = (Bt + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) - 899497514) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = Dt ^ At ^ St ^ _t
        Lt = (k << 1) | (k >>> 31)
        x = (Lt + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) - 899497514) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        k = Pt ^ Tt ^ Ct ^ wt
        Ot = (k << 1) | (k >>> 31)
        x = (Ot + ((w << 5) | (w >>> 27)) + M + (S ^ C ^ E) - 899497514) | 0
        M = E
        E = C
        C = (S << 30) | (S >>> 2)
        S = w
        w = x
        r = (r + w) | 0
        i = (i + S) | 0
        o = (o + C) | 0
        s = (s + E) | 0
        a = (a + M) | 0
      }
      function S(t) {
        t = t | 0
        w(
          (_[t | 0] << 24) | (_[t | 1] << 16) | (_[t | 2] << 8) | _[t | 3],
          (_[t | 4] << 24) | (_[t | 5] << 16) | (_[t | 6] << 8) | _[t | 7],
          (_[t | 8] << 24) | (_[t | 9] << 16) | (_[t | 10] << 8) | _[t | 11],
          (_[t | 12] << 24) | (_[t | 13] << 16) | (_[t | 14] << 8) | _[t | 15],
          (_[t | 16] << 24) | (_[t | 17] << 16) | (_[t | 18] << 8) | _[t | 19],
          (_[t | 20] << 24) | (_[t | 21] << 16) | (_[t | 22] << 8) | _[t | 23],
          (_[t | 24] << 24) | (_[t | 25] << 16) | (_[t | 26] << 8) | _[t | 27],
          (_[t | 28] << 24) | (_[t | 29] << 16) | (_[t | 30] << 8) | _[t | 31],
          (_[t | 32] << 24) | (_[t | 33] << 16) | (_[t | 34] << 8) | _[t | 35],
          (_[t | 36] << 24) | (_[t | 37] << 16) | (_[t | 38] << 8) | _[t | 39],
          (_[t | 40] << 24) | (_[t | 41] << 16) | (_[t | 42] << 8) | _[t | 43],
          (_[t | 44] << 24) | (_[t | 45] << 16) | (_[t | 46] << 8) | _[t | 47],
          (_[t | 48] << 24) | (_[t | 49] << 16) | (_[t | 50] << 8) | _[t | 51],
          (_[t | 52] << 24) | (_[t | 53] << 16) | (_[t | 54] << 8) | _[t | 55],
          (_[t | 56] << 24) | (_[t | 57] << 16) | (_[t | 58] << 8) | _[t | 59],
          (_[t | 60] << 24) | (_[t | 61] << 16) | (_[t | 62] << 8) | _[t | 63]
        )
      }
      function C(t) {
        t = t | 0
        _[t | 0] = r >>> 24
        _[t | 1] = (r >>> 16) & 255
        _[t | 2] = (r >>> 8) & 255
        _[t | 3] = r & 255
        _[t | 4] = i >>> 24
        _[t | 5] = (i >>> 16) & 255
        _[t | 6] = (i >>> 8) & 255
        _[t | 7] = i & 255
        _[t | 8] = o >>> 24
        _[t | 9] = (o >>> 16) & 255
        _[t | 10] = (o >>> 8) & 255
        _[t | 11] = o & 255
        _[t | 12] = s >>> 24
        _[t | 13] = (s >>> 16) & 255
        _[t | 14] = (s >>> 8) & 255
        _[t | 15] = s & 255
        _[t | 16] = a >>> 24
        _[t | 17] = (a >>> 16) & 255
        _[t | 18] = (a >>> 8) & 255
        _[t | 19] = a & 255
      }
      function E() {
        r = 1732584193
        i = 4023233417
        o = 2562383102
        s = 271733878
        a = 3285377520
        u = c = 0
      }
      function M(t, e, n, l, h, f, d) {
        t = t | 0
        e = e | 0
        n = n | 0
        l = l | 0
        h = h | 0
        f = f | 0
        d = d | 0
        r = t
        i = e
        o = n
        s = l
        a = h
        u = f
        c = d
      }
      function k(t, e) {
        t = t | 0
        e = e | 0
        var n = 0
        if (t & 63) return -1
        while ((e | 0) >= 64) {
          S(t)
          t = (t + 64) | 0
          e = (e - 64) | 0
          n = (n + 64) | 0
        }
        u = (u + n) | 0
        if (u >>> 0 < n >>> 0) c = (c + 1) | 0
        return n | 0
      }
      function x(t, e, n) {
        t = t | 0
        e = e | 0
        n = n | 0
        var r = 0,
          i = 0
        if (t & 63) return -1
        if (~n) if (n & 31) return -1
        if ((e | 0) >= 64) {
          r = k(t, e) | 0
          if ((r | 0) == -1) return -1
          t = (t + r) | 0
          e = (e - r) | 0
        }
        r = (r + e) | 0
        u = (u + e) | 0
        if (u >>> 0 < e >>> 0) c = (c + 1) | 0
        _[t | e] = 128
        if ((e | 0) >= 56) {
          for (i = (e + 1) | 0; (i | 0) < 64; i = (i + 1) | 0) _[t | i] = 0
          S(t)
          e = 0
          _[t | 0] = 0
        }
        for (i = (e + 1) | 0; (i | 0) < 59; i = (i + 1) | 0) _[t | i] = 0
        _[t | 56] = (c >>> 21) & 255
        _[t | 57] = (c >>> 13) & 255
        _[t | 58] = (c >>> 5) & 255
        _[t | 59] = ((c << 3) & 255) | (u >>> 29)
        _[t | 60] = (u >>> 21) & 255
        _[t | 61] = (u >>> 13) & 255
        _[t | 62] = (u >>> 5) & 255
        _[t | 63] = (u << 3) & 255
        S(t)
        if (~n) C(n)
        return r | 0
      }
      function A() {
        r = l
        i = h
        o = f
        s = d
        a = p
        u = 64
        c = 0
      }
      function T() {
        r = m
        i = g
        o = y
        s = v
        a = b
        u = 64
        c = 0
      }
      function I(t, e, n, _, S, C, M, k, x, A, T, I, R, N, D, P) {
        t = t | 0
        e = e | 0
        n = n | 0
        _ = _ | 0
        S = S | 0
        C = C | 0
        M = M | 0
        k = k | 0
        x = x | 0
        A = A | 0
        T = T | 0
        I = I | 0
        R = R | 0
        N = N | 0
        D = D | 0
        P = P | 0
        E()
        w(
          t ^ 1549556828,
          e ^ 1549556828,
          n ^ 1549556828,
          _ ^ 1549556828,
          S ^ 1549556828,
          C ^ 1549556828,
          M ^ 1549556828,
          k ^ 1549556828,
          x ^ 1549556828,
          A ^ 1549556828,
          T ^ 1549556828,
          I ^ 1549556828,
          R ^ 1549556828,
          N ^ 1549556828,
          D ^ 1549556828,
          P ^ 1549556828
        )
        m = r
        g = i
        y = o
        v = s
        b = a
        E()
        w(
          t ^ 909522486,
          e ^ 909522486,
          n ^ 909522486,
          _ ^ 909522486,
          S ^ 909522486,
          C ^ 909522486,
          M ^ 909522486,
          k ^ 909522486,
          x ^ 909522486,
          A ^ 909522486,
          T ^ 909522486,
          I ^ 909522486,
          R ^ 909522486,
          N ^ 909522486,
          D ^ 909522486,
          P ^ 909522486
        )
        l = r
        h = i
        f = o
        d = s
        p = a
        u = 64
        c = 0
      }
      function R(t, e, n) {
        t = t | 0
        e = e | 0
        n = n | 0
        var u = 0,
          c = 0,
          l = 0,
          h = 0,
          f = 0,
          d = 0
        if (t & 63) return -1
        if (~n) if (n & 31) return -1
        d = x(t, e, -1) | 0
        ;(u = r), (c = i), (l = o), (h = s), (f = a)
        T()
        w(u, c, l, h, f, 2147483648, 0, 0, 0, 0, 0, 0, 0, 0, 0, 672)
        if (~n) C(n)
        return d | 0
      }
      function N(t, e, n, u, c) {
        t = t | 0
        e = e | 0
        n = n | 0
        u = u | 0
        c = c | 0
        var l = 0,
          h = 0,
          f = 0,
          d = 0,
          p = 0,
          m = 0,
          g = 0,
          y = 0,
          v = 0,
          b = 0
        if (t & 63) return -1
        if (~c) if (c & 31) return -1
        _[(t + e) | 0] = n >>> 24
        _[(t + e + 1) | 0] = (n >>> 16) & 255
        _[(t + e + 2) | 0] = (n >>> 8) & 255
        _[(t + e + 3) | 0] = n & 255
        R(t, (e + 4) | 0, -1) | 0
        ;(l = m = r), (h = g = i), (f = y = o), (d = v = s), (p = b = a)
        u = (u - 1) | 0
        while ((u | 0) > 0) {
          A()
          w(m, g, y, v, b, 2147483648, 0, 0, 0, 0, 0, 0, 0, 0, 0, 672)
          ;(m = r), (g = i), (y = o), (v = s), (b = a)
          T()
          w(m, g, y, v, b, 2147483648, 0, 0, 0, 0, 0, 0, 0, 0, 0, 672)
          ;(m = r), (g = i), (y = o), (v = s), (b = a)
          l = l ^ r
          h = h ^ i
          f = f ^ o
          d = d ^ s
          p = p ^ a
          u = (u - 1) | 0
        }
        r = l
        i = h
        o = f
        s = d
        a = p
        if (~c) C(c)
        return 0
      }
      return {
        reset: E,
        init: M,
        process: k,
        finish: x,
        hmac_reset: A,
        hmac_init: I,
        hmac_finish: R,
        pbkdf2_generate_block: N,
      }
    }
    function tt(t) {
      ;(t = t || {}),
        (this.heap = y(Uint8Array, t)),
        (this.asm = t.asm || Q(e, null, this.heap.buffer)),
        (this.BLOCK_SIZE = an),
        (this.HASH_SIZE = un),
        this.reset()
    }
    function et() {
      return (
        null === ln &&
          (ln = new tt({
            heapSize: 1048576,
          })),
        ln
      )
    }
    function nt(t) {
      if (void 0 === t) throw new SyntaxError('data required')
      return et().reset().process(t).finish().result
    }
    function rt(t) {
      return c(nt(t))
    }
    function it(t) {
      return l(nt(t))
    }
    function ot(t, e, n) {
      'use asm'
      var r = 0,
        i = 0,
        o = 0,
        s = 0,
        a = 0,
        u = 0,
        c = 0,
        l = 0,
        h = 0,
        f = 0
      var d = 0,
        p = 0,
        m = 0,
        g = 0,
        y = 0,
        v = 0,
        b = 0,
        _ = 0,
        w = 0,
        S = 0,
        C = 0,
        E = 0,
        M = 0,
        k = 0,
        x = 0,
        A = 0
      var T = new t.Uint8Array(n)
      function I(t, e, n, h, f, d, p, m, g, y, v, b, _, w, S, C) {
        t = t | 0
        e = e | 0
        n = n | 0
        h = h | 0
        f = f | 0
        d = d | 0
        p = p | 0
        m = m | 0
        g = g | 0
        y = y | 0
        v = v | 0
        b = b | 0
        _ = _ | 0
        w = w | 0
        S = S | 0
        C = C | 0
        var E = 0,
          M = 0,
          k = 0,
          x = 0,
          A = 0,
          T = 0,
          I = 0,
          R = 0,
          N = 0
        E = r
        M = i
        k = o
        x = s
        A = a
        T = u
        I = c
        R = l
        N =
          (t +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            1116352408) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        N =
          (e +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            1899447441) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        N =
          (n +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            3049323471) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        N =
          (h +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            3921009573) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        N =
          (f +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            961987163) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        N =
          (d +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            1508970993) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        N =
          (p +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            2453635748) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        N =
          (m +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            2870763221) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        N =
          (g +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            3624381080) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        N =
          (y +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            310598401) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        N =
          (v +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            607225278) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        N =
          (b +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            1426881987) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        N =
          (_ +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            1925078388) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        N =
          (w +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            2162078206) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        N =
          (S +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            2614888103) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        N =
          (C +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            3248222580) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        t = N =
          (((e >>> 7) ^ (e >>> 18) ^ (e >>> 3) ^ (e << 25) ^ (e << 14)) +
            ((S >>> 17) ^ (S >>> 19) ^ (S >>> 10) ^ (S << 15) ^ (S << 13)) +
            t +
            y) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            3835390401) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        e = N =
          (((n >>> 7) ^ (n >>> 18) ^ (n >>> 3) ^ (n << 25) ^ (n << 14)) +
            ((C >>> 17) ^ (C >>> 19) ^ (C >>> 10) ^ (C << 15) ^ (C << 13)) +
            e +
            v) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            4022224774) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        n = N =
          (((h >>> 7) ^ (h >>> 18) ^ (h >>> 3) ^ (h << 25) ^ (h << 14)) +
            ((t >>> 17) ^ (t >>> 19) ^ (t >>> 10) ^ (t << 15) ^ (t << 13)) +
            n +
            b) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            264347078) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        h = N =
          (((f >>> 7) ^ (f >>> 18) ^ (f >>> 3) ^ (f << 25) ^ (f << 14)) +
            ((e >>> 17) ^ (e >>> 19) ^ (e >>> 10) ^ (e << 15) ^ (e << 13)) +
            h +
            _) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            604807628) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        f = N =
          (((d >>> 7) ^ (d >>> 18) ^ (d >>> 3) ^ (d << 25) ^ (d << 14)) +
            ((n >>> 17) ^ (n >>> 19) ^ (n >>> 10) ^ (n << 15) ^ (n << 13)) +
            f +
            w) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            770255983) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        d = N =
          (((p >>> 7) ^ (p >>> 18) ^ (p >>> 3) ^ (p << 25) ^ (p << 14)) +
            ((h >>> 17) ^ (h >>> 19) ^ (h >>> 10) ^ (h << 15) ^ (h << 13)) +
            d +
            S) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            1249150122) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        p = N =
          (((m >>> 7) ^ (m >>> 18) ^ (m >>> 3) ^ (m << 25) ^ (m << 14)) +
            ((f >>> 17) ^ (f >>> 19) ^ (f >>> 10) ^ (f << 15) ^ (f << 13)) +
            p +
            C) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            1555081692) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        m = N =
          (((g >>> 7) ^ (g >>> 18) ^ (g >>> 3) ^ (g << 25) ^ (g << 14)) +
            ((d >>> 17) ^ (d >>> 19) ^ (d >>> 10) ^ (d << 15) ^ (d << 13)) +
            m +
            t) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            1996064986) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        g = N =
          (((y >>> 7) ^ (y >>> 18) ^ (y >>> 3) ^ (y << 25) ^ (y << 14)) +
            ((p >>> 17) ^ (p >>> 19) ^ (p >>> 10) ^ (p << 15) ^ (p << 13)) +
            g +
            e) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            2554220882) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        y = N =
          (((v >>> 7) ^ (v >>> 18) ^ (v >>> 3) ^ (v << 25) ^ (v << 14)) +
            ((m >>> 17) ^ (m >>> 19) ^ (m >>> 10) ^ (m << 15) ^ (m << 13)) +
            y +
            n) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            2821834349) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        v = N =
          (((b >>> 7) ^ (b >>> 18) ^ (b >>> 3) ^ (b << 25) ^ (b << 14)) +
            ((g >>> 17) ^ (g >>> 19) ^ (g >>> 10) ^ (g << 15) ^ (g << 13)) +
            v +
            h) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            2952996808) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        b = N =
          (((_ >>> 7) ^ (_ >>> 18) ^ (_ >>> 3) ^ (_ << 25) ^ (_ << 14)) +
            ((y >>> 17) ^ (y >>> 19) ^ (y >>> 10) ^ (y << 15) ^ (y << 13)) +
            b +
            f) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            3210313671) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        _ = N =
          (((w >>> 7) ^ (w >>> 18) ^ (w >>> 3) ^ (w << 25) ^ (w << 14)) +
            ((v >>> 17) ^ (v >>> 19) ^ (v >>> 10) ^ (v << 15) ^ (v << 13)) +
            _ +
            d) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            3336571891) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        w = N =
          (((S >>> 7) ^ (S >>> 18) ^ (S >>> 3) ^ (S << 25) ^ (S << 14)) +
            ((b >>> 17) ^ (b >>> 19) ^ (b >>> 10) ^ (b << 15) ^ (b << 13)) +
            w +
            p) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            3584528711) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        S = N =
          (((C >>> 7) ^ (C >>> 18) ^ (C >>> 3) ^ (C << 25) ^ (C << 14)) +
            ((_ >>> 17) ^ (_ >>> 19) ^ (_ >>> 10) ^ (_ << 15) ^ (_ << 13)) +
            S +
            m) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            113926993) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        C = N =
          (((t >>> 7) ^ (t >>> 18) ^ (t >>> 3) ^ (t << 25) ^ (t << 14)) +
            ((w >>> 17) ^ (w >>> 19) ^ (w >>> 10) ^ (w << 15) ^ (w << 13)) +
            C +
            g) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            338241895) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        t = N =
          (((e >>> 7) ^ (e >>> 18) ^ (e >>> 3) ^ (e << 25) ^ (e << 14)) +
            ((S >>> 17) ^ (S >>> 19) ^ (S >>> 10) ^ (S << 15) ^ (S << 13)) +
            t +
            y) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            666307205) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        e = N =
          (((n >>> 7) ^ (n >>> 18) ^ (n >>> 3) ^ (n << 25) ^ (n << 14)) +
            ((C >>> 17) ^ (C >>> 19) ^ (C >>> 10) ^ (C << 15) ^ (C << 13)) +
            e +
            v) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            773529912) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        n = N =
          (((h >>> 7) ^ (h >>> 18) ^ (h >>> 3) ^ (h << 25) ^ (h << 14)) +
            ((t >>> 17) ^ (t >>> 19) ^ (t >>> 10) ^ (t << 15) ^ (t << 13)) +
            n +
            b) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            1294757372) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        h = N =
          (((f >>> 7) ^ (f >>> 18) ^ (f >>> 3) ^ (f << 25) ^ (f << 14)) +
            ((e >>> 17) ^ (e >>> 19) ^ (e >>> 10) ^ (e << 15) ^ (e << 13)) +
            h +
            _) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            1396182291) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        f = N =
          (((d >>> 7) ^ (d >>> 18) ^ (d >>> 3) ^ (d << 25) ^ (d << 14)) +
            ((n >>> 17) ^ (n >>> 19) ^ (n >>> 10) ^ (n << 15) ^ (n << 13)) +
            f +
            w) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            1695183700) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        d = N =
          (((p >>> 7) ^ (p >>> 18) ^ (p >>> 3) ^ (p << 25) ^ (p << 14)) +
            ((h >>> 17) ^ (h >>> 19) ^ (h >>> 10) ^ (h << 15) ^ (h << 13)) +
            d +
            S) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            1986661051) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        p = N =
          (((m >>> 7) ^ (m >>> 18) ^ (m >>> 3) ^ (m << 25) ^ (m << 14)) +
            ((f >>> 17) ^ (f >>> 19) ^ (f >>> 10) ^ (f << 15) ^ (f << 13)) +
            p +
            C) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            2177026350) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        m = N =
          (((g >>> 7) ^ (g >>> 18) ^ (g >>> 3) ^ (g << 25) ^ (g << 14)) +
            ((d >>> 17) ^ (d >>> 19) ^ (d >>> 10) ^ (d << 15) ^ (d << 13)) +
            m +
            t) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            2456956037) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        g = N =
          (((y >>> 7) ^ (y >>> 18) ^ (y >>> 3) ^ (y << 25) ^ (y << 14)) +
            ((p >>> 17) ^ (p >>> 19) ^ (p >>> 10) ^ (p << 15) ^ (p << 13)) +
            g +
            e) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            2730485921) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        y = N =
          (((v >>> 7) ^ (v >>> 18) ^ (v >>> 3) ^ (v << 25) ^ (v << 14)) +
            ((m >>> 17) ^ (m >>> 19) ^ (m >>> 10) ^ (m << 15) ^ (m << 13)) +
            y +
            n) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            2820302411) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        v = N =
          (((b >>> 7) ^ (b >>> 18) ^ (b >>> 3) ^ (b << 25) ^ (b << 14)) +
            ((g >>> 17) ^ (g >>> 19) ^ (g >>> 10) ^ (g << 15) ^ (g << 13)) +
            v +
            h) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            3259730800) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        b = N =
          (((_ >>> 7) ^ (_ >>> 18) ^ (_ >>> 3) ^ (_ << 25) ^ (_ << 14)) +
            ((y >>> 17) ^ (y >>> 19) ^ (y >>> 10) ^ (y << 15) ^ (y << 13)) +
            b +
            f) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            3345764771) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        _ = N =
          (((w >>> 7) ^ (w >>> 18) ^ (w >>> 3) ^ (w << 25) ^ (w << 14)) +
            ((v >>> 17) ^ (v >>> 19) ^ (v >>> 10) ^ (v << 15) ^ (v << 13)) +
            _ +
            d) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            3516065817) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        w = N =
          (((S >>> 7) ^ (S >>> 18) ^ (S >>> 3) ^ (S << 25) ^ (S << 14)) +
            ((b >>> 17) ^ (b >>> 19) ^ (b >>> 10) ^ (b << 15) ^ (b << 13)) +
            w +
            p) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            3600352804) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        S = N =
          (((C >>> 7) ^ (C >>> 18) ^ (C >>> 3) ^ (C << 25) ^ (C << 14)) +
            ((_ >>> 17) ^ (_ >>> 19) ^ (_ >>> 10) ^ (_ << 15) ^ (_ << 13)) +
            S +
            m) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            4094571909) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        C = N =
          (((t >>> 7) ^ (t >>> 18) ^ (t >>> 3) ^ (t << 25) ^ (t << 14)) +
            ((w >>> 17) ^ (w >>> 19) ^ (w >>> 10) ^ (w << 15) ^ (w << 13)) +
            C +
            g) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            275423344) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        t = N =
          (((e >>> 7) ^ (e >>> 18) ^ (e >>> 3) ^ (e << 25) ^ (e << 14)) +
            ((S >>> 17) ^ (S >>> 19) ^ (S >>> 10) ^ (S << 15) ^ (S << 13)) +
            t +
            y) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            430227734) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        e = N =
          (((n >>> 7) ^ (n >>> 18) ^ (n >>> 3) ^ (n << 25) ^ (n << 14)) +
            ((C >>> 17) ^ (C >>> 19) ^ (C >>> 10) ^ (C << 15) ^ (C << 13)) +
            e +
            v) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            506948616) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        n = N =
          (((h >>> 7) ^ (h >>> 18) ^ (h >>> 3) ^ (h << 25) ^ (h << 14)) +
            ((t >>> 17) ^ (t >>> 19) ^ (t >>> 10) ^ (t << 15) ^ (t << 13)) +
            n +
            b) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            659060556) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        h = N =
          (((f >>> 7) ^ (f >>> 18) ^ (f >>> 3) ^ (f << 25) ^ (f << 14)) +
            ((e >>> 17) ^ (e >>> 19) ^ (e >>> 10) ^ (e << 15) ^ (e << 13)) +
            h +
            _) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            883997877) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        f = N =
          (((d >>> 7) ^ (d >>> 18) ^ (d >>> 3) ^ (d << 25) ^ (d << 14)) +
            ((n >>> 17) ^ (n >>> 19) ^ (n >>> 10) ^ (n << 15) ^ (n << 13)) +
            f +
            w) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            958139571) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        d = N =
          (((p >>> 7) ^ (p >>> 18) ^ (p >>> 3) ^ (p << 25) ^ (p << 14)) +
            ((h >>> 17) ^ (h >>> 19) ^ (h >>> 10) ^ (h << 15) ^ (h << 13)) +
            d +
            S) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            1322822218) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        p = N =
          (((m >>> 7) ^ (m >>> 18) ^ (m >>> 3) ^ (m << 25) ^ (m << 14)) +
            ((f >>> 17) ^ (f >>> 19) ^ (f >>> 10) ^ (f << 15) ^ (f << 13)) +
            p +
            C) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            1537002063) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        m = N =
          (((g >>> 7) ^ (g >>> 18) ^ (g >>> 3) ^ (g << 25) ^ (g << 14)) +
            ((d >>> 17) ^ (d >>> 19) ^ (d >>> 10) ^ (d << 15) ^ (d << 13)) +
            m +
            t) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            1747873779) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        g = N =
          (((y >>> 7) ^ (y >>> 18) ^ (y >>> 3) ^ (y << 25) ^ (y << 14)) +
            ((p >>> 17) ^ (p >>> 19) ^ (p >>> 10) ^ (p << 15) ^ (p << 13)) +
            g +
            e) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            1955562222) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        y = N =
          (((v >>> 7) ^ (v >>> 18) ^ (v >>> 3) ^ (v << 25) ^ (v << 14)) +
            ((m >>> 17) ^ (m >>> 19) ^ (m >>> 10) ^ (m << 15) ^ (m << 13)) +
            y +
            n) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            2024104815) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        v = N =
          (((b >>> 7) ^ (b >>> 18) ^ (b >>> 3) ^ (b << 25) ^ (b << 14)) +
            ((g >>> 17) ^ (g >>> 19) ^ (g >>> 10) ^ (g << 15) ^ (g << 13)) +
            v +
            h) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            2227730452) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        b = N =
          (((_ >>> 7) ^ (_ >>> 18) ^ (_ >>> 3) ^ (_ << 25) ^ (_ << 14)) +
            ((y >>> 17) ^ (y >>> 19) ^ (y >>> 10) ^ (y << 15) ^ (y << 13)) +
            b +
            f) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            2361852424) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        _ = N =
          (((w >>> 7) ^ (w >>> 18) ^ (w >>> 3) ^ (w << 25) ^ (w << 14)) +
            ((v >>> 17) ^ (v >>> 19) ^ (v >>> 10) ^ (v << 15) ^ (v << 13)) +
            _ +
            d) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            2428436474) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        w = N =
          (((S >>> 7) ^ (S >>> 18) ^ (S >>> 3) ^ (S << 25) ^ (S << 14)) +
            ((b >>> 17) ^ (b >>> 19) ^ (b >>> 10) ^ (b << 15) ^ (b << 13)) +
            w +
            p) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            2756734187) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        S = N =
          (((C >>> 7) ^ (C >>> 18) ^ (C >>> 3) ^ (C << 25) ^ (C << 14)) +
            ((_ >>> 17) ^ (_ >>> 19) ^ (_ >>> 10) ^ (_ << 15) ^ (_ << 13)) +
            S +
            m) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            3204031479) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        C = N =
          (((t >>> 7) ^ (t >>> 18) ^ (t >>> 3) ^ (t << 25) ^ (t << 14)) +
            ((w >>> 17) ^ (w >>> 19) ^ (w >>> 10) ^ (w << 15) ^ (w << 13)) +
            C +
            g) |
          0
        N =
          (N +
            R +
            ((A >>> 6) ^
              (A >>> 11) ^
              (A >>> 25) ^
              (A << 26) ^
              (A << 21) ^
              (A << 7)) +
            (I ^ (A & (T ^ I))) +
            3329325298) |
          0
        R = I
        I = T
        T = A
        A = (x + N) | 0
        x = k
        k = M
        M = E
        E =
          (N +
            ((M & k) ^ (x & (M ^ k))) +
            ((M >>> 2) ^
              (M >>> 13) ^
              (M >>> 22) ^
              (M << 30) ^
              (M << 19) ^
              (M << 10))) |
          0
        r = (r + E) | 0
        i = (i + M) | 0
        o = (o + k) | 0
        s = (s + x) | 0
        a = (a + A) | 0
        u = (u + T) | 0
        c = (c + I) | 0
        l = (l + R) | 0
      }
      function R(t) {
        t = t | 0
        I(
          (T[t | 0] << 24) | (T[t | 1] << 16) | (T[t | 2] << 8) | T[t | 3],
          (T[t | 4] << 24) | (T[t | 5] << 16) | (T[t | 6] << 8) | T[t | 7],
          (T[t | 8] << 24) | (T[t | 9] << 16) | (T[t | 10] << 8) | T[t | 11],
          (T[t | 12] << 24) | (T[t | 13] << 16) | (T[t | 14] << 8) | T[t | 15],
          (T[t | 16] << 24) | (T[t | 17] << 16) | (T[t | 18] << 8) | T[t | 19],
          (T[t | 20] << 24) | (T[t | 21] << 16) | (T[t | 22] << 8) | T[t | 23],
          (T[t | 24] << 24) | (T[t | 25] << 16) | (T[t | 26] << 8) | T[t | 27],
          (T[t | 28] << 24) | (T[t | 29] << 16) | (T[t | 30] << 8) | T[t | 31],
          (T[t | 32] << 24) | (T[t | 33] << 16) | (T[t | 34] << 8) | T[t | 35],
          (T[t | 36] << 24) | (T[t | 37] << 16) | (T[t | 38] << 8) | T[t | 39],
          (T[t | 40] << 24) | (T[t | 41] << 16) | (T[t | 42] << 8) | T[t | 43],
          (T[t | 44] << 24) | (T[t | 45] << 16) | (T[t | 46] << 8) | T[t | 47],
          (T[t | 48] << 24) | (T[t | 49] << 16) | (T[t | 50] << 8) | T[t | 51],
          (T[t | 52] << 24) | (T[t | 53] << 16) | (T[t | 54] << 8) | T[t | 55],
          (T[t | 56] << 24) | (T[t | 57] << 16) | (T[t | 58] << 8) | T[t | 59],
          (T[t | 60] << 24) | (T[t | 61] << 16) | (T[t | 62] << 8) | T[t | 63]
        )
      }
      function N(t) {
        t = t | 0
        T[t | 0] = r >>> 24
        T[t | 1] = (r >>> 16) & 255
        T[t | 2] = (r >>> 8) & 255
        T[t | 3] = r & 255
        T[t | 4] = i >>> 24
        T[t | 5] = (i >>> 16) & 255
        T[t | 6] = (i >>> 8) & 255
        T[t | 7] = i & 255
        T[t | 8] = o >>> 24
        T[t | 9] = (o >>> 16) & 255
        T[t | 10] = (o >>> 8) & 255
        T[t | 11] = o & 255
        T[t | 12] = s >>> 24
        T[t | 13] = (s >>> 16) & 255
        T[t | 14] = (s >>> 8) & 255
        T[t | 15] = s & 255
        T[t | 16] = a >>> 24
        T[t | 17] = (a >>> 16) & 255
        T[t | 18] = (a >>> 8) & 255
        T[t | 19] = a & 255
        T[t | 20] = u >>> 24
        T[t | 21] = (u >>> 16) & 255
        T[t | 22] = (u >>> 8) & 255
        T[t | 23] = u & 255
        T[t | 24] = c >>> 24
        T[t | 25] = (c >>> 16) & 255
        T[t | 26] = (c >>> 8) & 255
        T[t | 27] = c & 255
        T[t | 28] = l >>> 24
        T[t | 29] = (l >>> 16) & 255
        T[t | 30] = (l >>> 8) & 255
        T[t | 31] = l & 255
      }
      function D() {
        r = 1779033703
        i = 3144134277
        o = 1013904242
        s = 2773480762
        a = 1359893119
        u = 2600822924
        c = 528734635
        l = 1541459225
        h = f = 0
      }
      function P(t, e, n, d, p, m, g, y, v, b) {
        t = t | 0
        e = e | 0
        n = n | 0
        d = d | 0
        p = p | 0
        m = m | 0
        g = g | 0
        y = y | 0
        v = v | 0
        b = b | 0
        r = t
        i = e
        o = n
        s = d
        a = p
        u = m
        c = g
        l = y
        h = v
        f = b
      }
      function B(t, e) {
        t = t | 0
        e = e | 0
        var n = 0
        if (t & 63) return -1
        while ((e | 0) >= 64) {
          R(t)
          t = (t + 64) | 0
          e = (e - 64) | 0
          n = (n + 64) | 0
        }
        h = (h + n) | 0
        if (h >>> 0 < n >>> 0) f = (f + 1) | 0
        return n | 0
      }
      function L(t, e, n) {
        t = t | 0
        e = e | 0
        n = n | 0
        var r = 0,
          i = 0
        if (t & 63) return -1
        if (~n) if (n & 31) return -1
        if ((e | 0) >= 64) {
          r = B(t, e) | 0
          if ((r | 0) == -1) return -1
          t = (t + r) | 0
          e = (e - r) | 0
        }
        r = (r + e) | 0
        h = (h + e) | 0
        if (h >>> 0 < e >>> 0) f = (f + 1) | 0
        T[t | e] = 128
        if ((e | 0) >= 56) {
          for (i = (e + 1) | 0; (i | 0) < 64; i = (i + 1) | 0) T[t | i] = 0
          R(t)
          e = 0
          T[t | 0] = 0
        }
        for (i = (e + 1) | 0; (i | 0) < 59; i = (i + 1) | 0) T[t | i] = 0
        T[t | 56] = (f >>> 21) & 255
        T[t | 57] = (f >>> 13) & 255
        T[t | 58] = (f >>> 5) & 255
        T[t | 59] = ((f << 3) & 255) | (h >>> 29)
        T[t | 60] = (h >>> 21) & 255
        T[t | 61] = (h >>> 13) & 255
        T[t | 62] = (h >>> 5) & 255
        T[t | 63] = (h << 3) & 255
        R(t)
        if (~n) N(n)
        return r | 0
      }
      function O() {
        r = d
        i = p
        o = m
        s = g
        a = y
        u = v
        c = b
        l = _
        h = 64
        f = 0
      }
      function q() {
        r = w
        i = S
        o = C
        s = E
        a = M
        u = k
        c = x
        l = A
        h = 64
        f = 0
      }
      function U(t, e, n, T, R, N, P, B, L, O, q, U, j, F, H, z) {
        t = t | 0
        e = e | 0
        n = n | 0
        T = T | 0
        R = R | 0
        N = N | 0
        P = P | 0
        B = B | 0
        L = L | 0
        O = O | 0
        q = q | 0
        U = U | 0
        j = j | 0
        F = F | 0
        H = H | 0
        z = z | 0
        D()
        I(
          t ^ 1549556828,
          e ^ 1549556828,
          n ^ 1549556828,
          T ^ 1549556828,
          R ^ 1549556828,
          N ^ 1549556828,
          P ^ 1549556828,
          B ^ 1549556828,
          L ^ 1549556828,
          O ^ 1549556828,
          q ^ 1549556828,
          U ^ 1549556828,
          j ^ 1549556828,
          F ^ 1549556828,
          H ^ 1549556828,
          z ^ 1549556828
        )
        w = r
        S = i
        C = o
        E = s
        M = a
        k = u
        x = c
        A = l
        D()
        I(
          t ^ 909522486,
          e ^ 909522486,
          n ^ 909522486,
          T ^ 909522486,
          R ^ 909522486,
          N ^ 909522486,
          P ^ 909522486,
          B ^ 909522486,
          L ^ 909522486,
          O ^ 909522486,
          q ^ 909522486,
          U ^ 909522486,
          j ^ 909522486,
          F ^ 909522486,
          H ^ 909522486,
          z ^ 909522486
        )
        d = r
        p = i
        m = o
        g = s
        y = a
        v = u
        b = c
        _ = l
        h = 64
        f = 0
      }
      function j(t, e, n) {
        t = t | 0
        e = e | 0
        n = n | 0
        var h = 0,
          f = 0,
          d = 0,
          p = 0,
          m = 0,
          g = 0,
          y = 0,
          v = 0,
          b = 0
        if (t & 63) return -1
        if (~n) if (n & 31) return -1
        b = L(t, e, -1) | 0
        ;(h = r), (f = i), (d = o), (p = s), (m = a), (g = u), (y = c), (v = l)
        q()
        I(h, f, d, p, m, g, y, v, 2147483648, 0, 0, 0, 0, 0, 0, 768)
        if (~n) N(n)
        return b | 0
      }
      function F(t, e, n, h, f) {
        t = t | 0
        e = e | 0
        n = n | 0
        h = h | 0
        f = f | 0
        var d = 0,
          p = 0,
          m = 0,
          g = 0,
          y = 0,
          v = 0,
          b = 0,
          _ = 0,
          w = 0,
          S = 0,
          C = 0,
          E = 0,
          M = 0,
          k = 0,
          x = 0,
          A = 0
        if (t & 63) return -1
        if (~f) if (f & 31) return -1
        T[(t + e) | 0] = n >>> 24
        T[(t + e + 1) | 0] = (n >>> 16) & 255
        T[(t + e + 2) | 0] = (n >>> 8) & 255
        T[(t + e + 3) | 0] = n & 255
        j(t, (e + 4) | 0, -1) | 0
        ;(d = w = r),
          (p = S = i),
          (m = C = o),
          (g = E = s),
          (y = M = a),
          (v = k = u),
          (b = x = c),
          (_ = A = l)
        h = (h - 1) | 0
        while ((h | 0) > 0) {
          O()
          I(w, S, C, E, M, k, x, A, 2147483648, 0, 0, 0, 0, 0, 0, 768)
          ;(w = r),
            (S = i),
            (C = o),
            (E = s),
            (M = a),
            (k = u),
            (x = c),
            (A = l)
          q()
          I(w, S, C, E, M, k, x, A, 2147483648, 0, 0, 0, 0, 0, 0, 768)
          ;(w = r),
            (S = i),
            (C = o),
            (E = s),
            (M = a),
            (k = u),
            (x = c),
            (A = l)
          d = d ^ r
          p = p ^ i
          m = m ^ o
          g = g ^ s
          y = y ^ a
          v = v ^ u
          b = b ^ c
          _ = _ ^ l
          h = (h - 1) | 0
        }
        r = d
        i = p
        o = m
        s = g
        a = y
        u = v
        c = b
        l = _
        if (~f) N(f)
        return 0
      }
      return {
        reset: D,
        init: P,
        process: B,
        finish: L,
        hmac_reset: O,
        hmac_init: U,
        hmac_finish: j,
        pbkdf2_generate_block: F,
      }
    }
    function st(t) {
      ;(t = t || {}),
        (this.heap = y(Uint8Array, t)),
        (this.asm = t.asm || ot(e, null, this.heap.buffer)),
        (this.BLOCK_SIZE = hn),
        (this.HASH_SIZE = fn),
        this.reset()
    }
    function at() {
      return (
        null === pn &&
          (pn = new st({
            heapSize: 1048576,
          })),
        pn
      )
    }
    function ut(t) {
      if (void 0 === t) throw new SyntaxError('data required')
      return at().reset().process(t).finish().result
    }
    function ct(t) {
      return c(ut(t))
    }
    function lt(t) {
      return l(ut(t))
    }
    function ht(t) {
      if (!(t = t || {}).hash)
        throw new SyntaxError("option 'hash' is required")
      if (!t.hash.HASH_SIZE)
        throw new SyntaxError(
          "option 'hash' supplied doesn't seem to be a valid hash function"
        )
      return (
        (this.hash = t.hash),
        (this.BLOCK_SIZE = this.hash.BLOCK_SIZE),
        (this.HMAC_SIZE = this.hash.HASH_SIZE),
        (this.key = null),
        (this.verify = null),
        (this.result = null),
        (void 0 !== t.password || void 0 !== t.verify) && this.reset(t),
        this
      )
    }
    function ft(t, e) {
      if ((p(e) && (e = new Uint8Array(e)), d(e) && (e = o(e)), !m(e)))
        throw new TypeError("password isn't of expected type")
      var n = new Uint8Array(t.BLOCK_SIZE)
      return (
        e.length > t.BLOCK_SIZE
          ? n.set(t.reset().process(e).finish().result)
          : n.set(e),
        n
      )
    }
    function dt(t) {
      if (p(t) || m(t)) t = new Uint8Array(t)
      else {
        if (!d(t)) throw new TypeError("verify tag isn't of expected type")
        t = o(t)
      }
      if (t.length !== this.HMAC_SIZE)
        throw new r('illegal verification tag size')
      this.verify = t
    }
    function pt(t) {
      var e = (t = t || {}).password
      if (null === this.key && !d(e) && !e)
        throw new n('no key is associated with the instance')
      ;(this.result = null),
        this.hash.reset(),
        (e || d(e)) && (this.key = ft(this.hash, e))
      for (var r = new Uint8Array(this.key), i = 0; i < r.length; ++i)
        r[i] ^= 54
      this.hash.process(r)
      var o = t.verify
      return void 0 !== o ? dt.call(this, o) : (this.verify = null), this
    }
    function mt(t) {
      if (null === this.key)
        throw new n('no key is associated with the instance')
      if (null !== this.result)
        throw new n('state must be reset before processing new data')
      return this.hash.process(t), this
    }
    function gt() {
      if (null === this.key)
        throw new n('no key is associated with the instance')
      if (null !== this.result)
        throw new n('state must be reset before processing new data')
      for (
        var t = this.hash.finish().result, e = new Uint8Array(this.key), r = 0;
        r < e.length;
        ++r
      )
        e[r] ^= 92
      var i = this.verify,
        o = this.hash.reset().process(e).process(t).finish().result
      if (i)
        if (i.length === o.length) {
          var s = 0
          for (r = 0; r < i.length; r++) s |= i[r] ^ o[r]
          this.result = !s
        } else this.result = !1
      else this.result = o
      return this
    }
    function yt(t) {
      return (
        (t = t || {}).hash instanceof tt || (t.hash = et()),
        ht.call(this, t),
        this
      )
    }
    function vt(t) {
      ;(t = t || {}), (this.result = null), this.hash.reset()
      var e = t.password
      if (void 0 !== e) {
        d(e) && (e = o(e))
        var n = (this.key = ft(this.hash, e))
        this.hash
          .reset()
          .asm.hmac_init(
            (n[0] << 24) | (n[1] << 16) | (n[2] << 8) | n[3],
            (n[4] << 24) | (n[5] << 16) | (n[6] << 8) | n[7],
            (n[8] << 24) | (n[9] << 16) | (n[10] << 8) | n[11],
            (n[12] << 24) | (n[13] << 16) | (n[14] << 8) | n[15],
            (n[16] << 24) | (n[17] << 16) | (n[18] << 8) | n[19],
            (n[20] << 24) | (n[21] << 16) | (n[22] << 8) | n[23],
            (n[24] << 24) | (n[25] << 16) | (n[26] << 8) | n[27],
            (n[28] << 24) | (n[29] << 16) | (n[30] << 8) | n[31],
            (n[32] << 24) | (n[33] << 16) | (n[34] << 8) | n[35],
            (n[36] << 24) | (n[37] << 16) | (n[38] << 8) | n[39],
            (n[40] << 24) | (n[41] << 16) | (n[42] << 8) | n[43],
            (n[44] << 24) | (n[45] << 16) | (n[46] << 8) | n[47],
            (n[48] << 24) | (n[49] << 16) | (n[50] << 8) | n[51],
            (n[52] << 24) | (n[53] << 16) | (n[54] << 8) | n[55],
            (n[56] << 24) | (n[57] << 16) | (n[58] << 8) | n[59],
            (n[60] << 24) | (n[61] << 16) | (n[62] << 8) | n[63]
          )
      } else this.hash.asm.hmac_reset()
      var r = t.verify
      return void 0 !== r ? dt.call(this, r) : (this.verify = null), this
    }
    function bt() {
      if (null === this.key)
        throw new n('no key is associated with the instance')
      if (null !== this.result)
        throw new n('state must be reset before processing new data')
      var t = this.hash,
        e = this.hash.asm,
        r = this.hash.heap
      e.hmac_finish(t.pos, t.len, 0)
      var i = this.verify,
        o = new Uint8Array(un)
      if ((o.set(r.subarray(0, un)), i))
        if (i.length === o.length) {
          for (var s = 0, a = 0; a < i.length; a++) s |= i[a] ^ o[a]
          this.result = !s
        } else this.result = !1
      else this.result = o
      return this
    }
    function _t() {
      return null === yn && (yn = new yt()), yn
    }
    function wt(t) {
      return (
        (t = t || {}).hash instanceof st || (t.hash = at()),
        ht.call(this, t),
        this
      )
    }
    function St(t) {
      ;(t = t || {}), (this.result = null), this.hash.reset()
      var e = t.password
      if (void 0 !== e) {
        d(e) && (e = o(e))
        var n = (this.key = ft(this.hash, e))
        this.hash
          .reset()
          .asm.hmac_init(
            (n[0] << 24) | (n[1] << 16) | (n[2] << 8) | n[3],
            (n[4] << 24) | (n[5] << 16) | (n[6] << 8) | n[7],
            (n[8] << 24) | (n[9] << 16) | (n[10] << 8) | n[11],
            (n[12] << 24) | (n[13] << 16) | (n[14] << 8) | n[15],
            (n[16] << 24) | (n[17] << 16) | (n[18] << 8) | n[19],
            (n[20] << 24) | (n[21] << 16) | (n[22] << 8) | n[23],
            (n[24] << 24) | (n[25] << 16) | (n[26] << 8) | n[27],
            (n[28] << 24) | (n[29] << 16) | (n[30] << 8) | n[31],
            (n[32] << 24) | (n[33] << 16) | (n[34] << 8) | n[35],
            (n[36] << 24) | (n[37] << 16) | (n[38] << 8) | n[39],
            (n[40] << 24) | (n[41] << 16) | (n[42] << 8) | n[43],
            (n[44] << 24) | (n[45] << 16) | (n[46] << 8) | n[47],
            (n[48] << 24) | (n[49] << 16) | (n[50] << 8) | n[51],
            (n[52] << 24) | (n[53] << 16) | (n[54] << 8) | n[55],
            (n[56] << 24) | (n[57] << 16) | (n[58] << 8) | n[59],
            (n[60] << 24) | (n[61] << 16) | (n[62] << 8) | n[63]
          )
      } else this.hash.asm.hmac_reset()
      var r = t.verify
      return void 0 !== r ? dt.call(this, r) : (this.verify = null), this
    }
    function Ct() {
      if (null === this.key)
        throw new n('no key is associated with the instance')
      if (null !== this.result)
        throw new n('state must be reset before processing new data')
      var t = this.hash,
        e = this.hash.asm,
        r = this.hash.heap
      e.hmac_finish(t.pos, t.len, 0)
      var i = this.verify,
        o = new Uint8Array(fn)
      if ((o.set(r.subarray(0, fn)), i))
        if (i.length === o.length) {
          for (var s = 0, a = 0; a < i.length; a++) s |= i[a] ^ o[a]
          this.result = !s
        } else this.result = !1
      else this.result = o
      return this
    }
    function Et() {
      return null === bn && (bn = new wt()), bn
    }
    function Mt(t, e) {
      if (void 0 === t) throw new SyntaxError('data required')
      if (void 0 === e) throw new SyntaxError('password required')
      return _t()
        .reset({
          password: e,
        })
        .process(t)
        .finish().result
    }
    function kt(t, e) {
      return c(Mt(t, e))
    }
    function xt(t, e) {
      return l(Mt(t, e))
    }
    function At(t, e) {
      if (void 0 === t) throw new SyntaxError('data required')
      if (void 0 === e) throw new SyntaxError('password required')
      return Et()
        .reset({
          password: e,
        })
        .process(t)
        .finish().result
    }
    function Tt(t, e) {
      return c(At(t, e))
    }
    function It(t, e) {
      return l(At(t, e))
    }
    function Rt(t) {
      if (!(t = t || {}).hmac)
        throw new SyntaxError("option 'hmac' is required")
      if (!t.hmac.HMAC_SIZE)
        throw new SyntaxError(
          "option 'hmac' supplied doesn't seem to be a valid HMAC function"
        )
      ;(this.hmac = t.hmac),
        (this.count = t.count || 4096),
        (this.length = t.length || this.hmac.HMAC_SIZE),
        (this.result = null)
      var e = t.password
      return (e || d(e)) && this.reset(t), this
    }
    function Nt(t) {
      return (this.result = null), this.hmac.reset(t), this
    }
    function Dt(t, e, i) {
      if (null !== this.result)
        throw new n('state must be reset before processing new data')
      if (!t && !d(t)) throw new r("bad 'salt' value")
      ;(e = e || this.count),
        (i = i || this.length),
        (this.result = new Uint8Array(i))
      for (var o = Math.ceil(i / this.hmac.HMAC_SIZE), s = 1; o >= s; ++s) {
        var a = (s - 1) * this.hmac.HMAC_SIZE,
          u = (o > s ? 0 : i % this.hmac.HMAC_SIZE) || this.hmac.HMAC_SIZE,
          c = new Uint8Array(
            this.hmac
              .reset()
              .process(t)
              .process(
                new Uint8Array([
                  (s >>> 24) & 255,
                  (s >>> 16) & 255,
                  (s >>> 8) & 255,
                  255 & s,
                ])
              )
              .finish().result
          )
        this.result.set(c.subarray(0, u), a)
        for (var l = 1; e > l; ++l) {
          c = new Uint8Array(this.hmac.reset().process(c).finish().result)
          for (var h = 0; u > h; ++h) this.result[a + h] ^= c[h]
        }
      }
      return this
    }
    function Pt(t) {
      return (
        (t = t || {}).hmac instanceof yt || (t.hmac = _t()),
        Rt.call(this, t),
        this
      )
    }
    function Bt(t, e, i) {
      if (null !== this.result)
        throw new n('state must be reset before processing new data')
      if (!t && !d(t)) throw new r("bad 'salt' value")
      ;(e = e || this.count),
        (i = i || this.length),
        (this.result = new Uint8Array(i))
      for (var o = Math.ceil(i / this.hmac.HMAC_SIZE), s = 1; o >= s; ++s) {
        var a = (s - 1) * this.hmac.HMAC_SIZE,
          u = (o > s ? 0 : i % this.hmac.HMAC_SIZE) || this.hmac.HMAC_SIZE
        this.hmac.reset().process(t),
          this.hmac.hash.asm.pbkdf2_generate_block(
            this.hmac.hash.pos,
            this.hmac.hash.len,
            s,
            e,
            0
          ),
          this.result.set(this.hmac.hash.heap.subarray(0, u), a)
      }
      return this
    }
    function Lt() {
      return null === Sn && (Sn = new Pt()), Sn
    }
    function Ot(t) {
      return (
        (t = t || {}).hmac instanceof wt || (t.hmac = Et()),
        Rt.call(this, t),
        this
      )
    }
    function qt(t, e, i) {
      if (null !== this.result)
        throw new n('state must be reset before processing new data')
      if (!t && !d(t)) throw new r("bad 'salt' value")
      ;(e = e || this.count),
        (i = i || this.length),
        (this.result = new Uint8Array(i))
      for (var o = Math.ceil(i / this.hmac.HMAC_SIZE), s = 1; o >= s; ++s) {
        var a = (s - 1) * this.hmac.HMAC_SIZE,
          u = (o > s ? 0 : i % this.hmac.HMAC_SIZE) || this.hmac.HMAC_SIZE
        this.hmac.reset().process(t),
          this.hmac.hash.asm.pbkdf2_generate_block(
            this.hmac.hash.pos,
            this.hmac.hash.len,
            s,
            e,
            0
          ),
          this.result.set(this.hmac.hash.heap.subarray(0, u), a)
      }
      return this
    }
    function Ut() {
      return null === En && (En = new Ot()), En
    }
    function jt(t, e, n, r) {
      if (void 0 === t) throw new SyntaxError('password required')
      if (void 0 === e) throw new SyntaxError('salt required')
      return Lt()
        .reset({
          password: t,
        })
        .generate(e, n, r).result
    }
    function Ft(t, e, n, r) {
      return c(jt(t, e, n, r))
    }
    function Ht(t, e, n, r) {
      return l(jt(t, e, n, r))
    }
    function zt(t, e, n, r) {
      if (void 0 === t) throw new SyntaxError('password required')
      if (void 0 === e) throw new SyntaxError('salt required')
      return Ut()
        .reset({
          password: t,
        })
        .generate(e, n, r).result
    }
    function Vt(t, e, n, r) {
      return c(zt(t, e, n, r))
    }
    function Kt(t, e, n, r) {
      return l(zt(t, e, n, r))
    }
    function $t() {
      if (void 0 !== In) (r = new Uint8Array(32)), Mn.call(In, r), Pn(r)
      else {
        var t,
          n,
          r = new $e(3)
        ;(r[0] = An()),
          (r[1] = xn()),
          (r[2] = Rn()),
          (r = new Uint8Array(r.buffer))
        var i = Ut()
        for (t = 0; 100 > t; t++)
          (r = i
            .reset({
              password: r,
            })
            .generate(e.location.href, 1e3, 32).result),
            (n = Rn()),
            (r[0] ^= n >>> 24),
            (r[1] ^= n >>> 16),
            (r[2] ^= n >>> 8),
            (r[3] ^= n)
        Pn(r)
      }
      ;(Bn = 0), (Ln = !0)
    }
    function Wt(t) {
      if (!p(t) && !g(t)) throw new TypeError('bad seed type')
      var e = t.byteOffest || 0,
        n = t.byteLength || t.length,
        r = new Uint8Array(t.buffer || t, e, n)
      Pn(r), (Bn = 0)
      for (var i = 0, o = 0; o < r.length; o++) (i |= r[o]), (r[o] = 0)
      return 0 !== i && (qn += 4 * n), (On = qn >= Un)
    }
    function Gt(t) {
      if ((Ln || $t(), !On && void 0 === In)) {
        if (!jn)
          throw new i('No strong PRNGs available. Use asmCrypto.random.seed().')
        void 0 !== We &&
          We.error(
            'No strong PRNGs available; your security is greatly lowered. Use asmCrypto.random.seed().'
          )
      }
      if (!Fn && !On && void 0 !== In && void 0 !== We) {
        var e = new Error().stack
        ;(Hn[e] |= 0),
          Hn[e]++ ||
            We.warn(
              'asmCrypto PRNG not seeded; your security relies on your system PRNG. If this is not acceptable, use asmCrypto.random.seed().'
            )
      }
      if (!p(t) && !g(t)) throw new TypeError('unexpected buffer type')
      var n,
        r,
        o = t.byteOffset || 0,
        s = t.byteLength || t.length,
        a = new Uint8Array(t.buffer || t, o, s)
      for (void 0 !== In && Mn.call(In, a), n = 0; s > n; n++)
        0 == (3 & n) && (Bn >= 1099511627776 && $t(), (r = Dn()), Bn++),
          (a[n] ^= r),
          (r >>>= 8)
      return t
    }
    function Xt() {
      ;(!Ln || Bn >= 1099511627776) && $t()
      var t = (1048576 * Dn() + (Dn() >>> 12)) / 4503599627370496
      return (Bn += 2), t
    }
    function Yt(t, e) {
      return (t * e) | 0
    }
    function Jt(t, e, n) {
      'use asm'
      var r = 0
      var i = new t.Uint32Array(n)
      var o = t.Math.imul
      function s(t) {
        t = t | 0
        r = t = (t + 31) & -32
        return t | 0
      }
      function a(t) {
        t = t | 0
        var e = 0
        e = r
        r = (e + ((t + 31) & -32)) | 0
        return e | 0
      }
      function u(t) {
        t = t | 0
        r = (r - ((t + 31) & -32)) | 0
      }
      function c(t, e, n) {
        t = t | 0
        e = e | 0
        n = n | 0
        var r = 0
        if ((e | 0) > (n | 0)) {
          for (; (r | 0) < (t | 0); r = (r + 4) | 0) {
            i[(n + r) >> 2] = i[(e + r) >> 2]
          }
        } else {
          for (r = (t - 4) | 0; (r | 0) >= 0; r = (r - 4) | 0) {
            i[(n + r) >> 2] = i[(e + r) >> 2]
          }
        }
      }
      function l(t, e, n) {
        t = t | 0
        e = e | 0
        n = n | 0
        var r = 0
        for (; (r | 0) < (t | 0); r = (r + 4) | 0) {
          i[(n + r) >> 2] = e
        }
      }
      function h(t, e, n, r) {
        t = t | 0
        e = e | 0
        n = n | 0
        r = r | 0
        var o = 0,
          s = 0,
          a = 0,
          u = 0,
          c = 0
        if ((r | 0) <= 0) r = e
        if ((r | 0) < (e | 0)) e = r
        s = 1
        for (; (c | 0) < (e | 0); c = (c + 4) | 0) {
          o = ~i[(t + c) >> 2]
          a = ((o & 65535) + s) | 0
          u = ((o >>> 16) + (a >>> 16)) | 0
          i[(n + c) >> 2] = (u << 16) | (a & 65535)
          s = u >>> 16
        }
        for (; (c | 0) < (r | 0); c = (c + 4) | 0) {
          i[(n + c) >> 2] = (s - 1) | 0
        }
        return s | 0
      }
      function f(t, e, n, r) {
        t = t | 0
        e = e | 0
        n = n | 0
        r = r | 0
        var o = 0,
          s = 0,
          a = 0
        if ((e | 0) > (r | 0)) {
          for (a = (e - 4) | 0; (a | 0) >= (r | 0); a = (a - 4) | 0) {
            if (i[(t + a) >> 2] | 0) return 1
          }
        } else {
          for (a = (r - 4) | 0; (a | 0) >= (e | 0); a = (a - 4) | 0) {
            if (i[(n + a) >> 2] | 0) return -1
          }
        }
        for (; (a | 0) >= 0; a = (a - 4) | 0) {
          ;(o = i[(t + a) >> 2] | 0), (s = i[(n + a) >> 2] | 0)
          if (o >>> 0 < s >>> 0) return -1
          if (o >>> 0 > s >>> 0) return 1
        }
        return 0
      }
      function d(t, e) {
        t = t | 0
        e = e | 0
        var n = 0
        for (n = (e - 4) | 0; (n | 0) >= 0; n = (n - 4) | 0) {
          if (i[(t + n) >> 2] | 0) return (n + 4) | 0
        }
        return 0
      }
      function p(t, e, n, r, o, s) {
        t = t | 0
        e = e | 0
        n = n | 0
        r = r | 0
        o = o | 0
        s = s | 0
        var a = 0,
          u = 0,
          c = 0,
          l = 0,
          h = 0,
          f = 0
        if ((e | 0) < (r | 0)) {
          ;(l = t), (t = n), (n = l)
          ;(l = e), (e = r), (r = l)
        }
        if ((s | 0) <= 0) s = (e + 4) | 0
        if ((s | 0) < (r | 0)) e = r = s
        for (; (f | 0) < (r | 0); f = (f + 4) | 0) {
          a = i[(t + f) >> 2] | 0
          u = i[(n + f) >> 2] | 0
          l = ((((a & 65535) + (u & 65535)) | 0) + c) | 0
          h = ((((a >>> 16) + (u >>> 16)) | 0) + (l >>> 16)) | 0
          i[(o + f) >> 2] = (l & 65535) | (h << 16)
          c = h >>> 16
        }
        for (; (f | 0) < (e | 0); f = (f + 4) | 0) {
          a = i[(t + f) >> 2] | 0
          l = ((a & 65535) + c) | 0
          h = ((a >>> 16) + (l >>> 16)) | 0
          i[(o + f) >> 2] = (l & 65535) | (h << 16)
          c = h >>> 16
        }
        for (; (f | 0) < (s | 0); f = (f + 4) | 0) {
          i[(o + f) >> 2] = c | 0
          c = 0
        }
        return c | 0
      }
      function m(t, e, n, r, o, s) {
        t = t | 0
        e = e | 0
        n = n | 0
        r = r | 0
        o = o | 0
        s = s | 0
        var a = 0,
          u = 0,
          c = 0,
          l = 0,
          h = 0,
          f = 0
        if ((s | 0) <= 0) s = (e | 0) > (r | 0) ? (e + 4) | 0 : (r + 4) | 0
        if ((s | 0) < (e | 0)) e = s
        if ((s | 0) < (r | 0)) r = s
        if ((e | 0) < (r | 0)) {
          for (; (f | 0) < (e | 0); f = (f + 4) | 0) {
            a = i[(t + f) >> 2] | 0
            u = i[(n + f) >> 2] | 0
            l = ((((a & 65535) - (u & 65535)) | 0) + c) | 0
            h = ((((a >>> 16) - (u >>> 16)) | 0) + (l >> 16)) | 0
            i[(o + f) >> 2] = (l & 65535) | (h << 16)
            c = h >> 16
          }
          for (; (f | 0) < (r | 0); f = (f + 4) | 0) {
            u = i[(n + f) >> 2] | 0
            l = (c - (u & 65535)) | 0
            h = ((l >> 16) - (u >>> 16)) | 0
            i[(o + f) >> 2] = (l & 65535) | (h << 16)
            c = h >> 16
          }
        } else {
          for (; (f | 0) < (r | 0); f = (f + 4) | 0) {
            a = i[(t + f) >> 2] | 0
            u = i[(n + f) >> 2] | 0
            l = ((((a & 65535) - (u & 65535)) | 0) + c) | 0
            h = ((((a >>> 16) - (u >>> 16)) | 0) + (l >> 16)) | 0
            i[(o + f) >> 2] = (l & 65535) | (h << 16)
            c = h >> 16
          }
          for (; (f | 0) < (e | 0); f = (f + 4) | 0) {
            a = i[(t + f) >> 2] | 0
            l = ((a & 65535) + c) | 0
            h = ((a >>> 16) + (l >> 16)) | 0
            i[(o + f) >> 2] = (l & 65535) | (h << 16)
            c = h >> 16
          }
        }
        for (; (f | 0) < (s | 0); f = (f + 4) | 0) {
          i[(o + f) >> 2] = c | 0
        }
        return c | 0
      }
      function g(t, e, n, r, s, a) {
        t = t | 0
        e = e | 0
        n = n | 0
        r = r | 0
        s = s | 0
        a = a | 0
        var u = 0,
          c = 0,
          l = 0,
          h = 0,
          f = 0,
          d = 0,
          p = 0,
          m = 0,
          g = 0,
          y = 0,
          v = 0,
          b = 0,
          _ = 0,
          w = 0,
          S = 0,
          C = 0,
          E = 0,
          M = 0,
          k = 0,
          x = 0,
          A = 0,
          T = 0,
          I = 0,
          R = 0,
          N = 0,
          D = 0,
          P = 0,
          B = 0,
          L = 0,
          O = 0,
          q = 0,
          U = 0,
          j = 0,
          F = 0,
          H = 0,
          z = 0,
          V = 0,
          K = 0,
          $ = 0,
          W = 0,
          G = 0,
          X = 0,
          Y = 0,
          J = 0,
          Z = 0,
          Q = 0,
          tt = 0,
          et = 0,
          nt = 0,
          rt = 0,
          it = 0,
          ot = 0,
          st = 0,
          at = 0,
          ut = 0,
          ct = 0,
          lt = 0
        if ((e | 0) > (r | 0)) {
          ;(nt = t), (rt = e)
          ;(t = n), (e = r)
          ;(n = nt), (r = rt)
        }
        ot = (e + r) | 0
        if (((a | 0) > (ot | 0)) | ((a | 0) <= 0)) a = ot
        if ((a | 0) < (e | 0)) e = a
        if ((a | 0) < (r | 0)) r = a
        for (; (st | 0) < (e | 0); st = (st + 32) | 0) {
          at = (t + st) | 0
          ;(g = i[(at | 0) >> 2] | 0),
            (y = i[(at | 4) >> 2] | 0),
            (v = i[(at | 8) >> 2] | 0),
            (b = i[(at | 12) >> 2] | 0),
            (_ = i[(at | 16) >> 2] | 0),
            (w = i[(at | 20) >> 2] | 0),
            (S = i[(at | 24) >> 2] | 0),
            (C = i[(at | 28) >> 2] | 0),
            (u = g & 65535),
            (c = y & 65535),
            (l = v & 65535),
            (h = b & 65535),
            (f = _ & 65535),
            (d = w & 65535),
            (p = S & 65535),
            (m = C & 65535),
            (g = g >>> 16),
            (y = y >>> 16),
            (v = v >>> 16),
            (b = b >>> 16),
            (_ = _ >>> 16),
            (w = w >>> 16),
            (S = S >>> 16),
            (C = C >>> 16)
          G = X = Y = J = Z = Q = tt = et = 0
          for (ut = 0; (ut | 0) < (r | 0); ut = (ut + 32) | 0) {
            ct = (n + ut) | 0
            lt = (s + ((st + ut) | 0)) | 0
            ;(N = i[(ct | 0) >> 2] | 0),
              (D = i[(ct | 4) >> 2] | 0),
              (P = i[(ct | 8) >> 2] | 0),
              (B = i[(ct | 12) >> 2] | 0),
              (L = i[(ct | 16) >> 2] | 0),
              (O = i[(ct | 20) >> 2] | 0),
              (q = i[(ct | 24) >> 2] | 0),
              (U = i[(ct | 28) >> 2] | 0),
              (E = N & 65535),
              (M = D & 65535),
              (k = P & 65535),
              (x = B & 65535),
              (A = L & 65535),
              (T = O & 65535),
              (I = q & 65535),
              (R = U & 65535),
              (N = N >>> 16),
              (D = D >>> 16),
              (P = P >>> 16),
              (B = B >>> 16),
              (L = L >>> 16),
              (O = O >>> 16),
              (q = q >>> 16),
              (U = U >>> 16)
            ;(j = i[(lt | 0) >> 2] | 0),
              (F = i[(lt | 4) >> 2] | 0),
              (H = i[(lt | 8) >> 2] | 0),
              (z = i[(lt | 12) >> 2] | 0),
              (V = i[(lt | 16) >> 2] | 0),
              (K = i[(lt | 20) >> 2] | 0),
              ($ = i[(lt | 24) >> 2] | 0),
              (W = i[(lt | 28) >> 2] | 0)
            nt = ((((o(u, E) | 0) + (G & 65535)) | 0) + (j & 65535)) | 0
            rt = ((((o(g, E) | 0) + (G >>> 16)) | 0) + (j >>> 16)) | 0
            it = ((((o(u, N) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(g, N) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            j = (it << 16) | (nt & 65535)
            nt = ((((o(u, M) | 0) + (ot & 65535)) | 0) + (F & 65535)) | 0
            rt = ((((o(g, M) | 0) + (ot >>> 16)) | 0) + (F >>> 16)) | 0
            it = ((((o(u, D) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(g, D) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            F = (it << 16) | (nt & 65535)
            nt = ((((o(u, k) | 0) + (ot & 65535)) | 0) + (H & 65535)) | 0
            rt = ((((o(g, k) | 0) + (ot >>> 16)) | 0) + (H >>> 16)) | 0
            it = ((((o(u, P) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(g, P) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            H = (it << 16) | (nt & 65535)
            nt = ((((o(u, x) | 0) + (ot & 65535)) | 0) + (z & 65535)) | 0
            rt = ((((o(g, x) | 0) + (ot >>> 16)) | 0) + (z >>> 16)) | 0
            it = ((((o(u, B) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(g, B) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            z = (it << 16) | (nt & 65535)
            nt = ((((o(u, A) | 0) + (ot & 65535)) | 0) + (V & 65535)) | 0
            rt = ((((o(g, A) | 0) + (ot >>> 16)) | 0) + (V >>> 16)) | 0
            it = ((((o(u, L) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(g, L) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            V = (it << 16) | (nt & 65535)
            nt = ((((o(u, T) | 0) + (ot & 65535)) | 0) + (K & 65535)) | 0
            rt = ((((o(g, T) | 0) + (ot >>> 16)) | 0) + (K >>> 16)) | 0
            it = ((((o(u, O) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(g, O) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            K = (it << 16) | (nt & 65535)
            nt = ((((o(u, I) | 0) + (ot & 65535)) | 0) + ($ & 65535)) | 0
            rt = ((((o(g, I) | 0) + (ot >>> 16)) | 0) + ($ >>> 16)) | 0
            it = ((((o(u, q) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(g, q) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            $ = (it << 16) | (nt & 65535)
            nt = ((((o(u, R) | 0) + (ot & 65535)) | 0) + (W & 65535)) | 0
            rt = ((((o(g, R) | 0) + (ot >>> 16)) | 0) + (W >>> 16)) | 0
            it = ((((o(u, U) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(g, U) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            W = (it << 16) | (nt & 65535)
            G = ot
            nt = ((((o(c, E) | 0) + (X & 65535)) | 0) + (F & 65535)) | 0
            rt = ((((o(y, E) | 0) + (X >>> 16)) | 0) + (F >>> 16)) | 0
            it = ((((o(c, N) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(y, N) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            F = (it << 16) | (nt & 65535)
            nt = ((((o(c, M) | 0) + (ot & 65535)) | 0) + (H & 65535)) | 0
            rt = ((((o(y, M) | 0) + (ot >>> 16)) | 0) + (H >>> 16)) | 0
            it = ((((o(c, D) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(y, D) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            H = (it << 16) | (nt & 65535)
            nt = ((((o(c, k) | 0) + (ot & 65535)) | 0) + (z & 65535)) | 0
            rt = ((((o(y, k) | 0) + (ot >>> 16)) | 0) + (z >>> 16)) | 0
            it = ((((o(c, P) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(y, P) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            z = (it << 16) | (nt & 65535)
            nt = ((((o(c, x) | 0) + (ot & 65535)) | 0) + (V & 65535)) | 0
            rt = ((((o(y, x) | 0) + (ot >>> 16)) | 0) + (V >>> 16)) | 0
            it = ((((o(c, B) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(y, B) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            V = (it << 16) | (nt & 65535)
            nt = ((((o(c, A) | 0) + (ot & 65535)) | 0) + (K & 65535)) | 0
            rt = ((((o(y, A) | 0) + (ot >>> 16)) | 0) + (K >>> 16)) | 0
            it = ((((o(c, L) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(y, L) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            K = (it << 16) | (nt & 65535)
            nt = ((((o(c, T) | 0) + (ot & 65535)) | 0) + ($ & 65535)) | 0
            rt = ((((o(y, T) | 0) + (ot >>> 16)) | 0) + ($ >>> 16)) | 0
            it = ((((o(c, O) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(y, O) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            $ = (it << 16) | (nt & 65535)
            nt = ((((o(c, I) | 0) + (ot & 65535)) | 0) + (W & 65535)) | 0
            rt = ((((o(y, I) | 0) + (ot >>> 16)) | 0) + (W >>> 16)) | 0
            it = ((((o(c, q) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(y, q) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            W = (it << 16) | (nt & 65535)
            nt = ((((o(c, R) | 0) + (ot & 65535)) | 0) + (G & 65535)) | 0
            rt = ((((o(y, R) | 0) + (ot >>> 16)) | 0) + (G >>> 16)) | 0
            it = ((((o(c, U) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(y, U) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            G = (it << 16) | (nt & 65535)
            X = ot
            nt = ((((o(l, E) | 0) + (Y & 65535)) | 0) + (H & 65535)) | 0
            rt = ((((o(v, E) | 0) + (Y >>> 16)) | 0) + (H >>> 16)) | 0
            it = ((((o(l, N) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(v, N) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            H = (it << 16) | (nt & 65535)
            nt = ((((o(l, M) | 0) + (ot & 65535)) | 0) + (z & 65535)) | 0
            rt = ((((o(v, M) | 0) + (ot >>> 16)) | 0) + (z >>> 16)) | 0
            it = ((((o(l, D) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(v, D) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            z = (it << 16) | (nt & 65535)
            nt = ((((o(l, k) | 0) + (ot & 65535)) | 0) + (V & 65535)) | 0
            rt = ((((o(v, k) | 0) + (ot >>> 16)) | 0) + (V >>> 16)) | 0
            it = ((((o(l, P) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(v, P) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            V = (it << 16) | (nt & 65535)
            nt = ((((o(l, x) | 0) + (ot & 65535)) | 0) + (K & 65535)) | 0
            rt = ((((o(v, x) | 0) + (ot >>> 16)) | 0) + (K >>> 16)) | 0
            it = ((((o(l, B) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(v, B) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            K = (it << 16) | (nt & 65535)
            nt = ((((o(l, A) | 0) + (ot & 65535)) | 0) + ($ & 65535)) | 0
            rt = ((((o(v, A) | 0) + (ot >>> 16)) | 0) + ($ >>> 16)) | 0
            it = ((((o(l, L) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(v, L) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            $ = (it << 16) | (nt & 65535)
            nt = ((((o(l, T) | 0) + (ot & 65535)) | 0) + (W & 65535)) | 0
            rt = ((((o(v, T) | 0) + (ot >>> 16)) | 0) + (W >>> 16)) | 0
            it = ((((o(l, O) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(v, O) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            W = (it << 16) | (nt & 65535)
            nt = ((((o(l, I) | 0) + (ot & 65535)) | 0) + (G & 65535)) | 0
            rt = ((((o(v, I) | 0) + (ot >>> 16)) | 0) + (G >>> 16)) | 0
            it = ((((o(l, q) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(v, q) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            G = (it << 16) | (nt & 65535)
            nt = ((((o(l, R) | 0) + (ot & 65535)) | 0) + (X & 65535)) | 0
            rt = ((((o(v, R) | 0) + (ot >>> 16)) | 0) + (X >>> 16)) | 0
            it = ((((o(l, U) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(v, U) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            X = (it << 16) | (nt & 65535)
            Y = ot
            nt = ((((o(h, E) | 0) + (J & 65535)) | 0) + (z & 65535)) | 0
            rt = ((((o(b, E) | 0) + (J >>> 16)) | 0) + (z >>> 16)) | 0
            it = ((((o(h, N) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(b, N) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            z = (it << 16) | (nt & 65535)
            nt = ((((o(h, M) | 0) + (ot & 65535)) | 0) + (V & 65535)) | 0
            rt = ((((o(b, M) | 0) + (ot >>> 16)) | 0) + (V >>> 16)) | 0
            it = ((((o(h, D) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(b, D) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            V = (it << 16) | (nt & 65535)
            nt = ((((o(h, k) | 0) + (ot & 65535)) | 0) + (K & 65535)) | 0
            rt = ((((o(b, k) | 0) + (ot >>> 16)) | 0) + (K >>> 16)) | 0
            it = ((((o(h, P) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(b, P) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            K = (it << 16) | (nt & 65535)
            nt = ((((o(h, x) | 0) + (ot & 65535)) | 0) + ($ & 65535)) | 0
            rt = ((((o(b, x) | 0) + (ot >>> 16)) | 0) + ($ >>> 16)) | 0
            it = ((((o(h, B) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(b, B) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            $ = (it << 16) | (nt & 65535)
            nt = ((((o(h, A) | 0) + (ot & 65535)) | 0) + (W & 65535)) | 0
            rt = ((((o(b, A) | 0) + (ot >>> 16)) | 0) + (W >>> 16)) | 0
            it = ((((o(h, L) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(b, L) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            W = (it << 16) | (nt & 65535)
            nt = ((((o(h, T) | 0) + (ot & 65535)) | 0) + (G & 65535)) | 0
            rt = ((((o(b, T) | 0) + (ot >>> 16)) | 0) + (G >>> 16)) | 0
            it = ((((o(h, O) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(b, O) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            G = (it << 16) | (nt & 65535)
            nt = ((((o(h, I) | 0) + (ot & 65535)) | 0) + (X & 65535)) | 0
            rt = ((((o(b, I) | 0) + (ot >>> 16)) | 0) + (X >>> 16)) | 0
            it = ((((o(h, q) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(b, q) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            X = (it << 16) | (nt & 65535)
            nt = ((((o(h, R) | 0) + (ot & 65535)) | 0) + (Y & 65535)) | 0
            rt = ((((o(b, R) | 0) + (ot >>> 16)) | 0) + (Y >>> 16)) | 0
            it = ((((o(h, U) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(b, U) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            Y = (it << 16) | (nt & 65535)
            J = ot
            nt = ((((o(f, E) | 0) + (Z & 65535)) | 0) + (V & 65535)) | 0
            rt = ((((o(_, E) | 0) + (Z >>> 16)) | 0) + (V >>> 16)) | 0
            it = ((((o(f, N) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(_, N) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            V = (it << 16) | (nt & 65535)
            nt = ((((o(f, M) | 0) + (ot & 65535)) | 0) + (K & 65535)) | 0
            rt = ((((o(_, M) | 0) + (ot >>> 16)) | 0) + (K >>> 16)) | 0
            it = ((((o(f, D) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(_, D) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            K = (it << 16) | (nt & 65535)
            nt = ((((o(f, k) | 0) + (ot & 65535)) | 0) + ($ & 65535)) | 0
            rt = ((((o(_, k) | 0) + (ot >>> 16)) | 0) + ($ >>> 16)) | 0
            it = ((((o(f, P) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(_, P) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            $ = (it << 16) | (nt & 65535)
            nt = ((((o(f, x) | 0) + (ot & 65535)) | 0) + (W & 65535)) | 0
            rt = ((((o(_, x) | 0) + (ot >>> 16)) | 0) + (W >>> 16)) | 0
            it = ((((o(f, B) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(_, B) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            W = (it << 16) | (nt & 65535)
            nt = ((((o(f, A) | 0) + (ot & 65535)) | 0) + (G & 65535)) | 0
            rt = ((((o(_, A) | 0) + (ot >>> 16)) | 0) + (G >>> 16)) | 0
            it = ((((o(f, L) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(_, L) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            G = (it << 16) | (nt & 65535)
            nt = ((((o(f, T) | 0) + (ot & 65535)) | 0) + (X & 65535)) | 0
            rt = ((((o(_, T) | 0) + (ot >>> 16)) | 0) + (X >>> 16)) | 0
            it = ((((o(f, O) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(_, O) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            X = (it << 16) | (nt & 65535)
            nt = ((((o(f, I) | 0) + (ot & 65535)) | 0) + (Y & 65535)) | 0
            rt = ((((o(_, I) | 0) + (ot >>> 16)) | 0) + (Y >>> 16)) | 0
            it = ((((o(f, q) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(_, q) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            Y = (it << 16) | (nt & 65535)
            nt = ((((o(f, R) | 0) + (ot & 65535)) | 0) + (J & 65535)) | 0
            rt = ((((o(_, R) | 0) + (ot >>> 16)) | 0) + (J >>> 16)) | 0
            it = ((((o(f, U) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(_, U) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            J = (it << 16) | (nt & 65535)
            Z = ot
            nt = ((((o(d, E) | 0) + (Q & 65535)) | 0) + (K & 65535)) | 0
            rt = ((((o(w, E) | 0) + (Q >>> 16)) | 0) + (K >>> 16)) | 0
            it = ((((o(d, N) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(w, N) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            K = (it << 16) | (nt & 65535)
            nt = ((((o(d, M) | 0) + (ot & 65535)) | 0) + ($ & 65535)) | 0
            rt = ((((o(w, M) | 0) + (ot >>> 16)) | 0) + ($ >>> 16)) | 0
            it = ((((o(d, D) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(w, D) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            $ = (it << 16) | (nt & 65535)
            nt = ((((o(d, k) | 0) + (ot & 65535)) | 0) + (W & 65535)) | 0
            rt = ((((o(w, k) | 0) + (ot >>> 16)) | 0) + (W >>> 16)) | 0
            it = ((((o(d, P) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(w, P) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            W = (it << 16) | (nt & 65535)
            nt = ((((o(d, x) | 0) + (ot & 65535)) | 0) + (G & 65535)) | 0
            rt = ((((o(w, x) | 0) + (ot >>> 16)) | 0) + (G >>> 16)) | 0
            it = ((((o(d, B) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(w, B) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            G = (it << 16) | (nt & 65535)
            nt = ((((o(d, A) | 0) + (ot & 65535)) | 0) + (X & 65535)) | 0
            rt = ((((o(w, A) | 0) + (ot >>> 16)) | 0) + (X >>> 16)) | 0
            it = ((((o(d, L) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(w, L) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            X = (it << 16) | (nt & 65535)
            nt = ((((o(d, T) | 0) + (ot & 65535)) | 0) + (Y & 65535)) | 0
            rt = ((((o(w, T) | 0) + (ot >>> 16)) | 0) + (Y >>> 16)) | 0
            it = ((((o(d, O) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(w, O) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            Y = (it << 16) | (nt & 65535)
            nt = ((((o(d, I) | 0) + (ot & 65535)) | 0) + (J & 65535)) | 0
            rt = ((((o(w, I) | 0) + (ot >>> 16)) | 0) + (J >>> 16)) | 0
            it = ((((o(d, q) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(w, q) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            J = (it << 16) | (nt & 65535)
            nt = ((((o(d, R) | 0) + (ot & 65535)) | 0) + (Z & 65535)) | 0
            rt = ((((o(w, R) | 0) + (ot >>> 16)) | 0) + (Z >>> 16)) | 0
            it = ((((o(d, U) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(w, U) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            Z = (it << 16) | (nt & 65535)
            Q = ot
            nt = ((((o(p, E) | 0) + (tt & 65535)) | 0) + ($ & 65535)) | 0
            rt = ((((o(S, E) | 0) + (tt >>> 16)) | 0) + ($ >>> 16)) | 0
            it = ((((o(p, N) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(S, N) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            $ = (it << 16) | (nt & 65535)
            nt = ((((o(p, M) | 0) + (ot & 65535)) | 0) + (W & 65535)) | 0
            rt = ((((o(S, M) | 0) + (ot >>> 16)) | 0) + (W >>> 16)) | 0
            it = ((((o(p, D) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(S, D) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            W = (it << 16) | (nt & 65535)
            nt = ((((o(p, k) | 0) + (ot & 65535)) | 0) + (G & 65535)) | 0
            rt = ((((o(S, k) | 0) + (ot >>> 16)) | 0) + (G >>> 16)) | 0
            it = ((((o(p, P) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(S, P) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            G = (it << 16) | (nt & 65535)
            nt = ((((o(p, x) | 0) + (ot & 65535)) | 0) + (X & 65535)) | 0
            rt = ((((o(S, x) | 0) + (ot >>> 16)) | 0) + (X >>> 16)) | 0
            it = ((((o(p, B) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(S, B) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            X = (it << 16) | (nt & 65535)
            nt = ((((o(p, A) | 0) + (ot & 65535)) | 0) + (Y & 65535)) | 0
            rt = ((((o(S, A) | 0) + (ot >>> 16)) | 0) + (Y >>> 16)) | 0
            it = ((((o(p, L) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(S, L) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            Y = (it << 16) | (nt & 65535)
            nt = ((((o(p, T) | 0) + (ot & 65535)) | 0) + (J & 65535)) | 0
            rt = ((((o(S, T) | 0) + (ot >>> 16)) | 0) + (J >>> 16)) | 0
            it = ((((o(p, O) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(S, O) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            J = (it << 16) | (nt & 65535)
            nt = ((((o(p, I) | 0) + (ot & 65535)) | 0) + (Z & 65535)) | 0
            rt = ((((o(S, I) | 0) + (ot >>> 16)) | 0) + (Z >>> 16)) | 0
            it = ((((o(p, q) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(S, q) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            Z = (it << 16) | (nt & 65535)
            nt = ((((o(p, R) | 0) + (ot & 65535)) | 0) + (Q & 65535)) | 0
            rt = ((((o(S, R) | 0) + (ot >>> 16)) | 0) + (Q >>> 16)) | 0
            it = ((((o(p, U) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(S, U) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            Q = (it << 16) | (nt & 65535)
            tt = ot
            nt = ((((o(m, E) | 0) + (et & 65535)) | 0) + (W & 65535)) | 0
            rt = ((((o(C, E) | 0) + (et >>> 16)) | 0) + (W >>> 16)) | 0
            it = ((((o(m, N) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(C, N) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            W = (it << 16) | (nt & 65535)
            nt = ((((o(m, M) | 0) + (ot & 65535)) | 0) + (G & 65535)) | 0
            rt = ((((o(C, M) | 0) + (ot >>> 16)) | 0) + (G >>> 16)) | 0
            it = ((((o(m, D) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(C, D) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            G = (it << 16) | (nt & 65535)
            nt = ((((o(m, k) | 0) + (ot & 65535)) | 0) + (X & 65535)) | 0
            rt = ((((o(C, k) | 0) + (ot >>> 16)) | 0) + (X >>> 16)) | 0
            it = ((((o(m, P) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(C, P) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            X = (it << 16) | (nt & 65535)
            nt = ((((o(m, x) | 0) + (ot & 65535)) | 0) + (Y & 65535)) | 0
            rt = ((((o(C, x) | 0) + (ot >>> 16)) | 0) + (Y >>> 16)) | 0
            it = ((((o(m, B) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(C, B) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            Y = (it << 16) | (nt & 65535)
            nt = ((((o(m, A) | 0) + (ot & 65535)) | 0) + (J & 65535)) | 0
            rt = ((((o(C, A) | 0) + (ot >>> 16)) | 0) + (J >>> 16)) | 0
            it = ((((o(m, L) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(C, L) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            J = (it << 16) | (nt & 65535)
            nt = ((((o(m, T) | 0) + (ot & 65535)) | 0) + (Z & 65535)) | 0
            rt = ((((o(C, T) | 0) + (ot >>> 16)) | 0) + (Z >>> 16)) | 0
            it = ((((o(m, O) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(C, O) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            Z = (it << 16) | (nt & 65535)
            nt = ((((o(m, I) | 0) + (ot & 65535)) | 0) + (Q & 65535)) | 0
            rt = ((((o(C, I) | 0) + (ot >>> 16)) | 0) + (Q >>> 16)) | 0
            it = ((((o(m, q) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(C, q) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            Q = (it << 16) | (nt & 65535)
            nt = ((((o(m, R) | 0) + (ot & 65535)) | 0) + (tt & 65535)) | 0
            rt = ((((o(C, R) | 0) + (ot >>> 16)) | 0) + (tt >>> 16)) | 0
            it = ((((o(m, U) | 0) + (rt & 65535)) | 0) + (nt >>> 16)) | 0
            ot = ((((o(C, U) | 0) + (rt >>> 16)) | 0) + (it >>> 16)) | 0
            tt = (it << 16) | (nt & 65535)
            et = ot
            ;(i[(lt | 0) >> 2] = j),
              (i[(lt | 4) >> 2] = F),
              (i[(lt | 8) >> 2] = H),
              (i[(lt | 12) >> 2] = z),
              (i[(lt | 16) >> 2] = V),
              (i[(lt | 20) >> 2] = K),
              (i[(lt | 24) >> 2] = $),
              (i[(lt | 28) >> 2] = W)
          }
          lt = (s + ((st + ut) | 0)) | 0
          ;(i[(lt | 0) >> 2] = G),
            (i[(lt | 4) >> 2] = X),
            (i[(lt | 8) >> 2] = Y),
            (i[(lt | 12) >> 2] = J),
            (i[(lt | 16) >> 2] = Z),
            (i[(lt | 20) >> 2] = Q),
            (i[(lt | 24) >> 2] = tt),
            (i[(lt | 28) >> 2] = et)
        }
      }
      function y(t, e, n) {
        t = t | 0
        e = e | 0
        n = n | 0
        var r = 0,
          s = 0,
          a = 0,
          u = 0,
          c = 0,
          l = 0,
          h = 0,
          f = 0,
          d = 0,
          p = 0,
          m = 0,
          g = 0,
          y = 0,
          v = 0,
          b = 0,
          _ = 0,
          w = 0,
          S = 0,
          C = 0,
          E = 0,
          M = 0,
          k = 0,
          x = 0,
          A = 0,
          T = 0,
          I = 0,
          R = 0,
          N = 0,
          D = 0,
          P = 0,
          B = 0,
          L = 0,
          O = 0,
          q = 0,
          U = 0,
          j = 0,
          F = 0,
          H = 0,
          z = 0,
          V = 0,
          K = 0,
          $ = 0,
          W = 0,
          G = 0,
          X = 0,
          Y = 0,
          J = 0,
          Z = 0,
          Q = 0,
          tt = 0,
          et = 0,
          nt = 0,
          rt = 0,
          it = 0,
          ot = 0,
          st = 0,
          at = 0,
          ut = 0,
          ct = 0,
          lt = 0,
          ht = 0,
          ft = 0,
          dt = 0,
          pt = 0
        for (; (ct | 0) < (e | 0); ct = (ct + 4) | 0) {
          pt = (n + (ct << 1)) | 0
          ;(d = i[(t + ct) >> 2] | 0), (r = d & 65535), (d = d >>> 16)
          Q = o(r, r) | 0
          tt = ((o(r, d) | 0) + (Q >>> 17)) | 0
          et = ((o(d, d) | 0) + (tt >>> 15)) | 0
          i[pt >> 2] = (tt << 17) | (Q & 131071)
          i[(pt | 4) >> 2] = et
        }
        for (ut = 0; (ut | 0) < (e | 0); ut = (ut + 8) | 0) {
          ;(ft = (t + ut) | 0), (pt = (n + (ut << 1)) | 0)
          ;(d = i[ft >> 2] | 0), (r = d & 65535), (d = d >>> 16)
          ;(T = i[(ft | 4) >> 2] | 0), (w = T & 65535), (T = T >>> 16)
          Q = o(r, w) | 0
          tt = ((o(r, T) | 0) + (Q >>> 16)) | 0
          et = ((o(d, w) | 0) + (tt & 65535)) | 0
          it = ((((o(d, T) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
          ot = i[(pt | 4) >> 2] | 0
          Q = ((ot & 65535) + ((Q & 65535) << 1)) | 0
          et = ((((ot >>> 16) + ((et & 65535) << 1)) | 0) + (Q >>> 16)) | 0
          i[(pt | 4) >> 2] = (et << 16) | (Q & 65535)
          nt = et >>> 16
          ot = i[(pt | 8) >> 2] | 0
          Q = ((((ot & 65535) + ((it & 65535) << 1)) | 0) + nt) | 0
          et = ((((ot >>> 16) + ((it >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
          i[(pt | 8) >> 2] = (et << 16) | (Q & 65535)
          nt = et >>> 16
          if (nt) {
            ot = i[(pt | 12) >> 2] | 0
            Q = ((ot & 65535) + nt) | 0
            et = ((ot >>> 16) + (Q >>> 16)) | 0
            i[(pt | 12) >> 2] = (et << 16) | (Q & 65535)
          }
        }
        for (ut = 0; (ut | 0) < (e | 0); ut = (ut + 16) | 0) {
          ;(ft = (t + ut) | 0), (pt = (n + (ut << 1)) | 0)
          ;(d = i[ft >> 2] | 0),
            (r = d & 65535),
            (d = d >>> 16),
            (p = i[(ft | 4) >> 2] | 0),
            (s = p & 65535),
            (p = p >>> 16)
          ;(T = i[(ft | 8) >> 2] | 0),
            (w = T & 65535),
            (T = T >>> 16),
            (I = i[(ft | 12) >> 2] | 0),
            (S = I & 65535),
            (I = I >>> 16)
          Q = o(r, w) | 0
          tt = o(d, w) | 0
          et = ((((o(r, T) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
          it = ((((o(d, T) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
          O = (et << 16) | (Q & 65535)
          Q = ((o(r, S) | 0) + (it & 65535)) | 0
          tt = ((o(d, S) | 0) + (it >>> 16)) | 0
          et = ((((o(r, I) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
          it = ((((o(d, I) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
          q = (et << 16) | (Q & 65535)
          U = it
          Q = ((o(s, w) | 0) + (q & 65535)) | 0
          tt = ((o(p, w) | 0) + (q >>> 16)) | 0
          et = ((((o(s, T) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
          it = ((((o(p, T) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
          q = (et << 16) | (Q & 65535)
          Q = ((((o(s, S) | 0) + (U & 65535)) | 0) + (it & 65535)) | 0
          tt = ((((o(p, S) | 0) + (U >>> 16)) | 0) + (it >>> 16)) | 0
          et = ((((o(s, I) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
          it = ((((o(p, I) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
          U = (et << 16) | (Q & 65535)
          j = it
          ot = i[(pt | 8) >> 2] | 0
          Q = ((ot & 65535) + ((O & 65535) << 1)) | 0
          et = ((((ot >>> 16) + ((O >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
          i[(pt | 8) >> 2] = (et << 16) | (Q & 65535)
          nt = et >>> 16
          ot = i[(pt | 12) >> 2] | 0
          Q = ((((ot & 65535) + ((q & 65535) << 1)) | 0) + nt) | 0
          et = ((((ot >>> 16) + ((q >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
          i[(pt | 12) >> 2] = (et << 16) | (Q & 65535)
          nt = et >>> 16
          ot = i[(pt | 16) >> 2] | 0
          Q = ((((ot & 65535) + ((U & 65535) << 1)) | 0) + nt) | 0
          et = ((((ot >>> 16) + ((U >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
          i[(pt | 16) >> 2] = (et << 16) | (Q & 65535)
          nt = et >>> 16
          ot = i[(pt | 20) >> 2] | 0
          Q = ((((ot & 65535) + ((j & 65535) << 1)) | 0) + nt) | 0
          et = ((((ot >>> 16) + ((j >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
          i[(pt | 20) >> 2] = (et << 16) | (Q & 65535)
          nt = et >>> 16
          for (ht = 24; !!nt & ((ht | 0) < 32); ht = (ht + 4) | 0) {
            ot = i[(pt | ht) >> 2] | 0
            Q = ((ot & 65535) + nt) | 0
            et = ((ot >>> 16) + (Q >>> 16)) | 0
            i[(pt | ht) >> 2] = (et << 16) | (Q & 65535)
            nt = et >>> 16
          }
        }
        for (ut = 0; (ut | 0) < (e | 0); ut = (ut + 32) | 0) {
          ;(ft = (t + ut) | 0), (pt = (n + (ut << 1)) | 0)
          ;(d = i[ft >> 2] | 0),
            (r = d & 65535),
            (d = d >>> 16),
            (p = i[(ft | 4) >> 2] | 0),
            (s = p & 65535),
            (p = p >>> 16),
            (m = i[(ft | 8) >> 2] | 0),
            (a = m & 65535),
            (m = m >>> 16),
            (g = i[(ft | 12) >> 2] | 0),
            (u = g & 65535),
            (g = g >>> 16)
          ;(T = i[(ft | 16) >> 2] | 0),
            (w = T & 65535),
            (T = T >>> 16),
            (I = i[(ft | 20) >> 2] | 0),
            (S = I & 65535),
            (I = I >>> 16),
            (R = i[(ft | 24) >> 2] | 0),
            (C = R & 65535),
            (R = R >>> 16),
            (N = i[(ft | 28) >> 2] | 0),
            (E = N & 65535),
            (N = N >>> 16)
          Q = o(r, w) | 0
          tt = o(d, w) | 0
          et = ((((o(r, T) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
          it = ((((o(d, T) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
          O = (et << 16) | (Q & 65535)
          Q = ((o(r, S) | 0) + (it & 65535)) | 0
          tt = ((o(d, S) | 0) + (it >>> 16)) | 0
          et = ((((o(r, I) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
          it = ((((o(d, I) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
          q = (et << 16) | (Q & 65535)
          Q = ((o(r, C) | 0) + (it & 65535)) | 0
          tt = ((o(d, C) | 0) + (it >>> 16)) | 0
          et = ((((o(r, R) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
          it = ((((o(d, R) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
          U = (et << 16) | (Q & 65535)
          Q = ((o(r, E) | 0) + (it & 65535)) | 0
          tt = ((o(d, E) | 0) + (it >>> 16)) | 0
          et = ((((o(r, N) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
          it = ((((o(d, N) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
          j = (et << 16) | (Q & 65535)
          F = it
          Q = ((o(s, w) | 0) + (q & 65535)) | 0
          tt = ((o(p, w) | 0) + (q >>> 16)) | 0
          et = ((((o(s, T) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
          it = ((((o(p, T) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
          q = (et << 16) | (Q & 65535)
          Q = ((((o(s, S) | 0) + (U & 65535)) | 0) + (it & 65535)) | 0
          tt = ((((o(p, S) | 0) + (U >>> 16)) | 0) + (it >>> 16)) | 0
          et = ((((o(s, I) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
          it = ((((o(p, I) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
          U = (et << 16) | (Q & 65535)
          Q = ((((o(s, C) | 0) + (j & 65535)) | 0) + (it & 65535)) | 0
          tt = ((((o(p, C) | 0) + (j >>> 16)) | 0) + (it >>> 16)) | 0
          et = ((((o(s, R) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
          it = ((((o(p, R) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
          j = (et << 16) | (Q & 65535)
          Q = ((((o(s, E) | 0) + (F & 65535)) | 0) + (it & 65535)) | 0
          tt = ((((o(p, E) | 0) + (F >>> 16)) | 0) + (it >>> 16)) | 0
          et = ((((o(s, N) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
          it = ((((o(p, N) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
          F = (et << 16) | (Q & 65535)
          H = it
          Q = ((o(a, w) | 0) + (U & 65535)) | 0
          tt = ((o(m, w) | 0) + (U >>> 16)) | 0
          et = ((((o(a, T) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
          it = ((((o(m, T) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
          U = (et << 16) | (Q & 65535)
          Q = ((((o(a, S) | 0) + (j & 65535)) | 0) + (it & 65535)) | 0
          tt = ((((o(m, S) | 0) + (j >>> 16)) | 0) + (it >>> 16)) | 0
          et = ((((o(a, I) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
          it = ((((o(m, I) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
          j = (et << 16) | (Q & 65535)
          Q = ((((o(a, C) | 0) + (F & 65535)) | 0) + (it & 65535)) | 0
          tt = ((((o(m, C) | 0) + (F >>> 16)) | 0) + (it >>> 16)) | 0
          et = ((((o(a, R) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
          it = ((((o(m, R) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
          F = (et << 16) | (Q & 65535)
          Q = ((((o(a, E) | 0) + (H & 65535)) | 0) + (it & 65535)) | 0
          tt = ((((o(m, E) | 0) + (H >>> 16)) | 0) + (it >>> 16)) | 0
          et = ((((o(a, N) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
          it = ((((o(m, N) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
          H = (et << 16) | (Q & 65535)
          z = it
          Q = ((o(u, w) | 0) + (j & 65535)) | 0
          tt = ((o(g, w) | 0) + (j >>> 16)) | 0
          et = ((((o(u, T) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
          it = ((((o(g, T) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
          j = (et << 16) | (Q & 65535)
          Q = ((((o(u, S) | 0) + (F & 65535)) | 0) + (it & 65535)) | 0
          tt = ((((o(g, S) | 0) + (F >>> 16)) | 0) + (it >>> 16)) | 0
          et = ((((o(u, I) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
          it = ((((o(g, I) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
          F = (et << 16) | (Q & 65535)
          Q = ((((o(u, C) | 0) + (H & 65535)) | 0) + (it & 65535)) | 0
          tt = ((((o(g, C) | 0) + (H >>> 16)) | 0) + (it >>> 16)) | 0
          et = ((((o(u, R) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
          it = ((((o(g, R) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
          H = (et << 16) | (Q & 65535)
          Q = ((((o(u, E) | 0) + (z & 65535)) | 0) + (it & 65535)) | 0
          tt = ((((o(g, E) | 0) + (z >>> 16)) | 0) + (it >>> 16)) | 0
          et = ((((o(u, N) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
          it = ((((o(g, N) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
          z = (et << 16) | (Q & 65535)
          V = it
          ot = i[(pt | 16) >> 2] | 0
          Q = ((ot & 65535) + ((O & 65535) << 1)) | 0
          et = ((((ot >>> 16) + ((O >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
          i[(pt | 16) >> 2] = (et << 16) | (Q & 65535)
          nt = et >>> 16
          ot = i[(pt | 20) >> 2] | 0
          Q = ((((ot & 65535) + ((q & 65535) << 1)) | 0) + nt) | 0
          et = ((((ot >>> 16) + ((q >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
          i[(pt | 20) >> 2] = (et << 16) | (Q & 65535)
          nt = et >>> 16
          ot = i[(pt | 24) >> 2] | 0
          Q = ((((ot & 65535) + ((U & 65535) << 1)) | 0) + nt) | 0
          et = ((((ot >>> 16) + ((U >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
          i[(pt | 24) >> 2] = (et << 16) | (Q & 65535)
          nt = et >>> 16
          ot = i[(pt | 28) >> 2] | 0
          Q = ((((ot & 65535) + ((j & 65535) << 1)) | 0) + nt) | 0
          et = ((((ot >>> 16) + ((j >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
          i[(pt | 28) >> 2] = (et << 16) | (Q & 65535)
          nt = et >>> 16
          ot = i[(pt + 32) >> 2] | 0
          Q = ((((ot & 65535) + ((F & 65535) << 1)) | 0) + nt) | 0
          et = ((((ot >>> 16) + ((F >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
          i[(pt + 32) >> 2] = (et << 16) | (Q & 65535)
          nt = et >>> 16
          ot = i[(pt + 36) >> 2] | 0
          Q = ((((ot & 65535) + ((H & 65535) << 1)) | 0) + nt) | 0
          et = ((((ot >>> 16) + ((H >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
          i[(pt + 36) >> 2] = (et << 16) | (Q & 65535)
          nt = et >>> 16
          ot = i[(pt + 40) >> 2] | 0
          Q = ((((ot & 65535) + ((z & 65535) << 1)) | 0) + nt) | 0
          et = ((((ot >>> 16) + ((z >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
          i[(pt + 40) >> 2] = (et << 16) | (Q & 65535)
          nt = et >>> 16
          ot = i[(pt + 44) >> 2] | 0
          Q = ((((ot & 65535) + ((V & 65535) << 1)) | 0) + nt) | 0
          et = ((((ot >>> 16) + ((V >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
          i[(pt + 44) >> 2] = (et << 16) | (Q & 65535)
          nt = et >>> 16
          for (ht = 48; !!nt & ((ht | 0) < 64); ht = (ht + 4) | 0) {
            ot = i[(pt + ht) >> 2] | 0
            Q = ((ot & 65535) + nt) | 0
            et = ((ot >>> 16) + (Q >>> 16)) | 0
            i[(pt + ht) >> 2] = (et << 16) | (Q & 65535)
            nt = et >>> 16
          }
        }
        for (st = 32; (st | 0) < (e | 0); st = st << 1) {
          at = st << 1
          for (ut = 0; (ut | 0) < (e | 0); ut = (ut + at) | 0) {
            pt = (n + (ut << 1)) | 0
            rt = 0
            for (ct = 0; (ct | 0) < (st | 0); ct = (ct + 32) | 0) {
              ft = (((t + ut) | 0) + ct) | 0
              ;(d = i[ft >> 2] | 0),
                (r = d & 65535),
                (d = d >>> 16),
                (p = i[(ft | 4) >> 2] | 0),
                (s = p & 65535),
                (p = p >>> 16),
                (m = i[(ft | 8) >> 2] | 0),
                (a = m & 65535),
                (m = m >>> 16),
                (g = i[(ft | 12) >> 2] | 0),
                (u = g & 65535),
                (g = g >>> 16),
                (y = i[(ft | 16) >> 2] | 0),
                (c = y & 65535),
                (y = y >>> 16),
                (v = i[(ft | 20) >> 2] | 0),
                (l = v & 65535),
                (v = v >>> 16),
                (b = i[(ft | 24) >> 2] | 0),
                (h = b & 65535),
                (b = b >>> 16),
                (_ = i[(ft | 28) >> 2] | 0),
                (f = _ & 65535),
                (_ = _ >>> 16)
              K = $ = W = G = X = Y = J = Z = nt = 0
              for (lt = 0; (lt | 0) < (st | 0); lt = (lt + 32) | 0) {
                dt = (((((t + ut) | 0) + st) | 0) + lt) | 0
                ;(T = i[dt >> 2] | 0),
                  (w = T & 65535),
                  (T = T >>> 16),
                  (I = i[(dt | 4) >> 2] | 0),
                  (S = I & 65535),
                  (I = I >>> 16),
                  (R = i[(dt | 8) >> 2] | 0),
                  (C = R & 65535),
                  (R = R >>> 16),
                  (N = i[(dt | 12) >> 2] | 0),
                  (E = N & 65535),
                  (N = N >>> 16),
                  (D = i[(dt | 16) >> 2] | 0),
                  (M = D & 65535),
                  (D = D >>> 16),
                  (P = i[(dt | 20) >> 2] | 0),
                  (k = P & 65535),
                  (P = P >>> 16),
                  (B = i[(dt | 24) >> 2] | 0),
                  (x = B & 65535),
                  (B = B >>> 16),
                  (L = i[(dt | 28) >> 2] | 0),
                  (A = L & 65535),
                  (L = L >>> 16)
                O = q = U = j = F = H = z = V = 0
                Q = ((((o(r, w) | 0) + (O & 65535)) | 0) + (K & 65535)) | 0
                tt = ((((o(d, w) | 0) + (O >>> 16)) | 0) + (K >>> 16)) | 0
                et = ((((o(r, T) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(d, T) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                O = (et << 16) | (Q & 65535)
                Q = ((((o(r, S) | 0) + (q & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(d, S) | 0) + (q >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(r, I) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(d, I) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                q = (et << 16) | (Q & 65535)
                Q = ((((o(r, C) | 0) + (U & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(d, C) | 0) + (U >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(r, R) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(d, R) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                U = (et << 16) | (Q & 65535)
                Q = ((((o(r, E) | 0) + (j & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(d, E) | 0) + (j >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(r, N) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(d, N) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                j = (et << 16) | (Q & 65535)
                Q = ((((o(r, M) | 0) + (F & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(d, M) | 0) + (F >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(r, D) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(d, D) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                F = (et << 16) | (Q & 65535)
                Q = ((((o(r, k) | 0) + (H & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(d, k) | 0) + (H >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(r, P) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(d, P) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                H = (et << 16) | (Q & 65535)
                Q = ((((o(r, x) | 0) + (z & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(d, x) | 0) + (z >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(r, B) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(d, B) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                z = (et << 16) | (Q & 65535)
                Q = ((((o(r, A) | 0) + (V & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(d, A) | 0) + (V >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(r, L) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(d, L) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                V = (et << 16) | (Q & 65535)
                K = it
                Q = ((((o(s, w) | 0) + (q & 65535)) | 0) + ($ & 65535)) | 0
                tt = ((((o(p, w) | 0) + (q >>> 16)) | 0) + ($ >>> 16)) | 0
                et = ((((o(s, T) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(p, T) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                q = (et << 16) | (Q & 65535)
                Q = ((((o(s, S) | 0) + (U & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(p, S) | 0) + (U >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(s, I) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(p, I) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                U = (et << 16) | (Q & 65535)
                Q = ((((o(s, C) | 0) + (j & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(p, C) | 0) + (j >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(s, R) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(p, R) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                j = (et << 16) | (Q & 65535)
                Q = ((((o(s, E) | 0) + (F & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(p, E) | 0) + (F >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(s, N) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(p, N) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                F = (et << 16) | (Q & 65535)
                Q = ((((o(s, M) | 0) + (H & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(p, M) | 0) + (H >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(s, D) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(p, D) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                H = (et << 16) | (Q & 65535)
                Q = ((((o(s, k) | 0) + (z & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(p, k) | 0) + (z >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(s, P) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(p, P) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                z = (et << 16) | (Q & 65535)
                Q = ((((o(s, x) | 0) + (V & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(p, x) | 0) + (V >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(s, B) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(p, B) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                V = (et << 16) | (Q & 65535)
                Q = ((((o(s, A) | 0) + (K & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(p, A) | 0) + (K >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(s, L) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(p, L) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                K = (et << 16) | (Q & 65535)
                $ = it
                Q = ((((o(a, w) | 0) + (U & 65535)) | 0) + (W & 65535)) | 0
                tt = ((((o(m, w) | 0) + (U >>> 16)) | 0) + (W >>> 16)) | 0
                et = ((((o(a, T) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(m, T) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                U = (et << 16) | (Q & 65535)
                Q = ((((o(a, S) | 0) + (j & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(m, S) | 0) + (j >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(a, I) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(m, I) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                j = (et << 16) | (Q & 65535)
                Q = ((((o(a, C) | 0) + (F & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(m, C) | 0) + (F >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(a, R) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(m, R) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                F = (et << 16) | (Q & 65535)
                Q = ((((o(a, E) | 0) + (H & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(m, E) | 0) + (H >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(a, N) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(m, N) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                H = (et << 16) | (Q & 65535)
                Q = ((((o(a, M) | 0) + (z & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(m, M) | 0) + (z >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(a, D) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(m, D) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                z = (et << 16) | (Q & 65535)
                Q = ((((o(a, k) | 0) + (V & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(m, k) | 0) + (V >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(a, P) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(m, P) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                V = (et << 16) | (Q & 65535)
                Q = ((((o(a, x) | 0) + (K & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(m, x) | 0) + (K >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(a, B) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(m, B) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                K = (et << 16) | (Q & 65535)
                Q = ((((o(a, A) | 0) + ($ & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(m, A) | 0) + ($ >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(a, L) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(m, L) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                $ = (et << 16) | (Q & 65535)
                W = it
                Q = ((((o(u, w) | 0) + (j & 65535)) | 0) + (G & 65535)) | 0
                tt = ((((o(g, w) | 0) + (j >>> 16)) | 0) + (G >>> 16)) | 0
                et = ((((o(u, T) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(g, T) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                j = (et << 16) | (Q & 65535)
                Q = ((((o(u, S) | 0) + (F & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(g, S) | 0) + (F >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(u, I) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(g, I) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                F = (et << 16) | (Q & 65535)
                Q = ((((o(u, C) | 0) + (H & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(g, C) | 0) + (H >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(u, R) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(g, R) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                H = (et << 16) | (Q & 65535)
                Q = ((((o(u, E) | 0) + (z & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(g, E) | 0) + (z >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(u, N) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(g, N) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                z = (et << 16) | (Q & 65535)
                Q = ((((o(u, M) | 0) + (V & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(g, M) | 0) + (V >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(u, D) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(g, D) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                V = (et << 16) | (Q & 65535)
                Q = ((((o(u, k) | 0) + (K & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(g, k) | 0) + (K >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(u, P) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(g, P) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                K = (et << 16) | (Q & 65535)
                Q = ((((o(u, x) | 0) + ($ & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(g, x) | 0) + ($ >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(u, B) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(g, B) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                $ = (et << 16) | (Q & 65535)
                Q = ((((o(u, A) | 0) + (W & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(g, A) | 0) + (W >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(u, L) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(g, L) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                W = (et << 16) | (Q & 65535)
                G = it
                Q = ((((o(c, w) | 0) + (F & 65535)) | 0) + (X & 65535)) | 0
                tt = ((((o(y, w) | 0) + (F >>> 16)) | 0) + (X >>> 16)) | 0
                et = ((((o(c, T) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(y, T) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                F = (et << 16) | (Q & 65535)
                Q = ((((o(c, S) | 0) + (H & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(y, S) | 0) + (H >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(c, I) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(y, I) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                H = (et << 16) | (Q & 65535)
                Q = ((((o(c, C) | 0) + (z & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(y, C) | 0) + (z >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(c, R) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(y, R) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                z = (et << 16) | (Q & 65535)
                Q = ((((o(c, E) | 0) + (V & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(y, E) | 0) + (V >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(c, N) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(y, N) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                V = (et << 16) | (Q & 65535)
                Q = ((((o(c, M) | 0) + (K & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(y, M) | 0) + (K >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(c, D) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(y, D) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                K = (et << 16) | (Q & 65535)
                Q = ((((o(c, k) | 0) + ($ & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(y, k) | 0) + ($ >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(c, P) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(y, P) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                $ = (et << 16) | (Q & 65535)
                Q = ((((o(c, x) | 0) + (W & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(y, x) | 0) + (W >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(c, B) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(y, B) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                W = (et << 16) | (Q & 65535)
                Q = ((((o(c, A) | 0) + (G & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(y, A) | 0) + (G >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(c, L) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(y, L) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                G = (et << 16) | (Q & 65535)
                X = it
                Q = ((((o(l, w) | 0) + (H & 65535)) | 0) + (Y & 65535)) | 0
                tt = ((((o(v, w) | 0) + (H >>> 16)) | 0) + (Y >>> 16)) | 0
                et = ((((o(l, T) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(v, T) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                H = (et << 16) | (Q & 65535)
                Q = ((((o(l, S) | 0) + (z & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(v, S) | 0) + (z >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(l, I) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(v, I) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                z = (et << 16) | (Q & 65535)
                Q = ((((o(l, C) | 0) + (V & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(v, C) | 0) + (V >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(l, R) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(v, R) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                V = (et << 16) | (Q & 65535)
                Q = ((((o(l, E) | 0) + (K & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(v, E) | 0) + (K >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(l, N) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(v, N) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                K = (et << 16) | (Q & 65535)
                Q = ((((o(l, M) | 0) + ($ & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(v, M) | 0) + ($ >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(l, D) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(v, D) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                $ = (et << 16) | (Q & 65535)
                Q = ((((o(l, k) | 0) + (W & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(v, k) | 0) + (W >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(l, P) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(v, P) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                W = (et << 16) | (Q & 65535)
                Q = ((((o(l, x) | 0) + (G & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(v, x) | 0) + (G >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(l, B) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(v, B) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                G = (et << 16) | (Q & 65535)
                Q = ((((o(l, A) | 0) + (X & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(v, A) | 0) + (X >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(l, L) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(v, L) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                X = (et << 16) | (Q & 65535)
                Y = it
                Q = ((((o(h, w) | 0) + (z & 65535)) | 0) + (J & 65535)) | 0
                tt = ((((o(b, w) | 0) + (z >>> 16)) | 0) + (J >>> 16)) | 0
                et = ((((o(h, T) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(b, T) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                z = (et << 16) | (Q & 65535)
                Q = ((((o(h, S) | 0) + (V & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(b, S) | 0) + (V >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(h, I) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(b, I) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                V = (et << 16) | (Q & 65535)
                Q = ((((o(h, C) | 0) + (K & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(b, C) | 0) + (K >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(h, R) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(b, R) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                K = (et << 16) | (Q & 65535)
                Q = ((((o(h, E) | 0) + ($ & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(b, E) | 0) + ($ >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(h, N) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(b, N) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                $ = (et << 16) | (Q & 65535)
                Q = ((((o(h, M) | 0) + (W & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(b, M) | 0) + (W >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(h, D) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(b, D) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                W = (et << 16) | (Q & 65535)
                Q = ((((o(h, k) | 0) + (G & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(b, k) | 0) + (G >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(h, P) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(b, P) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                G = (et << 16) | (Q & 65535)
                Q = ((((o(h, x) | 0) + (X & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(b, x) | 0) + (X >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(h, B) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(b, B) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                X = (et << 16) | (Q & 65535)
                Q = ((((o(h, A) | 0) + (Y & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(b, A) | 0) + (Y >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(h, L) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(b, L) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                Y = (et << 16) | (Q & 65535)
                J = it
                Q = ((((o(f, w) | 0) + (V & 65535)) | 0) + (Z & 65535)) | 0
                tt = ((((o(_, w) | 0) + (V >>> 16)) | 0) + (Z >>> 16)) | 0
                et = ((((o(f, T) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(_, T) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                V = (et << 16) | (Q & 65535)
                Q = ((((o(f, S) | 0) + (K & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(_, S) | 0) + (K >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(f, I) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(_, I) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                K = (et << 16) | (Q & 65535)
                Q = ((((o(f, C) | 0) + ($ & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(_, C) | 0) + ($ >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(f, R) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(_, R) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                $ = (et << 16) | (Q & 65535)
                Q = ((((o(f, E) | 0) + (W & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(_, E) | 0) + (W >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(f, N) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(_, N) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                W = (et << 16) | (Q & 65535)
                Q = ((((o(f, M) | 0) + (G & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(_, M) | 0) + (G >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(f, D) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(_, D) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                G = (et << 16) | (Q & 65535)
                Q = ((((o(f, k) | 0) + (X & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(_, k) | 0) + (X >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(f, P) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(_, P) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                X = (et << 16) | (Q & 65535)
                Q = ((((o(f, x) | 0) + (Y & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(_, x) | 0) + (Y >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(f, B) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(_, B) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                Y = (et << 16) | (Q & 65535)
                Q = ((((o(f, A) | 0) + (J & 65535)) | 0) + (it & 65535)) | 0
                tt = ((((o(_, A) | 0) + (J >>> 16)) | 0) + (it >>> 16)) | 0
                et = ((((o(f, L) | 0) + (tt & 65535)) | 0) + (Q >>> 16)) | 0
                it = ((((o(_, L) | 0) + (tt >>> 16)) | 0) + (et >>> 16)) | 0
                J = (et << 16) | (Q & 65535)
                Z = it
                ht = (st + ((ct + lt) | 0)) | 0
                ot = i[(pt + ht) >> 2] | 0
                Q = ((((ot & 65535) + ((O & 65535) << 1)) | 0) + nt) | 0
                et = ((((ot >>> 16) + ((O >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
                i[(pt + ht) >> 2] = (et << 16) | (Q & 65535)
                nt = et >>> 16
                ht = (ht + 4) | 0
                ot = i[(pt + ht) >> 2] | 0
                Q = ((((ot & 65535) + ((q & 65535) << 1)) | 0) + nt) | 0
                et = ((((ot >>> 16) + ((q >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
                i[(pt + ht) >> 2] = (et << 16) | (Q & 65535)
                nt = et >>> 16
                ht = (ht + 4) | 0
                ot = i[(pt + ht) >> 2] | 0
                Q = ((((ot & 65535) + ((U & 65535) << 1)) | 0) + nt) | 0
                et = ((((ot >>> 16) + ((U >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
                i[(pt + ht) >> 2] = (et << 16) | (Q & 65535)
                nt = et >>> 16
                ht = (ht + 4) | 0
                ot = i[(pt + ht) >> 2] | 0
                Q = ((((ot & 65535) + ((j & 65535) << 1)) | 0) + nt) | 0
                et = ((((ot >>> 16) + ((j >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
                i[(pt + ht) >> 2] = (et << 16) | (Q & 65535)
                nt = et >>> 16
                ht = (ht + 4) | 0
                ot = i[(pt + ht) >> 2] | 0
                Q = ((((ot & 65535) + ((F & 65535) << 1)) | 0) + nt) | 0
                et = ((((ot >>> 16) + ((F >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
                i[(pt + ht) >> 2] = (et << 16) | (Q & 65535)
                nt = et >>> 16
                ht = (ht + 4) | 0
                ot = i[(pt + ht) >> 2] | 0
                Q = ((((ot & 65535) + ((H & 65535) << 1)) | 0) + nt) | 0
                et = ((((ot >>> 16) + ((H >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
                i[(pt + ht) >> 2] = (et << 16) | (Q & 65535)
                nt = et >>> 16
                ht = (ht + 4) | 0
                ot = i[(pt + ht) >> 2] | 0
                Q = ((((ot & 65535) + ((z & 65535) << 1)) | 0) + nt) | 0
                et = ((((ot >>> 16) + ((z >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
                i[(pt + ht) >> 2] = (et << 16) | (Q & 65535)
                nt = et >>> 16
                ht = (ht + 4) | 0
                ot = i[(pt + ht) >> 2] | 0
                Q = ((((ot & 65535) + ((V & 65535) << 1)) | 0) + nt) | 0
                et = ((((ot >>> 16) + ((V >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
                i[(pt + ht) >> 2] = (et << 16) | (Q & 65535)
                nt = et >>> 16
              }
              ht = (st + ((ct + lt) | 0)) | 0
              ot = i[(pt + ht) >> 2] | 0
              Q =
                ((((((ot & 65535) + ((K & 65535) << 1)) | 0) + nt) | 0) + rt) |
                0
              et = ((((ot >>> 16) + ((K >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
              i[(pt + ht) >> 2] = (et << 16) | (Q & 65535)
              nt = et >>> 16
              ht = (ht + 4) | 0
              ot = i[(pt + ht) >> 2] | 0
              Q = ((((ot & 65535) + (($ & 65535) << 1)) | 0) + nt) | 0
              et = ((((ot >>> 16) + (($ >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
              i[(pt + ht) >> 2] = (et << 16) | (Q & 65535)
              nt = et >>> 16
              ht = (ht + 4) | 0
              ot = i[(pt + ht) >> 2] | 0
              Q = ((((ot & 65535) + ((W & 65535) << 1)) | 0) + nt) | 0
              et = ((((ot >>> 16) + ((W >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
              i[(pt + ht) >> 2] = (et << 16) | (Q & 65535)
              nt = et >>> 16
              ht = (ht + 4) | 0
              ot = i[(pt + ht) >> 2] | 0
              Q = ((((ot & 65535) + ((G & 65535) << 1)) | 0) + nt) | 0
              et = ((((ot >>> 16) + ((G >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
              i[(pt + ht) >> 2] = (et << 16) | (Q & 65535)
              nt = et >>> 16
              ht = (ht + 4) | 0
              ot = i[(pt + ht) >> 2] | 0
              Q = ((((ot & 65535) + ((X & 65535) << 1)) | 0) + nt) | 0
              et = ((((ot >>> 16) + ((X >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
              i[(pt + ht) >> 2] = (et << 16) | (Q & 65535)
              nt = et >>> 16
              ht = (ht + 4) | 0
              ot = i[(pt + ht) >> 2] | 0
              Q = ((((ot & 65535) + ((Y & 65535) << 1)) | 0) + nt) | 0
              et = ((((ot >>> 16) + ((Y >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
              i[(pt + ht) >> 2] = (et << 16) | (Q & 65535)
              nt = et >>> 16
              ht = (ht + 4) | 0
              ot = i[(pt + ht) >> 2] | 0
              Q = ((((ot & 65535) + ((J & 65535) << 1)) | 0) + nt) | 0
              et = ((((ot >>> 16) + ((J >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
              i[(pt + ht) >> 2] = (et << 16) | (Q & 65535)
              nt = et >>> 16
              ht = (ht + 4) | 0
              ot = i[(pt + ht) >> 2] | 0
              Q = ((((ot & 65535) + ((Z & 65535) << 1)) | 0) + nt) | 0
              et = ((((ot >>> 16) + ((Z >>> 16) << 1)) | 0) + (Q >>> 16)) | 0
              i[(pt + ht) >> 2] = (et << 16) | (Q & 65535)
              rt = et >>> 16
            }
            for (
              ht = (ht + 4) | 0;
              !!rt & ((ht | 0) < at << 1);
              ht = (ht + 4) | 0
            ) {
              ot = i[(pt + ht) >> 2] | 0
              Q = ((ot & 65535) + rt) | 0
              et = ((ot >>> 16) + (Q >>> 16)) | 0
              i[(pt + ht) >> 2] = (et << 16) | (Q & 65535)
              rt = et >>> 16
            }
          }
        }
      }
      function v(t, e, n, r, s) {
        t = t | 0
        e = e | 0
        n = n | 0
        r = r | 0
        s = s | 0
        var a = 0,
          u = 0,
          c = 0,
          l = 0,
          h = 0,
          f = 0,
          d = 0,
          p = 0,
          m = 0,
          g = 0,
          y = 0,
          v = 0,
          b = 0,
          _ = 0,
          w = 0,
          S = 0,
          C = 0,
          E = 0,
          M = 0
        for (C = (e - 1) & -4; (C | 0) >= 0; C = (C - 4) | 0) {
          a = i[(t + C) >> 2] | 0
          if (a) {
            e = C
            break
          }
        }
        for (C = (r - 1) & -4; (C | 0) >= 0; C = (C - 4) | 0) {
          u = i[(n + C) >> 2] | 0
          if (u) {
            r = C
            break
          }
        }
        while ((u & 2147483648) == 0) {
          u = u << 1
          c = (c + 1) | 0
        }
        h = i[(t + e) >> 2] | 0
        if (c) {
          l = h >>> ((32 - c) | 0)
          for (C = (e - 4) | 0; (C | 0) >= 0; C = (C - 4) | 0) {
            a = i[(t + C) >> 2] | 0
            i[(t + C + 4) >> 2] = (h << c) | (c ? a >>> ((32 - c) | 0) : 0)
            h = a
          }
          i[t >> 2] = h << c
        }
        if (c) {
          f = i[(n + r) >> 2] | 0
          for (C = (r - 4) | 0; (C | 0) >= 0; C = (C - 4) | 0) {
            u = i[(n + C) >> 2] | 0
            i[(n + C + 4) >> 2] = (f << c) | (u >>> ((32 - c) | 0))
            f = u
          }
          i[n >> 2] = f << c
        }
        f = i[(n + r) >> 2] | 0
        ;(d = f >>> 16), (p = f & 65535)
        for (C = e; (C | 0) >= (r | 0); C = (C - 4) | 0) {
          E = (C - r) | 0
          h = i[(t + C) >> 2] | 0
          ;(m = ((l >>> 0) / (d >>> 0)) | 0),
            (y = (l >>> 0) % (d >>> 0) | 0),
            (b = o(m, p) | 0)
          while (
            ((m | 0) == 65536) |
            (b >>> 0 > ((y << 16) | (h >>> 16)) >>> 0)
          ) {
            ;(m = (m - 1) | 0), (y = (y + d) | 0), (b = (b - p) | 0)
            if ((y | 0) >= 65536) break
          }
          ;(w = 0), (S = 0)
          for (M = 0; (M | 0) <= (r | 0); M = (M + 4) | 0) {
            u = i[(n + M) >> 2] | 0
            b = ((o(m, u & 65535) | 0) + (w >>> 16)) | 0
            _ = ((o(m, u >>> 16) | 0) + (b >>> 16)) | 0
            u = (w & 65535) | (b << 16)
            w = _
            a = i[(t + E + M) >> 2] | 0
            b = ((((a & 65535) - (u & 65535)) | 0) + S) | 0
            _ = ((((a >>> 16) - (u >>> 16)) | 0) + (b >> 16)) | 0
            i[(t + E + M) >> 2] = (_ << 16) | (b & 65535)
            S = _ >> 16
          }
          b = ((((l & 65535) - (w & 65535)) | 0) + S) | 0
          _ = ((((l >>> 16) - (w >>> 16)) | 0) + (b >> 16)) | 0
          l = (_ << 16) | (b & 65535)
          S = _ >> 16
          if (S) {
            m = (m - 1) | 0
            S = 0
            for (M = 0; (M | 0) <= (r | 0); M = (M + 4) | 0) {
              u = i[(n + M) >> 2] | 0
              a = i[(t + E + M) >> 2] | 0
              b = ((a & 65535) + S) | 0
              _ = ((a >>> 16) + u + (b >>> 16)) | 0
              i[(t + E + M) >> 2] = (_ << 16) | (b & 65535)
              S = _ >>> 16
            }
            l = (l + S) | 0
          }
          h = i[(t + C) >> 2] | 0
          a = (l << 16) | (h >>> 16)
          ;(g = ((a >>> 0) / (d >>> 0)) | 0),
            (v = (a >>> 0) % (d >>> 0) | 0),
            (b = o(g, p) | 0)
          while (
            ((g | 0) == 65536) |
            (b >>> 0 > ((v << 16) | (h & 65535)) >>> 0)
          ) {
            ;(g = (g - 1) | 0), (v = (v + d) | 0), (b = (b - p) | 0)
            if ((v | 0) >= 65536) break
          }
          ;(w = 0), (S = 0)
          for (M = 0; (M | 0) <= (r | 0); M = (M + 4) | 0) {
            u = i[(n + M) >> 2] | 0
            b = ((o(g, u & 65535) | 0) + (w & 65535)) | 0
            _ = ((((o(g, u >>> 16) | 0) + (b >>> 16)) | 0) + (w >>> 16)) | 0
            u = (b & 65535) | (_ << 16)
            w = _ >>> 16
            a = i[(t + E + M) >> 2] | 0
            b = ((((a & 65535) - (u & 65535)) | 0) + S) | 0
            _ = ((((a >>> 16) - (u >>> 16)) | 0) + (b >> 16)) | 0
            S = _ >> 16
            i[(t + E + M) >> 2] = (_ << 16) | (b & 65535)
          }
          b = ((((l & 65535) - (w & 65535)) | 0) + S) | 0
          _ = ((((l >>> 16) - (w >>> 16)) | 0) + (b >> 16)) | 0
          S = _ >> 16
          if (S) {
            g = (g - 1) | 0
            S = 0
            for (M = 0; (M | 0) <= (r | 0); M = (M + 4) | 0) {
              u = i[(n + M) >> 2] | 0
              a = i[(t + E + M) >> 2] | 0
              b = ((((a & 65535) + (u & 65535)) | 0) + S) | 0
              _ = ((((a >>> 16) + (u >>> 16)) | 0) + (b >>> 16)) | 0
              S = _ >>> 16
              i[(t + E + M) >> 2] = (b & 65535) | (_ << 16)
            }
          }
          i[(s + E) >> 2] = (m << 16) | g
          l = i[(t + C) >> 2] | 0
        }
        if (c) {
          h = i[t >> 2] | 0
          for (C = 4; (C | 0) <= (r | 0); C = (C + 4) | 0) {
            a = i[(t + C) >> 2] | 0
            i[(t + C - 4) >> 2] = (a << ((32 - c) | 0)) | (h >>> c)
            h = a
          }
          i[(t + r) >> 2] = h >>> c
        }
      }
      function b(t, e, n, r, s, h) {
        t = t | 0
        e = e | 0
        n = n | 0
        r = r | 0
        s = s | 0
        h = h | 0
        var d = 0,
          p = 0,
          g = 0,
          y = 0,
          v = 0,
          b = 0,
          _ = 0,
          w = 0,
          S = 0,
          C = 0,
          E = 0,
          M = 0,
          k = 0,
          x = 0
        d = a(r << 1) | 0
        l(r << 1, 0, d)
        c(e, t, d)
        for (M = 0; (M | 0) < (r | 0); M = (M + 4) | 0) {
          ;(g = i[(d + M) >> 2] | 0), (y = g & 65535), (g = g >>> 16)
          ;(b = s >>> 16), (v = s & 65535)
          ;(_ = o(y, v) | 0),
            (w = ((((o(y, b) | 0) + (o(g, v) | 0)) | 0) + (_ >>> 16)) | 0)
          ;(y = _ & 65535), (g = w & 65535)
          E = 0
          for (k = 0; (k | 0) < (r | 0); k = (k + 4) | 0) {
            x = (M + k) | 0
            ;(b = i[(n + k) >> 2] | 0), (v = b & 65535), (b = b >>> 16)
            C = i[(d + x) >> 2] | 0
            _ = ((((o(y, v) | 0) + (E & 65535)) | 0) + (C & 65535)) | 0
            w = ((((o(y, b) | 0) + (E >>> 16)) | 0) + (C >>> 16)) | 0
            S = ((((o(g, v) | 0) + (w & 65535)) | 0) + (_ >>> 16)) | 0
            E = ((((o(g, b) | 0) + (S >>> 16)) | 0) + (w >>> 16)) | 0
            C = (S << 16) | (_ & 65535)
            i[(d + x) >> 2] = C
          }
          x = (M + k) | 0
          C = i[(d + x) >> 2] | 0
          _ = ((((C & 65535) + (E & 65535)) | 0) + p) | 0
          w = ((((C >>> 16) + (E >>> 16)) | 0) + (_ >>> 16)) | 0
          i[(d + x) >> 2] = (w << 16) | (_ & 65535)
          p = w >>> 16
        }
        c(r, (d + r) | 0, h)
        u(r << 1)
        if (p | ((f(n, r, h, r) | 0) <= 0)) {
          m(h, r, n, r, h, r) | 0
        }
      }
      return {
        sreset: s,
        salloc: a,
        sfree: u,
        z: l,
        tst: d,
        neg: h,
        cmp: f,
        add: p,
        sub: m,
        mul: g,
        sqr: y,
        div: v,
        mredc: b,
      }
    }
    function Zt(t) {
      return t instanceof Qt
    }
    function Qt(t) {
      var e = Kn,
        n = 0,
        r = 0
      if ((d(t) && (t = o(t)), p(t) && (t = new Uint8Array(t)), void 0 === t));
      else if (f(t)) {
        var i = Math.abs(t)
        i > 4294967295
          ? (((e = new Uint32Array(2))[0] = 0 | i),
            (e[1] = (i / 4294967296) | 0),
            (n = 52))
          : i > 0
          ? (((e = new Uint32Array(1))[0] = i), (n = 32))
          : ((e = Kn), (n = 0)),
          (r = 0 > t ? -1 : 1)
      } else if (m(t)) {
        if (!(n = 8 * t.length)) return Wn
        e = new Uint32Array((n + 31) >> 5)
        for (var s = t.length - 4; s >= 0; s -= 4)
          e[(t.length - 4 - s) >> 2] =
            (t[s] << 24) | (t[s + 1] << 16) | (t[s + 2] << 8) | t[s + 3]
        ;-3 === s
          ? (e[e.length - 1] = t[0])
          : -2 === s
          ? (e[e.length - 1] = (t[0] << 8) | t[1])
          : -1 === s && (e[e.length - 1] = (t[0] << 16) | (t[1] << 8) | t[2]),
          (r = 1)
      } else {
        if ('object' != typeof t || null === t)
          throw new TypeError('number is of unexpected type')
        ;(e = new Uint32Array(t.limbs)), (n = t.bitLength), (r = t.sign)
      }
      ;(this.limbs = e), (this.bitLength = n), (this.sign = r)
    }
    function te(t) {
      t = t || 16
      var e = this.limbs,
        n = this.bitLength,
        i = ''
      if (16 !== t) throw new r('bad radix')
      for (var o = ((n + 31) >> 5) - 1; o >= 0; o--) {
        var s = e[o].toString(16)
        ;(i += '00000000'.substr(s.length)), (i += s)
      }
      return (
        (i = i.replace(/^0+/, '')).length || (i = '0'),
        this.sign < 0 && (i = '-' + i),
        i
      )
    }
    function ee() {
      var t = this.bitLength,
        e = this.limbs
      if (0 === t) return new Uint8Array(0)
      for (var n = (t + 7) >> 3, r = new Uint8Array(n), i = 0; n > i; i++) {
        var o = n - i - 1
        r[i] = e[o >> 2] >> ((3 & o) << 3)
      }
      return r
    }
    function ne() {
      var t = this.limbs,
        e = this.bitLength,
        n = this.sign
      if (!n) return 0
      if (32 >= e) return n * (t[0] >>> 0)
      if (52 >= e) return n * (4294967296 * (t[1] >>> 0) + (t[0] >>> 0))
      var r,
        i,
        o = 0
      for (r = t.length - 1; r >= 0; r--)
        if (0 !== (i = t[r])) {
          for (; 0 == ((i << o) & 2147483648); ) o++
          break
        }
      return 0 === r
        ? n * (t[0] >>> 0)
        : n *
            (1048576 * (((t[r] << o) | (o ? t[r - 1] >>> (32 - o) : 0)) >>> 0) +
              (((t[r - 1] << o) | (o && r > 1 ? t[r - 2] >>> (32 - o) : 0)) >>>
                12)) *
            Math.pow(2, 32 * r - o - 52)
    }
    function re(t) {
      var e = this.limbs
      if (t >= this.bitLength) return this
      var n = new Qt(),
        r = (t + 31) >> 5,
        i = t % 32
      return (
        (n.limbs = new Uint32Array(e.subarray(0, r))),
        (n.bitLength = t),
        (n.sign = this.sign),
        i && (n.limbs[r - 1] &= -1 >>> (32 - i)),
        n
      )
    }
    function ie(t, e) {
      if (!f(t)) throw new TypeError('TODO')
      if (void 0 !== e && !f(e)) throw new TypeError('TODO')
      var n = this.limbs,
        r = this.bitLength
      if (0 > t) throw new RangeError('TODO')
      if (t >= r) return Wn
      ;(void 0 === e || e > r - t) && (e = r - t)
      var i,
        o = new Qt(),
        s = t >> 5,
        a = (t + e + 31) >> 5,
        u = (e + 31) >> 5,
        c = t % 32,
        l = e % 32
      if (((i = new Uint32Array(u)), c)) {
        for (var h = 0; a - s - 1 > h; h++)
          i[h] = (n[s + h] >>> c) | (n[s + h + 1] << (32 - c))
        i[h] = n[s + h] >>> c
      } else i.set(n.subarray(s, a))
      return (
        l && (i[u - 1] &= -1 >>> (32 - l)),
        (o.limbs = i),
        (o.bitLength = e),
        (o.sign = this.sign),
        o
      )
    }
    function oe() {
      var t = new Qt()
      return (
        (t.limbs = this.limbs),
        (t.bitLength = this.bitLength),
        (t.sign = -1 * this.sign),
        t
      )
    }
    function se(t) {
      Zt(t) || (t = new Qt(t))
      var e = this.limbs,
        n = e.length,
        r = t.limbs,
        i = r.length
      return this.sign < t.sign
        ? -1
        : this.sign > t.sign
        ? 1
        : (Vn.set(e, 0),
          Vn.set(r, n),
          Jt.cmp(0, n << 2, n << 2, i << 2) * this.sign)
    }
    function ae(t) {
      if ((Zt(t) || (t = new Qt(t)), !this.sign)) return t
      if (!t.sign) return this
      var e,
        n,
        r,
        i,
        o = this.bitLength,
        s = this.limbs,
        a = s.length,
        u = this.sign,
        c = t.bitLength,
        l = t.limbs,
        h = l.length,
        f = t.sign,
        d = new Qt()
      ;(n = ((e = (o > c ? o : c) + (u * f > 0 ? 1 : 0)) + 31) >> 5),
        Jt.sreset()
      var p = Jt.salloc(a << 2),
        m = Jt.salloc(h << 2),
        g = Jt.salloc(n << 2)
      return (
        Jt.z(g - p + (n << 2), 0, p),
        Vn.set(s, p >> 2),
        Vn.set(l, m >> 2),
        u * f > 0
          ? (Jt.add(p, a << 2, m, h << 2, g, n << 2), (r = u))
          : u > f
          ? (r = (i = Jt.sub(p, a << 2, m, h << 2, g, n << 2)) ? f : u)
          : (r = (i = Jt.sub(m, h << 2, p, a << 2, g, n << 2)) ? u : f),
        i && Jt.neg(g, n << 2, g, n << 2),
        0 === Jt.tst(g, n << 2)
          ? Wn
          : ((d.limbs = new Uint32Array(Vn.subarray(g >> 2, (g >> 2) + n))),
            (d.bitLength = e),
            (d.sign = r),
            d)
      )
    }
    function ue(t) {
      return Zt(t) || (t = new Qt(t)), this.add(t.negate())
    }
    function ce(t) {
      if ((Zt(t) || (t = new Qt(t)), !this.sign || !t.sign)) return Wn
      var e,
        n,
        r = this.bitLength,
        i = this.limbs,
        o = i.length,
        s = t.bitLength,
        a = t.limbs,
        u = a.length,
        c = new Qt()
      ;(n = ((e = r + s) + 31) >> 5), Jt.sreset()
      var l = Jt.salloc(o << 2),
        h = Jt.salloc(u << 2),
        f = Jt.salloc(n << 2)
      return (
        Jt.z(f - l + (n << 2), 0, l),
        Vn.set(i, l >> 2),
        Vn.set(a, h >> 2),
        Jt.mul(l, o << 2, h, u << 2, f, n << 2),
        (c.limbs = new Uint32Array(Vn.subarray(f >> 2, (f >> 2) + n))),
        (c.sign = this.sign * t.sign),
        (c.bitLength = e),
        c
      )
    }
    function le() {
      if (!this.sign) return Wn
      var t,
        e,
        n = this.bitLength,
        r = this.limbs,
        i = r.length,
        o = new Qt()
      ;(e = ((t = n << 1) + 31) >> 5), Jt.sreset()
      var s = Jt.salloc(i << 2),
        a = Jt.salloc(e << 2)
      return (
        Jt.z(a - s + (e << 2), 0, s),
        Vn.set(r, s >> 2),
        Jt.sqr(s, i << 2, a),
        (o.limbs = new Uint32Array(Vn.subarray(a >> 2, (a >> 2) + e))),
        (o.bitLength = t),
        (o.sign = 1),
        o
      )
    }
    function he(t) {
      Zt(t) || (t = new Qt(t))
      var e,
        n,
        r = this.bitLength,
        i = this.limbs,
        o = i.length,
        s = t.bitLength,
        a = t.limbs,
        u = a.length,
        c = Wn,
        l = Wn
      Jt.sreset()
      var h = Jt.salloc(o << 2),
        f = Jt.salloc(u << 2),
        d = Jt.salloc(o << 2)
      return (
        Jt.z(d - h + (o << 2), 0, h),
        Vn.set(i, h >> 2),
        Vn.set(a, f >> 2),
        Jt.div(h, o << 2, f, u << 2, d),
        (e = Jt.tst(d, o << 2) >> 2) &&
          (((c = new Qt()).limbs = new Uint32Array(
            Vn.subarray(d >> 2, (d >> 2) + e)
          )),
          (c.bitLength = e << 5 > r ? r : e << 5),
          (c.sign = this.sign * t.sign)),
        (n = Jt.tst(h, u << 2) >> 2) &&
          (((l = new Qt()).limbs = new Uint32Array(
            Vn.subarray(h >> 2, (h >> 2) + n)
          )),
          (l.bitLength = n << 5 > s ? s : n << 5),
          (l.sign = this.sign)),
        {
          quotient: c,
          remainder: l,
        }
      )
    }
    function fe(t, e) {
      var n,
        r,
        i,
        o,
        s = 0 > t ? -1 : 1,
        a = 0 > e ? -1 : 1,
        u = 1,
        c = 0,
        l = 0,
        h = 1
      for (
        (o = (e *= a) > (t *= s)) &&
          ((i = t), (t = e), (e = i), (i = s), (s = a), (a = i)),
          n = t - (r = Math.floor(t / e)) * e;
        n;

      )
        (i = u - r * c),
          (u = c),
          (c = i),
          (i = l - r * h),
          (l = h),
          (h = i),
          (t = e),
          (e = n),
          (n = t - (r = Math.floor(t / e)) * e)
      return (
        (c *= s),
        (h *= a),
        o && ((i = c), (c = h), (h = i)),
        {
          gcd: e,
          x: c,
          y: h,
        }
      )
    }
    function de(t, e) {
      Zt(t) || (t = new Qt(t)), Zt(e) || (e = new Qt(e))
      var n = t.sign,
        r = e.sign
      0 > n && (t = t.negate()), 0 > r && (e = e.negate())
      var i = t.compare(e)
      if (0 > i) {
        var o = t
        ;(t = e), (e = o), (o = n), (n = r), (r = o)
      }
      var s,
        a,
        u,
        c = Gn,
        l = Wn,
        h = e.bitLength,
        f = Wn,
        d = Gn,
        p = t.bitLength
      for (s = t.divide(e); (a = s.remainder) !== Wn; )
        (u = s.quotient),
          (s = c.subtract(u.multiply(l).clamp(h)).clamp(h)),
          (c = l),
          (l = s),
          (s = f.subtract(u.multiply(d).clamp(p)).clamp(p)),
          (f = d),
          (d = s),
          (t = e),
          (e = a),
          (s = t.divide(e))
      if ((0 > n && (l = l.negate()), 0 > r && (d = d.negate()), 0 > i)) {
        o = l
        ;(l = d), (d = o)
      }
      return {
        gcd: e,
        x: l,
        y: d,
      }
    }
    function pe() {
      if ((Qt.apply(this, arguments), this.valueOf() < 1))
        throw new RangeError()
      var t
      if (!(this.bitLength <= 32) && 1 & this.limbs[0]) {
        var e = 1 + ((this.bitLength + 31) & -32),
          n = new Uint32Array((e + 31) >> 5)
        ;(n[n.length - 1] = 1),
          ((t = new Qt()).sign = 1),
          (t.bitLength = e),
          (t.limbs = n)
        var r = fe(4294967296, this.limbs[0]).y
        ;(this.coefficient = 0 > r ? -r : 4294967296 - r),
          (this.comodulus = t),
          (this.comodulusRemainder = t.divide(this).remainder),
          (this.comodulusRemainderSquare = t.square().divide(this).remainder)
      }
    }
    function me(t) {
      return (
        Zt(t) || (t = new Qt(t)),
        t.bitLength <= 32 && this.bitLength <= 32
          ? new Qt(t.valueOf() % this.valueOf())
          : t.compare(this) < 0
          ? t
          : t.divide(this).remainder
      )
    }
    function ge(t) {
      var e = de(this, (t = this.reduce(t)))
      return 1 !== e.gcd.valueOf()
        ? null
        : ((e = e.y).sign < 0 && (e = e.add(this).clamp(this.bitLength)), e)
    }
    function ye(t, e) {
      Zt(t) || (t = new Qt(t)), Zt(e) || (e = new Qt(e))
      for (var n = 0, r = 0; r < e.limbs.length; r++)
        for (var i = e.limbs[r]; i; ) 1 & i && n++, (i >>>= 1)
      var o = 8
      e.bitLength <= 4536 && (o = 7),
        e.bitLength <= 1736 && (o = 6),
        e.bitLength <= 630 && (o = 5),
        e.bitLength <= 210 && (o = 4),
        e.bitLength <= 60 && (o = 3),
        e.bitLength <= 12 && (o = 2),
        1 << (o - 1) >= n && (o = 1)
      var s = ve(
          (t = ve(
            this.reduce(t).multiply(this.comodulusRemainderSquare),
            this
          )).square(),
          this
        ),
        a = new Array(1 << (o - 1))
      ;(a[0] = t), (a[1] = ve(t.multiply(s), this))
      for (r = 2; 1 << (o - 1) > r; r++) a[r] = ve(a[r - 1].multiply(s), this)
      var u = this.comodulusRemainder,
        c = u
      for (r = e.limbs.length - 1; r >= 0; r--) {
        i = e.limbs[r]
        for (var l = 32; l > 0; )
          if (2147483648 & i) {
            for (var h = i >>> (32 - o), f = o; 0 == (1 & h); ) (h >>>= 1), f--
            for (var d = a[h >>> 1]; h; )
              (h >>>= 1), c !== u && (c = ve(c.square(), this))
            ;(c = c !== u ? ve(c.multiply(d), this) : d), (i <<= f), (l -= f)
          } else c !== u && (c = ve(c.square(), this)), (i <<= 1), l--
      }
      return ve(c, this)
    }
    function ve(t, e) {
      var n = t.limbs,
        r = n.length,
        i = e.limbs,
        o = i.length,
        s = e.coefficient
      Jt.sreset()
      var a = Jt.salloc(r << 2),
        u = Jt.salloc(o << 2),
        c = Jt.salloc(o << 2)
      Jt.z(c - a + (o << 2), 0, a),
        Vn.set(n, a >> 2),
        Vn.set(i, u >> 2),
        Jt.mredc(a, r << 2, u, o << 2, s, c)
      var l = new Qt()
      return (
        (l.limbs = new Uint32Array(Vn.subarray(c >> 2, (c >> 2) + o))),
        (l.bitLength = e.bitLength),
        (l.sign = 1),
        l
      )
    }
    function be(t) {
      var e = new Qt(this),
        n = 0
      for (e.limbs[0] -= 1; 0 === e.limbs[n >> 5]; ) n += 32
      for (; 0 == ((e.limbs[n >> 5] >> (31 & n)) & 1); ) n++
      e = e.slice(n)
      for (
        var r = new pe(this),
          i = this.subtract(Gn),
          o = new Qt(this),
          s = this.limbs.length - 1;
        0 === o.limbs[s];

      )
        s--
      for (; --t >= 0; ) {
        for (
          Gt(o.limbs), o.limbs[0] < 2 && (o.limbs[0] += 2);
          o.compare(i) >= 0;

        )
          o.limbs[s] >>>= 1
        var a = r.power(o, e)
        if (0 !== a.compare(Gn) && 0 !== a.compare(i)) {
          for (var u = n; --u > 0; ) {
            if (0 === (a = a.square().divide(r).remainder).compare(Gn))
              return !1
            if (0 === a.compare(i)) break
          }
          if (0 === u) return !1
        }
      }
      return !0
    }
    function _e(t) {
      t = t || 80
      var e = this.limbs,
        n = 0
      if (0 == (1 & e[0])) return !1
      if (1 >= t) return !0
      var r = 0,
        i = 0,
        o = 0
      for (n = 0; n < e.length; n++) {
        for (var s = e[n]; s; ) (r += 3 & s), (s >>>= 2)
        for (var a = e[n]; a; ) (i += 3 & a), (i -= 3 & (a >>>= 2)), (a >>>= 2)
        for (var u = e[n]; u; )
          (o += 15 & u), (o -= 15 & (u >>>= 4)), (u >>>= 4)
      }
      return !!(r % 3 && i % 5 && o % 17) && (2 >= t || be.call(this, t >>> 1))
    }
    function we(t) {
      if (Yn.length >= t) return Yn.slice(0, t)
      for (var e = Yn[Yn.length - 1] + 2; Yn.length < t; e += 2) {
        for (var n = 0, r = Yn[n]; e >= r * r && e % r != 0; r = Yn[++n]);
        r * r > e && Yn.push(e)
      }
      return Yn
    }
    function Se(t, n) {
      var r = (t + 31) >> 5,
        i = new Qt({
          sign: 1,
          bitLength: t,
          limbs: r,
        }),
        o = i.limbs,
        s = 1e4
      512 >= t && (s = 2200), 256 >= t && (s = 600)
      var a = we(s),
        u = new Uint32Array(s),
        c = (t * e.Math.LN2) | 0,
        l = 27
      for (
        t >= 250 && (l = 12),
          t >= 450 && (l = 6),
          t >= 850 && (l = 3),
          t >= 1300 && (l = 2);
        ;

      ) {
        Gt(o),
          (o[0] |= 1),
          (o[r - 1] |= 1 << ((t - 1) & 31)),
          31 & t && (o[r - 1] &= h((t + 1) & 31) - 1),
          (u[0] = 1)
        for (var f = 1; s > f; f++) u[f] = i.divide(a[f]).remainder.valueOf()
        t: for (var d = 0; c > d; d += 2, o[0] += 2) {
          for (f = 1; s > f; f++) if ((u[f] + d) % a[f] == 0) continue t
          if (('function' != typeof n || n(i)) && be.call(i, l)) return i
        }
      }
    }
    function Ce(t) {
      ;(t = t || {}), (this.key = null), (this.result = null), this.reset(t)
    }
    function Ee(t) {
      ;(t = t || {}), (this.result = null)
      var e = t.key
      if (void 0 !== e) {
        if (!(e instanceof Array)) throw new TypeError('unexpected key type')
        var n = e.length
        if (2 !== n && 3 !== n && 8 !== n)
          throw new SyntaxError('unexpected key type')
        var r = []
        ;(r[0] = new pe(e[0])),
          (r[1] = new Qt(e[1])),
          n > 2 && (r[2] = new Qt(e[2])),
          n > 3 &&
            ((r[3] = new pe(e[3])),
            (r[4] = new pe(e[4])),
            (r[5] = new Qt(e[5])),
            (r[6] = new Qt(e[6])),
            (r[7] = new Qt(e[7]))),
          (this.key = r)
      }
      return this
    }
    function Me(t) {
      if (!this.key) throw new n('no key is associated with the instance')
      var e
      if ((d(t) && (t = o(t)), p(t) && (t = new Uint8Array(t)), m(t)))
        e = new Qt(t)
      else {
        if (!Zt(t)) throw new TypeError('unexpected data type')
        e = t
      }
      if (this.key[0].compare(e) <= 0) throw new RangeError('data too large')
      var r = this.key[0],
        i = this.key[1],
        s = r.power(e, i).toBytes(),
        a = (r.bitLength + 7) >> 3
      if (s.length < a) {
        var u = new Uint8Array(a)
        u.set(s, a - s.length), (s = u)
      }
      return (this.result = s), this
    }
    function ke(t) {
      if (!this.key) throw new n('no key is associated with the instance')
      if (this.key.length < 3) throw new n("key isn't suitable for decription")
      var e, r
      if ((d(t) && (t = o(t)), p(t) && (t = new Uint8Array(t)), m(t)))
        e = new Qt(t)
      else {
        if (!Zt(t)) throw new TypeError('unexpected data type')
        e = t
      }
      if (this.key[0].compare(e) <= 0) throw new RangeError('data too large')
      if (this.key.length > 3) {
        for (
          var i = this.key[0],
            s = this.key[3],
            a = this.key[4],
            u = this.key[5],
            c = this.key[6],
            l = this.key[7],
            h = s.power(e, u),
            f = a.power(e, c),
            g = h.subtract(f);
          g.sign < 0;

        )
          g = g.add(s)
        r = s
          .reduce(l.multiply(g))
          .multiply(a)
          .add(f)
          .clamp(i.bitLength)
          .toBytes()
      } else {
        i = this.key[0]
        var y = this.key[2]
        r = i.power(e, y).toBytes()
      }
      var v = (i.bitLength + 7) >> 3
      if (r.length < v) {
        var b = new Uint8Array(v)
        b.set(r, v - r.length), (r = b)
      }
      return (this.result = r), this
    }
    function xe(t, e) {
      if (((e = e || 65537), 512 > (t = t || 2048)))
        throw new r('bit length is too small')
      if (
        (d(e) && (e = o(e)),
        p(e) && (e = new Uint8Array(e)),
        !(m(e) || f(e) || Zt(e)))
      )
        throw new TypeError('unexpected exponent type')
      if (0 == (1 & (e = new Qt(e)).limbs[0]))
        throw new r('exponent must be an odd number')
      var n, i, s, a, u, c, l, h
      ;(s = Se(t >> 1, function (t) {
        return ((u = new Qt(t)).limbs[0] -= 1), 1 == de(u, e).gcd.valueOf()
      })),
        (a = Se(t - (t >> 1), function (r) {
          return (
            !!(
              (n = new pe(s.multiply(r))).limbs[((t + 31) >> 5) - 1] >>>
              ((t - 1) & 31)
            ) && (((c = new Qt(r)).limbs[0] -= 1), 1 == de(c, e).gcd.valueOf())
          )
        })),
        (l = (i = new pe(u.multiply(c)).inverse(e)).divide(u).remainder),
        (h = i.divide(c).remainder),
        (s = new pe(s)),
        (a = new pe(a))
      var g = s.inverse(a)
      return [n, e, i, s, a, l, h, g]
    }
    function Ae(t) {
      if (!(t = t || {}).hash)
        throw new SyntaxError("option 'hash' is required")
      if (!t.hash.HASH_SIZE)
        throw new SyntaxError(
          "option 'hash' supplied doesn't seem to be a valid hash function"
        )
      ;(this.hash = t.hash), (this.label = null), this.reset(t)
    }
    function Te(t) {
      var e = (t = t || {}).label
      if (void 0 !== e) {
        if (p(e) || m(e)) e = new Uint8Array(e)
        else {
          if (!d(e)) throw new TypeError('unexpected label type')
          e = o(e)
        }
        this.label = e.length > 0 ? e : null
      } else this.label = null
      Ee.call(this, t)
    }
    function Ie(t) {
      if (!this.key) throw new n('no key is associated with the instance')
      var e = Math.ceil(this.key[0].bitLength / 8),
        i = this.hash.HASH_SIZE,
        s = t.byteLength || t.length || 0,
        a = e - s - 2 * i - 2
      if (s > e - 2 * this.hash.HASH_SIZE - 2) throw new r('data too large')
      var u = new Uint8Array(e),
        c = u.subarray(1, i + 1),
        l = u.subarray(i + 1)
      if (m(t)) l.set(t, i + a + 1)
      else if (p(t)) l.set(new Uint8Array(t), i + a + 1)
      else {
        if (!d(t)) throw new TypeError('unexpected data type')
        l.set(o(t), i + a + 1)
      }
      l.set(
        this.hash
          .reset()
          .process(this.label || '')
          .finish().result,
        0
      ),
        (l[i + a] = 1),
        Gt(c)
      for (var h = Ne.call(this, c, l.length), f = 0; f < l.length; f++)
        l[f] ^= h[f]
      var g = Ne.call(this, l, c.length)
      for (f = 0; f < c.length; f++) c[f] ^= g[f]
      return Me.call(this, u), this
    }
    function Re(t) {
      if (!this.key) throw new n('no key is associated with the instance')
      var e = Math.ceil(this.key[0].bitLength / 8),
        o = this.hash.HASH_SIZE
      if ((t.byteLength || t.length || 0) !== e) throw new r('bad data')
      ke.call(this, t)
      var s = this.result[0],
        a = this.result.subarray(1, o + 1),
        u = this.result.subarray(o + 1)
      if (0 !== s) throw new i('decryption failed')
      for (var c = Ne.call(this, u, a.length), l = 0; l < a.length; l++)
        a[l] ^= c[l]
      var h = Ne.call(this, a, u.length)
      for (l = 0; l < u.length; l++) u[l] ^= h[l]
      var f = this.hash
        .reset()
        .process(this.label || '')
        .finish().result
      for (l = 0; o > l; l++)
        if (f[l] !== u[l]) throw new i('decryption failed')
      for (var d = o; d < u.length; d++) {
        var p = u[d]
        if (1 === p) break
        if (0 !== p) throw new i('decryption failed')
      }
      if (d === u.length) throw new i('decryption failed')
      return (this.result = u.subarray(d + 1)), this
    }
    function Ne(t, e) {
      ;(t = t || ''), (e = e || 0)
      for (
        var n = this.hash.HASH_SIZE,
          r = new Uint8Array(e),
          i = new Uint8Array(4),
          o = Math.ceil(e / n),
          s = 0;
        o > s;
        s++
      ) {
        ;(i[0] = s >>> 24),
          (i[1] = (s >>> 16) & 255),
          (i[2] = (s >>> 8) & 255),
          (i[3] = 255 & s)
        var a = r.subarray(s * n),
          u = this.hash.reset().process(t).process(i).finish().result
        u.length > a.length && (u = u.subarray(0, a.length)), a.set(u)
      }
      return r
    }
    function De(t) {
      if (!(t = t || {}).hash)
        throw new SyntaxError("option 'hash' is required")
      if (!t.hash.HASH_SIZE)
        throw new SyntaxError(
          "option 'hash' supplied doesn't seem to be a valid hash function"
        )
      ;(this.hash = t.hash), (this.saltLength = 4), this.reset(t)
    }
    function Pe(t) {
      ;(t = t || {}), Ee.call(this, t)
      var e = t.saltLength
      if (void 0 !== e) {
        if (!f(e) || 0 > e)
          throw new TypeError('saltLength should be a non-negative number')
        if (
          null !== this.key &&
          Math.ceil((this.key[0].bitLength - 1) / 8) <
            this.hash.HASH_SIZE + e + 2
        )
          throw new SyntaxError('saltLength is too large')
        this.saltLength = e
      } else this.saltLength = 4
    }
    function Be(t) {
      if (!this.key) throw new n('no key is associated with the instance')
      var e = this.key[0].bitLength,
        r = this.hash.HASH_SIZE,
        i = Math.ceil((e - 1) / 8),
        o = this.saltLength,
        s = i - o - r - 2,
        a = new Uint8Array(i),
        u = a.subarray(i - r - 1, i - 1),
        c = a.subarray(0, i - r - 1),
        l = c.subarray(s + 1),
        h = new Uint8Array(8 + r + o),
        f = h.subarray(8, 8 + r),
        d = h.subarray(8 + r)
      f.set(this.hash.reset().process(t).finish().result),
        o > 0 && Gt(d),
        (c[s] = 1),
        l.set(d),
        u.set(this.hash.reset().process(h).finish().result)
      for (var p = Ne.call(this, u, c.length), m = 0; m < c.length; m++)
        c[m] ^= p[m]
      a[i - 1] = 188
      var g = 8 * i - e + 1
      return g % 8 && (a[0] &= 255 >>> g), ke.call(this, a), this
    }
    function Le(t, e) {
      if (!this.key) throw new n('no key is associated with the instance')
      var r = this.key[0].bitLength,
        o = this.hash.HASH_SIZE,
        s = Math.ceil((r - 1) / 8),
        a = this.saltLength,
        u = s - a - o - 2
      Me.call(this, t)
      var c = this.result
      if (188 !== c[s - 1]) throw new i('bad signature')
      var l = c.subarray(s - o - 1, s - 1),
        h = c.subarray(0, s - o - 1),
        f = h.subarray(u + 1),
        d = 8 * s - r + 1
      if (d % 8 && c[0] >>> (8 - d)) throw new i('bad signature')
      for (var p = Ne.call(this, l, h.length), m = 0; m < h.length; m++)
        h[m] ^= p[m]
      d % 8 && (c[0] &= 255 >>> d)
      for (m = 0; u > m; m++) if (0 !== h[m]) throw new i('bad signature')
      if (1 !== h[u]) throw new i('bad signature')
      var g = new Uint8Array(8 + o + a),
        y = g.subarray(8, 8 + o),
        v = g.subarray(8 + o)
      y.set(this.hash.reset().process(e).finish().result), v.set(f)
      var b = this.hash.reset().process(g).finish().result
      for (m = 0; o > m; m++) if (l[m] !== b[m]) throw new i('bad signature')
      return this
    }
    function Oe(t, e) {
      if (void 0 === t) throw new SyntaxError('bitlen required')
      if (void 0 === e) throw new SyntaxError('e required')
      for (var n = xe(t, e), r = 0; r < n.length; r++)
        Zt(n[r]) && (n[r] = n[r].toBytes())
      return n
    }
    function qe(t, e, n) {
      if (void 0 === t) throw new SyntaxError('data required')
      if (void 0 === e) throw new SyntaxError('key required')
      return new Ae({
        hash: et(),
        key: e,
        label: n,
      }).encrypt(t).result
    }
    function Ue(t, e, n) {
      if (void 0 === t) throw new SyntaxError('data required')
      if (void 0 === e) throw new SyntaxError('key required')
      return new Ae({
        hash: et(),
        key: e,
        label: n,
      }).decrypt(t).result
    }
    function je(t, e, n) {
      if (void 0 === t) throw new SyntaxError('data required')
      if (void 0 === e) throw new SyntaxError('key required')
      return new Ae({
        hash: at(),
        key: e,
        label: n,
      }).encrypt(t).result
    }
    function Fe(t, e, n) {
      if (void 0 === t) throw new SyntaxError('data required')
      if (void 0 === e) throw new SyntaxError('key required')
      return new Ae({
        hash: at(),
        key: e,
        label: n,
      }).decrypt(t).result
    }
    function He(t, e, n) {
      if (void 0 === t) throw new SyntaxError('data required')
      if (void 0 === e) throw new SyntaxError('key required')
      return new De({
        hash: et(),
        key: e,
        saltLength: n,
      }).sign(t).result
    }
    function ze(t, e, n, r) {
      if (void 0 === t) throw new SyntaxError('signature required')
      if (void 0 === e) throw new SyntaxError('data required')
      if (void 0 === n) throw new SyntaxError('key required')
      try {
        return (
          new De({
            hash: et(),
            key: n,
            saltLength: r,
          }).verify(t, e),
          !0
        )
      } catch (t) {
        if (!(t instanceof i)) throw t
      }
      return !1
    }
    function Ve(t, e, n) {
      if (void 0 === t) throw new SyntaxError('data required')
      if (void 0 === e) throw new SyntaxError('key required')
      return new De({
        hash: at(),
        key: e,
        saltLength: n,
      }).sign(t).result
    }
    function Ke(t, e, n, r) {
      if (void 0 === t) throw new SyntaxError('signature required')
      if (void 0 === e) throw new SyntaxError('data required')
      if (void 0 === n) throw new SyntaxError('key required')
      try {
        return (
          new De({
            hash: at(),
            key: n,
            saltLength: r,
          }).verify(t, e),
          !0
        )
      } catch (t) {
        if (!(t instanceof i)) throw t
      }
      return !1
    }
    ;(n.prototype = Object.create(Error.prototype, {
      name: {
        value: 'IllegalStateError',
      },
    })),
      (r.prototype = Object.create(Error.prototype, {
        name: {
          value: 'IllegalArgumentError',
        },
      })),
      (i.prototype = Object.create(Error.prototype, {
        name: {
          value: 'SecurityError',
        },
      }))
    var $e = e.Float64Array || e.Float32Array,
      We = e.console
    !e.location.protocol.search(/https:|file:|chrome:|chrome-extension:/) ||
      void 0 === We ||
      We.warn(
        'asmCrypto seems to be load from an insecure origin; this may cause to MitM-attack vulnerability. Consider using secure transport protocol.'
      ),
      (t.string_to_bytes = o),
      (t.hex_to_bytes = s),
      (t.base64_to_bytes = a),
      (t.bytes_to_string = u),
      (t.bytes_to_hex = c),
      (t.bytes_to_base64 = l),
      (e.IllegalStateError = n),
      (e.IllegalArgumentError = r),
      (e.SecurityError = i)
    var Ge = (function () {
        'use strict'
        function t() {
          ;(i = []), (o = [])
          var t,
            e,
            n = 1
          for (t = 0; 255 > t; t++)
            (i[t] = n),
              (e = 128 & n),
              (n <<= 1),
              (n &= 255),
              128 === e && (n ^= 27),
              (n ^= i[t]),
              (o[i[t]] = t)
          ;(i[255] = i[0]), (o[0] = 0), (l = !0)
        }
        function e(t, e) {
          var n = i[(o[t] + o[e]) % 255]
          return (0 === t || 0 === e) && (n = 0), n
        }
        function n(t) {
          var e = i[255 - o[t]]
          return 0 === t && (e = 0), e
        }
        function r() {
          function r(t) {
            var e, r, i
            for (r = i = n(t), e = 0; 4 > e; e++)
              i ^= r = 255 & ((r << 1) | (r >>> 7))
            return 99 ^ i
          }
          l || t(),
            (s = []),
            (a = []),
            (u = [[], [], [], []]),
            (c = [[], [], [], []])
          for (var i = 0; 256 > i; i++) {
            var o = r(i)
            ;(s[i] = o),
              (a[o] = i),
              (u[0][i] = (e(2, o) << 24) | (o << 16) | (o << 8) | e(3, o)),
              (c[0][o] =
                (e(14, i) << 24) | (e(9, i) << 16) | (e(13, i) << 8) | e(11, i))
            for (var h = 1; 4 > h; h++)
              (u[h][i] = (u[h - 1][i] >>> 8) | (u[h - 1][i] << 24)),
                (c[h][o] = (c[h - 1][o] >>> 8) | (c[h - 1][o] << 24))
          }
        }
        var i,
          o,
          s,
          a,
          u,
          c,
          l = !1,
          h = !1,
          f = function (t, e, n) {
            function i(t, e, n, r, i, a, u, l, h) {
              var d = o.subarray(0, 60),
                p = o.subarray(256, 316)
              d.set([e, n, r, i, a, u, l, h])
              for (var m = t, g = 1; 4 * t + 28 > m; m++) {
                var y = d[m - 1]
                ;(m % t == 0 || (8 === t && m % t == 4)) &&
                  (y =
                    (s[y >>> 24] << 24) ^
                    (s[(y >>> 16) & 255] << 16) ^
                    (s[(y >>> 8) & 255] << 8) ^
                    s[255 & y]),
                  m % t == 0 &&
                    ((y = (y << 8) ^ (y >>> 24) ^ (g << 24)),
                    (g = (g << 1) ^ (128 & g ? 27 : 0))),
                  (d[m] = d[m - t] ^ y)
              }
              for (var v = 0; m > v; v += 4)
                for (var b = 0; 4 > b; b++) {
                  y = d[m - (4 + v) + ((4 - b) % 4)]
                  p[v + b] =
                    4 > v || v >= m - 4
                      ? y
                      : c[0][s[y >>> 24]] ^
                        c[1][s[(y >>> 16) & 255]] ^
                        c[2][s[(y >>> 8) & 255]] ^
                        c[3][s[255 & y]]
                }
              f.set_rounds(t + 5)
            }
            h || r()
            var o = new Uint32Array(n)
            o.set(s, 512), o.set(a, 768)
            for (var l = 0; 4 > l; l++)
              o.set(u[l], (4096 + 1024 * l) >> 2),
                o.set(c[l], (8192 + 1024 * l) >> 2)
            var f = (function (t, e, n) {
              'use asm'
              var r = 0,
                i = 0,
                o = 0,
                s = 0,
                a = 0,
                u = 0,
                c = 0,
                l = 0,
                h = 0,
                f = 0,
                d = 0,
                p = 0,
                m = 0,
                g = 0,
                y = 0,
                v = 0,
                b = 0,
                _ = 0,
                w = 0,
                S = 0,
                C = 0
              var E = new t.Uint32Array(n),
                M = new t.Uint8Array(n)
              function k(t, e, n, a, u, c, l, h) {
                t = t | 0
                e = e | 0
                n = n | 0
                a = a | 0
                u = u | 0
                c = c | 0
                l = l | 0
                h = h | 0
                var f = 0,
                  d = 0,
                  p = 0,
                  m = 0,
                  g = 0,
                  y = 0,
                  v = 0,
                  b = 0
                ;(f = n | 1024), (d = n | 2048), (p = n | 3072)
                ;(u = u ^ E[(t | 0) >> 2]),
                  (c = c ^ E[(t | 4) >> 2]),
                  (l = l ^ E[(t | 8) >> 2]),
                  (h = h ^ E[(t | 12) >> 2])
                for (b = 16; (b | 0) <= a << 4; b = (b + 16) | 0) {
                  ;(m =
                    E[(n | ((u >> 22) & 1020)) >> 2] ^
                    E[(f | ((c >> 14) & 1020)) >> 2] ^
                    E[(d | ((l >> 6) & 1020)) >> 2] ^
                    E[(p | ((h << 2) & 1020)) >> 2] ^
                    E[(t | b | 0) >> 2]),
                    (g =
                      E[(n | ((c >> 22) & 1020)) >> 2] ^
                      E[(f | ((l >> 14) & 1020)) >> 2] ^
                      E[(d | ((h >> 6) & 1020)) >> 2] ^
                      E[(p | ((u << 2) & 1020)) >> 2] ^
                      E[(t | b | 4) >> 2]),
                    (y =
                      E[(n | ((l >> 22) & 1020)) >> 2] ^
                      E[(f | ((h >> 14) & 1020)) >> 2] ^
                      E[(d | ((u >> 6) & 1020)) >> 2] ^
                      E[(p | ((c << 2) & 1020)) >> 2] ^
                      E[(t | b | 8) >> 2]),
                    (v =
                      E[(n | ((h >> 22) & 1020)) >> 2] ^
                      E[(f | ((u >> 14) & 1020)) >> 2] ^
                      E[(d | ((c >> 6) & 1020)) >> 2] ^
                      E[(p | ((l << 2) & 1020)) >> 2] ^
                      E[(t | b | 12) >> 2])
                  ;(u = m), (c = g), (l = y), (h = v)
                }
                ;(r =
                  (E[(e | ((u >> 22) & 1020)) >> 2] << 24) ^
                  (E[(e | ((c >> 14) & 1020)) >> 2] << 16) ^
                  (E[(e | ((l >> 6) & 1020)) >> 2] << 8) ^
                  E[(e | ((h << 2) & 1020)) >> 2] ^
                  E[(t | b | 0) >> 2]),
                  (i =
                    (E[(e | ((c >> 22) & 1020)) >> 2] << 24) ^
                    (E[(e | ((l >> 14) & 1020)) >> 2] << 16) ^
                    (E[(e | ((h >> 6) & 1020)) >> 2] << 8) ^
                    E[(e | ((u << 2) & 1020)) >> 2] ^
                    E[(t | b | 4) >> 2]),
                  (o =
                    (E[(e | ((l >> 22) & 1020)) >> 2] << 24) ^
                    (E[(e | ((h >> 14) & 1020)) >> 2] << 16) ^
                    (E[(e | ((u >> 6) & 1020)) >> 2] << 8) ^
                    E[(e | ((c << 2) & 1020)) >> 2] ^
                    E[(t | b | 8) >> 2]),
                  (s =
                    (E[(e | ((h >> 22) & 1020)) >> 2] << 24) ^
                    (E[(e | ((u >> 14) & 1020)) >> 2] << 16) ^
                    (E[(e | ((c >> 6) & 1020)) >> 2] << 8) ^
                    E[(e | ((l << 2) & 1020)) >> 2] ^
                    E[(t | b | 12) >> 2])
              }
              function x(t, e, n, r) {
                t = t | 0
                e = e | 0
                n = n | 0
                r = r | 0
                k(0, 2048, 4096, C, t, e, n, r)
              }
              function A(t, e, n, r) {
                t = t | 0
                e = e | 0
                n = n | 0
                r = r | 0
                var o = 0
                k(1024, 3072, 8192, C, t, r, n, e)
                ;(o = i), (i = s), (s = o)
              }
              function T(t, e, n, h) {
                t = t | 0
                e = e | 0
                n = n | 0
                h = h | 0
                k(0, 2048, 4096, C, a ^ t, u ^ e, c ^ n, l ^ h)
                ;(a = r), (u = i), (c = o), (l = s)
              }
              function I(t, e, n, h) {
                t = t | 0
                e = e | 0
                n = n | 0
                h = h | 0
                var f = 0
                k(1024, 3072, 8192, C, t, h, n, e)
                ;(f = i), (i = s), (s = f)
                ;(r = r ^ a), (i = i ^ u), (o = o ^ c), (s = s ^ l)
                ;(a = t), (u = e), (c = n), (l = h)
              }
              function R(t, e, n, h) {
                t = t | 0
                e = e | 0
                n = n | 0
                h = h | 0
                k(0, 2048, 4096, C, a, u, c, l)
                ;(a = r = r ^ t),
                  (u = i = i ^ e),
                  (c = o = o ^ n),
                  (l = s = s ^ h)
              }
              function N(t, e, n, h) {
                t = t | 0
                e = e | 0
                n = n | 0
                h = h | 0
                k(0, 2048, 4096, C, a, u, c, l)
                ;(r = r ^ t), (i = i ^ e), (o = o ^ n), (s = s ^ h)
                ;(a = t), (u = e), (c = n), (l = h)
              }
              function D(t, e, n, h) {
                t = t | 0
                e = e | 0
                n = n | 0
                h = h | 0
                k(0, 2048, 4096, C, a, u, c, l)
                ;(a = r), (u = i), (c = o), (l = s)
                ;(r = r ^ t), (i = i ^ e), (o = o ^ n), (s = s ^ h)
              }
              function P(t, e, n, a) {
                t = t | 0
                e = e | 0
                n = n | 0
                a = a | 0
                k(0, 2048, 4096, C, h, f, d, p)
                ;(p = (~v & p) | (v & (p + 1))),
                  (d = (~y & d) | (y & (d + ((p | 0) == 0)))),
                  (f = (~g & f) | (g & (f + ((d | 0) == 0)))),
                  (h = (~m & h) | (m & (h + ((f | 0) == 0))))
                ;(r = r ^ t), (i = i ^ e), (o = o ^ n), (s = s ^ a)
              }
              function B(t, e, n, r) {
                t = t | 0
                e = e | 0
                n = n | 0
                r = r | 0
                var i = 0,
                  o = 0,
                  s = 0,
                  h = 0,
                  f = 0,
                  d = 0,
                  p = 0,
                  m = 0,
                  g = 0,
                  y = 0
                ;(t = t ^ a), (e = e ^ u), (n = n ^ c), (r = r ^ l)
                ;(i = b | 0), (o = _ | 0), (s = w | 0), (h = S | 0)
                for (; (g | 0) < 128; g = (g + 1) | 0) {
                  if (i >>> 31) {
                    ;(f = f ^ t), (d = d ^ e), (p = p ^ n), (m = m ^ r)
                  }
                  ;(i = (i << 1) | (o >>> 31)),
                    (o = (o << 1) | (s >>> 31)),
                    (s = (s << 1) | (h >>> 31)),
                    (h = h << 1)
                  y = r & 1
                  ;(r = (r >>> 1) | (n << 31)),
                    (n = (n >>> 1) | (e << 31)),
                    (e = (e >>> 1) | (t << 31)),
                    (t = t >>> 1)
                  if (y) t = t ^ 3774873600
                }
                ;(a = f), (u = d), (c = p), (l = m)
              }
              function L(t) {
                t = t | 0
                C = t
              }
              function O(t, e, n, a) {
                t = t | 0
                e = e | 0
                n = n | 0
                a = a | 0
                ;(r = t), (i = e), (o = n), (s = a)
              }
              function q(t, e, n, r) {
                t = t | 0
                e = e | 0
                n = n | 0
                r = r | 0
                ;(a = t), (u = e), (c = n), (l = r)
              }
              function U(t, e, n, r) {
                t = t | 0
                e = e | 0
                n = n | 0
                r = r | 0
                ;(h = t), (f = e), (d = n), (p = r)
              }
              function j(t, e, n, r) {
                t = t | 0
                e = e | 0
                n = n | 0
                r = r | 0
                ;(m = t), (g = e), (y = n), (v = r)
              }
              function F(t, e, n, r) {
                t = t | 0
                e = e | 0
                n = n | 0
                r = r | 0
                ;(p = (~v & p) | (v & r)),
                  (d = (~y & d) | (y & n)),
                  (f = (~g & f) | (g & e)),
                  (h = (~m & h) | (m & t))
              }
              function H(t) {
                t = t | 0
                if (t & 15) return -1
                ;(M[t | 0] = r >>> 24),
                  (M[t | 1] = (r >>> 16) & 255),
                  (M[t | 2] = (r >>> 8) & 255),
                  (M[t | 3] = r & 255),
                  (M[t | 4] = i >>> 24),
                  (M[t | 5] = (i >>> 16) & 255),
                  (M[t | 6] = (i >>> 8) & 255),
                  (M[t | 7] = i & 255),
                  (M[t | 8] = o >>> 24),
                  (M[t | 9] = (o >>> 16) & 255),
                  (M[t | 10] = (o >>> 8) & 255),
                  (M[t | 11] = o & 255),
                  (M[t | 12] = s >>> 24),
                  (M[t | 13] = (s >>> 16) & 255),
                  (M[t | 14] = (s >>> 8) & 255),
                  (M[t | 15] = s & 255)
                return 16
              }
              function z(t) {
                t = t | 0
                if (t & 15) return -1
                ;(M[t | 0] = a >>> 24),
                  (M[t | 1] = (a >>> 16) & 255),
                  (M[t | 2] = (a >>> 8) & 255),
                  (M[t | 3] = a & 255),
                  (M[t | 4] = u >>> 24),
                  (M[t | 5] = (u >>> 16) & 255),
                  (M[t | 6] = (u >>> 8) & 255),
                  (M[t | 7] = u & 255),
                  (M[t | 8] = c >>> 24),
                  (M[t | 9] = (c >>> 16) & 255),
                  (M[t | 10] = (c >>> 8) & 255),
                  (M[t | 11] = c & 255),
                  (M[t | 12] = l >>> 24),
                  (M[t | 13] = (l >>> 16) & 255),
                  (M[t | 14] = (l >>> 8) & 255),
                  (M[t | 15] = l & 255)
                return 16
              }
              function V() {
                x(0, 0, 0, 0)
                ;(b = r), (_ = i), (w = o), (S = s)
              }
              function K(t, e, n) {
                t = t | 0
                e = e | 0
                n = n | 0
                var a = 0
                if (e & 15) return -1
                while ((n | 0) >= 16) {
                  W[t & 7](
                    (M[e | 0] << 24) |
                      (M[e | 1] << 16) |
                      (M[e | 2] << 8) |
                      M[e | 3],
                    (M[e | 4] << 24) |
                      (M[e | 5] << 16) |
                      (M[e | 6] << 8) |
                      M[e | 7],
                    (M[e | 8] << 24) |
                      (M[e | 9] << 16) |
                      (M[e | 10] << 8) |
                      M[e | 11],
                    (M[e | 12] << 24) |
                      (M[e | 13] << 16) |
                      (M[e | 14] << 8) |
                      M[e | 15]
                  )
                  ;(M[e | 0] = r >>> 24),
                    (M[e | 1] = (r >>> 16) & 255),
                    (M[e | 2] = (r >>> 8) & 255),
                    (M[e | 3] = r & 255),
                    (M[e | 4] = i >>> 24),
                    (M[e | 5] = (i >>> 16) & 255),
                    (M[e | 6] = (i >>> 8) & 255),
                    (M[e | 7] = i & 255),
                    (M[e | 8] = o >>> 24),
                    (M[e | 9] = (o >>> 16) & 255),
                    (M[e | 10] = (o >>> 8) & 255),
                    (M[e | 11] = o & 255),
                    (M[e | 12] = s >>> 24),
                    (M[e | 13] = (s >>> 16) & 255),
                    (M[e | 14] = (s >>> 8) & 255),
                    (M[e | 15] = s & 255)
                  ;(a = (a + 16) | 0), (e = (e + 16) | 0), (n = (n - 16) | 0)
                }
                return a | 0
              }
              function $(t, e, n) {
                t = t | 0
                e = e | 0
                n = n | 0
                var r = 0
                if (e & 15) return -1
                while ((n | 0) >= 16) {
                  G[t & 1](
                    (M[e | 0] << 24) |
                      (M[e | 1] << 16) |
                      (M[e | 2] << 8) |
                      M[e | 3],
                    (M[e | 4] << 24) |
                      (M[e | 5] << 16) |
                      (M[e | 6] << 8) |
                      M[e | 7],
                    (M[e | 8] << 24) |
                      (M[e | 9] << 16) |
                      (M[e | 10] << 8) |
                      M[e | 11],
                    (M[e | 12] << 24) |
                      (M[e | 13] << 16) |
                      (M[e | 14] << 8) |
                      M[e | 15]
                  )
                  ;(r = (r + 16) | 0), (e = (e + 16) | 0), (n = (n - 16) | 0)
                }
                return r | 0
              }
              var W = [x, A, T, I, R, N, D, P]
              var G = [T, B]
              return {
                set_rounds: L,
                set_state: O,
                set_iv: q,
                set_nonce: U,
                set_mask: j,
                set_counter: F,
                get_state: H,
                get_iv: z,
                gcm_init: V,
                cipher: K,
                mac: $,
              }
            })(t, e, n)
            return (f.set_key = i), f
          }
        return (
          (f.ENC = {
            ECB: 0,
            CBC: 2,
            CFB: 4,
            OFB: 6,
            CTR: 7,
          }),
          (f.DEC = {
            ECB: 1,
            CBC: 3,
            CFB: 5,
            OFB: 6,
            CTR: 7,
          }),
          (f.MAC = {
            CBC: 0,
            GCM: 1,
          }),
          (f.HEAP_DATA = 16384),
          f
        )
      })(),
      Xe = A.prototype
    ;(Xe.BLOCK_SIZE = 16), (Xe.reset = C), (Xe.encrypt = M), (Xe.decrypt = x)
    var Ye = T.prototype
    ;(Ye.BLOCK_SIZE = 16), (Ye.reset = C), (Ye.process = E), (Ye.finish = M)
    var Je = I.prototype
    ;(Je.BLOCK_SIZE = 16), (Je.reset = C), (Je.process = k), (Je.finish = x)
    var Ze = R.prototype
    ;(Ze.BLOCK_SIZE = 16), (Ze.reset = P), (Ze.encrypt = M), (Ze.decrypt = M)
    var Qe = N.prototype
    ;(Qe.BLOCK_SIZE = 16), (Qe.reset = P), (Qe.process = E), (Qe.finish = M)
    var tn = 68719476704,
      en = L.prototype
    ;(en.BLOCK_SIZE = 16), (en.reset = U), (en.encrypt = H), (en.decrypt = K)
    var nn = O.prototype
    ;(nn.BLOCK_SIZE = 16), (nn.reset = U), (nn.process = j), (nn.finish = F)
    var rn = q.prototype
    ;(rn.BLOCK_SIZE = 16), (rn.reset = U), (rn.process = z), (rn.finish = V)
    var on = new Uint8Array(1048576),
      sn = Ge(e, null, on.buffer)
    ;(t.AES_CBC = A),
      (t.AES_CBC.encrypt = $),
      (t.AES_CBC.decrypt = W),
      (t.AES_CBC.Encrypt = T),
      (t.AES_CBC.Decrypt = I),
      (t.AES_GCM = L),
      (t.AES_GCM.encrypt = G),
      (t.AES_GCM.decrypt = X),
      (t.AES_GCM.Encrypt = O),
      (t.AES_GCM.Decrypt = q)
    var an = 64,
      un = 20
    ;(tt.BLOCK_SIZE = an), (tt.HASH_SIZE = un)
    var cn = tt.prototype
    ;(cn.reset = Y), (cn.process = J), (cn.finish = Z)
    var ln = null
    ;(tt.bytes = nt), (tt.hex = rt), (tt.base64 = it), (t.SHA1 = tt)
    var hn = 64,
      fn = 32
    ;(st.BLOCK_SIZE = hn), (st.HASH_SIZE = fn)
    var dn = st.prototype
    ;(dn.reset = Y), (dn.process = J), (dn.finish = Z)
    var pn = null
    ;(st.bytes = ut), (st.hex = ct), (st.base64 = lt), (t.SHA256 = st)
    var mn = ht.prototype
    ;(mn.reset = pt),
      (mn.process = mt),
      (mn.finish = gt),
      (yt.BLOCK_SIZE = tt.BLOCK_SIZE),
      (yt.HMAC_SIZE = tt.HASH_SIZE)
    var gn = yt.prototype
    ;(gn.reset = vt), (gn.process = mt), (gn.finish = bt)
    var yn = null
    ;(wt.BLOCK_SIZE = st.BLOCK_SIZE), (wt.HMAC_SIZE = st.HASH_SIZE)
    var vn = wt.prototype
    ;(vn.reset = St), (vn.process = mt), (vn.finish = Ct)
    var bn = null
    ;(t.HMAC = ht),
      (yt.bytes = Mt),
      (yt.hex = kt),
      (yt.base64 = xt),
      (t.HMAC_SHA1 = yt),
      (wt.bytes = At),
      (wt.hex = Tt),
      (wt.base64 = It),
      (t.HMAC_SHA256 = wt)
    var _n = Rt.prototype
    ;(_n.reset = Nt), (_n.generate = Dt)
    var wn = Pt.prototype
    ;(wn.reset = Nt), (wn.generate = Bt)
    var Sn = null,
      Cn = Ot.prototype
    ;(Cn.reset = Nt), (Cn.generate = qt)
    var En = null
    ;(t.PBKDF2 = t.PBKDF2_HMAC_SHA1 =
      {
        bytes: jt,
        hex: Ft,
        base64: Ht,
      }),
      (t.PBKDF2_HMAC_SHA256 = {
        bytes: zt,
        hex: Vt,
        base64: Kt,
      })
    var Mn,
      kn = (function () {
        function t() {
          function t() {
            ;(e ^= r << 11),
              (r = (r + o) | 0),
              (r ^= o >>> 2),
              (o = (o + (h = (h + e) | 0)) | 0),
              (o ^= h << 8),
              (h = (h + (f = (f + r) | 0)) | 0),
              (h ^= f >>> 16),
              (f = (f + (d = (d + o) | 0)) | 0),
              (f ^= d << 10),
              (d = (d + (p = (p + h) | 0)) | 0),
              (d ^= p >>> 4),
              (p = (p + (m = (m + f) | 0)) | 0),
              (p ^= m << 8),
              (m = (m + (e = (e + d) | 0)) | 0),
              (o = (o + (m ^= e >>> 9)) | 0),
              (e = (e + (r = (r + p) | 0)) | 0)
          }
          var e, r, o, h, f, d, p, m
          ;(a = u = c = 0), (e = r = o = h = f = d = p = m = 2654435769)
          for (var g = 0; 4 > g; g++) t()
          for (g = 0; 256 > g; g += 8)
            (e = (e + s[0 | g]) | 0),
              (r = (r + s[1 | g]) | 0),
              (o = (o + s[2 | g]) | 0),
              (h = (h + s[3 | g]) | 0),
              (f = (f + s[4 | g]) | 0),
              (d = (d + s[5 | g]) | 0),
              (p = (p + s[6 | g]) | 0),
              (m = (m + s[7 | g]) | 0),
              t(),
              i.set([e, r, o, h, f, d, p, m], g)
          for (g = 0; 256 > g; g += 8)
            (e = (e + i[0 | g]) | 0),
              (r = (r + i[1 | g]) | 0),
              (o = (o + i[2 | g]) | 0),
              (h = (h + i[3 | g]) | 0),
              (f = (f + i[4 | g]) | 0),
              (d = (d + i[5 | g]) | 0),
              (p = (p + i[6 | g]) | 0),
              (m = (m + i[7 | g]) | 0),
              t(),
              i.set([e, r, o, h, f, d, p, m], g)
          n(1), (l = 256)
        }
        function e(e) {
          var n, r, i, a, u
          if (g(e)) e = new Uint8Array(e.buffer)
          else if (f(e))
            ((a = new $e(1))[0] = e), (e = new Uint8Array(a.buffer))
          else if (d(e)) e = o(e)
          else {
            if (!p(e)) throw new TypeError('bad seed type')
            e = new Uint8Array(e)
          }
          for (u = e.length, r = 0; u > r; r += 1024) {
            for (i = r, n = 0; 1024 > n && u > i; i = r | ++n)
              s[n >> 2] ^= e[i] << ((3 & n) << 3)
            t()
          }
        }
        function n(t) {
          t = t || 1
          for (var e, n, r; t--; )
            for (u = (u + (c = (c + 1) | 0)) | 0, e = 0; 256 > e; e += 4)
              (a ^= a << 13),
                (a = (i[(e + 128) & 255] + a) | 0),
                (n = i[0 | e]),
                (i[0 | e] = r = (i[(n >>> 2) & 255] + ((a + u) | 0)) | 0),
                (s[0 | e] = u = (i[(r >>> 10) & 255] + n) | 0),
                (a ^= a >>> 6),
                (a = (i[(e + 129) & 255] + a) | 0),
                (n = i[1 | e]),
                (i[1 | e] = r = (i[(n >>> 2) & 255] + ((a + u) | 0)) | 0),
                (s[1 | e] = u = (i[(r >>> 10) & 255] + n) | 0),
                (a ^= a << 2),
                (a = (i[(e + 130) & 255] + a) | 0),
                (n = i[2 | e]),
                (i[2 | e] = r = (i[(n >>> 2) & 255] + ((a + u) | 0)) | 0),
                (s[2 | e] = u = (i[(r >>> 10) & 255] + n) | 0),
                (a ^= a >>> 16),
                (a = (i[(e + 131) & 255] + a) | 0),
                (n = i[3 | e]),
                (i[3 | e] = r = (i[(n >>> 2) & 255] + ((a + u) | 0)) | 0),
                (s[3 | e] = u = (i[(r >>> 10) & 255] + n) | 0)
        }
        function r() {
          return l-- || (n(1), (l = 255)), s[l]
        }
        var i = new Uint32Array(256),
          s = new Uint32Array(256),
          a = 0,
          u = 0,
          c = 0,
          l = 0
        return {
          seed: e,
          prng: n,
          rand: r,
        }
      })(),
      xn = ((We = e.console), e.Date.now),
      An = e.Math.random,
      Tn = e.performance,
      In = e.crypto || e.msCrypto
    void 0 !== In && (Mn = In.getRandomValues)
    var Rn,
      Nn,
      Dn = kn.rand,
      Pn = kn.seed,
      Bn = 0,
      Ln = !1,
      On = !1,
      qn = 0,
      Un = 256,
      jn = !1,
      Fn = !1,
      Hn = {}
    if (void 0 !== Tn)
      Rn = function () {
        return (1e3 * Tn.now()) | 0
      }
    else {
      var zn = (1e3 * xn()) | 0
      Rn = function () {
        return (1e3 * xn() - zn) | 0
      }
    }
    ;(t.random = Xt),
      (t.random.seed = Wt),
      Object.defineProperty(Xt, 'allowWeak', {
        get: function () {
          return jn
        },
        set: function (t) {
          jn = t
        },
      }),
      Object.defineProperty(Xt, 'skipSystemRNGWarning', {
        get: function () {
          return Fn
        },
        set: function (t) {
          Fn = t
        },
      }),
      (t.getRandomValues = Gt),
      (t.getRandomValues.seed = Wt),
      Object.defineProperty(Gt, 'allowWeak', {
        get: function () {
          return jn
        },
        set: function (t) {
          jn = t
        },
      }),
      Object.defineProperty(Gt, 'skipSystemRNGWarning', {
        get: function () {
          return Fn
        },
        set: function (t) {
          Fn = t
        },
      }),
      (e.Math.random = Xt),
      void 0 === e.crypto && (e.crypto = {}),
      (e.crypto.getRandomValues = Gt),
      (Nn =
        void 0 === e.Math.imul
          ? function (t, n, r) {
              e.Math.imul = Yt
              var i = Jt(t, n, r)
              return delete e.Math.imul, i
            }
          : Jt)
    var Vn = new Uint32Array(1048576),
      Jt = Nn(e, null, Vn.buffer),
      Kn = new Uint32Array(0),
      $n = (Qt.prototype = new Number())
    ;($n.toString = te),
      ($n.toBytes = ee),
      ($n.valueOf = ne),
      ($n.clamp = re),
      ($n.slice = ie),
      ($n.negate = oe),
      ($n.compare = se),
      ($n.add = ae),
      ($n.subtract = ue),
      ($n.multiply = ce),
      ($n.square = le),
      ($n.divide = he)
    var Wn = new Qt(0),
      Gn = new Qt(1)
    Object.freeze(Wn), Object.freeze(Gn)
    var Xn = (pe.prototype = new Qt())
    ;(Xn.reduce = me), (Xn.inverse = ge), (Xn.power = ye)
    var Yn = [2, 3]
    ;($n.isProbablePrime = _e),
      (Qt.randomProbablePrime = Se),
      (Qt.ZERO = Wn),
      (Qt.ONE = Gn),
      (Qt.extGCD = de),
      (t.BigNumber = Qt),
      (t.Modulus = pe)
    var Jn = Ce.prototype
    ;(Jn.reset = Ee),
      (Jn.encrypt = Me),
      (Jn.decrypt = ke),
      (Ce.generateKey = xe)
    var Zn = Ae.prototype
    ;(Zn.reset = Te), (Zn.encrypt = Ie), (Zn.decrypt = Re)
    var Qn = De.prototype
    ;(Qn.reset = Pe),
      (Qn.sign = Be),
      (Qn.verify = Le),
      (t.RSA = {
        generateKey: Oe,
      }),
      (t.RSA_OAEP = Ae),
      (t.RSA_OAEP_SHA1 = {
        encrypt: qe,
        decrypt: Ue,
      }),
      (t.RSA_OAEP = Ae),
      (t.RSA_OAEP_SHA256 = {
        encrypt: je,
        decrypt: Fe,
      }),
      (t.RSA_PSS = De),
      (t.RSA_PSS_SHA1 = {
        sign: He,
        verify: ze,
      }),
      (t.RSA_PSS = De),
      (t.RSA_PSS_SHA256 = {
        sign: Ve,
        verify: Ke,
      }),
      'function' == typeof define && define.amd
        ? define([], function () {
            return t
          })
        : 'object' == typeof module && module.exports
        ? (module.exports = t)
        : (e.asmCrypto = t)
  })(
    {},
    (function () {
      return this
    })()
  ),
  Uint8Array.prototype.slice ||
    Object.defineProperty(Uint8Array.prototype, 'slice', {
      value: Array.prototype.slice,
    })
var crypto_wrapper = {
    SHA1: function (t) {
      return asmCrypto.SHA1.hex(t)
    },
    SHA256: function (t) {
      return asmCrypto.SHA256.hex(t)
    },
    random: function (t) {
      var e = new Uint8Array(t)
      return asmCrypto.getRandomValues(e), asmCrypto.bytes_to_hex(e)
    },
    createKeyAndIV: function (t, e) {
      var n = t + convertFromHex(e),
        r = '',
        i = '',
        o = [],
        s = 1,
        a = 3,
        u = 0
      o[u++] = n
      for (var c = 0; c < a; c++) {
        0 == c ? (i = n) : ((r = convertFromHex(i)), (i = r += n))
        for (var l = 0; l < s; l++) i = md5(i)
        o[u++] = i
      }
      return {
        key: asmCrypto.hex_to_bytes(o[1] + o[2]),
        iv: asmCrypto.hex_to_bytes(o[3]),
        salt: e,
      }
    },
    aes_encrypt: function (t, e) {
      var n = t.key,
        r = t.iv,
        i = 16,
        o = e
      try {
        var s = asmCrypto.string_to_bytes(encodeUTF8(e)),
          a = i - ((s.length + 1) % i),
          u = new Uint8Array(s.length + a + 1)
        u.set(s)
        var c = 0
        u[s.length + c++] = 10
        for (var l = 0; l < a; l++) u[s.length + c++] = a
        return asmCrypto.bytes_to_base64(
          asmCrypto.AES_CBC.encrypt(u, n, null, r)
        )
      } catch (h) {
        return o
      }
    },
    aes_decrypt: function (t, e) {
      var n = t.key,
        r = t.iv,
        i = e
      try {
        var o = asmCrypto.AES_CBC.decrypt(atob(e), n, null, r),
          s = o.length
        return (
          (o = o.slice(0, s - o[s - 1] - 1)),
          decodeUTF8(asmCrypto.bytes_to_string(o))
        )
      } catch (a) {
        return i
      }
    },
  },
  keyIVCache = {}
