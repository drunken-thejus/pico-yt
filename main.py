"""
YouTube Music FastAPI — Search Endpoints
Covers: general search, album search, playlist search
"""

from fastapi import FastAPI, HTTPException, Query
from typing import Optional, List
from ytmusicapi import YTMusic
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI(
    title="YouTube Music API",
    description="FastAPI wrapper around ytmusicapi for searching songs, albums, playlists & more.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

yt = YTMusic()


# ══════════════════════════════════════════════
# HELPER / UTILITY FUNCTIONS
# ══════════════════════════════════════════════

def format_thumbnail(thumbnails: list) -> Optional[str]:
    if not thumbnails:
        return None
    return thumbnails[-1].get("url")


def format_duration(duration_seconds: Optional[int]) -> Optional[str]:
    if duration_seconds is None:
        return None
    minutes, seconds = divmod(int(duration_seconds), 60)
    return f"{minutes}:{seconds:02d}"


def extract_artists(artists: Optional[list]) -> List[dict]:
    if not artists:
        return []
    return [
        {"name": a.get("name"), "id": a.get("id")}
        for a in artists
        if isinstance(a, dict)
    ]


def format_song(track: dict) -> dict:
    return {
        "videoId": track.get("videoId"),
        "title": track.get("title"),
        "artists": extract_artists(track.get("artists")),
        "album": (track.get("album") or {}).get("name"),
        "albumId": (track.get("album") or {}).get("id"),
        "duration": track.get("duration"),
        "durationSeconds": track.get("duration_seconds"),
        "isExplicit": track.get("isExplicit", False),
        "thumbnail": format_thumbnail(track.get("thumbnails")),
        "feedbackTokens": track.get("feedbackTokens"),
        "videoType": track.get("videoType"),
        "likeStatus": track.get("likeStatus"),
    }


def format_album_result(item: dict) -> dict:
    return {
        "browseId": item.get("browseId"),
        "title": item.get("title"),
        "artists": extract_artists(item.get("artists")),
        "year": item.get("year"),
        "type": item.get("type"),
        "isExplicit": item.get("isExplicit", False),
        "thumbnail": format_thumbnail(item.get("thumbnails")),
    }


def format_artist_result(item: dict) -> dict:
    return {
        "browseId": item.get("browseId"),
        "name": item.get("artist"),
        "shuffleId": item.get("shuffleId"),
        "radioId": item.get("radioId"),
        "thumbnail": format_thumbnail(item.get("thumbnails")),
    }


def format_playlist_result(item: dict) -> dict:
    return {
        "browseId": item.get("browseId"),
        "title": item.get("title"),
        "author": item.get("author"),
        "itemCount": item.get("itemCount"),
        "thumbnail": format_thumbnail(item.get("thumbnails")),
    }


def format_video_result(item: dict) -> dict:
    return {
        "videoId": item.get("videoId"),
        "title": item.get("title"),
        "artists": extract_artists(item.get("artists")),
        "views": item.get("views"),
        "duration": item.get("duration"),
        "thumbnail": format_thumbnail(item.get("thumbnails")),
        "videoType": item.get("videoType"),
    }


def classify_and_format(item: dict) -> dict:
    result_type = item.get("resultType", "unknown")
    if result_type == "song":
        return {"resultType": "song", **format_song(item)}
    if result_type == "album":
        return {"resultType": "album", **format_album_result(item)}
    if result_type == "artist":
        return {"resultType": "artist", **format_artist_result(item)}
    if result_type in ("playlist", "community_playlist", "featured_playlist"):
        return {"resultType": result_type, **format_playlist_result(item)}
    if result_type == "video":
        return {"resultType": "video", **format_video_result(item)}
    return {"resultType": result_type, **item}


def get_album_by_id(browse_id: str) -> dict:
    try:
        raw = yt.get_album(browse_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"YTMusic error: {exc}")
    tracks = [format_song(t) for t in raw.get("tracks", [])]
    return {
        "browseId": browse_id,
        "title": raw.get("title"),
        "type": raw.get("type"),
        "year": raw.get("year"),
        "trackCount": raw.get("trackCount"),
        "duration": raw.get("duration"),
        "durationMs": raw.get("durationMs"),
        "description": raw.get("description"),
        "isExplicit": raw.get("isExplicit", False),
        "artists": extract_artists(raw.get("artists")),
        "thumbnail": format_thumbnail(raw.get("thumbnails")),
        "playlistId": raw.get("audioPlaylistId"),
        "tracks": tracks,
    }


def format_artist_top_songs(songs: list) -> List[dict]:
    results = []
    for s in songs:
        results.append({
            "videoId": s.get("videoId"),
            "title": s.get("title"),
            "artists": extract_artists(s.get("artists")),
            "album": (s.get("album") or {}).get("name"),
            "albumId": (s.get("album") or {}).get("id"),
            "duration": s.get("duration"),
            "isExplicit": s.get("isExplicit", False),
            "thumbnail": format_thumbnail(s.get("thumbnails")),
            "views": s.get("views"),
        })
    return results


def format_artist_albums(releases: list) -> List[dict]:
    results = []
    for a in releases:
        results.append({
            "browseId": a.get("browseId"),
            "audioPlaylistId": a.get("audioPlaylistId"),
            "title": a.get("title"),
            "year": a.get("year"),
            "type": a.get("type"),
            "isExplicit": a.get("isExplicit", False),
            "thumbnail": format_thumbnail(a.get("thumbnails")),
        })
    return results


def get_artist_releases(channel_id: str, raw_section: dict, release_type: str) -> List[dict]:
    items = raw_section.get("results", [])
    params = raw_section.get("params")
    browse_id = raw_section.get("browseId")
    if params and browse_id:
        try:
            items = yt.get_artist_albums(browse_id, params) or items
        except Exception:
            pass
    return format_artist_albums(items)


def get_playlist_by_id(playlist_id: str, limit: int = 100) -> dict:
    try:
        raw = yt.get_playlist(playlist_id, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"YTMusic error: {exc}")
    tracks = [format_song(t) for t in (raw.get("tracks") or [])]
    return {
        "id": raw.get("id"),
        "title": raw.get("title"),
        "author": (raw.get("author") or {}).get("name"),
        "description": raw.get("description"),
        "trackCount": raw.get("trackCount"),
        "duration": raw.get("duration"),
        "privacy": raw.get("privacy"),
        "thumbnail": format_thumbnail(raw.get("thumbnails")),
        "tracks": tracks,
    }


# ══════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════

@app.get("/search", summary="General search", tags=["Search"])
def general_search(
    q: str = Query(..., description="Search query string"),
    filter: Optional[str] = Query(None, description="songs | videos | albums | artists | playlists | community_playlists | featured_playlists | uploads"),
    limit: int = Query(20, ge=1, le=100),
    ignore_spelling: bool = Query(False),
):
    valid_filters = {"songs","videos","albums","artists","playlists","community_playlists","featured_playlists","uploads"}
    if filter and filter not in valid_filters:
        raise HTTPException(status_code=400, detail=f"Invalid filter '{filter}'. Choose from: {sorted(valid_filters)}")
    try:
        raw_results = yt.search(query=q, filter=filter, limit=limit, ignore_spelling=ignore_spelling)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"YTMusic error: {exc}")
    results = [classify_and_format(item) for item in (raw_results or [])]
    if not filter:
        grouped: dict = {}
        for r in results:
            rtype = r.get("resultType", "other")
            grouped.setdefault(rtype, []).append(r)
        return {"query": q, "total": len(results), "grouped": grouped, "results": results}
    return {"query": q, "filter": filter, "total": len(results), "results": results}


