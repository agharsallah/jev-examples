/* The seven pieces and their rotations, as the server defines them. */
import { KEYS } from "./rules.js";
let shapes = {};
const rotations = {};
const normalize = (cells) => {
    const left = Math.min(...cells.map((c) => c[0]));
    const top = Math.min(...cells.map((c) => c[1]));
    return cells
        .map(([x, y]) => [x - left, y - top])
        .sort((a, b) => a[0] - b[0] || a[1] - b[1]);
};
const turn = (cells) => {
    const bottom = Math.max(...cells.map((c) => c[1]));
    return normalize(cells.map(([x, y]) => [bottom - y, x]));
};
/** Every distinct rotation of a piece drawn as rows of '#' and '.', in turning order. */
function orientations(rows) {
    const cells = [];
    rows.forEach((row, y) => [...row].forEach((ch, x) => ch === "#" && cells.push([x, y])));
    const out = [];
    let shape = normalize(cells);
    for (let i = 0; i < 4; i++) {
        const key = JSON.stringify(shape);
        if (!out.some((s) => JSON.stringify(s) === key))
            out.push(shape);
        shape = turn(shape);
    }
    return out;
}
/** Take the piece drawings from /api/setup, so the page and the server agree on every shape. */
export function loadPieces(drawings) {
    shapes = drawings;
    for (const key of KEYS)
        rotations[key] = orientations(drawings[key]);
}
export const drawing = (piece) => shapes[piece];
export const turns = (piece) => rotations[piece];
