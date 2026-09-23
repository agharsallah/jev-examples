/* Everything the page asks the server, and the shapes of the answers.
 *
 * These types mirror web.py and duel.as_payload one to one; if either changes,
 * this is the file that has to follow.
 */

import type { Cell, PieceKey } from "./game/rules.js";

export interface Level {
  key: string;
  label: string;
  blurb: string;
  gravity_ms: number;
  sees: string;
  house_rules: boolean;
  well_guard: boolean;
}

export interface PlayerInfo {
  key: string;
  name: string;
  about: string;
  /** Why this player cannot play right now, or null when it can. */
  blocked: string | null;
  levels: Level[];
}

export interface Setup {
  players: PlayerInfo[];
  well: { width: number; height: number };
  pieces: Record<PieceKey, string[]>;
}

export interface MoveRequest {
  rows: string[];
  piece: PieceKey;
  next: PieceKey | null;
  cleared: number;
  since_bar: number;
  difficulty: string;
}

export interface Option {
  spot: string;
  where: string;
  probability: number;
  rows_cleared: number;
  new_gaps: number;
  chosen: boolean;
  /** The model's own first pick, before any house rule moved it. */
  jev: boolean;
}

/** One move: where the piece goes, and every number behind the choice. */
export interface Plan {
  piece: PieceKey;
  rotation: number;
  cells: Cell[];
  where: string;
  rows_cleared: number;
  new_gaps: number;
  menu_size: number;
  options: Option[];
  confidence: number;
  torn: boolean;
  sure: boolean;
  column: number;
  landing_row: number;
  danger: { value: number; level: string };
  clear_now: number;
  mood: { key: string; line: string };
  overruled: boolean;
  note: string;
  guarding: number | null;
  keep_slot: number | null;
  difficulty: { key: string; label: string; gravity_ms: number };
  model: string;
  usage: { input_tokens?: number; output_tokens?: number };
}

export type MoveAnswer = Plan | { game_over: true } | { error: string };

export async function fetchSetup(): Promise<Setup> {
  return (await fetch("/api/setup")).json() as Promise<Setup>;
}

export async function askMove(player: string, move: MoveRequest): Promise<MoveAnswer> {
  const response = await fetch(`/api/move/${player}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(move),
  });
  return response.json() as Promise<MoveAnswer>;
}

/** Ask a slow player to load before its first piece. Failing here is fine: the move will say why. */
export function warm(player: string): void {
  fetch(`/api/warm/${player}`, { method: "POST" }).catch(() => {});
}