@app.get("/search/album", summary="Search albums + full tracklist", tags=["Search"])
def search_album(
    q: str = Query(...),
    limit: int = Query(5, ge=1, le=20),
    ignore_spelling: bool = Query(False),
):
    try:
        album_results = yt.search(query=q, filter="albums", limit=limit, ignore_spelling=ignore_spelling)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"YTMusic search error: {exc}")
    if not album_results:
        return {"query": q, "total": 0, "albums": []}
    albums = []
    for item in album_results[:limit]:
        browse_id = item.get("browseId")
        if not browse_id:
            continue
        try:
            albums.append(get_album_by_id(browse_id))
        except HTTPException:
            albums.append({"browseId": browse_id, "title": item.get("title"), "error": "Failed to fetch full album details"})
    return {"query": q, "total": len(albums), "albums": albums}


@app.get("/album/{browse_id}", summary="Get full album by browseId", tags=["Albums"])
def get_album(browse_id: str):
    return get_album_by_id(browse_id)


@app.get("/search/playlist", summary="Search playlists + full tracklist", tags=["Search"])
def search_playlist(
    q: str = Query(...),
    limit: int = Query(5, ge=1, le=20),
    tracks_limit: int = Query(50, ge=1, le=500),
    ignore_spelling: bool = Query(False),
):
    try:
        community = yt.search(query=q, filter="community_playlists", limit=limit, ignore_spelling=ignore_spelling) or []
        featured = yt.search(query=q, filter="featured_playlists", limit=limit, ignore_spelling=ignore_spelling) or []
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"YTMusic search error: {exc}")
    raw_list = (community + featured)[:limit]
    if not raw_list:
        return {"query": q, "total": 0, "playlists": []}
    playlists = []
    for item in raw_list:
        browse_id = item.get("browseId")
        if not browse_id:
            continue
        playlist_id = browse_id.replace("VL", "") if browse_id.startswith("VL") else browse_id
        try:
            playlists.append(get_playlist_by_id(playlist_id, limit=tracks_limit))
        except HTTPException:
            playlists.append({"browseId": browse_id, "title": item.get("title"), "error": "Failed to fetch full playlist details"})
    return {"query": q, "total": len(playlists), "playlists": playlists}


