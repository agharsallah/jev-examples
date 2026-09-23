/* The shapes the server sends, mirrored from triage/triage.py and policy.py,
 * and the handful of calls the page makes. */
async function call(path, init) {
    const response = await fetch(path, init);
    const body = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
    if (!response.ok || body.error)
        throw new Error(body.error ?? `HTTP ${response.status}`);
    return body;
}
function post(path, payload) {
    return call(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
}
export const api = {
    meta: () => call("/api/meta"),
    repo: (ref) => call(`/api/repo?ref=${encodeURIComponent(ref)}`),
    issue: (ref, fresh = false) => post("/api/issue", { ref, fresh }),
    rescore: (measurement, settings) => post("/api/rescore", { measurement, settings }),
    counterfactual: (ref, removals) => post("/api/counterfactual", { ref, removals }),
};
export const queueApi = {
    scan: (ref, limit, settings) => post("/api/scan", { ref, limit, settings }),
    rescore: (measurements, taxonomy, settings) => post("/api/scan/rescore", { measurements, taxonomy, settings }),
    evaluate: (ref, limit) => post("/api/eval", { ref, limit }),
};
export const overviewApi = {
    start: (ref, limit, refresh) => post("/api/overview", { ref, limit, refresh }),
    /** The last overview saved for this repo, or null. Reads a file; asks nothing. */
    saved: async (ref) => {
        const response = await fetch(`/api/overview/saved?ref=${encodeURIComponent(ref)}`);
        return response.ok ? (await response.json()) : null;
    },
    poll: (job) => call(`/api/jobs/${job}`),
};
