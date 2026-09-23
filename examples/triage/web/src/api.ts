/* The shapes the server sends, mirrored from triage/triage.py and policy.py,
 * and the handful of calls the page makes. */

export interface ChoiceAnswer {
  type: "choice";
  choice: string;
  probabilities: Record<string, number>;
  confidence: number;
}
export interface ScoreAnswer {
  type: "score";
  score: number;
  probabilities: Record<string, number>;
  levels: number;
  confidence: number;
}
export interface NoulAnswer {
  type: "noul";
  noul: number;
}
export type Answer = ChoiceAnswer | ScoreAnswer | NoulAnswer;

export interface Unit {
  index: number;
  text: string;
  start: number;
  end: number;
  kind: "sentence" | "item" | "code" | "heading";
  asked: boolean;
}

export interface Family {
  key: string;
  role: string;
  title: string;
  labels: string[];
  mode: "choice" | "nouls";
  descriptions: Record<string, string>;
}

export interface RoleReading {
  role: string;
  confidence: number;
  probabilities: Record<string, number>;
  prefix: string | null;
  issues: number;
}

export interface Taxonomy {
  repo: string;
  roles: Record<string, RoleReading>;
  families: Family[];
  ignored: Record<string, string>;
  reading: { input_tokens: number; latency_s: number; cost_usd: number; cached: boolean } | null;
}

export interface Measurement {
  repo: { slug: string; description: string; url: string };
  issue: {
    number: number;
    title: string;
    url: string;
    state: string;
    author: string;
    association: string;
    created_at: string;
    labels: string[];
    comments: number;
  };
  body: string;
  units: Unit[];
  candidates: { number: number; title: string; state: string; url: string }[];
  taxonomy: Taxonomy;
  answers: Record<string, Answer>;
  usage: {
    model: string;
    input_tokens: number;
    latency_s: number;
    cost_usd: number;
    cached: boolean;
    questions: number;
  };
}

export interface SuggestedLabel {
  label: string;
  family: string;
  family_mode: "choice" | "nouls";
  p: number;
  confidence: number | null;
  status: "apply" | "confirm" | "unsure";
}

export interface Rule {
  rule: string;
  value: number | string | null;
  threshold: number | string | null;
  fired: boolean;
  note: string;
}

export interface Evidence {
  target: string;
  index: number;
  signal: string;
  p_target: number;
  p_neutral: number;
  probabilities: Record<string, number>;
}

export interface Duplicate {
  number: number;
  title: string;
  state: string;
  url: string;
  same: number;
  related: number;
  verdict: "duplicate" | "related" | "unrelated";
}

export interface Drift {
  family: string;
  current: string;
  suggested: string;
  p_current: number;
  p_suggested: number;
}

export interface Assessment {
  lane: string;
  lanes: string[];
  labels: SuggestedLabel[];
  priority: number;
  priority_parts: Record<string, number>;
  missing: string[];
  reply: string | null;
  duplicates: Duplicate[];
  drift: Drift[];
  evidence: { kind?: Evidence[]; comp?: Evidence[] };
  trace: Rule[];
}

export interface Settings {
  [key: string]: number | Record<string, number>;
  weights: Record<string, number>;
}

export interface Meta {
  defaults: Settings;
  lanes: Record<string, string>;
  levels: Record<string, string[]>;
  examples: string[];
}

export interface IssueResult {
  measurement: Measurement;
  assessment: Assessment;
  request: { state: unknown; questions: Record<string, unknown> };
}

export interface RepoResult {
  repo: {
    slug: string;
    description: string;
    url: string;
    open_issues: number;
    labels: { name: string; description: string; color: string; issues: number; pull_requests: number }[];
  };
  taxonomy: Taxonomy;
}

export interface Move {
  target: string;
  before: number;
  after: number;
  now: string | null;
  flipped: boolean;
}

export interface Counterfactual {
  removed: number[];
  moves: Record<string, Move>;
  input_tokens: number;
  cost_usd: number;
  latency_s: number;
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  const body = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
  if (!response.ok || body.error) throw new Error(body.error ?? `HTTP ${response.status}`);
  return body as T;
}

