/* Everything the page asks the server, and the shapes of the answers.
 *
 * These types mirror web.py and duel.as_payload one to one; if either changes,
 * this is the file that has to follow.
 */
export async function fetchSetup() {
    return (await fetch("/api/setup")).json();
}
export async function askMove(player, move) {
    const response = await fetch(`/api/move/${player}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(move),
    });
    return response.json();
}
/** Ask a slow player to load before its first piece. Failing here is fine: the move will say why. */
export function warm(player) {
    fetch(`/api/warm/${player}`, { method: "POST" }).catch(() => { });
}
