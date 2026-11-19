// Planning an eval run: how many cases for a margin, and pass@k / pass^k for repeated tries.
// Used by sample-size.html, checked by tests/demos/check-sample-size.js.
const Z = 1.96;

// Cases needed so a 95% range is about ±margin (normal approximation; p = expected pass rate).
function nFor(margin, p = 0.5, z = Z) {
  if (!(margin > 0) || !(p >= 0 && p <= 1)) return null;
  return Math.ceil(z * z * p * (1 - p) / (margin * margin));
}
function marginFor(n, p = 0.5, z = Z) { return n > 0 ? z * Math.sqrt(p * (1 - p) / n) : null; }

function choose(n, k) { if (k < 0 || k > n) return 0; let c = 1; for (let i = 1; i <= k; i++) c = c * (n - k + i) / i; return c; }

// n tries per case, c of them passed. pass@k: chance at least one of k tries passes (unbiased, Chen et al. 2021).
function passAtK(n, c, k) {
  if (!(k >= 1) || k > n || c < 0 || c > n) return null;
  if (n - c < k) return 1;
  return 1 - choose(n - c, k) / choose(n, k);
}
// pass^k: chance that all k tries pass (the reliability view).
function passHatK(n, c, k) {
  if (!(k >= 1) || k > n || c < 0 || c > n) return null;
  return choose(c, k) / choose(n, k);
}

// Two versions on the same cases: how many cases to detect a real gain, with McNemar's test
// (two-sided alpha 0.05, power 0.8; normal approximation, Connor 1987).
// pBetter / pWorse: expected share of cases that flip to pass / to fail.
function nPaired(pBetter, pWorse, zA = 1.959963984540054, zB = 0.8416212335729143) {
  const disc = pBetter + pWorse, d = pBetter - pWorse;
  if (!(d > 0) || pWorse < 0 || disc > 1) return null;
  return Math.ceil(Math.pow(zA * Math.sqrt(disc) + zB * Math.sqrt(disc - d * d), 2) / (d * d));
}

if (typeof module !== "undefined") module.exports = { nFor, marginFor, passAtK, passHatK, nPaired };
