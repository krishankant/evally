// Agreement between a grader and a person, with "fail" as the class we hunt for.
// Used by kappa.html and checked by tests/demos/check-kappa.js.

function confusion(human, grader) {
  const c = { tp: 0, fp: 0, fn: 0, tn: 0 };
  human.forEach((h, i) => {
    const hf = h === "fail", gf = grader[i] === "fail";
    if (hf && gf) c.tp++; else if (gf) c.fp++; else if (hf) c.fn++; else c.tn++;
  });
  return c;
}

function parts({ tp, fp, fn, tn }) {
  const n = tp + fp + fn + tn;
  const po = (tp + tn) / n;                       // observed agreement
  const humanFail = (tp + fn) / n, graderFail = (tp + fp) / n;
  const pe = humanFail * graderFail + (1 - humanFail) * (1 - graderFail);  // agreement by chance
  return { n, po, pe };
}

// Cohen's kappa; null when chance agreement is 1 (both always give the same single label).
function kappa(c) {
  const { n, po, pe } = parts(c);
  if (n === 0 || pe >= 1) return null;
  return (po - pe) / (1 - pe);
}

function precisionRecall({ tp, fp, fn }) {
  return {
    precision: tp + fp ? tp / (tp + fp) : null,   // of the grader's fails, how many are real
    recall: tp + fn ? tp / (tp + fn) : null,      // of the real fails, how many the grader caught
  };
}

if (typeof module !== "undefined") module.exports = { confusion, parts, kappa, precisionRecall };
