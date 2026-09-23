/* Your well: the keyboard moves the piece, gravity does the rest. */

import { turns } from "../game/pieces.js";
import { H, W, width, type Block, type Shape } from "../game/rules.js";
import type { Supply } from "../game/supply.js";
import { drawMini } from "../ui/screen.js";
import { Player } from "./player.js";

const KICKS = [0, -1, 1, -2, 2];

export class Human extends Player {
  private rot = 0;
  private shape: Shape | null = null;
  private x = 0;
  private y = 0;

  override reset(supply: Supply | null): void {
    super.reset(supply);
    this.shape = null;
    if (this.piece) this.spawn();
  }

  private spawn(): void {
    const piece = this.piece!;
    this.rot = 0;
    this.shape = turns(piece)[0]!;
    this.x = Math.floor((W - width(this.shape)) / 2);
    this.y = 0;
    this.fall = 0;
    drawMini(this.els.next, this.next);
    if (!this.fits(this.shape, this.x, this.y)) this.topOut();
  }

  private cells(shape = this.shape!, x = this.x, y = this.y): Block[] {
    return shape.map(([cx, cy]): Block => [cx + x, cy + y, this.piece!]);
  }

  private fits(shape: Shape, x: number, y: number): boolean {
    return shape.every(([cx, cy]) => {
      const gx = cx + x;
      const gy = cy + y;
      return gx >= 0 && gx < W && gy < H && (gy < 0 || !this.grid[gy]![gx]);
    });
  }

  move(dx: number, dy: number): boolean {
    if (this.over || this.clearing || !this.shape) return false;
    if (!this.fits(this.shape, this.x + dx, this.y + dy)) return false;
    this.x += dx;
    this.y += dy;
    return true;
  }

  rotate(dir: number): void {
    if (this.over || this.clearing || !this.shape) return;
    const shapes = turns(this.piece!);
    const rot = (this.rot + dir + shapes.length) % shapes.length;
    const shape = shapes[rot]!;
    for (const kick of KICKS) {
      if (this.fits(shape, this.x + kick, this.y)) {
        this.rot = rot;
        this.shape = shape;
        this.x += kick;
        return;
      }
    }
  }

  private ghost(): Block[] {
    let y = this.y;
    while (this.fits(this.shape!, this.x, y + 1)) y += 1;
    return this.cells(this.shape!, this.x, y);
  }

  lock(): void {
    if (this.over || !this.shape) return;
    this.settle(this.cells());
    if (!this.clearing) this.spawn();
  }

  hardDrop(): void {
    if (this.over || this.clearing) return;
    while (this.move(0, 1));
    this.lock();
  }

  tick(dt: number): void {
    if (this.over) return;
    this.ms += dt;
    if (this.hold > 0) {
      this.hold -= dt;
      if (this.hold <= 0 && this.clearing) {
        this.finishClear();
        this.spawn();
      }
      return;
    }
    this.fall += dt;
    if (this.fall >= this.gravity) {
      this.fall = 0;
      if (!this.move(0, 1)) this.lock();
    }
  }

  paint(): void {
    if (!this.shape || this.over || this.clearing) {
      this.screen.paint(this.grid, [], [], this.clearing ?? []);
    } else {
      this.screen.paint(this.grid, this.cells(), this.ghost());
    }
  }
}
