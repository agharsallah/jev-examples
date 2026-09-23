/* The tetris duel arcade.
 *
 * The browser owns both wells: it draws them, runs the clock and reads the
 * keyboard. Who sits at each well is picked on the page from the players the
 * server has installed. A model's well asks the server where each piece goes,
 * one POST per piece, and animates the answer; your well is the keyboard.
 */

import { fetchSetup } from "./api.js";
import { bindControls } from "./controls.js";
import { loadPieces } from "./game/pieces.js";
import { setLadder } from "./game/speed.js";
import { Match } from "./match.js";
import { $ } from "./ui/dom.js";
import { drawSeats, seatsFromUrl, seatsToUrl, settleSeats } from "./ui/seats.js";

async function boot(): Promise<void> {
  const setup = await fetchSetup();
  loadPieces(setup.pieces);
  setLadder((setup.players.find((p) => p.key === "jev") ?? setup.players[0]!).levels);

  const seats = seatsFromUrl();
  if (!settleSeats(seats, setup.players)) {
    const reasons = setup.players.map((p) => `${p.name} ${p.blocked}`).join("; ");
    const box = $("error");
    box.hidden = false;
    box.textContent = `No model can play right now (${reasons}).`;
    return;
  }

  const match = new Match(setup.players, seats);
  const redraw = (): void => {
    drawSeats(seats, setup.players, (side, key) => {
      seats[side] = key;
      redraw();
      match.seat();
    });
    seatsToUrl(seats);
  };
  redraw();
  match.seat();
  bindControls(match);

  let last = 0;
  const frame = (now: number): void => {
    requestAnimationFrame(frame); // scheduled first, so one bad frame cannot stop the clock
    const dt = Math.min(64, now - last || 16);
    last = now;
    match.tick(dt);
  };
  requestAnimationFrame(frame);
}

void boot();
