/* Keys, the touch pad, the level pills and the start buttons. */
import { setLevel } from "./game/speed.js";
import { $ } from "./ui/dom.js";
const ACTIONS = {
    left: (you) => you.move(-1, 0),
    right: (you) => you.move(1, 0),
    rotate: (you) => you.rotate(1),
    soft: (you) => void (you.move(0, 1) || you.lock()),
    drop: (you) => you.hardDrop(),
};
const KEYMAP = {
    ArrowLeft: "left",
    ArrowRight: "right",
    ArrowUp: "rotate",
    ArrowDown: "soft",
    " ": "drop",
    x: "rotate",
    X: "rotate",
    z: "rotate",
    Z: "rotate",
};
/** Your well, if you are playing and it is taking moves right now. */
function playable(match) {
    const you = match.human;
    return you && match.running && !match.paused && !you.over ? you : null;
}
export function bindControls(match) {
    document.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && match.canRestart)
            return match.start();
        if (event.key.toLowerCase() === "p" && match.running)
            return match.togglePause();
        const you = playable(match);
        const action = KEYMAP[event.key];
        if (!you || !action)
            return;
        event.preventDefault();
        if (event.key.toLowerCase() === "z")
            you.rotate(-1);
        else
            ACTIONS[action](you);
    });
    document.querySelectorAll(".pad button").forEach((button) => button.addEventListener("click", () => {
        const you = playable(match);
        if (you)
            ACTIONS[button.dataset["key"]](you);
    }));
    const levels = document.querySelectorAll(".level[data-level]");
    levels.forEach((button) => button.addEventListener("click", () => {
        setLevel(button.dataset["level"]);
        levels.forEach((other) => {
            other.classList.toggle("is-on", other === button);
            other.setAttribute("aria-checked", String(other === button));
        });
        match.describe();
    }));
    $("start").addEventListener("click", () => match.start());
    $("again").addEventListener("click", () => match.start());
}
