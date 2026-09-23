/* A model's well. Each piece is one question to the server; the answer is a
 * rotation and a column, which the piece then plays out the way a player would. */
import { askMove } from "../api.js";
import { currentLevel } from "../game/speed.js";
import { turns } from "../game/pieces.js";
import { W, asRows, width } from "../game/rules.js";
import { setTag } from "../ui/dom.js";
import { drawMini } from "../ui/screen.js";
import { Player } from "./player.js";
export class Bot extends Player {
    key;
    card;
    state = "idle";
    plan = null;
    shape = null;
    target = { rot: 0, x: 0, y: 0 };
    rot = 0;
    x = 0;
    y = 0;
    keying = 0;
    run = 0; // a restart makes any answer still in flight stale
    constructor(name, screen, els, hooks, key, card) {
        super(name, screen, els, hooks);
        this.key = key;
        this.card = card;
    }
    reset(supply) {
        super.reset(supply);
        this.state = "idle";
        this.plan = null;
        this.shape = null;
        this.keying = 0;
        this.run += 1;
    }
    begin() {
        void this.think();
    }
    /** How long the model takes between one keypress and the next. */
    get keyMs() {
        return Math.max(55, Math.round(this.gravity / 6));
    }
    async think() {
        if (this.over || !this.piece)
            return;
        this.state = "thinking";
        setTag(this.els.status, "thinking…", "is-thinking");
        drawMini(this.els.next, this.next);
        const started = performance.now();
        const run = this.run;
        try {
            const answer = await askMove(this.key, {
                rows: asRows(this.grid),
                piece: this.piece,
                next: this.next,
                cleared: this.lines,
                since_bar: this.sinceBar(),
                difficulty: currentLevel(),
            });
            if (run !== this.run || this.over)
                return; // the match moved on without this answer
            if ("error" in answer)
                return this.offline(answer.error);
            if ("game_over" in answer)
                return this.topOut();
            this.card.show(answer, Math.round(performance.now() - started), this.name);
            this.take(answer);
        }
        catch (error) {
            if (run === this.run)
                this.offline(`Could not reach the server: ${error.message}`);
        }
    }
    /** Put the piece at the top the way you get it, and remember where it has to end up. */
    take(plan) {
        this.plan = plan;
        this.rot = 0;
        this.shape = turns(plan.piece)[0];
        this.x = Math.floor((W - width(this.shape)) / 2);
        this.y = 0;
        this.target = { rot: plan.rotation, x: plan.column, y: plan.landing_row };
        this.state = "lining up";
        this.keying = 0;
        this.fall = 0;
        setTag(this.els.status, "lining up", "is-live");
    }
    /** One keypress: turn it, or walk it one column towards the spot the model chose. */
    press() {
        const shapes = turns(this.plan.piece);
        if (this.rot !== this.target.rot) {
            const cw = (this.target.rot - this.rot + shapes.length) % shapes.length;
            const ccw = (this.rot - this.target.rot + shapes.length) % shapes.length;
            this.rot = (this.rot + (cw <= ccw ? 1 : -1) + shapes.length) % shapes.length;
            this.shape = shapes[this.rot];
            this.x = Math.max(0, Math.min(this.x, W - width(this.shape)));
            return true;
        }
        if (this.x !== this.target.x) {
            this.x += Math.sign(this.target.x - this.x);
            return true;
        }
        return false; // lined up
    }
    /** Sure of the pick? Slam it. Otherwise let it fall and think it over on the way down. */
    release() {
        if (this.plan.sure) {
            this.y = this.target.y;
            this.els.status.textContent = "hard drop";
            this.screen.el.classList.add("slam");
            setTimeout(() => this.screen.el.classList.remove("slam"), 240);
            this.lock();
        }
        else {
            this.state = "dropping";
            setTag(this.els.status, "dropping", "is-live");
        }
    }
    offline(message) {
        this.card.error(message);
        this.state = "error";
        this.topOut(`${this.name.toLowerCase()} offline`);
    }
    cells() {
        if (!this.plan || !this.shape)
            return [];
        const piece = this.plan.piece;
        return this.shape.map(([cx, cy]) => [cx + this.x, cy + this.y, piece]);
    }
    lock() {
        // The plan is what actually gets written in: the walk across the top is theatre.
        const plan = this.plan;
        this.settle(plan.cells.map(([x, y]) => [x, y, plan.piece]));
        this.plan = null;
        this.shape = null;
        if (this.clearing)
            this.state = "clearing";
        else
            void this.think();
    }
    tick(dt) {
        if (this.over)
            return;
        this.ms += dt; // thinking counts: the well is still on the clock
        if (this.hold > 0) {
            this.hold -= dt;
            if (this.hold <= 0 && this.clearing) {
                this.finishClear();
                void this.think();
            }
            return;
        }
        if (this.state === "lining up") {
            this.keying += dt;
            if (this.keying >= this.keyMs) {
                this.keying = 0;
                if (!this.press())
                    this.release();
            }
            return;
        }
        if (this.state !== "dropping")
            return;
        this.fall += dt;
        if (this.fall >= this.gravity) {
            this.fall = 0;
            if (this.y < this.target.y)
                this.y += 1;
            else
                this.lock();
        }
    }
    paint() {
        if (this.clearing)
            this.screen.paint(this.grid, [], [], this.clearing);
        else if (this.plan && this.shape) {
            const piece = this.plan.piece;
            const ghost = this.plan.cells.map(([x, y]) => [x, y, piece]);
            this.screen.paint(this.grid, this.cells(), ghost);
        }
        else
            this.screen.paint(this.grid);
    }
}
