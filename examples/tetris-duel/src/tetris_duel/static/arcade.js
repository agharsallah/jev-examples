/* Jev vs You — the arcade.
 *
 * The browser owns both wells: it draws them, runs the clock and reads the
 * keyboard. The right-hand well is you. The left-hand one asks the server
 * where each piece goes, one POST per piece, and animates the answer.
 */

const W = 10;
const H = 20;
const KEYS = ["I", "O", "T", "S", "Z", "J", "L"];
const LINE_SCORES = [0, 100, 300, 500, 800];
const CLEAR_NAMES = ["", "single", "double", "triple", "TETRIS!"];

let SHAPES = {};
let ROTATIONS = {};
let LEVELS = [];
let level = "steady";

/* ------------------------------------------------------------ geometry */

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

function orientations(rows) {
  const cells = [];
  rows.forEach((row, y) => [...row].forEach((ch, x) => ch === "#" && cells.push([x, y])));
  const out = [];
  let shape = normalize(cells);
  for (let i = 0; i < 4; i++) {
    const key = JSON.stringify(shape);
    if (!out.some((s) => JSON.stringify(s) === key)) out.push(shape);
    shape = turn(shape);
  }
  return out;
}

/* --------------------------------------------------------- piece supply */

function mulberry32(seed) {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** The standard seven-bag, dealt from a seed so both wells get the same pieces. */
class Supply {
  constructor(seed) {
    this.rng = mulberry32(seed);
    this.items = [];
  }
  at(i) {
    while (this.items.length <= i) {
      const bag = [...KEYS];
      for (let j = bag.length - 1; j > 0; j--) {
        const k = Math.floor(this.rng() * (j + 1));
        [bag[j], bag[k]] = [bag[k], bag[j]];
      }
      this.items.push(...bag);
    }
    return this.items[i];
  }
}

/* --------------------------------------------------------------- a well */

const emptyGrid = () => Array.from({ length: H }, () => Array(W).fill(null));

class Screen {
  constructor(el) {
    this.el = el;
    this.cells = [];
    for (let i = 0; i < W * H; i++) {
      const cell = document.createElement("div");
      cell.className = "cell";
      el.appendChild(cell);
      this.cells.push(cell);
    }
    this.last = Array(W * H).fill("");
  }

  paint(grid, active = [], ghost = [], flash = []) {
    const next = Array(W * H).fill("");
    const colour = Array(W * H).fill("");
    grid.forEach((row, y) =>
      row.forEach((piece, x) => {
        if (piece) {
          next[y * W + x] = "cell on";
          colour[y * W + x] = piece;
        }
      })
    );
    for (const [x, y, piece] of ghost) {
      if (y >= 0 && !next[y * W + x]) {
        next[y * W + x] = "cell ghost";
        colour[y * W + x] = piece;
      }
    }
    for (const [x, y, piece] of active) {
      if (y >= 0) {
        next[y * W + x] = "cell on";
        colour[y * W + x] = piece;
      }
    }
    for (const y of flash) {
      for (let x = 0; x < W; x++) next[y * W + x] = "cell flash";
    }
    next.forEach((klass, i) => {
      const want = klass || "cell";
      if (this.last[i] !== want + colour[i]) {
        this.cells[i].className = want;
        this.cells[i].style.setProperty("--c", colour[i] ? `var(--${colour[i]})` : "transparent");
        this.last[i] = want + colour[i];
      }
    });
  }
}

function drawMini(el, piece) {
  el.innerHTML = "";
  if (!piece) return;
  for (const row of SHAPES[piece]) {
    const line = document.createElement("div");
    line.className = "row";
    for (const ch of row) {
      const blk = document.createElement("div");
      blk.className = ch === "#" ? "blk" : "gap";
      if (ch === "#") blk.style.setProperty("--c", `var(--${piece})`);
      line.appendChild(blk);
    }
    el.appendChild(line);
  }
}

/* -------------------------------------------------------------- players */

class Player {
  constructor(name, screen, els) {
    this.name = name;
    this.screen = screen;
    this.els = els;
    this.reset();
  }

  reset(supply) {
    this.supply = supply;
    this.grid = emptyGrid();
    this.score = 0;
    this.lines = 0;
    this.placed = 0;
    this.ms = 0; // how long this well has been in play
    this.index = 0;
    this.over = false;
    this.hold = 0; // ms of animation the clock has to wait for
    this.clearing = null;
    this.fall = 0;
    this.screen.paint(this.grid);
  }

  get level() {
    return Math.floor(this.lines / 10) + 1;
  }

  get gravity() {
    const base = (LEVELS.find((l) => l.key === level) || { gravity_ms: 560 }).gravity_ms;
    return Math.max(90, Math.round(base * Math.pow(0.86, this.level - 1)));
  }

  get piece() {
    return this.supply ? this.supply.at(this.index) : null;
  }

  get next() {
    return this.supply ? this.supply.at(this.index + 1) : null;
  }

  rows() {
    return this.grid.map((row) => row.map((cell) => (cell ? "#" : ".")).join(""));
  }

  /** Pieces dealt since the last straight bar — one per bag, so the wait matters. */
  sinceBar() {
    for (let back = 1; back <= this.index; back++) {
      if (this.supply.at(this.index - back) === "I") return back - 1;
    }
    return this.index;
  }

  /** Lock cells in, flash any full rows, and hand the score over after the flash. */
  settle(cells) {
    for (const [x, y, piece] of cells) {
      if (y >= 0) this.grid[y][x] = piece;
    }
    this.placed += 1;
    this.index += 1;
    const full = [];
    this.grid.forEach((row, y) => row.every((cell) => cell) && full.push(y));
    if (!full.length) return 0;
    this.clearing = full;
    this.hold = 230;
    return full.length;
  }

  finishClear() {
    const rows = this.clearing;
    this.clearing = null;
    this.grid = this.grid.filter((_, y) => !rows.includes(y));
    while (this.grid.length < H) this.grid.unshift(Array(W).fill(null));
    this.lines += rows.length;
    this.score += LINE_SCORES[rows.length] * this.level;
    bump(this.els.score, this.score);
    bump(this.els.lines, this.lines);
    celebrate(rows.length, this.name);
    return rows.length;
  }

  topOut(tag = "topped out") {
    this.over = true;
    this.els.stamp.textContent = tag;
    this.els.stamp.hidden = false;
    setTag(this.els.status, "done", "is-over");
    checkFinale();
  }
}

/* ------------------------------------------------------------- you play */

class Human extends Player {
  reset(supply) {
    super.reset(supply);
    this.piece && this.spawn();
  }

  spawn() {
    this.rot = 0;
    this.shape = ROTATIONS[this.piece][0];
    this.x = Math.floor((W - (Math.max(...this.shape.map((c) => c[0])) + 1)) / 2);
    this.y = 0;
    this.fall = 0;
    drawMini(this.els.next, this.next);
    if (!this.fits(this.shape, this.x, this.y)) this.topOut();
  }

  cells(shape = this.shape, x = this.x, y = this.y) {
    return shape.map(([cx, cy]) => [cx + x, cy + y, this.piece]);
  }

  fits(shape, x, y) {
    return shape.every(([cx, cy]) => {
      const gx = cx + x;
      const gy = cy + y;
      return gx >= 0 && gx < W && gy < H && (gy < 0 || !this.grid[gy][gx]);
    });
  }

  move(dx, dy) {
    if (this.over || this.clearing) return false;
    if (!this.fits(this.shape, this.x + dx, this.y + dy)) return false;
    this.x += dx;
    this.y += dy;
    return true;
  }

  rotate(dir) {
    if (this.over || this.clearing) return;
    const shapes = ROTATIONS[this.piece];
    const rot = (this.rot + dir + shapes.length) % shapes.length;
    const shape = shapes[rot];
    for (const kick of [0, -1, 1, -2, 2]) {
      if (this.fits(shape, this.x + kick, this.y)) {
        this.rot = rot;
        this.shape = shape;
        this.x += kick;
        return;
      }
    }
  }

  ghost() {
    let y = this.y;
    while (this.fits(this.shape, this.x, y + 1)) y += 1;
    return this.cells(this.shape, this.x, y);
  }

  lock() {
    this.settle(this.cells());
    if (!this.clearing) this.spawn();
  }

  hardDrop() {
    if (this.over || this.clearing) return;
    while (this.move(0, 1));
    this.lock();
  }

  tick(dt) {
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

  paint() {
    if (!this.shape || this.over || this.clearing) {
      this.screen.paint(this.grid, [], [], this.clearing || []);
    } else {
      this.screen.paint(this.grid, this.cells(), this.ghost());
    }
  }
}

/* -------------------------------------------------------------- jev plays */

const width = (shape) => Math.max(...shape.map((c) => c[0])) + 1;

class Jev extends Player {
  reset(supply) {
    super.reset(supply);
    this.state = "idle";
    this.plan = null;
    this.shape = null;
    this.target = null;
    this.keying = 0;
    this.run = (this.run || 0) + 1; // a restart makes any answer still in flight stale
  }

  begin() {
    this.think();
  }

  /** How long Jev takes between one keypress and the next. */
  get keyMs() {
    return Math.max(55, Math.round(this.gravity / 6));
  }

  async think() {
    if (this.over) return;
    this.state = "thinking";
    setTag(this.els.status, "thinking…", "is-thinking");
    drawMini(this.els.next, this.next);
    const started = performance.now();
    const run = this.run;
    try {
      const response = await fetch("/api/move", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rows: this.rows(),
          piece: this.piece,
          next: this.next,
          cleared: this.lines,
          since_bar: this.sinceBar(),
          difficulty: level,
        }),
      });
      const data = await response.json();
      if (run !== this.run || this.over) return; // the match moved on without this answer
      if (data.error) return this.offline(data.error);
      if (data.game_over) return this.topOut();

      showThinking(data, Math.round(performance.now() - started));
      this.take(data);
    } catch (error) {
      if (run === this.run) this.offline(`Could not reach the server: ${error.message}`);
    }
  }

  /** Put the piece at the top the way you get it, and remember where it has to end up. */
  take(plan) {
    this.plan = plan;
    this.rot = 0;
    this.shape = ROTATIONS[plan.piece][0];
    this.x = Math.floor((W - width(this.shape)) / 2);
    this.y = 0;
    this.target = { rot: plan.rotation, x: plan.column, y: plan.landing_row };
    this.state = "lining up";
    this.keying = 0;
    this.fall = 0;
    setTag(this.els.status, "lining up", "is-live");
  }

  /** One keypress: turn it, or walk it one column towards the spot Jev chose. */
  press() {
    const shapes = ROTATIONS[this.plan.piece];
    if (this.rot !== this.target.rot) {
      const cw = (this.target.rot - this.rot + shapes.length) % shapes.length;
      const ccw = (this.rot - this.target.rot + shapes.length) % shapes.length;
      const dir = cw <= ccw ? 1 : -1;
      this.rot = (this.rot + dir + shapes.length) % shapes.length;
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
    } else {
      this.state = "dropping";
      setTag(this.els.status, "dropping", "is-live");
    }
  }

  offline(message) {
    showError(message);
    this.state = "error";
    this.topOut("jev offline");
  }

  cells() {
    if (!this.plan || !this.shape) return [];
    return this.shape.map(([cx, cy]) => [cx + this.x, cy + this.y, this.plan.piece]);
  }

  lock() {
    // The plan is what actually gets written in: the walk across the top is theatre.
    this.settle(this.plan.cells.map(([x, y]) => [x, y, this.plan.piece]));
    this.plan = null;
    this.shape = null;
    if (this.clearing) this.state = "clearing";
    else this.think();
  }

  tick(dt) {
    if (this.over) return;
    this.ms += dt; // thinking counts: the well is still on the clock
    if (this.hold > 0) {
      this.hold -= dt;
      if (this.hold <= 0 && this.clearing) {
        this.finishClear();
        this.think();
      }
      return;
    }
    if (this.state === "lining up") {
      this.keying += dt;
      if (this.keying >= this.keyMs) {
        this.keying = 0;
        if (!this.press()) this.release();
      }
      return;
    }
    if (this.state !== "dropping") return;
    this.fall += dt;
    if (this.fall >= this.gravity) {
      this.fall = 0;
      if (this.y < this.target.y) this.y += 1;
      else this.lock();
    }
  }

  paint() {
    if (this.clearing) this.screen.paint(this.grid, [], [], this.clearing);
    else if (this.plan && this.shape) {
      const ghost = this.plan.cells.map(([x, y]) => [x, y, this.plan.piece]);
      this.screen.paint(this.grid, this.cells(), ghost);
    } else this.screen.paint(this.grid);
  }
}

