"""The browser side's server: a thin JSON layer over the same functions the CLI calls.

Nothing is stored here. A triage response carries its `measurement` — the
raw answers, units and taxonomy — and the page sends it back to be rescored
under new thresholds or weights, which runs `policy.assess` and never Jev.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import evaluate, explain, github, overview, policy, questions, scan
from .jev import TriageError
from .triage import read_repo, triage, verdict

STATIC = Path(__file__).resolve().parent / "static"

EXAMPLES = [
    "omnigent-ai/omnigent#8107",
    "astral-sh/uv",
    "pallets/click",
]


class IssueRequest(BaseModel):
    ref: str
    fresh: bool = False
    model: str | None = None


class RescoreRequest(BaseModel):
    measurement: dict
    settings: dict = {}


class ScanRequest(BaseModel):
    ref: str
    limit: int = 60
    settings: dict = {}
    model: str | None = None
    refresh: bool = False


class QueueRescoreRequest(BaseModel):
    measurements: list[dict]
    taxonomy: dict
    settings: dict = {}


class OverviewRequest(BaseModel):
    ref: str
    limit: int | None = None
    model: str | None = None
    refresh: bool = False


class Jobs:
    """Long reads run in a thread; the page polls for progress.

    Kept in memory: a restarted server forgets its jobs, and re-running one is
    nearly free because every answer is cached on disk.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()

    def start(self, work) -> str:
        job_id = uuid.uuid4().hex[:12]
        job = {"status": "running", "done": 0, "total": 0, "started": time.time()}
        with self._lock:
            # Old finished jobs go, so a long session doesn't hold every result.
            for key in [k for k, j in self._jobs.items() if time.time() - j["started"] > 3600]:
                del self._jobs[key]
            self._jobs[job_id] = job

        def progress(done: int, total: int) -> None:
            job["done"], job["total"] = done, total

        def run() -> None:
            try:
                job["result"] = work(progress)
                job["status"] = "done"
            except TriageError as error:
                job["error"], job["status"] = str(error), "failed"
            except Exception as error:  # noqa: BLE001 - reported to the page, not swallowed
                job["error"], job["status"] = f"Unexpected error: {error}", "failed"

        threading.Thread(target=run, daemon=True).start()
        return job_id

    def get(self, job_id: str) -> dict | None:
        return self._jobs.get(job_id)


class CounterfactualRequest(BaseModel):
    ref: str
    removals: list[list[int]]
    model: str | None = None


def _levels() -> dict[str, list[str]]:
    return {name: list(score.criteria) for name, score in questions.SCORES.items()}


def _error(error: Exception, status: int = 502) -> JSONResponse:
    return JSONResponse({"error": str(error)}, status_code=status)


def create_app() -> FastAPI:
    app = FastAPI(title="triage", docs_url=None, redoc_url=None)
    jobs = Jobs()
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    @app.get("/api/meta")
    def meta() -> dict:
        return {
            "defaults": policy.DEFAULTS,
            "lanes": policy.LANES,
            "levels": _levels(),
            "examples": EXAMPLES,
        }

    @app.get("/api/repo")
    def repo(ref: str, model: str | None = None):
        try:
            found, tax = read_repo(ref, model=model)
        except TriageError as error:
            return _error(error)
        return {
            "repo": {
                "slug": found.slug,
                "description": found.description,
                "url": found.url,
                "open_issues": found.open_issues,
                "labels": [asdict(label) for label in found.labels],
            },
            "taxonomy": tax.to_dict(),
        }

    @app.post("/api/issue")
    def issue(body: IssueRequest):
        try:
            m, assessment, raw = triage(body.ref, model=body.model, fresh=body.fresh)
        except TriageError as error:
            return _error(error)
        return {"measurement": m, "assessment": asdict(assessment), "request": raw}

    @app.post("/api/rescore")
    def rescore(body: RescoreRequest):
        try:
            return {"assessment": asdict(verdict(body.measurement, body.settings))}
        except (KeyError, TypeError, ValueError) as error:
            return _error(f"That measurement could not be rescored: {error}", 400)

    @app.post("/api/counterfactual")
    def counterfactual(body: CounterfactualRequest):
        try:
            github.parse(body.ref)
            # Everything upstream is cached, so this rebuilds the same state
            # the original request saw without asking Jev again.
            m, _, raw = triage(body.ref, model=body.model)
            results = explain.counterfactuals(m, raw["state"], body.removals, model=body.model)
        except TriageError as error:
            return _error(error)
        return {"results": results}

    @app.post("/api/scan")
    def scan_queue(body: ScanRequest):
        try:
            limit = max(1, min(body.limit, 200))
            return scan.scan(
                body.ref,
                limit=limit,
                model=body.model,
                settings=body.settings,
                refresh=body.refresh,
            )
        except TriageError as error:
            return _error(error)

    @app.post("/api/scan/rescore")
    def scan_rescore(body: QueueRescoreRequest):
        try:
            return {"rows": scan.rescore(body.measurements, body.taxonomy, body.settings)}
        except (KeyError, TypeError, ValueError) as error:
            return _error(f"That queue could not be rescored: {error}", 400)

    @app.post("/api/eval")
    def eval_repo(body: ScanRequest):
        try:
            limit = max(10, min(body.limit, 300))
            report = evaluate.evaluate(
                body.ref, limit=limit, model=body.model, refresh=body.refresh
            )
        except TriageError as error:
            return _error(error)
        report.pop("measurements", None)  # The page shows metrics, not raw answers.
        return report

    @app.post("/api/overview")
    def start_overview(body: OverviewRequest):
        try:
            github.parse(body.ref)
        except TriageError as error:
            return _error(error, 400)
        job_id = jobs.start(
            lambda progress: overview.overview(
                body.ref,
                limit=body.limit,
                model=body.model,
                on_progress=progress,
                refresh=body.refresh,
            )
        )
        return {"job": job_id}

    @app.get("/api/overview/saved")
    def saved_overview(ref: str):
        # Reads a file and nothing else: opening the page never costs a request.
        try:
            found = overview.saved(ref)
        except TriageError as error:
            return _error(error, 400)
        if found is None:
            return _error("No overview saved for this repo yet.", 404)
        return found

    @app.get("/api/jobs/{job_id}")
    def job(job_id: str):
        found = jobs.get(job_id)
        if found is None:
            return _error("That job is gone (the server restarted?). Run it again.", 404)
        return {k: v for k, v in found.items() if k != "started"}

    return app


app = create_app()
