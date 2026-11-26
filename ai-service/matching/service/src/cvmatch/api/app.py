"""FastAPI cho backend Java (Q-7: HTTP, AI co DB rieng).

Chay: `cvmatch api serve` hoac `uvicorn cvmatch.api.app:app`. Khi khoi dong nap config, KB snapshot,
encoder va `CvIndex` MOT lan (xem `services.py`). OpenAPI: `/openapi.json`, giao dien thu: `/docs`.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

import hmac
import os
import threading

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from cvmatch.api import schemas as S
from cvmatch.api.jobs import JobRegistry
from cvmatch.api.logjson import log_event, setup_json_logging
from cvmatch.api.services import Services, config_and_encoder
from cvmatch.explain.checks import ExplainCheckError
from cvmatch.explain.facts import FactsNotFound
from cvmatch.rerank.run import RerankError
from cvmatch.retrieve.jd_to_cvs import JdNotReady
from cvmatch.retrieve.cv_to_jds import CvNotReady

_ERR = {404: {"model": S.ErrorOut}, 409: {"model": S.ErrorOut}}


def default_services() -> Services:
    cfg, enc = config_and_encoder()
    return Services(cfg, encoder=enc)


def _cv_result(o) -> dict:
    return {"source": o.source, "status": o.status, "cv_id": o.cv_id, "version": o.version, "flags": o.flags,
            "detail": o.detail}


def _cv_response(o) -> JSONResponse:
    code = {"invalid": 422, "failed": 500}.get(o.status, 200)
    return JSONResponse(S.CvIngestResult(**_cv_result(o)).model_dump(mode="json"), status_code=code)


def _jd_response(o) -> JSONResponse:
    code = {"invalid": 422, "failed": 500}.get(o.status, 200)
    body = S.JdIngestResult(source=o.source, status=o.status, jd_id=o.jd_id, version=o.version,
                            warnings=o.warnings, detail=o.detail)
    return JSONResponse(body.model_dump(mode="json"), status_code=code)


def _match_out(m) -> dict:
    return S.MatchOut(run_id=m.run_id, retrieve_run_id=m.retrieve_run_id, jd_id=m.jd_id, jd_version=m.jd_version,
                      n_pool=m.n_pool, items=m.items, warnings=m.warnings, timings=m.timings).model_dump(mode="json")


TOKEN_HEADER = "X-Service-Token"
OPEN_PATHS = {"/health"}


def service_token(token: str | None = None, env: str | None = None) -> str | None:
    """Token giua backend Java va API. `CVMATCH_ENV=prod` bat buoc co token (khong co -> loi khi tao app)."""
    token = token if token is not None else (os.environ.get("CVMATCH_SERVICE_TOKEN") or None)
    env = env or os.environ.get("CVMATCH_ENV", "dev")
    if env == "prod" and not token:
        raise RuntimeError("CVMATCH_ENV=prod can CVMATCH_SERVICE_TOKEN")
    return token


def create_app(services: Services | Callable[[], Services] | None = None, *, token: str | None = None,
               env: str | None = None) -> FastAPI:
    """`services`: doi tuong co san (test - app KHONG dong no), ham tao, hoac None (doc env).

    `token` (mac dinh env `CVMATCH_SERVICE_TOKEN`): co -> moi request tru `/health` phai gui header
    `X-Service-Token` dung (ke ca `/docs`, `/openapi.json`). Khong co -> chi dung khi dev.
    """
    expected = service_token(token, env)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        setup_json_logging(stream=True)
        own = not isinstance(services, Services)
        svc = services if isinstance(services, Services) else (services or default_services)()
        app.state.svc, app.state.jobs = svc, JobRegistry()
        log_event("api_start", **{k: v for k, v in svc.cfg.versions.model_dump().items()})
        # S05 / V-12: lam nong cache token BERTScore chay nen (API nhan request ngay). 0 = tat.
        warm_s = float(os.environ.get("CVMATCH_WARM_MAX_S", "600" if own else "0"))
        if warm_s > 0:
            threading.Thread(target=svc.warm_cache, kwargs={"max_s": warm_s}, name="warm-cache", daemon=True).start()
        try:
            yield
        finally:
            app.state.jobs.shutdown()
            if own:
                svc.close()

    app = FastAPI(title="cvmatch", version="0.1.0", lifespan=lifespan,
                  description="Match CV ↔ JD (Tầng 0–3). Luồng: POST /cv, POST /jd → POST /match/jd/{jd_id} → "
                              "GET /match/{run_id}/cv/{cv_id}/explain.")

    if expected:
        @app.middleware("http")
        async def _auth(request: Request, call_next):
            if request.url.path not in OPEN_PATHS:
                got = request.headers.get(TOKEN_HEADER, "")
                if not hmac.compare_digest(got.encode("utf-8"), expected.encode("utf-8")):
                    return JSONResponse({"detail": f"thieu hoac sai {TOKEN_HEADER}"}, status_code=401)
            return await call_next(request)

    def svc(req: Request) -> Services:
        return req.app.state.svc

    @app.exception_handler(JdNotReady)
    async def _jd_not_ready(_: Request, e: JdNotReady):
        return JSONResponse({"detail": str(e)}, status_code=404 if str(e).startswith("khong co") else 409)

    @app.exception_handler(CvNotReady)
    async def _cv_not_ready(_: Request, e: CvNotReady):
        return JSONResponse({"detail": str(e)}, status_code=404 if str(e).startswith("khong co") else 409)

    @app.exception_handler(FactsNotFound)
    async def _facts(_: Request, e: FactsNotFound):
        return JSONResponse({"detail": str(e)}, status_code=404)

    @app.exception_handler(RerankError)
    async def _rerank(_: Request, e: RerankError):
        return JSONResponse({"detail": str(e)}, status_code=409)

    @app.exception_handler(ExplainCheckError)
    async def _explain_check(_: Request, e: ExplainCheckError):
        log_event("explain_check_error", problems=getattr(e, "problems", str(e)))
        return JSONResponse({"detail": f"Explain kiem tra khong qua (bug mau): {e}"}, status_code=500)

    # ------------------------------------------------------------- Tang 0

    @app.post("/cv", response_model=S.CvIngestResult, tags=["cv"],
              responses={422: {"model": S.CvIngestResult}, 500: {"model": S.CvIngestResult}})
    def post_cv(request: Request, cv: dict[str, Any] = Body(..., description="CV JSON (dau ra Module 1)")):
        """Luong A cho MOT CV (dong bo). `duplicate` -> tra cv_id da co."""
        return _cv_response(svc(request).ingest_cv(cv))

    @app.post("/cv/batch", tags=["cv"], responses={200: {"model": S.CvBatchOut}, 202: {"model": S.JobOut}})
    def post_cv_batch(request: Request, body: S.CvBatchIn):
        """Nap CV theo lo. `background=true` (mac dinh) -> 202 + job; ket qua o `GET /jobs/{id}`."""
        s = svc(request)
        items = [(f"batch[{i}]", cv) for i, cv in enumerate(body.items)]
        run = lambda: {"results": [_cv_result(o) for o in s.ingest_cvs(items)]}  # noqa: E731
        if body.background:
            return JSONResponse(request.app.state.jobs.submit("ingest_cv_batch", run), status_code=202)
        return run()

    @app.patch("/cv/{cv_id}", response_model=S.CvPatchOut, tags=["cv"], responses=_ERR)
    def patch_cv(request: Request, cv_id: str, body: S.CvPatchIn):
        """S07: ung vien bat / tat nhan goi y viec lam (ap cho moi ban CV cua cung nguoi)."""
        ids = svc(request).set_recommendable(cv_id, body.recommendable)
        if ids is None:
            raise HTTPException(404, f"khong co CV {cv_id}")
        return {"cv_id": cv_id, "recommendable": body.recommendable, "cv_ids": ids}

    @app.delete("/cv/{cv_id}", response_model=S.CvDeleteOut, tags=["cv"], responses=_ERR)
    def del_cv(request: Request, cv_id: str):
        if not svc(request).delete_cv(cv_id):
            raise HTTPException(404, f"khong co CV {cv_id}")
        return {"cv_id": cv_id, "deleted": True}

    @app.post("/jd", response_model=S.JdIngestResult, tags=["jd"],
              responses={422: {"model": S.JdIngestResult}, 500: {"model": S.JdIngestResult}})
    def post_jd(request: Request, jd: dict[str, Any] = Body(..., description="JD JSON (dau ra Module 1)")):
        """Luong B. Noi dung khong doi -> `unchanged` (giu version)."""
        return _jd_response(svc(request).ingest_jd(jd))

    @app.patch("/jd/{jd_id}/status", response_model=S.JdStatusOut, tags=["jd"], responses=_ERR)
    def patch_jd_status(request: Request, jd_id: str, body: S.JdStatusIn):
        v = svc(request).set_jd_status(jd_id, body.status)
        if v is None:
            raise HTTPException(404, f"khong co JD {jd_id}")
        return {"jd_id": jd_id, "version": v, "status": body.status}

    # ------------------------------------------------------------- Tang 1-3

    @app.post("/match/jd/{jd_id}", tags=["match"], responses={200: {"model": S.MatchOut}, 202: {"model": S.JobOut},
                                                               **_ERR})
    def match_jd(request: Request, jd_id: str, body: S.MatchIn | None = None):
        """Retrieve (top K) -> Rerank (top N). `background=true` -> 202 + job."""
        body = body or S.MatchIn()
        s = svc(request)
        hf = body.hard_filters.model_dump(exclude_none=True) if body.hard_filters else None
        if hf is not None and not (hf.get("location") or hf.get("min_years") is not None):
            hf = None
        run = lambda: _match_out(s.match_jd(jd_id, K=body.K, N=body.N, hard_filters=hf,  # noqa: E731
                                            exclude_cv_ids=body.exclude_cv_ids, views=body.views,
                                            ref_ym=body.ref_ym, include_cv_ids=body.include_cv_ids,
                                            only_recommendable=body.only_recommendable, min_score=body.min_score))
        if body.background:
            return JSONResponse(request.app.state.jobs.submit("match_jd", run), status_code=202)
        return run()

    @app.get("/match/{run_id}/cv/{cv_id}/explain", response_model=S.ExplainOut, tags=["match"], responses=_ERR)
    def get_explain(request: Request, run_id: str, cv_id: str, force: bool = False):
        """Explain luoi (mau xac dinh, cache theo facts + template_version)."""
        return svc(request).explain(run_id, cv_id, force=force)

    # ------------------------------------------------------------- Luong D (CV -> JD, cho ung vien)

    @app.post("/match/cv:preview", response_model=S.PreviewOut, tags=["match-cv"])
    def match_cv_preview(request: Request, body: S.PreviewIn):
        """CV tam: Luong A -> D -> giai thich ngay; KHONG luu CV, log match/rerank sau khi tra."""
        hf = body.hard_filters.model_dump(exclude_none=True) if body.hard_filters else None
        out = svc(request).preview_cv(body.cv, N=body.N, hard_filters=hf or None, ref_ym=body.ref_ym,
                                      n_explain=body.n_explain)
        code = {"invalid": 422, "failed": 500}.get(out["status"], 200)
        return JSONResponse(S.PreviewOut(**out).model_dump(mode="json"), status_code=code)

    @app.post("/match/cv/{cv_id}", tags=["match-cv"], responses={200: {"model": S.MatchCvOut},
                                                                 202: {"model": S.JobOut}, **_ERR})
    def match_cv(request: Request, cv_id: str, body: S.MatchCvIn | None = None):
        """Luong D: CV da co trong kho -> top N JD dang mo (kiem lai status luc tra)."""
        body = body or S.MatchCvIn()
        s = svc(request)
        hf = body.hard_filters.model_dump(exclude_none=True) if body.hard_filters else None

        def run():
            m = s.match_cv(cv_id, K=body.K, N=body.N, hard_filters=hf or None, exclude_jd_ids=body.exclude_jd_ids,
                           views=body.views, ref_ym=body.ref_ym, include_jd_ids=body.include_jd_ids)
            return S.MatchCvOut(run_id=m.run_id, retrieve_run_id=m.retrieve_run_id, cv_id=cv_id, n_pool=m.n_pool,
                                items=m.items, warnings=m.warnings, timings=m.timings).model_dump(mode="json")

        if body.background:
            return JSONResponse(request.app.state.jobs.submit("match_cv", run), status_code=202)
        return run()

    @app.get("/match/{run_id}/jd/{jd_id}/explain", response_model=S.ExplainOut, tags=["match-cv"], responses=_ERR)
    def get_explain_candidate(request: Request, run_id: str, jd_id: str, force: bool = False):
        """Giai thich huong ung vien (08 muc 5): khong diem so, nhan "CV cua ban chua the hien ..."."""
        return svc(request).explain(run_id, jd_id, force=force)

    # ------------------------------------------------------------- khac

    @app.get("/jobs/{job_id}", response_model=S.JobOut, tags=["jobs"], responses=_ERR)
    def get_job(request: Request, job_id: str):
        j = request.app.state.jobs.get(job_id)
        if j is None:
            raise HTTPException(404, f"khong co job {job_id}")
        return j

    @app.get("/health", response_model=S.HealthOut, tags=["health"], responses={503: {"model": S.HealthOut}})
    def health(request: Request):
        h = svc(request).health()
        if h["status"] != "ok":
            return JSONResponse(S.HealthOut(**h).model_dump(mode="json"), status_code=503)
        return h

    return app


app = create_app()  # uvicorn cvmatch.api.app:app (doc env)