/* ------------------------------------------------------------------ chrome */

const $ = (id) => document.getElementById(id);

/** Milliseconds as a scoreboard reads them. */
const clock = (ms) => {
  const total = Math.floor(ms / 1000);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
};

function setTag(el, text, klass) {
  el.textContent = text;
  el.className = `tag ${klass || ""}`.trim();
}

function bump(el, value) {
  el.textContent = value;
  el.classList.remove("pop");
  void el.offsetWidth;
  el.classList.add("pop");
}

const CONFETTI = ["--I", "--O", "--T", "--S", "--Z", "--J", "--L"];

function celebrate(rows, who) {
  const box = $("confetti");
  const count = rows * 18;
  const left = who === "Jev" ? 12 : 72;
  for (let i = 0; i < count; i++) {
    const bit = document.createElement("div");
    bit.className = "bit";
    bit.style.left = `${left + Math.random() * 18}vw`;
    bit.style.top = `${18 + Math.random() * 20}vh`;
    bit.style.background = `var(${CONFETTI[i % CONFETTI.length]})`;
    bit.style.setProperty("--dx", `${(Math.random() - 0.5) * 320}px`);
    bit.style.setProperty("--spin", `${Math.random() * 900 - 450}deg`);
    bit.style.animationDuration = `${1.1 + Math.random() * 0.9}s`;
    box.appendChild(bit);
    setTimeout(() => bit.remove(), 2200);
  }
  if (rows > 1) $("lead").textContent = `${who}: ${CLEAR_NAMES[rows]}`;
}

