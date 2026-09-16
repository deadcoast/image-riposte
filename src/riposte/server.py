from __future__ import annotations
import concurrent.futures
import io
import json
import secrets
import threading
import uuid
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal
from PIL import Image
from .errors import RiposteError
from .policy import Policy
from .store import check_root, catalog, find_image, safe_child, state_relative, legacy_workspace, upgrade_workspace
from .sanitize import encode_clean, png_audit
from .organizer import plan, organize, audit_workspace
from .lab import create_candidate, compare_external, trials, trial_report, export_candidate, trial_pixels

STATIC = Path(__file__).parent / "static"

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class OrganizeRequest(StrictModel):
    apply: bool = False
    acknowledge_source_removal: bool = False
    discard_sidecars: bool = False
    date_mode: str = "download"

class GuardRequest(StrictModel):
    image_id: str
    vae_directory: str = Field(min_length=1,max_length=2048)
    max_edge: int = Field(default=1536,ge=64,le=4096)
    epsilon: int = Field(default=4,ge=1,le=16)
    steps: int = Field(default=48,ge=1,le=1000)
    seed: int = Field(default=7,ge=0,lt=2**32)
    engine: Literal["encoder", "coupled"] = "encoder"
    pipeline_directory: str = Field(default="", max_length=2048)
    device: Literal["auto", "cpu", "cuda", "mps"] = "auto"
    preserve_white: bool = True

class PreflightRequest(StrictModel):
    vae_directory: str = Field(default="", max_length=2048)

class QualificationRequest(StrictModel):
    trial_id: str = Field(min_length=32, max_length=32)
    vae_directory: str = Field(min_length=1, max_length=2048)
    device: Literal["auto", "cpu", "cuda", "mps"] = "auto"

class GenerationRequest(StrictModel):
    trial_id: str = Field(min_length=32, max_length=32)
    model_directory: str = Field(min_length=1, max_length=2048)
    task: Literal["edit", "inpaint", "video"] = "edit"
    steps: int = Field(default=25, ge=1, le=100)

class CompareRequest(StrictModel):
    image_id: str
    candidate_path: str = Field(min_length=1,max_length=2048)
    max_edge: int = Field(default=1536,ge=64,le=4096)
    method: str = "external"

class ExportRequest(StrictModel):
    trial_id: str
    acknowledge_unverified: bool = False

class Jobs:
    def __init__(self):
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="riposte")
        self.data, self.events = {}, {}
        self.lock = threading.Lock()

    def start(self, fn, cancellable: bool = True, **kwargs):
        with self.lock:
            if any(j["state"] in {"queued", "running"} for j in self.data.values()):
                raise RiposteError("JOB_ALREADY_RUNNING")
            if len(self.data) > 20:
                self.data.clear()
                self.events.clear()
            key = uuid.uuid4().hex
            event = threading.Event()
            self.events[key] = event
            self.data[key] = {"id": key, "state": "queued", "phase": "Queued",
                              "cancellable": cancellable, "cancel_requested": False}

        def progress(update):
            if cancellable and event.is_set():
                raise RiposteError("JOB_CANCELLED")
            with self.lock:
                self.data[key].update(update)

        def finish(update):
            with self.lock:
                self.data[key].update(update)

        def run():
            try:
                progress({"state": "running"})
                result = fn(progress=progress, **kwargs)
                finish({"state": "done", "phase": "Complete", "result": result})
            except RiposteError as exc:
                finish({"state": "cancelled" if exc.code == "JOB_CANCELLED" else "error",
                        "phase": "Cancelled safely" if exc.code == "JOB_CANCELLED" else "Stopped", "code": exc.code})
            except Exception:
                finish({"state": "error", "phase": "Stopped", "code": "OPERATION_FAILED"})
        self.pool.submit(run)
        return {"job_id": key}

    def cancel(self, key):
        with self.lock:
            job = self.data.get(key)
            if not job or job["state"] not in {"queued", "running"}:
                raise RiposteError("RUNNING_JOB_NOT_FOUND")
            if not job["cancellable"]:
                raise RiposteError("JOB_CANCELLATION_UNSUPPORTED")
            job["cancel_requested"] = True
            self.events[key].set()
        return {"status": "CANCEL_REQUESTED", "boundary": "NEXT_MODEL_OR_ITERATION_CHECKPOINT"}

    def snapshot(self):
        with self.lock:
            return [dict(v) for v in self.data.values()]

    def close(self):
        with self.lock:
            for key, job in self.data.items():
                if job["cancellable"]:
                    self.events[key].set()
        self.pool.shutdown(wait=False, cancel_futures=True)

