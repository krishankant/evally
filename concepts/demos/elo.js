// From pairwise results to a ranking: Elo (order-dependent) and Bradley-Terry (order-free).
// A game is [winnerSide, loserSide, score] read as [a, b, scoreForA]: 1 = a wins, 0.5 = tie, 0 = b wins.
// Used by elo.html, checked by tests/demos/check-elo.js.

const expected = (ra, rb) => 1 / (1 + Math.pow(10, (rb - ra) / 400));

function eloUpdate(ra, rb, scoreA, k = 32) {
  const ea = expected(ra, rb);
  return [ra + k * (scoreA - ea), rb + k * ((1 - scoreA) - (1 - ea))];
}

function players(games) { return [...new Set(games.flatMap(([a, b]) => [a, b]))]; }

function runElo(games, k = 32, start = 1500) {
  const r = Object.fromEntries(players(games).map(p => [p, start]));
  for (const [a, b, s] of games) [r[a], r[b]] = eloUpdate(r[a], r[b], s, k);
  return r;
}

// Bradley-Terry: P(i beats j) = p_i / (p_i + p_j), fitted by maximum likelihood with
// Hunter's MM updates. Ties count half a win to each side. null when a player has no wins
// or no losses (its strength runs off to 0 or infinity).
function bradleyTerry(games, iters = 1000) {
  const ps = players(games), W = {}, N = {};
  ps.forEach(p => { W[p] = 0; N[p] = {}; ps.forEach(q => N[p][q] = 0); });
  for (const [a, b, s] of games) { W[a] += s; W[b] += 1 - s; N[a][b]++; N[b][a]++; }
  for (const p of ps) { const n = ps.reduce((t, q) => t + N[p][q], 0); if (W[p] <= 0 || W[p] >= n) return null; }
  let str = Object.fromEntries(ps.map(p => [p, 1]));
  for (let it = 0; it < iters; it++) {
    const next = {};
    for (const p of ps) {
      let d = 0; for (const q of ps) if (q !== p && N[p][q]) d += N[p][q] / (str[p] + str[q]);
      next[p] = W[p] / d;
    }
    const g = Math.exp(ps.reduce((t, p) => t + Math.log(next[p]), 0) / ps.length);   // geometric mean 1
    ps.forEach(p => next[p] /= g); str = next;
  }
  return str;
}

// Strength on an Elo-like scale (400 points = 10x odds), centred on 1500.
const btToElo = (s) => 1500 + 400 * Math.log10(s);

const winRate = (w, l, t) => (w + l + t) ? (w + t / 2) / (w + l + t) : null;

if (typeof module !== "undefined") module.exports = { expected, eloUpdate, runElo, bradleyTerry, btToElo, winRate, players };