function showThinking(data, ms) {
  $("error").hidden = true;
  $("chatter").textContent = data.mood.line;
  $("pick").innerHTML =
    `<b>${data.piece}</b> → ${data.where} · chosen from <b>${data.menu_size}</b> legal landings` +
    (data.rows_cleared ? ` · clears <b>${data.rows_cleared}</b>` : "") +
    (data.torn ? " · <b>Jev is torn</b>" : "") +
    (data.sure ? " · sure enough to <b>hard drop</b> it" : "") +
    (data.guarding ? ` · holding <b>column ${data.guarding}</b> open` : "");

  const overrule = $("overrule");
  overrule.hidden = !data.overruled;
  if (data.overruled) overrule.textContent = data.note;

  const bars = $("bars");
  bars.innerHTML = "";
  for (const option of data.options) {
    const bar = document.createElement("div");
    bar.className = `bar${option.jev ? " is-pick" : ""}${option.chosen ? " is-taken" : ""}`;
    bar.innerHTML =
      `<span class="pct">${Math.round(option.probability * 100)}%</span>` +
      `<span class="track"><span class="fill" style="width:${Math.max(3, option.probability * 100)}%"></span>` +
      `<span class="label">${option.where}${option.rows_cleared ? ` · clears ${option.rows_cleared}` : ""}` +
      `${option.new_gaps ? ` · buries ${option.new_gaps}` : ""}</span></span>`;
    bars.appendChild(bar);
  }

  meter("danger", data.danger.value / 4, `${data.danger.value.toFixed(2)} / 4`);
  $("dangerNote").textContent = data.danger.level;
  meter("clear", data.clear_now, `${Math.round(data.clear_now * 100)}%`);
  const slot = $("slotMeter");
  slot.hidden = data.keep_slot === null || data.keep_slot === undefined;
  if (!slot.hidden) {
    meter("slot", data.keep_slot, `${Math.round(data.keep_slot * 100)}%`);
    $("slotNote").textContent = data.guarding
      ? `column ${data.guarding} is being kept clear for a four-row clear`
      : "not worth waiting for a bar right now";
  }
  meter("conf", data.confidence, `${Math.round(data.confidence * 100)}%`);

  const tokens = data.usage.input_tokens || 0;
  $("modelNote").textContent = `${data.model} · ${tokens} input tokens · ${ms}ms`;
}

