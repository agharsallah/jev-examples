// The court's HTTP surface. These types mirror payload.py field for field, so
// a change to one side is a change to both.
export async function judge(plea) {
    const response = await fetch("/api/judge", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(plea),
    });
    const data = await response.json();
    if (!response.ok) {
        return { ok: false, message: data.error || `The clerk returned ${response.status}.` };
    }
    return { ok: true, verdict: data };
}
export async function fetchRecord() {
    const response = await fetch("/api/record");
    return (await response.json());
}
export async function expungeRecord() {
    await fetch("/api/record", { method: "DELETE" });
}
