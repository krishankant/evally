// Ranges for pass rates: Wilson interval, bootstrap, paired bootstrap, McNemar's exact test.
// Used by bootstrap.html, checked by tests/demos/check-bootstrap.js. Outcomes are arrays of 0/1.
const Z95 = 1.959963984540054;

function rng(seed) {             // mulberry32
  let t = seed >>> 0;
  return () => { t = (t + 0x6D2B79F5) >>> 0; let x = Math.imul(t ^ (t >>> 15), 1 | t);
    x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x; return ((x ^ (x >>> 14)) >>> 0) / 4294967296; };
}
const mean = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length;
function percentile(sorted, q) {   // linear interpolation, like numpy's default
  const i = (sorted.length - 1) * q, lo = Math.floor(i), hi = Math.ceil(i);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (i - lo);
}

function wilson(k, n, z = Z95) {
  if (!(n > 0)) return null;
  const p = k / n, d = 1 + z * z / n;
  const centre = (p + z * z / (2 * n)) / d;
  const half = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d;
  return { low: Math.max(0, centre - half), high: Math.min(1, centre + half) };
}

// Resample cases with replacement B times; 95% percentile interval of the pass rate.
function bootstrap(xs, { seed = 1, B = 2000, level = 0.95 } = {}) {
  if (!xs.length) return null;
  const r = rng(seed), n = xs.length, stats = new Array(B);
  for (let b = 0; b < B; b++) { let s = 0; for (let i = 0; i < n; i++) s += xs[Math.floor(r() * n)]; stats[b] = s / n; }
  stats.sort((a, b) => a - b);
  return { est: mean(xs), low: percentile(stats, (1 - level) / 2), high: percentile(stats, 1 - (1 - level) / 2), stats };
}

// Same cases, two versions: resample case indices, keep each case's pair together.
function pairedBootstrap(a, b, { seed = 1, B = 2000, level = 0.95 } = {}) {
  if (!a.length || a.length !== b.length) return null;
  const r = rng(seed), n = a.length, diffs = new Array(B);
  for (let k = 0; k < B; k++) { let s = 0; for (let i = 0; i < n; i++) { const j = Math.floor(r() * n); s += b[j] - a[j]; } diffs[k] = s / n; }
  diffs.sort((x, y) => x - y);
  return { diff: mean(b) - mean(a), low: percentile(diffs, (1 - level) / 2), high: percentile(diffs, 1 - (1 - level) / 2) };
}

function choose(n, k) { if (k < 0 || k > n) return 0; let c = 1; for (let i = 1; i <= k; i++) c = c * (n - k + i) / i; return c; }

// Only the cases that flipped carry information. Two-sided exact binomial test on them.
function mcnemar(a, b) {
  let up = 0, down = 0;
  a.forEach((x, i) => { if (x === 1 && b[i] === 0) up++; else if (x === 0 && b[i] === 1) down++; });
  const m = up + down, lo = Math.min(up, down);
  let tail = 0; for (let i = 0; i <= lo; i++) tail += choose(m, i) / Math.pow(2, m);
  return { b: up, c: down, p: m === 0 ? 1 : Math.min(1, 2 * tail) };
}

if (typeof module !== "undefined") module.exports = { rng, wilson, bootstrap, pairedBootstrap, mcnemar, percentile, choose };
