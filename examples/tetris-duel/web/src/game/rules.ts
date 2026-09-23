/* The well and the pieces: sizes, scoring, and the grid everything draws from. */

export const W = 10;
export const H = 20;

export const KEYS = ["I", "O", "T", "S", "Z", "J", "L"] as const;
export type PieceKey = (typeof KEYS)[number];

/** Points for clearing 0-4 rows at once, before the level multiplier. */
export const LINE_SCORES = [0, 100, 300, 500, 800] as const;
export const CLEAR_NAMES = ["", "single", "double", "triple", "TETRIS!"] as const;

/** A cell in shape coordinates: [x, y], with y growing downwards. */
export type Cell = [number, number];
export type Shape = Cell[];
/** A cell in the well, with the piece that filled it (for its colour). */
export type Block = [number, number, PieceKey];
export type Grid = (PieceKey | null)[][];

export const emptyGrid = (): Grid => Array.from({ length: H }, () => Array<PieceKey | null>(W).fill(null));

export const width = (shape: Shape): number => Math.max(...shape.map((c) => c[0])) + 1;

/** A well as the server reads it: one string per row, '#' filled and '.' empty. */
export const asRows = (grid: Grid): string[] =>
  grid.map((row) => row.map((cell) => (cell ? "#" : ".")).join(""));
