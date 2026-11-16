// A judge comparing two equally good replies, asked twice with the order swapped.
// With probability b it picks whichever reply it was shown first. Used by position-bias.html,
// checked by tests/demos/check-position-bias.js.

function rng(seed) {             // mulberry32: small, seedable, good enough for a demo
  let t = seed >>> 0;
  return () => {
    t = (t + 0x6D2B79F5) >>> 0;
    let x = Math.imul(t ^ (t >>> 15), 1 | t);
    x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x;
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
  };
}

// n pairs -> {calls, pickedFirst, consistent, inconsistent, winsA, winsB}; null when n < 1
function simulate({ b, n, seed }) {
  if (!(n >= 1)) return null;
  const r = rng(seed);
  const out = { calls: 2 * n, pickedFirst: 0, consistent: 0, inconsistent: 0, winsA: 0, winsB: 0 };
  for (let i = 0; i < n; i++) {
    const first1 = r() < b;            // A shown first
    const first2 = r() < b;            // B shown first
    const w1 = first1 ? "A" : "B", w2 = first2 ? "B" : "A";
    out.pickedFirst += first1 + first2;
    if (w1 === w2) { out.consistent++; w1 === "A" ? out.winsA++ : out.winsB++; } else out.inconsistent++;
  }
  return out;
}

const expectedConsistent = (b) => 2 * b * (1 - b);

// How far a picked-first count is from a fair 50%, in standard errors (normal approximation).
function zScore(pickedFirst, calls) {
  if (!(calls >= 1)) return null;
  return (pickedFirst - calls / 2) / Math.sqrt(calls / 4);
}

if (typeof module !== "undefined") module.exports = { rng, simulate, expectedConsistent, zScore };
