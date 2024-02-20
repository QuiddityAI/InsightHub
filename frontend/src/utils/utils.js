import * as math from "mathjs"

export function normalizeArray(a, gamma = 1.0, max_default = 1.0) {
  if (a.length === 0) return a
  a = math.subtract(a, math.min(a))
  return math.dotPow(math.divide(a, math.max(math.max(a), max_default)), gamma)
}

export function normalizeArrayMedianGamma(a, gamma_factor, max_default = 1.0) {
  if (a.length === 0) return a
  const aMin = math.min(a)
  const aMax = math.max(a)
  if (aMin == aMax) {
    return Array(a.length).fill(1.0)
  }
  a = math.subtract(a, aMin)
  a = math.divide(a, math.max(math.max(a), max_default))
  // using the median as gamma should provide a good, balanced distribution:
  const gamma = math.max(0.1, math.median(a) * 2.0 * gamma_factor)
  return math.dotPow(a, gamma)
}

export class FieldType {
  static VECTOR = "VECTOR"
  static INTEGER = "INTEGER"
  static FLOAT = "FLOAT"
  static IDENTIFIER = "IDENTIFIER"
}

export function ellipse(text, length) {
  if (!text) return ""
  let re = new RegExp("(.{" + length + "})..+")
  return text.replace(re, "$1…")
}

export function ensureLength(x, size, fillValue, removeRest = false) {
  if (x.length < size) {
    return Array(size).fill(fillValue)
  } else if (x.length > size && removeRest) {
    // for "computed" arrays like currentPositions, the rest should be removed:
    return x.slice(0, size)
  }
  // for "non-computed" arrays like the saturation values, we want to keep the rest
  // in case the saturation array was loaded before the positions were set
  // the array length is in this case correct on-demand in the updateGeometry() method
  return x
}
