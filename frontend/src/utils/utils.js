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
  static STRING = "STRING"
  static VECTOR = "VECTOR"
  static INTEGER = "INTEGER"
  static FLOAT = "FLOAT"
  static IDENTIFIER = "IDENTIFIER"
  static CHUNK = "CHUNK"
  static CLASS_PROBABILITY = "CLASS_PROBABILITY"
  static ARBITRARY_OBJECT = "ARBITRARY_OBJECT"
}

export class CollectionItemSizeMode {
  static SMALL = 1
  static MEDIUM = 2
  static FULL = 3
}

export class CollectionItemLayout {
  static COLUMNS = 'columns'
  static GRID = 'grid'
  static SPREADSHEET = 'spreadsheet'
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
  const filteredWords = words.filter(word => word && !stopWords.includes(word.toLowerCase()))
  if (filteredWords.length === 0) return text
  const regex = new RegExp(`\\b(${filteredWords.join("|")})\\b`, "gi")
  return text.replace(regex, (match) => `<b>${match}</b>`)
}

export function get_download_url(local_path) {
  // meant to be used in item rendering definitions
  return local_path ? `/data_backend/download_file/${local_path}` : null
}

export function icon_for_file_suffix(suffix) {
  // from https://www.svgrepo.com/collection/file-types/
  if (!suffix) return "https://www.svgrepo.com/show/81310/file.svg"
  const lowerSuffix = suffix.toLowerCase()
  if (lowerSuffix === "pdf") return "https://www.svgrepo.com/show/56192/pdf.svg"
  if (lowerSuffix === "doc" || lowerSuffix === "docx") return "https://www.svgrepo.com/show/54310/doc.svg"
  if (lowerSuffix === "xls" || lowerSuffix === "xlsx") return "https://www.svgrepo.com/show/44103/xls.svg"
  if (lowerSuffix === "ppt" || lowerSuffix === "pptx") return "https://www.svgrepo.com/show/146106/ppt.svg"
  if (lowerSuffix === "zip" || lowerSuffix === "tar" || lowerSuffix === "gz" || lowerSuffix === "7z") return "https://www.svgrepo.com/show/6172/zip.svg"
  if (lowerSuffix === "jpg" || lowerSuffix === "jpeg") return "https://www.svgrepo.com/show/21642/jpg.svg"
  if (lowerSuffix === "png") return "https://www.svgrepo.com/show/21675/png.svg"
  if (lowerSuffix === "mp3" || lowerSuffix === "wav" || lowerSuffix === "flac") return "https://www.svgrepo.com/show/22847/mp3.svg"
  if (lowerSuffix === "mp4" || lowerSuffix === "avi" || lowerSuffix === "mov" || lowerSuffix === "mkv") return "https://www.svgrepo.com/show/41018/mp4.svg"
  if (lowerSuffix === "txt" || lowerSuffix === "log" || lowerSuffix === "csv") return "https://www.svgrepo.com/show/22837/txt.svg"
  if (lowerSuffix === "folder") return "https://www.svgrepo.com/show/474852/folder.svg"
  return "https://www.svgrepo.com/show/81310/file.svg"
}

export const available_filter_operators = [
  { id: "contains", title: "contains" },
  { id: "does_not_contain", title: "does not contain" },
  { id: "is", title: "is exact" },
  { id: "is_not", title: "is not" },
  { id: "is_empty", title: "is empty" },
  { id: "is_not_empty", title: "is not empty" },
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

export const languages = [
  { 'name': 'English', 'code': 'en', 'flag': '🇬🇧' },
  { 'name': 'German', 'code': 'de', 'flag': '🇩🇪' },
  { 'name': 'French', 'code': 'fr', 'flag': '🇫🇷' },
  { 'name': 'Spanish', 'code': 'es', 'flag': '🇪🇸' },
  { 'name': 'Italian', 'code': 'it', 'flag': '🇮🇹' },
  { 'name': 'Dutch', 'code': 'nl', 'flag': '🇳🇱' },
  { 'name': 'Portuguese', 'code': 'pt', 'flag': '🇵🇹' },
  { 'name': 'Russian', 'code': 'ru', 'flag': '🇷🇺' },
  { 'name': 'Chinese', 'code': 'zh', 'flag': '🇨🇳' },
  { 'name': 'Japanese', 'code': 'ja', 'flag': '🇯🇵' },
  { 'name': 'Korean', 'code': 'ko', 'flag': '🇰🇷' },
  { 'name': 'Arabic', 'code': 'ar', 'flag': '🇸🇦' },
  { 'name': 'Turkish', 'code': 'tr', 'flag': '🇹🇷' },
  { 'name': 'Polish', 'code': 'pl', 'flag': '🇵🇱' },
  { 'name': 'Swedish', 'code': 'sv', 'flag': '🇸🇪' },
  { 'name': 'Finnish', 'code': 'fi', 'flag': '🇫🇮' },
  { 'name': 'Danish', 'code': 'da', 'flag': '🇩🇰' },
  { 'name': 'Norwegian', 'code': 'no', 'flag': '🇳🇴' },
  { 'name': 'Greek', 'code': 'el', 'flag': '🇬🇷' },
  { 'name': 'Czech', 'code': 'cs', 'flag': '🇨🇿' },
  { 'name': 'Hungarian', 'code': 'hu', 'flag': '🇭🇺' },
]

export function update_array(old_arr, new_arr) {
  // update the array in-place
  // Ensure old_arr has enough elements
  while (old_arr.length < new_arr.length) {
    old_arr.push(undefined);
  }
  for (let i = 0; i < new_arr.length; i++) {
    if (typeof new_arr[i] === "object" && new_arr[i] !== null && !Array.isArray(new_arr[i])
      && typeof old_arr[i] === "object" && old_arr[i] !== null && !Array.isArray(old_arr[i])) {
      update_object(old_arr[i], new_arr[i])
    } else if (Array.isArray(new_arr[i]) && Array.isArray(old_arr[i])) {
      update_array(old_arr[i], new_arr[i])
    } else {
      old_arr[i] = new_arr[i]
    }
  }
  // Remove extra elements
  while (old_arr.length > new_arr.length) {
    old_arr.pop();
  }
}

export function update_object(old_obj, new_obj) {
  // update the object in-place
  for (const key in new_obj) {
    if (typeof new_obj[key] === "object" && new_obj[key] !== null && !Array.isArray(new_obj[key])
      && typeof old_obj[key] === "object" && old_obj[key] !== null && !Array.isArray(old_obj[key])) {
      update_object(old_obj[key], new_obj[key])
    } else if (Array.isArray(new_obj[key]) && Array.isArray(old_obj[key])) {
      update_array(old_obj[key], new_obj[key])
    } else {
      old_obj[key] = new_obj[key]
    }
  }
  // Remove extra keys
  for (const key in old_obj) {
    if (!(key in new_obj)) {
      delete old_obj[key]
    }
  }
}