function meter(name, fraction, text) {
  $(`${name}Fill`).style.width = `${Math.min(100, Math.max(0, fraction * 100))}%`;
  $(`${name}Value`).textContent = text;
}

function showError(message) {
  const box = $("error");
  box.hidden = false;
  box.textContent = message;
}

/* -------------------------------------------------------------- the match */

const jev = new Jev("Jev", new Screen($("jevWell")), {
  score: $("jevScore"),
  lines: $("jevLines"),
  pieces: $("jevPieces"),
  time: $("jevTime"),
  next: $("jevNext"),
  status: $("jevStatus"),
  stamp: $("jevStamp"),
});

const you = new Human("You", new Screen($("youWell")), {
  score: $("youScore"),
  lines: $("youLines"),
  pieces: $("youPieces"),
  time: $("youTime"),
  next: $("youNext"),
  status: $("youStatus"),
  stamp: $("youStamp"),
});

let running = false;
let paused = false;
let last = 0;
let matchMs = 0;

function start() {
  const seed = Math.floor(Math.random() * 1e9);
  const supply = () => new Supply(seed); // one deal, two identical hands
  $("finale").hidden = true;
  $("error").hidden = true;
  for (const player of [jev, you]) {
    player.els.stamp.hidden = true;
    player.reset(supply());
    bump(player.els.score, 0);
    bump(player.els.lines, 0);
    player.els.pieces.textContent = 0;
    player.els.time.textContent = "0:00";
  }
  matchMs = 0;
  $("clock").textContent = "0:00";
  $("clock").parentElement.classList.remove("is-stopped");
  setTag(jev.els.status, "thinking…", "is-thinking");
  setTag(you.els.status, "playing", "is-live");
  $("start").textContent = "Restart";
  $("lead").textContent = "dead even";
  running = true;
  paused = false;
  jev.begin();
}

