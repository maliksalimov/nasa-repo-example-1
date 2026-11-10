// Browsers often ship without Azerbaijani locale data, so formatting is done
// with a locale that has the same conventions (1.234,5) and our own month names.
const NUMBER_LOCALE = 'de-DE'
const MONTHS_SHORT = ['yan', 'fev', 'mar', 'apr', 'may', 'iyn', 'iyl', 'avq', 'sen', 'okt', 'noy', 'dek']
const MONTHS_LONG = [
  'yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun',
  'iyul', 'avqust', 'sentyabr', 'oktyabr', 'noyabr', 'dekabr',
]

const integer = new Intl.NumberFormat(NUMBER_LOCALE, { maximumFractionDigits: 0 })
const oneDecimal = new Intl.NumberFormat(NUMBER_LOCALE, { maximumFractionDigits: 1 })
const twoDecimals = new Intl.NumberFormat(NUMBER_LOCALE, { minimumFractionDigits: 2, maximumFractionDigits: 2 })

/** Parses "2026-11-02" as a UTC calendar day, or a full ISO timestamp as-is. */
function toDate(iso: string) {
  return new Date(iso.length === 10 ? `${iso}T00:00:00Z` : iso)
}

const pad = (n: number) => String(n).padStart(2, '0')

export const fmt = {
  int: (value: number) => integer.format(value),
  one: (value: number) => oneDecimal.format(value),
  two: (value: number) => twoDecimals.format(value),
  /** Distances in lunar distances: more precision when close. */
  ld: (value: number) => (value < 10 ? twoDecimals.format(value) : oneDecimal.format(value)),
  meters: (value: number | null) => (value == null ? 'naməlum' : `${integer.format(value)} m`),
  km: (value: number) =>
    value >= 1_000_000 ? `${oneDecimal.format(value / 1_000_000)} mln km` : `${integer.format(value)} km`,
  /** "2026-11-02" -> "2 noy" */
  day: (iso: string) => {
    const d = toDate(iso.slice(0, 10))
    return `${d.getUTCDate()} ${MONTHS_SHORT[d.getUTCMonth()]}`
  },
  /** "2026-11-02" -> "2 noyabr" */
  dayLong: (iso: string) => {
    const d = toDate(iso.slice(0, 10))
    return `${d.getUTCDate()} ${MONTHS_LONG[d.getUTCMonth()]}`
  },
  /** Local time: "8 noy, 21:54" */
  dateTime: (iso: string) => {
    const d = toDate(iso)
    return `${d.getDate()} ${MONTHS_SHORT[d.getMonth()]}, ${pad(d.getHours())}:${pad(d.getMinutes())}`
  },
  /** 0.000571 -> "1 / 1.749" */
  probability: (value: number) => (value > 0 ? `1 / ${integer.format(Math.round(1 / value))}` : 'yoxdur'),
}

export const METRIC_LABELS = {
  diameter_m: 'Diametr',
  velocity_km_s: 'Sürət',
  miss_distance_km: 'Yerə məsafə',
} as const

export function formatMetric(metric: keyof typeof METRIC_LABELS, value: number) {
  if (metric === 'diameter_m') return `${fmt.int(value)} m`
  if (metric === 'velocity_km_s') return `${fmt.one(value)} km/s`
  return fmt.km(value)
}

/** Strip the parentheses NeoWs puts around provisional designations. */
export function displayName(name: string) {
  return name.replace(/^\((.*)\)$/, '$1')
}
