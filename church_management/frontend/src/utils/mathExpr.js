/**
 * Tiny safe arithmetic evaluator for money fields.
 * Supports + - * / with parentheses and decimals, e.g. "500+250*2" or "(100+50)/2".
 * Returns a finite number, or null when the expression is invalid.
 */
export function evaluateExpression(input) {
  const src = String(input ?? "").replace(/[₱,\s]/g, "");
  if (!src) return null;
  if (!/^[\d+\-*/().]+$/.test(src)) return null;

  let pos = 0;

  function parseExpr() {
    let value = parseTerm();
    while (pos < src.length && (src[pos] === "+" || src[pos] === "-")) {
      const op = src[pos++];
      const rhs = parseTerm();
      value = op === "+" ? value + rhs : value - rhs;
    }
    return value;
  }

  function parseTerm() {
    let value = parseFactor();
    while (pos < src.length && (src[pos] === "*" || src[pos] === "/")) {
      const op = src[pos++];
      const rhs = parseFactor();
      value = op === "*" ? value * rhs : value / rhs;
    }
    return value;
  }

  function parseFactor() {
    if (src[pos] === "-") {
      pos++;
      return -parseFactor();
    }
    if (src[pos] === "+") {
      pos++;
      return parseFactor();
    }
    if (src[pos] === "(") {
      pos++;
      const value = parseExpr();
      if (src[pos] !== ")") throw new Error("unbalanced");
      pos++;
      return value;
    }
    const m = /^\d+(\.\d+)?|^\.\d+/.exec(src.slice(pos));
    if (!m) throw new Error("expected number");
    pos += m[0].length;
    return parseFloat(m[0]);
  }

  try {
    const result = parseExpr();
    if (pos !== src.length || !Number.isFinite(result)) return null;
    return result;
  } catch {
    return null;
  }
}

/** True when the string contains math beyond a plain number. */
export function isExpression(input) {
  const src = String(input ?? "").replace(/[₱,\s]/g, "");
  return /[+*/()]/.test(src) || /\d-/.test(src);
}
