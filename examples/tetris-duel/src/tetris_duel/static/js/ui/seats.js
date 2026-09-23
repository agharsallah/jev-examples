/* The two seat pickers: who plays the left-hand well, and who plays the right. */
import { $ } from "./dom.js";
export const YOU = "you";
/** The matchup in the URL, or Jev against you. */
export function seatsFromUrl() {
    const params = new URLSearchParams(location.search);
    return { left: params.get("left") ?? "jev", right: params.get("right") ?? YOU };
}
export function seatsToUrl(seats) {
    history.replaceState(null, "", `?${new URLSearchParams(seats)}`);
}
/**
 * Keep the matchup legal: a model that can play on the left, and on the right
 * you or a different model. Returns false when no model can play at all.
 */
export function settleSeats(seats, players) {
    const ok = (key) => players.some((p) => p.key === key && !p.blocked);
    const free = players.filter((p) => !p.blocked).map((p) => p.key);
    if (!ok(seats.left)) {
        if (!free.length)
            return false;
        seats.left = free[0];
    }
    if (seats.right !== YOU && (!ok(seats.right) || seats.right === seats.left))
        seats.right = YOU;
    return true;
}
/** Draw both pickers. A model that cannot play says why, and one model sits only once. */
export function drawSeats(seats, players, pick) {
    for (const side of ["left", "right"]) {
        const box = $(`${side}Seats`);
        box.innerHTML = "";
        const choices = players.map((p) => ({ key: p.key, name: p.name, blocked: p.blocked }));
        if (side === "right")
            choices.unshift({ key: YOU, name: "You", blocked: null });
        const other = seats[side === "left" ? "right" : "left"];
        for (const choice of choices)
            box.appendChild(seatButton(side, choice, seats[side] === choice.key, other, pick));
    }
}
function seatButton(side, choice, on, other, pick) {
    const taken = choice.key !== YOU && choice.key === other;
    const button = document.createElement("button");
    button.className = `level${on ? " is-on" : ""}`;
    button.dataset["seat"] = side;
    button.textContent = choice.name;
    button.setAttribute("role", "radio");
    button.setAttribute("aria-checked", String(on));
    button.disabled = Boolean(choice.blocked) || taken;
    if (choice.blocked)
        button.title = `${choice.name} ${choice.blocked}`;
    else if (taken)
        button.title = `${choice.name} is already in the other well`;
    button.addEventListener("click", () => pick(side, choice.key));
    return button;
}
