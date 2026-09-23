/* The two wells on the page, and the scoreboard around each.
 *
 * The element ids are historical — "jev" is the left-hand well and "you" the
 * right — and are only ever spelled here.
 */
import { $ } from "./dom.js";
import { Screen } from "./screen.js";
function well(side, id) {
    return {
        side,
        screen: new Screen($(`${id}Well`)),
        board: $(`${id}Well`),
        nameplate: document.querySelector(`.player.${id} .who`),
        els: {
            score: $(`${id}Score`),
            lines: $(`${id}Lines`),
            pieces: $(`${id}Pieces`),
            time: $(`${id}Time`),
            next: $(`${id}Next`),
            status: $(`${id}Status`),
            stamp: $(`${id}Stamp`),
        },
    };
}
export const wells = () => ({ left: well("left", "jev"), right: well("right", "you") });
/** Say who is sitting at a well, wherever the page names it. */
export function nameWell(place, name, yours) {
    place.nameplate.textContent = name;
    place.board.setAttribute("aria-label", yours ? "Your well" : `${name}'s well`);
}
