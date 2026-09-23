/* The well and the pieces: sizes, scoring, and the grid everything draws from. */
export const W = 10;
export const H = 20;
export const KEYS = ["I", "O", "T", "S", "Z", "J", "L"];
/** Points for clearing 0-4 rows at once, before the level multiplier. */
export const LINE_SCORES = [0, 100, 300, 500, 800];
export const CLEAR_NAMES = ["", "single", "double", "triple", "TETRIS!"];
export const emptyGrid = () => Array.from({ length: H }, () => Array(W).fill(null));
export const width = (shape) => Math.max(...shape.map((c) => c[0])) + 1;
/** A well as the server reads it: one string per row, '#' filled and '.' empty. */
export const asRows = (grid) => grid.map((row) => row.map((cell) => (cell ? "#" : ".")).join(""));
