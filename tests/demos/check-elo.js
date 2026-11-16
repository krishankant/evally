const e = require(process.argv[2]);
let bad = 0; const ok = (c, m, g) => { if (!c) { console.log("FAIL", m, g); bad++; } };
const near = (a, b, t) => Math.abs(a - b) < t;
// one game between equals, K = 32
const [ra, rb] = e.eloUpdate(1500, 1500, 1, 32);
ok(near(ra, 1516, 1e-9) && near(rb, 1484, 1e-9), "1500 v 1500 win -> 1516/1484", [ra, rb]);
ok(near(e.expected(1600, 1400), 1 / (1 + Math.pow(10, -0.5)), 1e-12), "expected score at +200", e.expected(1600, 1400));
// the same games, two orders
const games = [["A","B",1],["A","B",1],["B","C",1],["A","C",1],["C","A",1],["B","A",0.5],["C","B",1],["A","C",1]];
const rev = games.slice().reverse();
const e1 = e.runElo(games, 32), e2 = e.runElo(rev, 32);
ok(Math.abs(e1.A - e2.A) > 1, "Elo depends on game order", [e1.A, e2.A]);
const b1 = e.bradleyTerry(games, 2000), b2 = e.bradleyTerry(rev, 2000);
ok(["A","B","C"].every(p => near(b1[p], b2[p], 1e-6)), "BT does not depend on order", [b1, b2]);
// BT strengths reproduce the data: for two players with 3-1 record, P(A beats B) = 0.75
const bt2 = e.bradleyTerry([["A","B",1],["A","B",1],["A","B",1],["B","A",1]], 5000);
ok(near(bt2.A / (bt2.A + bt2.B), 0.75, 1e-6), "BT matches 3-1 record", bt2);
// win rate with ties
ok(near(e.winRate(10, 0, 5), (10 + 2.5) / 15, 1e-12), "win rate counts a tie as half", e.winRate(10, 0, 5));
ok(e.winRate(0, 0, 0) === null, "no games -> null", null);
// a player who never won: BT strength can't be estimated
ok(e.bradleyTerry([["A","B",1],["A","B",1]], 100) === null, "unbeaten/winless -> null", null);
if (!bad) console.log("all checks pass"); else process.exitCode = 1;
