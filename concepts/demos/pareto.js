// Quality, cost and speed together: percentiles and the Pareto front.
// Used by pareto.html, checked by tests/demos/check-pareto.js.

// Linear interpolation between closest ranks (numpy's default). q in 0..100.
function percentile(xs, q) {
  if (!xs.length) return null;
  const s = xs.slice().sort((a, b) => a - b), i = (s.length - 1) * q / 100;
  const lo = Math.floor(i), hi = Math.ceil(i);
  return s[lo] + (s[hi] - s[lo]) * (i - lo);
}

// a dominates b: at least as good on both (quality up, cost down) and better on one.
const dominates = (a, b) => a.quality >= b.quality && a.cost <= b.cost && (a.quality > b.quality || a.cost < b.cost);

function paretoFront(points) {
  if (!points.length) return null;
  return points.filter(p => !points.some(q => q !== p && dominates(q, p)));
}

const qualityPerDollar = ({ quality, cost }) => cost > 0 ? quality / cost : null;

if (typeof module !== "undefined") module.exports = { percentile, dominates, paretoFront, qualityPerDollar };
