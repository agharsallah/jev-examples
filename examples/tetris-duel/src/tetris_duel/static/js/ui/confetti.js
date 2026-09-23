/* A little celebration over whichever well cleared rows. */
const COLOURS = ["--I", "--O", "--T", "--S", "--Z", "--J", "--L"];
export function celebrate(box, rows, side) {
    const left = side === "left" ? 12 : 72;
    for (let i = 0; i < rows * 18; i++) {
        const bit = document.createElement("div");
        bit.className = "bit";
        bit.style.left = `${left + Math.random() * 18}vw`;
        bit.style.top = `${18 + Math.random() * 20}vh`;
        bit.style.background = `var(${COLOURS[i % COLOURS.length]})`;
        bit.style.setProperty("--dx", `${(Math.random() - 0.5) * 320}px`);
        bit.style.setProperty("--spin", `${Math.random() * 900 - 450}deg`);
        bit.style.animationDuration = `${1.1 + Math.random() * 0.9}s`;
        box.appendChild(bit);
        setTimeout(() => bit.remove(), 2200);
    }
}
