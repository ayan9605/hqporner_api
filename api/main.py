from fastapi import FastAPI, HTTPException, Query, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import logging
import os
import base64
import requests
from io import BytesIO

# Import the hqporner package
from hqporner_api import Client, Video, Sort

app = FastAPI(
    title="HQPorner — FastAPI Exposer (Unofficial)",
    description="Unofficial wrapper exposing selected HQPorner functionality via FastAPI. Use responsibly.",
    version="0.1.0",
)

# Basic CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # CHANGE in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API key (optional)
API_KEY = os.environ.get("HS_API_KEY", None)

def require_api_key(x_api_key: Optional[str] = Header(None)):
    if API_KEY is None:
        return True
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API Key")
    return True

# Shared client instance
_client = None

def get_client():
    global _client
    if _client is None:
        _client = Client()
    return _client

# Utility: convert video to dict and optionally include base64
def video_to_dict(video, as_base64: bool = False):
    try:
        base_dict = {
            "url": getattr(video, "url", None),
            "title": getattr(video, "title", None),
            "pornstars": getattr(video, "pornstars", []),
            "length": getattr(video, "length", None),
            "publish_date": getattr(video, "publish_date", None),
            "thumbnails": video.get_thumbnails() if hasattr(video, "get_thumbnails") else [],
            "direct_download_urls": video.direct_download_urls() if hasattr(video, "direct_download_urls") else [],
        }
        if as_base64:
            dd = base_dict["direct_download_urls"]
            if dd:
                first_url = dd[0]
                if first_url.startswith("data:video/mp4;base64,"):
                    base64_data = first_url.split(",")[1]
                else:
                    response = requests.get(first_url)
                    base64_data = base64.b64encode(response.content).decode("utf-8")
                base_dict["download_base64"] = base64_data
        return base_dict
    except Exception:
        return {"url": getattr(video, "url", None)}

@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}

@app.get("/search", tags=["search"])
def search(
    query: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    as_base64: bool = Query(False, description="Return MP4 as base64"),
    api_key_ok: bool = Depends(require_api_key)
):
    client = get_client()
    try:
        results = []
        videos = client.search_videos(query, pages=page)
        for idx, v in enumerate(videos):
            if idx >= 30:
                break
            results.append(video_to_dict(v, as_base64=as_base64))
        return {"query": query, "page": page, "count": len(results), "results": results}
    except Exception as e:
        logging.exception("Search failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/video", tags=["video"])
def get_video(
    url: str = Query(...),
    as_base64: bool = Query(False, description="Return MP4 as base64"),
    api_key_ok: bool = Depends(require_api_key)
):
    client = get_client()
    try:
        video = client.get_video(url)
        return video_to_dict(video, as_base64=as_base64)
    except Exception as e:
        logging.exception("get_video error")
        raise HTTPException(status_code=400, detail=str(getattr(e, "msg", str(e))))

@app.get("/top", tags=["browse"])
def top(
    sort: Optional[str] = Query(None, description="sort by: 'all-time' or 'week'"),
    limit: int = Query(10, ge=1, le=50),
    as_base64: bool = Query(False, description="Return MP4 as base64"),
    api_key_ok: bool = Depends(require_api_key)
):
    client = get_client()
    try:
        sort_val = sort or Sort.ALL_TIME
        videos = client.get_top_porn(sort_by=sort_val)
        out = [video_to_dict(v, as_base64=as_base64) for idx, v in enumerate(videos) if idx < limit]
        return {"sort": sort_val, "count": len(out), "results": out}
    except Exception as e:
        logging.exception("top error")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/actor", tags=["browse"])
def videos_by_actress(
    name: str = Query(...),
    limit: int = Query(10, ge=1, le=50),
    as_base64: bool = Query(False, description="Return MP4 as base64"),
    api_key_ok: bool = Depends(require_api_key)
):
    client = get_client()
    try:
        videos = client.get_videos_by_actress(name)
        out = [video_to_dict(v, as_base64=as_base64) for idx, v in enumerate(videos) if idx < limit]
        return {"actress": name, "count": len(out), "results": out}
    except Exception as e:
        logging.exception("actress error")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/random", tags=["browse"])
def random_video(
    as_base64: bool = Query(False, description="Return MP4 as base64"),
    api_key_ok: bool = Depends(require_api_key)
):
    client = get_client()
    try:
        v = client.get_random_video()
        return video_to_dict(v, as_base64=as_base64)
    except Exception as e:
        logging.exception("random error")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download-links", tags=["download"])
def download_links(
    url: str = Query(...),
    as_base64: bool = Query(False, description="Return MP4 as base64"),
    api_key_ok: bool = Depends(require_api_key)
):
    client = get_client()
    try:
        video = client.get_video(url)
        return video_to_dict(video, as_base64=as_base64)
    except Exception as e:
        logging.exception("download_links error")
        raise HTTPException(status_code=400, detail=str(e))