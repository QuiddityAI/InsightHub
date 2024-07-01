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
  static TEXT = "TEXT"
  static VECTOR = "VECTOR"
  static INTEGER = "INTEGER"
  static FLOAT = "FLOAT"
  static IDENTIFIER = "IDENTIFIER"
  static CHUNK = "CHUNK"
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

export function highlight_words_in_text(text, words) {
  if (!text || !words || words.length === 0) return text
  // strip quotation marks at the beginning or end from words
  words = words.map(word => word.replace(/^["']|["']$/g, ""))
  const stopWords = ["a", "an", "and", "be", "the", "in", "on", "is", "are", "was", "were", "to", "for", "of", "can"]
  const filteredWords = words.filter(word => !stopWords.includes(word.toLowerCase()))
  const regex = new RegExp(`\\b(${filteredWords.join("|")})\\b`, "gi")
  return text.replace(regex, (match) => `<b>${match}</b>`)
}

export function get_download_url(local_path) {
  // meant to be used in item rendering definitions
  return local_path ? `/data_backend/download_file/${local_path}` : null
}

export const available_filter_operators = [
  { id: "contains", title: "contains" },
  { id: "does_not_contain", title: "does not contain" },
  { id: "is", title: "is exact" },
  { id: "is_not", title: "is not" },
  // { id: "is_empty", title: "is empty" },
  // { id: "is_not_empty", title: "is not empty" },
  { id: "lt", title: "<" },
  { id: "lte", title: "<=" },
  { id: "gt", title: ">" },
  { id: "gte", title: ">=" },
]


export function debounce(func, timeout = 300) {
  let timer
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => { func.apply(this, args); }, timeout);
  };
}
