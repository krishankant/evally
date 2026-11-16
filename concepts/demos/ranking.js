// Retrieval metrics for one ranked list of document ids against relevance labels.
// Used by ranking.html, checked by tests/demos/check-ranking.js. null = not defined for this input.

function recallAtK(ranked, rel, k) {
  if (!rel.size) return null;
  return ranked.slice(0, k).filter(d => rel.has(d)).length / rel.size;
}
function precisionAtK(ranked, rel, k) {
  const top = ranked.slice(0, k);
  if (!top.length) return null;
  return top.filter(d => rel.has(d)).length / top.length;
}
function reciprocalRank(ranked, rel) {
  const i = ranked.findIndex(d => rel.has(d));
  return i < 0 ? 0 : 1 / (i + 1);
}
const mrr = (cases) => cases.length ? cases.reduce((t, [ranked, rel]) => t + reciprocalRank(ranked, rel), 0) / cases.length : null;

// Mean of precision@i at each rank i that holds a relevant doc, over all relevant docs.
function averagePrecision(ranked, rel) {
  if (!rel.size) return null;
  let hits = 0, sum = 0;
  ranked.forEach((d, i) => { if (rel.has(d)) { hits++; sum += hits / (i + 1); } });
  return sum / rel.size;
}

// nDCG@k with graded relevance (gains: id -> 0, 1, 2, 3 ...), linear gain, log2 discount.
function ndcgAtK(ranked, gains, k) {
  const dcg = (list) => list.slice(0, k).reduce((t, g, i) => t + g / Math.log2(i + 2), 0);
  const ideal = dcg(Object.values(gains).sort((a, b) => b - a));
  if (!(ideal > 0)) return null;
  return dcg(ranked.map(d => gains[d] || 0)) / ideal;
}

if (typeof module !== "undefined") module.exports = { recallAtK, precisionAtK, reciprocalRank, mrr, averagePrecision, ndcgAtK };
