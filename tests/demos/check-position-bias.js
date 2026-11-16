const pb = require(process.argv[2]);
let bad = 0;
const ok = (cond, msg, got) => { if (!cond) { console.log("FAIL", msg, got); bad++; } };
// deterministic for a seed
const a = pb.simulate({ b: 0.5, n: 15, seed: 1 }), b = pb.simulate({ b: 0.5, n: 15, seed: 1 });
ok(JSON.stringify(a) === JSON.stringify(b), "same seed, same result", [a, b]);
ok(a.calls === 30 && a.consistent + a.inconsistent === 15, "counts add up", a);
// spread: over many seeds the averages match theory (observation 0032: test the estimator, not one draw)
let share = 0, cons = 0; const S = 2000;
for (let s = 1; s <= S; s++) { const r = pb.simulate({ b: 0.7, n: 15, seed: s }); share += r.pickedFirst / r.calls; cons += r.consistent / 15; }
share /= S; cons /= S;
ok(share > 0.68 && share < 0.72, "mean picked-first share ~ b", share);
ok(Math.abs(cons - pb.expectedConsistent(0.7)) < 0.02, "mean consistent share ~ 2b(1-b)", cons);
// unbiased judge: half the calls pick first on average
let s2 = 0; for (let s = 1; s <= S; s++) s2 += pb.simulate({ b: 0.5, n: 15, seed: s }).pickedFirst / 30; s2 /= S;
ok(Math.abs(s2 - 0.5) < 0.01, "b=0.5 centred", s2);
// edge
ok(pb.simulate({ b: 0.5, n: 0, seed: 1 }) === null, "n=0 -> null", null);
ok(pb.zScore(13, 30) !== null && Math.abs(pb.zScore(15, 30)) < 1e-12, "z of a fair count is 0", pb.zScore(15, 30));
if (!bad) console.log("all checks pass");
else process.exitCode = 1;