function post<T>(path: string, payload: unknown): Promise<T> {
  return call<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export const api = {
  meta: () => call<Meta>("/api/meta"),
  repo: (ref: string) => call<RepoResult>(`/api/repo?ref=${encodeURIComponent(ref)}`),
  issue: (ref: string, fresh = false) => post<IssueResult>("/api/issue", { ref, fresh }),
  rescore: (measurement: Measurement, settings: Settings) =>
    post<{ assessment: Assessment }>("/api/rescore", { measurement, settings }),
  counterfactual: (ref: string, removals: number[][]) =>
    post<{ results: Counterfactual[] }>("/api/counterfactual", { ref, removals }),
};

export interface QueueRow {
  number: number;
  title: string;
  url: string;
  state: string;
  labels: string[];
  kind: string;
  kind_confidence: number;
  assessment: Assessment;
}

export interface Totals {
  issues: number;
  requests: number;
  fresh_requests: number;
  questions: number;
  input_tokens: number;
  cost_usd: number;
  wall_s: number;
  mean_latency_s: number;
  defanged: number;
  skipped: { number: number; title: string; url: string }[];
}

export interface ScanResult {
  repo: string;
  taxonomy: Taxonomy;
  rows: QueueRow[];
  measurements: Measurement[];
  totals: Totals;
}

export interface EvalFamily {
  family: string;
  key: string;
  n: number;
  agreement: number;
  top2: number;
  abstained: number;
  macro_f1: number | null;
  ece: number;
  reliability: { bin: number; lo: number; hi: number; n: number; mean_p: number; accuracy: number }[];
  coverage: { threshold: number; coverage: number; accuracy: number | null }[];
  confusion: { labels: string[]; cells: number[][] };
  confusions: { truth: string; pick: string; n: number }[];
  top_confusion_share: number;
  disagreements: { number: number; title: string; url: string; truth: string[]; pick: string; p: number; p_truth: number }[];
}

export interface EvalReport {
  repo: string;
  families: EvalFamily[];
  totals: Totals;
}

export const queueApi = {
  scan: (ref: string, limit: number, settings: Settings) =>
    post<ScanResult>("/api/scan", { ref, limit, settings }),
  rescore: (measurements: Measurement[], taxonomy: Taxonomy, settings: Settings) =>
    post<{ rows: QueueRow[] }>("/api/scan/rescore", { measurements, taxonomy, settings }),
  evaluate: (ref: string, limit: number) => post<EvalReport>("/api/eval", { ref, limit }),
};

export interface OverviewRow {
  number: number;
  title: string;
  url: string;
  author: string;
  labels: string[];
  comments: number;
  age_days: number | null;
  idle_days: number | null;
  kind: string;
  kind_confidence: number;
  component: string | null;
  component_p: number;
  lane: string;
  lanes: string[];
  priority: number;
  readiness: number;
  readiness_parts: Record<string, number>;
  beginner: number;
  beginner_parts: Record<string, number>;
  impact: number;
  scope: number;
  frustration: number;
  needs_decision: number;
  security: number;
  low_effort: number;
  waiting_on_reporter: number;
  fixed_in_thread: number;
  missing: string[];
  beginner_label: string | null;
  beginner_label_p: number | null;
  suggested: { label: string; status: string; p: number }[];
  drift: Drift[];
  cost_usd: number;
}

export interface OverviewEdge {
  a: number;
  b: number;
  b_title: string;
  b_state: string;
  b_url: string;
  same: number;
  related: number;
}

export interface Overview {
  repo: { slug: string; url: string; description: string; open_issues: number; read: number };
  rows: OverviewRow[];
  edges: OverviewEdge[];
  breakdown: {
    component_kind: { component: string; total: number; kinds: Record<string, number> }[];
    lanes: Record<string, number>;
    kinds: Record<string, number>;
  };
  weights: { readiness: Record<string, number>; beginner: Record<string, number> };
  lanes: Record<string, string>;
  totals: Totals;
  saved_at: number;
  limit: number | null;
}

export interface Job<T> {
  status: "running" | "done" | "failed";
  done: number;
  total: number;
  result?: T;
  error?: string;
}

export const overviewApi = {
  start: (ref: string, limit: number | null, refresh: boolean) =>
    post<{ job: string }>("/api/overview", { ref, limit, refresh }),
  /** The last overview saved for this repo, or null. Reads a file; asks nothing. */
  saved: async (ref: string): Promise<Overview | null> => {
    const response = await fetch(`/api/overview/saved?ref=${encodeURIComponent(ref)}`);
    return response.ok ? ((await response.json()) as Overview) : null;
  },
  poll: <T>(job: string) => call<Job<T>>(`/api/jobs/${job}`),
};
