const p = require(process.argv[2]);
let bad = 0; const ok = (c, m, g) => { if (!c) { console.log("FAIL", m, g); bad++; } };
const near = (a, b, t = 1e-9) => a !== null && Math.abs(a - b) < t;
// percentile, linear interpolation (numpy's default)
const lat = [0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5, 2.0, 4.0, 9.5];
ok(near(p.percentile(lat, 50), 1.25), "p50", p.percentile(lat, 50));
ok(near(p.percentile(lat, 95), 7.025), "p95", p.percentile(lat, 95));
ok(near(p.percentile(lat, 99), 9.005), "p99", p.percentile(lat, 99));
ok(near(p.percentile([5], 95), 5), "single value", p.percentile([5], 95));
ok(p.percentile([], 50) === null, "empty -> null", null);
// Pareto front: maximise quality, minimise cost
const pts = [
  { name: "A", quality: 0.80, cost: 4.0 },
  { name: "B", quality: 0.75, cost: 1.0 },
  { name: "C", quality: 0.70, cost: 2.0 },   // dominated by B (worse quality, higher cost)
  { name: "D", quality: 0.80, cost: 4.0 },   // tie with A: both stay
  { name: "E", quality: 0.60, cost: 0.2 },
];
const front = p.paretoFront(pts).map(x => x.name).sort().join(",");
ok(front === "A,B,D,E", "front excludes only the dominated point", front);
ok(p.paretoFront([]) === null, "empty -> null", null);
ok(near(p.qualityPerDollar({ quality: 0.75, cost: 1.5 }), 0.5), "quality per dollar", null);
ok(p.qualityPerDollar({ quality: 0.5, cost: 0 }) === null, "free -> null (undefined ratio)", null);
if (!bad) console.log("all checks pass"); else process.exitCode = 1;
