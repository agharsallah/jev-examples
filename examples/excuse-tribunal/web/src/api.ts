// The court's HTTP surface. These types mirror payload.py field for field, so
// a change to one side is a change to both.

export interface Measure {
  label: string;
  /** On the 0-4 scale every Score uses. */
  value: number;
  detail: string;
}

export interface Charge {
  label: string;
  probability: number;
  /** True for aggravating findings, false for mitigating ones. */
  against: boolean;
}

export interface RankedArchetype {
  name: string;
  probability: number;
  chosen: boolean;
}

export interface Verdict {
  excuse: string;
  ruling: string;
  headline: string;
  sentence: string;
  mistrial: boolean;
  remarks: string[];
  /** Jev's confidence in the believability reading. */
  confidence: number;
  measures: Measure[];
  charges: Charge[];
  archetype: { name: string; confidence: number; ranked: RankedArchetype[] };
}

export interface Hearing {
  /** ISO timestamp, UTC, to the second. */
  when: string;
  excuse: string;
  ruling: string;
  archetype: string;
  believability: number;
}

export interface RecordSummary {
  hearings: number;
  average_believability: number;
  signature_move: string | null;
}

export interface CourtRecord {
  hearings: Hearing[];
  summary: RecordSummary;
}

export interface Plea {
  excuse: string;
  context: string | null;
  audience: string | null;
}

/** What POST /api/judge settles into: a verdict, or the clerk's reason why not. */
export type HearingOutcome = { ok: true; verdict: Verdict } | { ok: false; message: string };

export async function judge(plea: Plea): Promise<HearingOutcome> {
  const response = await fetch("/api/judge", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(plea),
  });
  const data = await response.json();
  if (!response.ok) {
    return { ok: false, message: data.error || `The clerk returned ${response.status}.` };
  }
  return { ok: true, verdict: data as Verdict };
}

export async function fetchRecord(): Promise<CourtRecord> {
  const response = await fetch("/api/record");
  return (await response.json()) as CourtRecord;
}

export async function expungeRecord(): Promise<void> {
  await fetch("/api/record", { method: "DELETE" });
}
