/* The seven pieces and their rotations, as the server defines them. */

import { KEYS, type PieceKey, type Shape } from "./rules.js";

let shapes = {} as Record<PieceKey, string[]>;
const rotations = {} as Record<PieceKey, Shape[]>;

const normalize = (cells: Shape): Shape => {
  const left = Math.min(...cells.map((c) => c[0]));
  const top = Math.min(...cells.map((c) => c[1]));
  return cells
    .map(([x, y]): [number, number] => [x - left, y - top])
    .sort((a, b) => a[0] - b[0] || a[1] - b[1]);
};

const turn = (cells: Shape): Shape => {
  const bottom = Math.max(...cells.map((c) => c[1]));
  return normalize(cells.map(([x, y]): [number, number] => [bottom - y, x]));
};

/** Every distinct rotation of a piece drawn as rows of '#' and '.', in turning order. */
function orientations(rows: string[]): Shape[] {
  const cells: Shape = [];
  rows.forEach((row, y) => [...row].forEach((ch, x) => ch === "#" && cells.push([x, y])));
  const out: Shape[] = [];
  let shape = normalize(cells);
  for (let i = 0; i < 4; i++) {
    const key = JSON.stringify(shape);
    if (!out.some((s) => JSON.stringify(s) === key)) out.push(shape);
    shape = turn(shape);
  }
  return out;
}

/** Take the piece drawings from /api/setup, so the page and the server agree on every shape. */
export function loadPieces(drawings: Record<PieceKey, string[]>): void {
  shapes = drawings;
  for (const key of KEYS) rotations[key] = orientations(drawings[key]);
}

export const drawing = (piece: PieceKey): string[] => shapes[piece];
export const turns = (piece: PieceKey): Shape[] => rotations[piece];
