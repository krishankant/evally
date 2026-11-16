const ss = require(process.argv[2]);
let bad = 0; const ok = (c, m, g) => { if (!c) { console.log("FAIL", m, g); bad++; } };
const near = (a, b, t) => Math.abs(a - b) < t;
ok(ss.nFor(0.05) === 385, "n for ±5%", ss.nFor(0.05));
ok(ss.nFor(0.1) === 97, "n for ±10%", ss.nFor(0.1));
ok(ss.nFor(0.1, 0.9) === 35, "n for ±10% at p=0.9", ss.nFor(0.1, 0.9));
ok(ss.nFor(0) === null && ss.nFor(-1) === null, "margin <= 0 -> null", null);
ok(near(ss.marginFor(16, 0.625), 0.2372, 0.0005), "margin at n=16", ss.marginFor(16, 0.625));
// pass@k (unbiased estimator, Chen et al. 2021) and pass^k
ok(near(ss.passAtK(10, 3, 1), 0.3, 1e-12), "pass@1 = c/n", ss.passAtK(10, 3, 1));
ok(near(ss.passAtK(10, 3, 5), 1 - 21 / 252, 1e-12), "pass@5 = 1 - C(7,5)/C(10,5)", ss.passAtK(10, 3, 5));
ok(ss.passAtK(10, 8, 3) === 1, "n-c < k -> 1", ss.passAtK(10, 8, 3));
ok(near(ss.passHatK(10, 7, 3), 35 / 120, 1e-12), "pass^3 = C(7,3)/C(10,3)", ss.passHatK(10, 7, 3));
ok(ss.passAtK(3, 1, 5) === null && ss.passHatK(3, 1, 5) === null, "k > n -> null", null);
if (!bad) console.log("all checks pass"); else process.exitCode = 1;
