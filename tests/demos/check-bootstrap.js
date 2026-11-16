const bs = require(process.argv[2]);
let bad = 0; const ok = (c, m, g) => { if (!c) { console.log("FAIL", m, g); bad++; } };
const near = (a, b, t) => Math.abs(a - b) < t;
const qwen = [1,1,1,1,1,1,1,0,0,0,0,0,1,1,0,1], llama = [0,1,1,1,1,1,1,1,0,1,1,1,1,1,0,1];
// Wilson matches scipy 1.18.1 (binomtest(...).proportion_ci(method="wilson"))
const w = bs.wilson(10, 16); ok(near(w.low, 0.386, 0.001) && near(w.high, 0.815, 0.001), "wilson 10/16", w);
const w2 = bs.wilson(13, 16); ok(near(w2.low, 0.570, 0.001) && near(w2.high, 0.934, 0.001), "wilson 13/16", w2);
ok(bs.wilson(0, 0) === null, "wilson n=0", null);
// bootstrap: same seed same answer
const a = bs.bootstrap(qwen, { seed: 3, B: 2000 }), b = bs.bootstrap(qwen, { seed: 3, B: 2000 });
ok(JSON.stringify(a) === JSON.stringify(b), "deterministic", [a, b]);
ok(a.low <= 0.625 && 0.625 <= a.high, "interval holds the point estimate", a);
// spread over seeds (observation 0032): width near the normal approximation, low/high stable
let width = 0, lows = []; const S = 300;
for (let s = 1; s <= S; s++) { const r = bs.bootstrap(qwen, { seed: s, B: 2000 }); width += r.high - r.low; lows.push(r.low); }
width /= S; const normal = 2 * 1.96 * Math.sqrt(0.625 * 0.375 / 16);
ok(near(width, normal, 0.06), "mean width ~ normal approx", [width, normal]);
const meanLow = lows.reduce((x, y) => x + y) / S;
ok(near(meanLow, 0.375, 0.04), "mean lower bound ~ 0.375 (scipy, seed 0)", meanLow);
ok(bs.bootstrap([], { seed: 1, B: 100 }) === null, "empty -> null", null);
// paired difference: llama - qwen, resampling cases
const d = bs.pairedBootstrap(qwen, llama, { seed: 1, B: 4000 });
ok(near(d.diff, 0.1875, 1e-9), "observed diff 3/16", d.diff);
ok(d.low < 0 && d.high > 0, "range for the difference crosses 0", d);
ok(bs.pairedBootstrap([1], [1, 0], { seed: 1, B: 10 }) === null, "unequal lengths -> null", null);
// McNemar exact on the flipped cases
const m = bs.mcnemar(qwen, llama); ok(m.b === 1 && m.c === 4 && near(m.p, 0.375, 1e-9), "mcnemar 1 vs 4", m);
ok(bs.mcnemar([1,0], [1,0]).p === 1, "no flips -> p = 1", bs.mcnemar([1,0],[1,0]));
if (!bad) console.log("all checks pass"); else process.exitCode = 1;
