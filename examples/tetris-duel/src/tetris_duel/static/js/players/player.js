/* What every well has in common, whoever is playing it: the grid, the score,
 * the clock, and what happens when rows fill or the stack reaches the top. */
import { gravity } from "../game/speed.js";
import { H, LINE_SCORES, W, emptyGrid } from "../game/rules.js";
import { bump, setTag } from "../ui/dom.js";
const FLASH_MS = 230;
export class Player {
    name;
    screen;
    els;
    hooks;
    supply = null;
    grid = emptyGrid();
    score = 0;
    lines = 0;
    placed = 0;
    ms = 0; // how long this well has been in play
    index = 0;
    over = false;
    hold = 0; // ms of animation the clock has to wait for
    clearing = null;
    fall = 0;
    constructor(name, screen, els, hooks) {
        this.name = name;
        this.screen = screen;
        this.els = els;
        this.hooks = hooks;
    }
    reset(supply) {
        this.supply = supply;
        this.grid = emptyGrid();
        this.score = 0;
        this.lines = 0;
        this.placed = 0;
        this.ms = 0;
        this.index = 0;
        this.over = false;
        this.hold = 0;
        this.clearing = null;
        this.fall = 0;
        this.screen.paint(this.grid);
    }
    /** The level this well has reached: one more every ten rows. */
    get stage() {
        return Math.floor(this.lines / 10) + 1;
    }
    get gravity() {
        return gravity(this.lines);
    }
    get piece() {
        return this.supply ? this.supply.at(this.index) : null;
    }
    get next() {
        return this.supply ? this.supply.at(this.index + 1) : null;
    }
    /** Pieces dealt since the last straight bar — one per bag, so the wait matters. */
    sinceBar() {
        if (!this.supply)
            return 0;
        for (let back = 1; back <= this.index; back++) {
            if (this.supply.at(this.index - back) === "I")
                return back - 1;
        }
        return this.index;
    }
    /** Lock cells in, flash any full rows, and hand the score over after the flash. */
    settle(cells) {
        for (const [x, y, piece] of cells) {
            if (y >= 0)
                this.grid[y][x] = piece;
        }
        this.placed += 1;
        this.index += 1;
        const full = [];
        this.grid.forEach((row, y) => row.every((cell) => cell) && full.push(y));
        if (!full.length)
            return 0;
        this.clearing = full;
        this.hold = FLASH_MS;
        return full.length;
    }
    finishClear() {
        const rows = this.clearing ?? [];
        this.clearing = null;
        this.grid = this.grid.filter((_, y) => !rows.includes(y));
        while (this.grid.length < H)
            this.grid.unshift(Array(W).fill(null));
        this.lines += rows.length;
        this.score += LINE_SCORES[rows.length] * this.stage;
        bump(this.els.score, this.score);
        bump(this.els.lines, this.lines);
        this.hooks.cleared(this, rows.length);
        return rows.length;
    }
    topOut(tag = "topped out") {
        this.over = true;
        this.els.stamp.textContent = tag;
        this.els.stamp.hidden = false;
        setTag(this.els.status, "done", "is-over");
        this.hooks.over(this);
    }
}
