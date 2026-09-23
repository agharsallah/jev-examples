/* Drawing a well: a grid of cells, repainted only where something changed. */
import { drawing } from "../game/pieces.js";
import { H, W } from "../game/rules.js";
export class Screen {
    el;
    cells = [];
    last = Array(W * H).fill("");
    constructor(el) {
        this.el = el;
        for (let i = 0; i < W * H; i++) {
            const cell = document.createElement("div");
            cell.className = "cell";
            el.appendChild(cell);
            this.cells.push(cell);
        }
    }
    /** The settled grid, then the ghost of where the piece lands, then the piece itself. */
    paint(grid, active = [], ghost = [], flash = []) {
        const klass = Array(W * H).fill("");
        const colour = Array(W * H).fill("");
        grid.forEach((row, y) => row.forEach((piece, x) => {
            if (piece) {
                klass[y * W + x] = "cell on";
                colour[y * W + x] = piece;
            }
        }));
        for (const [x, y, piece] of ghost) {
            if (y >= 0 && !klass[y * W + x]) {
                klass[y * W + x] = "cell ghost";
                colour[y * W + x] = piece;
            }
        }
        for (const [x, y, piece] of active) {
            if (y >= 0) {
                klass[y * W + x] = "cell on";
                colour[y * W + x] = piece;
            }
        }
        for (const y of flash) {
            for (let x = 0; x < W; x++)
                klass[y * W + x] = "cell flash";
        }
        klass.forEach((name, i) => {
            const want = (name || "cell") + colour[i];
            if (this.last[i] === want)
                return;
            this.cells[i].className = name || "cell";
            this.cells[i].style.setProperty("--c", colour[i] ? `var(--${colour[i]})` : "transparent");
            this.last[i] = want;
        });
    }
}
/** The little "next piece" preview. */
export function drawMini(el, piece) {
    el.innerHTML = "";
    if (!piece)
        return;
    for (const row of drawing(piece)) {
        const line = document.createElement("div");
        line.className = "row";
        for (const ch of row) {
            const blk = document.createElement("div");
            blk.className = ch === "#" ? "blk" : "gap";
            if (ch === "#")
                blk.style.setProperty("--c", `var(--${piece})`);
            line.appendChild(blk);
        }
        el.appendChild(line);
    }
}
