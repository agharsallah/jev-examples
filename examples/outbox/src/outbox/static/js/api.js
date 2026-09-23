/* Everything the page asks the server, and the shapes of the answers.
 *
 * These types mirror outbox/web/payload.py field for field; if the payload
 * changes, this is the file that has to follow. Two calls matter: /api/read
 * asks Jev, /api/rescore never does. */
async function post(url, body) {
    const response = await fetch(url, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok)
        throw new Error(data.error || `Request failed (${response.status})`);
    return data;
}
export async function fetchDesk() {
    const response = await fetch("/api/desk");
    return (await response.json());
}
/** One or two requests to Jev, depending on `deep`. */
export function readDraft(body) {
    return post("/api/read", body);
}
/** The same measurements, weighed against another reader. No model call. */
export function rescoreDraft(measurement, audience) {
    return post("/api/rescore", { measurement, audience });
}
