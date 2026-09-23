/* Everything the page asks the server, and the shapes of the answers.
 *
 * These types mirror outbox/web/payload.py field for field; if the payload
 * changes, this is the file that has to follow. Two calls matter: /api/read
 * asks Jev, /api/rescore never does. */

export type Verdict = "SEND IT" | "TIGHTEN IT" | "REWRITE IT" | "DO NOT SEND" | "UNREADABLE";
export type Severity = "blocker" | "major" | "minor" | "good";
export type RailVerdict = "unsure" | "in band" | "too low" | "too high";
export type Probe =
  | "carries_the_ask" | "barbed" | "hedged" | "ambiguous" | "sensitive" | "cuttable";

export interface Band { low: number; high: number; weight: number }

export interface Audience {
  key: string;
  label: string;
  wants: string;
  bands: Record<string, Band>;
}

export interface Sample {
  draft: string;
  to: string | null;
  goal: string | null;
  channel: string | null;
}

/** GET /api/desk: the readers on offer and the drafts to try. */
export interface DeskConfig { audiences: Audience[]; samples: Sample[] }

export interface Rail {
  key: string;
  label: string;
  score: number;
  confidence: number;
  low: number;
  high: number;
  weight: number;
  miss: number;
  counted: boolean;
  level: string;
  verdict: RailVerdict;
}

export interface Finding {
  key: string;
  severity: Severity;
  title: string;
  fix: string;
  value: number;
  strength: number;
}

export interface MarkedSentence {
  start: number;
  end: number;
  text: string;
  /** The one highlight this sentence gets, or null if nothing cleared its bar. */
  probe: Probe | null;
  label: string;
  probability: number;
  probes: Record<string, number>;
}

export interface Cost {
  requests: number;
  questions: number;
  inputTokens: number;
  outputTokens: number;
}

/** What Jev said, with none of the interpretation. Handed back on a rescore. */
export interface Measurement {
  draft: string;
  intent: string;
  intent_confidence: number;
  intent_ranked: [string, number][];
  risk: string;
  risk_confidence: number;
  rails: Pick<Rail, "key" | "score" | "confidence" | "level" | "counted">[];
  findings: Finding[];
}

/** What /api/read and /api/rescore both return. */
export interface Payload {
  draft: string;
  verdict: Verdict;
  blurb: string;
  sendScore: number;
  fit: number;
  rescored: boolean;
  audience: { key: string; label: string; wants: string };
  intent: {
    choice: string;
    confidence: number;
    ranked: { name: string; probability: number }[];
  };
  risk: { choice: string; confidence: number };
  rails: Rail[];
  findings: Finding[];
  sentences: MarkedSentence[];
  cost: Cost;
  measurement: Measurement;
}

export interface ReadBody {
  draft: string;
  to: string | null;
  goal: string | null;
  channel: string | null;
  deep: boolean;
}

async function post<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data as T;
}

export async function fetchDesk(): Promise<DeskConfig> {
  const response = await fetch("/api/desk");
  return (await response.json()) as DeskConfig;
}

/** One or two requests to Jev, depending on `deep`. */
export function readDraft(body: ReadBody): Promise<Payload> {
  return post<Payload>("/api/read", body);
}

/** The same measurements, weighed against another reader. No model call. */
export function rescoreDraft(measurement: Measurement, audience: string): Promise<Payload> {
  return post<Payload>("/api/rescore", { measurement, audience });
}