function checkFinale() {
  if (!running || !jev.over || !you.over) return;
  running = false;
  const gap = Math.abs(jev.score - you.score);
  const drew = jev.score === you.score;
  const won = you.score > jev.score;
  $("finaleTitle").textContent = drew ? "A dead heat!" : won ? "You win! 🎉" : "Jev wins 🤖";
  $("clock").parentElement.classList.add("is-stopped");
  $("finaleLine").textContent =
    (drew
      ? `${you.score} points each, from exactly the same pieces. `
      : `${won ? "You" : "Jev"} finished ${gap} points ahead. `) +
    `Jev: ${jev.score} points from ${jev.placed} pieces in ${clock(jev.ms)}. ` +
    `You: ${you.score} from ${you.placed} in ${clock(you.ms)}. ` +
    `The match ran ${clock(matchMs)}.`;
  $("finale").hidden = false;
  if (won || drew) celebrate(3, "You");
}

function leadLine() {
  if (!running) return;
  const gap = jev.score - you.score;
  if (gap === 0) $("lead").textContent = "dead even";
  else if (gap > 0) $("lead").textContent = `Jev leads by ${gap}`;
  else $("lead").textContent = `you lead by ${-gap}`;
}

let leadTimer = 0;
let clockTimer = 0;

function frame(now) {
  requestAnimationFrame(frame); // scheduled first, so one bad frame cannot stop the clock
  const dt = Math.min(64, now - last || 16);
  last = now;
  if (running && !paused) {
    matchMs += dt;
    jev.tick(dt);
    you.tick(dt);
    jev.els.pieces.textContent = jev.placed;
    you.els.pieces.textContent = you.placed;
    clockTimer += dt;
    if (clockTimer > 200) {
      clockTimer = 0;
      $("clock").textContent = clock(matchMs);
      jev.els.time.textContent = clock(jev.ms);
      you.els.time.textContent = clock(you.ms);
    }
    leadTimer += dt;
    if (leadTimer > 900) {
      leadTimer = 0;
      leadLine();
    }
  }
  jev.paint();
  you.paint();
}

/* ---------------------------------------------------------------- controls */

const ACTIONS = {
  left: () => you.move(-1, 0),
  right: () => you.move(1, 0),
  rotate: () => you.rotate(1),
  soft: () => you.move(0, 1) || you.lock(),
  drop: () => you.hardDrop(),
};

document.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (!running || you.over)) return start();
  if (event.key.toLowerCase() === "p" && running) {
    paused = !paused;
    setTag(you.els.status, paused ? "paused" : "playing", paused ? "" : "is-live");
    return;
  }
  if (!running || paused || you.over) return;
  const action = {
    ArrowLeft: "left",
    ArrowRight: "right",
    ArrowUp: "rotate",
    ArrowDown: "soft",
    " ": "drop",
    x: "rotate",
    X: "rotate",
    z: "rotate",
    Z: "rotate",
  }[event.key];
  if (!action) return;
  event.preventDefault();
  if (action === "rotate" && event.key.toLowerCase() === "z") you.rotate(-1);
  else ACTIONS[action]();
});

document.querySelectorAll(".pad button").forEach((button) =>
  button.addEventListener("click", () => {
    if (running && !paused && !you.over) ACTIONS[button.dataset.key]();
  })
);

document.querySelectorAll(".level").forEach((button) =>
  button.addEventListener("click", () => {
    level = button.dataset.level;
    document.querySelectorAll(".level").forEach((other) => {
      other.classList.toggle("is-on", other === button);
      other.setAttribute("aria-checked", String(other === button));
    });
    const chosen = LEVELS.find((l) => l.key === level);
    if (chosen) $("blurb").textContent = chosen.blurb;
  })
);

$("start").addEventListener("click", start);
$("again").addEventListener("click", start);

/* ------------------------------------------------------------------- boot */

(async function boot() {
  const data = await (await fetch("/api/levels")).json();
  SHAPES = data.pieces;
  LEVELS = data.levels;
  for (const key of KEYS) ROTATIONS[key] = orientations(SHAPES[key]);
  $("blurb").textContent = (LEVELS.find((l) => l.key === level) || LEVELS[1]).blurb;
  jev.screen.paint(jev.grid);
  you.screen.paint(you.grid);
  requestAnimationFrame(frame);
})();
