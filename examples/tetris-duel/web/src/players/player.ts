/* What every well has in common, whoever is playing it: the grid, the score,
 * the clock, and what happens when rows fill or the stack reaches the top. */

import { gravity } from "../game/speed.js";
import { H, LINE_SCORES, W, emptyGrid, type Block, type Grid, type PieceKey } from "../game/rules.js";
import type { Supply } from "../game/supply.js";
import { bump, setTag } from "../ui/dom.js";
import type { Screen } from "../ui/screen.js";

/** The scoreboard around one well. */
export interface WellEls {
  score: HTMLElement;
  lines: HTMLElement;
  pieces: HTMLElement;
  time: HTMLElement;
  next: HTMLElement;
  status: HTMLElement;
  stamp: HTMLElement;
}

/** What a well tells the match about, so the match can react without the well knowing it. */
export interface Hooks {
  cleared(player: Player, rows: number): void;
  over(player: Player): void;
}

const FLASH_MS = 230;

export abstract class Player {
  supply: Supply | null = null;
  grid: Grid = emptyGrid();
  score = 0;
  lines = 0;
  placed = 0;
  ms = 0; // how long this well has been in play
  index = 0;
  over = false;
  hold = 0; // ms of animation the clock has to wait for
  clearing: number[] | null = null;
  fall = 0;

  constructor(
    readonly name: string,
    readonly screen: Screen,
    readonly els: WellEls,
    protected readonly hooks: Hooks
  ) {}

  reset(supply: Supply | null): void {
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

  abstract tick(dt: number): void;
  abstract paint(): void;

  /** The level this well has reached: one more every ten rows. */
  get stage(): number {
    return Math.floor(this.lines / 10) + 1;
  }

  get gravity(): number {
    return gravity(this.lines);
  }

  get piece(): PieceKey | null {
    return this.supply ? this.supply.at(this.index) : null;
  }

  get next(): PieceKey | null {
    return this.supply ? this.supply.at(this.index + 1) : null;
  }

  /** Pieces dealt since the last straight bar — one per bag, so the wait matters. */
  sinceBar(): number {
    if (!this.supply) return 0;
    for (let back = 1; back <= this.index; back++) {
      if (this.supply.at(this.index - back) === "I") return back - 1;
    }
    return this.index;
  }

  /** Lock cells in, flash any full rows, and hand the score over after the flash. */
  settle(cells: Block[]): number {
    for (const [x, y, piece] of cells) {
      if (y >= 0) this.grid[y]![x] = piece;
    }
    this.placed += 1;
    this.index += 1;
    const full: number[] = [];
    this.grid.forEach((row, y) => row.every((cell) => cell) && full.push(y));
    if (!full.length) return 0;
    this.clearing = full;
    this.hold = FLASH_MS;
    return full.length;
  }

  finishClear(): number {
    const rows = this.clearing ?? [];
    this.clearing = null;
    this.grid = this.grid.filter((_, y) => !rows.includes(y));
    while (this.grid.length < H) this.grid.unshift(Array<PieceKey | null>(W).fill(null));
    this.lines += rows.length;
    this.score += LINE_SCORES[rows.length]! * this.stage;
    bump(this.els.score, this.score);
    bump(this.els.lines, this.lines);
    this.hooks.cleared(this, rows.length);
    return rows.length;
  }

  topOut(tag = "topped out"): void {
    this.over = true;
    this.els.stamp.textContent = tag;
    this.els.stamp.hidden = false;
    setTag(this.els.status, "done", "is-over");
    this.hooks.over(this);
  }
}
