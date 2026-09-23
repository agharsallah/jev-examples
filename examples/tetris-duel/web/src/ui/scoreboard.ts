/* The words around the match: who leads, and how it ended. Pure text, no DOM. */

import type { Player } from "../players/player.js";
import { clock } from "./dom.js";

export interface Contestant {
  player: Player;
  yours: boolean;
}

export function leadLine(left: Contestant, right: Contestant): string {
  const gap = left.player.score - right.player.score;
  if (gap === 0) return "dead even";
  const ahead = gap > 0 ? left : right;
  return ahead.yours ? `you lead by ${-gap}` : `${ahead.player.name} leads by ${Math.abs(gap)}`;
}

export interface Finale {
  title: string;
  line: string;
  /** Whether you won or drew, which earns you the confetti. */
  cheer: boolean;
}

export function finale(left: Contestant, right: Contestant, matchMs: number): Finale {
  const [l, r] = [left.player, right.player];
  const drew = l.score === r.score;
  const winner = r.score > l.score ? right : left;
  const gap = Math.abs(l.score - r.score);
  const title = drew ? "A dead heat!" : winner.yours ? "You win! 🎉" : `${winner.player.name} wins 🤖`;
  const line =
    (drew ? `${l.score} points each, from exactly the same pieces. ` : `${winner.player.name} finished ${gap} points ahead. `) +
    `${l.name}: ${l.score} points from ${l.placed} pieces in ${clock(l.ms)}. ` +
    `${r.name}: ${r.score} from ${r.placed} in ${clock(r.ms)}. ` +
    `The match ran ${clock(matchMs)}.`;
  return { title, line, cheer: drew || winner.yours };
}
