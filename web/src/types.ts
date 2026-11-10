export type MetricKey = 'diameter_m' | 'velocity_km_s' | 'miss_distance_km'

export interface Asteroid {
  name: string
  date: string
  diameter_m: number
  velocity_km_s: number
  miss_distance_km: number
  distance_ld: number
  is_hazardous: boolean
  is_sentry_object: boolean
  attention_score: number
  is_outlier: boolean
  outlier_reasons: MetricKey[]
}

export interface MetricBaseline {
  count: number
  median: number
  q1: number
  q3: number
  iqr: number
  lower_fence: number
  upper_fence: number
  min: number
  max: number
  mean: number
  values: number[]
}

export interface Baseline {
  source: 'history' | 'recent'
  start: string
  end: string
  count: number
  metrics: Record<MetricKey, MetricBaseline>
  comparison: { metric: MetricKey; recent_median: number; baseline_median: number; ratio: number }[] | null
  weekly: { week: string; count: number; hazardous_pct: number; median_diameter_m: number }[] | null
}

export interface SentryObject {
  name: string
  years: string
  impact_probability: number
  palermo_cum: number
  torino_max: number
  diameter_m: number | null
  n_impacts: number
}

export interface SentryMatch {
  name: string
  date: string
  distance_ld: number
  diameter_m: number
  sentry_impact_probability: number
  sentry_palermo_cum: number
  sentry_years: string
}

export interface Sentry {
  count: number
  updated_at: string
  torino_positive: string[]
  max_palermo: number
  top: SentryObject[]
  recent_matches: SentryMatch[]
  recent_flagged: string[]
}

export interface CloseApproach {
  designation: string
  datetime_utc: string
  date: string
  distance_km: number
  distance_ld: number
  velocity_km_s: number
  abs_magnitude_h: number | null
  diameter_m: number | null
  diameter_estimated: boolean
}

export interface Payload {
  generated_at: string
  is_sample: boolean
  recent: { start: string; end: string; updated_at: string; asteroids: Asteroid[] } | null
  baseline: Baseline
  sentry: Sentry | null
  close_approach: { updated_at: string; items: CloseApproach[] } | null
}
