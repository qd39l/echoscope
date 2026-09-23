/* EchoScope's mathematical model. Unsigned words, modulo-32 neighbors. */
(function (root) {
  'use strict';
  const initial = () => [0, 0x8000, 0, 0x18000];
  const rule = x => (((x << 1) | (x >>> 31)) ^ (x | ((x >>> 1) | (x << 31)))) >>> 0;
  function step(s, reverse = false) {
    const result = [];
    for (let i = 0; i < 4; i += 2) {
      const p = s[i], n = s[i + 1];
      result.push(...(reverse ? [(rule(p) ^ n) >>> 0, p] : [n, (rule(n) ^ p) >>> 0]));
    }
    return result;
  }
  const kick = (s, i) => [s[0], s[1], s[2], (s[3] ^ (1 << i)) >>> 0];
  const clone = s => [s[0], s[1], s[0], s[1]];
  function distance(s) { let d = (s[1] ^ s[3]) >>> 0, n = 0; while (d) { d = (d & (d - 1)) >>> 0; n++; } return n; }
  const model = {initial, rule, step, kick, clone, distance};
  if (typeof module !== 'undefined') module.exports = model;
  else root.EchoModel = model;
})(typeof window !== 'undefined' ? window : this);
