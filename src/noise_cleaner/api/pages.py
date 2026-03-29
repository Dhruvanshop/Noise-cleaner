"""HTML page routes — serve every static tool page."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ..config import STATIC_DIR

router = APIRouter(tags=["pages"])


def _page(rel: str) -> HTMLResponse:
    return HTMLResponse((STATIC_DIR / rel).read_text(encoding="utf-8"))


@router.get("/",                  response_class=HTMLResponse)
def page_index():      return _page("index.html")

@router.get("/tools/normalize",   response_class=HTMLResponse)
def page_normalize():  return _page("tools/normalize.html")

@router.get("/tools/convert",     response_class=HTMLResponse)
def page_convert():    return _page("tools/convert.html")

@router.get("/tools/trim",        response_class=HTMLResponse)
def page_trim():       return _page("tools/trim.html")

@router.get("/tools/stems",       response_class=HTMLResponse)
def page_stems():      return _page("tools/stems.html")

@router.get("/tools/video",       response_class=HTMLResponse)
def page_video():      return _page("tools/video.html")

@router.get("/tools/caption",       response_class=HTMLResponse)
def page_caption():       return _page("tools/caption.html")

@router.get("/tools/repair",        response_class=HTMLResponse)
def page_repair():        return _page("tools/repair.html")

@router.get("/tools/dereverberate", response_class=HTMLResponse)
def page_dereverberate(): return _page("tools/dereverberate.html")

@router.get("/tools/analyze",       response_class=HTMLResponse)
def page_analyze():       return _page("tools/analyze.html")

@router.get("/tools/batch",         response_class=HTMLResponse)
def page_batch():         return _page("tools/batch.html")

@router.get("/tools/remix",         response_class=HTMLResponse)
def page_remix():         return _page("tools/remix.html")

@router.get("/privacy",             response_class=HTMLResponse)
def page_privacy():       return _page("privacy.html")

@router.get("/terms",               response_class=HTMLResponse)
def page_terms():         return _page("terms.html")

@router.get("/tools/pipeline",      response_class=HTMLResponse)
def page_pipeline():      return _page("tools/pipeline.html")