def create_app(root: Path, token: str | None = None) -> FastAPI:
    root=check_root(root)
    from contextlib import asynccontextmanager
    jobs = Jobs()
    @asynccontextmanager
    async def lifespan(app):
        yield
        jobs.close()
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None, lifespan=lifespan)
    app.state.token=token or secrets.token_urlsafe(32)
    app.state.jobs=jobs

    @app.middleware("http")
    async def security(request: Request, call_next):
        host=request.headers.get("host","").split(":")[0]
        if host not in {"127.0.0.1","localhost","testserver"}:
            return JSONResponse({"code":"HOST_REJECTED"},status_code=403)
        if request.url.path.startswith("/api/"):
            offered=request.headers.get("x-riposte-token","")
            if not secrets.compare_digest(offered,app.state.token):
                return JSONResponse({"code":"SESSION_REQUIRED"},status_code=401)
            origin=request.headers.get("origin")
            if origin and origin != str(request.base_url).rstrip("/"):
                return JSONResponse({"code":"ORIGIN_REJECTED"},status_code=403)
            if request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse({"code":"ORIGIN_REJECTED"},status_code=403)
            length=request.headers.get("content-length")
            if length and (not length.isdigit() or int(length)>16384):
                return JSONResponse({"code":"REQUEST_TOO_LARGE"},status_code=413)
        response=await call_next(request)
        response.headers.update({"Cache-Control":"no-store", "Referrer-Policy":"no-referrer",
            "X-Content-Type-Options":"nosniff", "X-Frame-Options":"DENY",
            "Content-Security-Policy":"default-src 'self'; img-src 'self' blob: data:; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"})
        return response

    @app.exception_handler(RiposteError)
    async def safe_error(request,exc):
        return JSONResponse({"code":exc.code},status_code=400)
    @app.exception_handler(RequestValidationError)
    async def validation_error(request,exc):
        return JSONResponse({"code":"REQUEST_INVALID"},status_code=422)
    @app.exception_handler(Exception)
    async def unknown_error(request,exc):
        return JSONResponse({"code":"OPERATION_FAILED"},status_code=500)

    app.mount("/static",StaticFiles(directory=STATIC),name="static")
    @app.get("/",response_class=HTMLResponse)
    def home():
        return (STATIC/"index.html").read_text()
    @app.get("/api/state")
    def state():
        images=catalog(root)
        return {"version":"0.2.0","images":images,"trials":trials(root),"jobs":app.state.jobs.snapshot(),
                "privacy":"Local only • no telemetry • date-only image metadata","root_label":"Active artwork folder", "legacy_workspace":legacy_workspace(root), "demo":safe_child(root, state_relative(root,"DEMO")).is_file()}
    @app.get("/api/methods")
    def methods():
        return json.loads((Path(__file__).parent/"methods.json").read_text())
    @app.post("/api/organize")
    def organize_endpoint(body:OrganizeRequest):
        if body.apply and not body.acknowledge_source_removal:
            raise RiposteError("ACKNOWLEDGE_SOURCE_REMOVAL_REQUIRED")
        policy=Policy(date_mode=body.date_mode,discard_sidecars=body.discard_sidecars)
        return app.state.jobs.start(organize if body.apply else plan,cancellable=False,root=root,policy=policy)
    @app.get("/api/audit")
    def audit():
        return audit_workspace(root)
    @app.post("/api/guard")
    def guard(body:GuardRequest):
        return app.state.jobs.start(create_candidate,root=root,identifier=body.image_id,
            vae_dirs=[Path(body.vae_directory)],max_edge=body.max_edge,epsilon=body.epsilon,steps=body.steps,seed=body.seed,
            engine=body.engine, pipeline_dir=Path(body.pipeline_directory) if body.pipeline_directory else None,
            device=body.device, preserve_white=body.preserve_white)
    @app.post("/api/compare")
    def compare(body:CompareRequest):
        def work(progress,**kwargs):
            progress({"phase":"Testing external candidate"})
            return compare_external(**kwargs)
        return app.state.jobs.start(work,root=root,identifier=body.image_id,candidate_path=Path(body.candidate_path),max_edge=body.max_edge,method=body.method)
    @app.post("/api/export")
    def export(body:ExportRequest):
        return export_candidate(root,body.trial_id,body.acknowledge_unverified)
    @app.get("/api/image/{identifier}")
    def image(identifier:str,thumb:bool=False):
        row=find_image(root,identifier)
        data=safe_child(root,row["relative"]).read_bytes()
        if thumb:
            with Image.open(io.BytesIO(data)) as im:
                im.thumbnail((360,360),Image.Resampling.LANCZOS)
                data=encode_clean(im,row["day"])
        return Response(data,media_type="image/png")
    @app.get("/api/trial/{identifier}/{kind}")
    def trial_image(identifier: str, kind: str, view: str = "identity"):
        return Response(trial_pixels(root, identifier, kind, view), media_type="image/png")

    @app.get("/api/runtime")
    def runtime():
        from .models import runtime_capabilities
        return runtime_capabilities()

    @app.post("/api/preflight")
    def preflight(body: PreflightRequest):
        from .models import inspect_vae, runtime_capabilities
        result = {"runtime": runtime_capabilities()}
        if body.vae_directory:
            result["model"] = inspect_vae(Path(body.vae_directory))
        return result

    @app.post("/api/qualify")
    def qualify(body: QualificationRequest):
        from .qualification import qualify_trial
        return app.state.jobs.start(qualify_trial, root=root, trial_id=body.trial_id,
                                   vae_dirs=[Path(body.vae_directory)], device=body.device)

    @app.get("/api/evaluations/{trial_id}")
    def qualification_results(trial_id: str):
        from .qualification import evaluations
        return {"evaluations": evaluations(root, trial_id)}

    @app.post("/api/jobs/{identifier}/cancel")
    def cancel(identifier: str):
        return app.state.jobs.cancel(identifier)

    @app.post("/api/generate")
    def generate(body: GenerationRequest):
        from .generation import controlled_generation
        return app.state.jobs.start(controlled_generation, root=root, trial_id=body.trial_id,
                                   model_dir=Path(body.model_directory), task=body.task, steps=body.steps)

    @app.get("/api/generations/{trial_id}")
    def generated_runs(trial_id: str):
        from .generation import generation_runs
        return {"runs": generation_runs(root, trial_id)}

    @app.get("/api/generation/{identifier}/frame")
    def generated_frame(identifier: str, relative: str):
        from .generation import generation_frame
        return Response(generation_frame(root, identifier, relative), media_type="image/png")

    @app.post("/api/upgrade-workspace")
    def upgrade():
        if any(job["state"] in {"queued", "running"} for job in app.state.jobs.snapshot()):
            raise RiposteError("JOB_ALREADY_RUNNING")
        return upgrade_workspace(root)
    return app
