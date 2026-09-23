/* Where the pieces come from: a seeded seven-bag, so both wells get the same deal. */
import { KEYS } from "./rules.js";
function mulberry32(seed) {
    return function () {
        seed |= 0;
        seed = (seed + 0x6d2b79f5) | 0;
        let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}
/** The standard seven-bag: every piece once, shuffled, then the next bag. */
export class Supply {
    rng;
    items = [];
    constructor(seed) {
        this.rng = mulberry32(seed);
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
