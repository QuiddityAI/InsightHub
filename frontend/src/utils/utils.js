
import * as math from 'mathjs'

export function normalizeArray(a, gamma=1.0, max_default=1.0) {
  if (a.length === 0) return a;
  a = math.subtract(a, math.min(a))
  return math.dotPow(math.divide(a, math.max(math.max(a), max_default)), gamma)
}

export function normalizeArrayMedianGamma(a, max_default=1.0) {
  if (a.length === 0) return a;
  const aMin = math.min(a);
  const aMax = math.max(a);
  if (aMin == aMax) {
    return [1.0] * a.length;
  }
  a = math.subtract(a, math.min(a))
  a = math.divide(a, math.max(math.max(a), max_default))
  // using the median as gamma should provide a good, balanced distribution:
  const gamma = math.max(0.1, math.median(a) * 0.6)
  return math.dotPow(a, gamma)
}
