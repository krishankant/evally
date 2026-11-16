const r = require(process.argv[2]);
let bad = 0; const ok = (c, m, g) => { if (!c) { console.log("FAIL", m, g); bad++; } };
const near = (a, b, t = 1e-9) => a !== null && Math.abs(a - b) < t;
const ranked = ["d1", "x", "d2"], rel = new Set(["d1", "d2"]);
ok(near(r.recallAtK(ranked, rel, 1), 0.5), "recall@1", r.recallAtK(ranked, rel, 1));
ok(near(r.recallAtK(ranked, rel, 3), 1), "recall@3", r.recallAtK(ranked, rel, 3));
ok(near(r.precisionAtK(ranked, rel, 3), 2 / 3), "precision@3", r.precisionAtK(ranked, rel, 3));
ok(near(r.reciprocalRank(ranked, rel), 1), "RR first", r.reciprocalRank(ranked, rel));
ok(near(r.averagePrecision(ranked, rel), (1 / 1 + 2 / 3) / 2), "AP", r.averagePrecision(ranked, rel));
// the four labelled Bramble dev cases (real retrieval, author's labels)
const cases = [
  [["returns.md", "returns-2023.md", "gift-cards.md"], ["returns.md"]],
  [["damaged-items.md", "preorders.md", "gift-cards.md"], ["returns.md"]],
  [["returns-2023.md", "returns.md", "shipping.md"], ["returns.md"]],
  [["international-shipping.md", "membership.md", "shipping.md"], ["shipping.md", "membership.md"]],
].map(([a, b]) => [a, new Set(b)]);
ok(near(r.mrr(cases), (1 + 0 + 0.5 + 0.5) / 4), "MRR over 4 cases", r.mrr(cases));
ok(near(r.reciprocalRank(cases[1][0], cases[1][1]), 0), "a miss scores 0", null);
// graded nDCG, linear gains
const gains = { d1: 3, d2: 2, d3: 0 };
const want = (0 + 3 / Math.log2(3) + 2 / Math.log2(4)) / (3 + 2 / Math.log2(3) + 0);
ok(near(r.ndcgAtK(["d3", "d1", "d2"], gains, 3), want), "nDCG@3", [r.ndcgAtK(["d3", "d1", "d2"], gains, 3), want]);
ok(near(r.ndcgAtK(["d1", "d2", "d3"], gains, 3), 1), "ideal order = 1", null);
// edges
ok(r.recallAtK(ranked, new Set(), 3) === null && r.ndcgAtK(["a"], {}, 3) === null, "no relevant docs -> null", null);
ok(r.precisionAtK([], rel, 3) === null, "empty ranking -> null", null);
if (!bad) console.log("all checks pass"); else process.exitCode = 1;
