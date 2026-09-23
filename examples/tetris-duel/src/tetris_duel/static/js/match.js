/* One match: who sits where, the shared deal, the clock, and how it ends. */
import { warm } from "./api.js";
import { CLEAR_NAMES } from "./game/rules.js";
import { currentLevel } from "./game/speed.js";
import { Supply } from "./game/supply.js";
import { Bot } from "./players/bot.js";
import { Human } from "./players/human.js";
import { celebrate } from "./ui/confetti.js";
import { $, bump, clock, setTag } from "./ui/dom.js";
import { describe, title } from "./ui/masthead.js";
import { finale, leadLine } from "./ui/scoreboard.js";
import { YOU } from "./ui/seats.js";
import { ThinkingCard } from "./ui/thinking.js";
import { nameWell, wells } from "./ui/wells.js";
const LEAD_EVERY_MS = 900;
const CLOCK_EVERY_MS = 200;
export class Match {
    players;
    seats;
    left;
    right;
    running = false;
    paused = false;
    matchMs = 0;
    leadTimer = 0;
    clockTimer = 0;
    places = wells();
    hooks = {
        cleared: (player, rows) => this.cleared(player, rows),
        over: () => this.checkFinale(),
    };
    constructor(players, seats) {
        this.players = players;
        this.seats = seats;
    }
    /** Your well, when you are playing. */
    get human() {
        return this.right instanceof Human ? this.right : null;
    }
    model(key) {
        return this.players.find((p) => p.key === key);
    }
    /** Sit everyone down for the chosen matchup, stopping whatever was running. */
    seat() {
        this.running = false;
        $("finale").hidden = true;
        // Anyone being replaced stops here, so an answer still in flight lands nowhere.
        for (const old of [this.left, this.right])
            if (old)
                old.over = true;
        this.left = this.sit("left", this.seats.left);
        this.right = this.sit("right", this.seats.right);
        for (const player of [this.left, this.right]) {
            player.els.stamp.hidden = true;
            player.reset(null);
            setTag(player.els.status, "ready");
        }
        title(this.left.name, this.right.name, Boolean(this.human));
        $("lead").textContent = "tap start";
        $("start").textContent = "Start the match";
        this.describe();
    }
    sit(side, key) {
        const place = this.places[side];
        if (key === YOU) {
            ThinkingCard.removeCopy();
            nameWell(place, "You", true);
            return new Human("You", place.screen, place.els, this.hooks);
        }
        const info = this.model(key);
        nameWell(place, info.name, false);
        warm(key);
        const card = side === "left" ? ThinkingCard.original() : ThinkingCard.copy();
        card.reset(info.name, side);
        return new Bot(info.name, place.screen, place.els, this.hooks, key, card);
    }
    describe() {
        const models = [this.seats.left, this.seats.right].filter((k) => k !== YOU).map((k) => this.model(k));
        describe(models, currentLevel());
    }
    start() {
        const seed = Math.floor(Math.random() * 1e9); // one deal, two identical hands
        $("finale").hidden = true;
        for (const player of [this.left, this.right]) {
            if (player instanceof Bot)
                player.card.hideError();
            player.els.stamp.hidden = true;
            player.reset(new Supply(seed));
            bump(player.els.score, 0);
            bump(player.els.lines, 0);
            player.els.pieces.textContent = "0";
            player.els.time.textContent = "0:00";
            if (player instanceof Bot)
                setTag(player.els.status, "thinking…", "is-thinking");
            else
                setTag(player.els.status, "playing", "is-live");
        }
        this.matchMs = 0;
        $("clock").textContent = "0:00";
        $("clock").parentElement.classList.remove("is-stopped");
        $("start").textContent = "Restart";
        $("lead").textContent = "dead even";
        this.running = true;
        this.paused = false;
        for (const player of [this.left, this.right])
            if (player instanceof Bot)
                player.begin();
    }
    togglePause() {
        this.paused = !this.paused;
        const human = this.human;
        if (human)
            setTag(human.els.status, this.paused ? "paused" : "playing", this.paused ? "" : "is-live");
    }
    /** Enter restarts once there is nothing left for you to play. */
    get canRestart() {
        return !this.running || (this.left.over && this.right.over) || Boolean(this.human?.over);
    }
    contestants() {
        return [
            { player: this.left, yours: false },
            { player: this.right, yours: Boolean(this.human) },
        ];
    }
    cleared(player, rows) {
        celebrate($("confetti"), rows, player === this.left ? "left" : "right");
        if (rows > 1)
            $("lead").textContent = `${player.name}: ${CLEAR_NAMES[rows]}`;
    }
    checkFinale() {
        if (!this.running || !this.left.over || !this.right.over)
            return;
        this.running = false;
        const end = finale(...this.contestants(), this.matchMs);
        $("finaleTitle").textContent = end.title;
        $("finaleLine").textContent = end.line;
        $("clock").parentElement.classList.add("is-stopped");
        $("finale").hidden = false;
        if (end.cheer)
            celebrate($("confetti"), 3, "right");
    }
    /** One animation frame: advance both wells, then draw them. */
    tick(dt) {
        if (this.running && !this.paused) {
            this.matchMs += dt;
            for (const player of [this.left, this.right]) {
                player.tick(dt);
                player.els.pieces.textContent = String(player.placed);
            }
            this.clockTimer += dt;
            if (this.clockTimer > CLOCK_EVERY_MS) {
                this.clockTimer = 0;
                $("clock").textContent = clock(this.matchMs);
                for (const player of [this.left, this.right])
                    player.els.time.textContent = clock(player.ms);
            }
            this.leadTimer += dt;
            if (this.leadTimer > LEAD_EVERY_MS) {
                this.leadTimer = 0;
                if (this.running)
                    $("lead").textContent = leadLine(...this.contestants());
            }
        }
        this.left.paint();
        this.right.paint();
    }
}