@app.get("/playlist/{playlist_id}", summary="Get full playlist by ID", tags=["Playlists"])
def get_playlist(
    playlist_id: str,
    limit: int = Query(100, ge=1, le=500),
):
    return get_playlist_by_id(playlist_id, limit=limit)


@app.get("/search/suggestions", summary="Autocomplete suggestions", tags=["Search"])
def search_suggestions(
    q: str = Query(...),
    detailed: bool = Query(False),
):
    try:
        suggestions = yt.get_search_suggestions(q, detailed_runs=detailed)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"YTMusic error: {exc}")
    return {"query": q, "suggestions": suggestions}


@app.get(
    "/artist/{channel_id}",
    summary="Artist profile — top songs, albums, singles",
    tags=["Artists"],
)
def get_artist_profile(
    channel_id: str,
    full_albums: bool = Query(False, description="Fetch full tracklists for every album/single"),
    albums_limit: int = Query(10, ge=1, le=50),
    top_songs_limit: int = Query(10, ge=1, le=50),
):
    try:
        raw = yt.get_artist(channel_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"YTMusic error: {exc}")

    songs_section = raw.get("songs", {})
    top_songs = format_artist_top_songs(songs_section.get("results", [])[:top_songs_limit])
    songs_playlist_id = songs_section.get("browseId")

    albums_raw = get_artist_releases(channel_id, raw.get("albums", {}), "albums")[:albums_limit]
    if full_albums:
        expanded = []
        for a in albums_raw:
            bid = a.get("browseId")
            try:
                expanded.append(get_album_by_id(bid) if bid else a)
            except HTTPException:
                expanded.append({**a, "error": "Could not fetch full album"})
        albums_raw = expanded

    singles_raw = get_artist_releases(channel_id, raw.get("singles", {}), "singles")[:albums_limit]
    if full_albums:
        expanded = []
        for s in singles_raw:
            bid = s.get("browseId")
            try:
                expanded.append(get_album_by_id(bid) if bid else s)
            except HTTPException:
                expanded.append({**s, "error": "Could not fetch full single"})
        singles_raw = expanded

    related = [
        {
            "browseId": r.get("browseId"),
            "name": r.get("title"),
            "subscribers": r.get("subscribers"),
            "thumbnail": format_thumbnail(r.get("thumbnails")),
        }
        for r in raw.get("related", {}).get("results", [])
    ]

    return {
        "channelId": channel_id,
        "name": raw.get("name"),
        "description": raw.get("description"),
        "views": raw.get("views"),
        "subscribers": raw.get("subscribers"),
        "thumbnail": format_thumbnail(raw.get("thumbnails")),
        "bannerThumbnail": format_thumbnail(raw.get("bannerThumbnails")),
        "shuffleId": raw.get("shuffleId"),
        "radioId": raw.get("radioId"),
        "songsPlaylistId": songs_playlist_id,
        "topSongs": top_songs,
        "albums": {"total": len(albums_raw), "items": albums_raw},
        "singles": {"total": len(singles_raw), "items": singles_raw},
        "relatedArtists": related,
    }


@app.get("/health", tags=["Utility"])
def health():
    return {"status": "ok", "client": "ytmusicapi", "authenticated": False}
