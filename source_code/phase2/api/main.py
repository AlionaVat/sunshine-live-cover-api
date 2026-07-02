from pathlib import Path
from urllib.parse import quote
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi import Depends
from phase2.api.auth import check_demo_access


MIN_SCORE = 0.45

DB_CONFIG = {
    "dbname": "music_archive_phase2",
    "user": "Aliona",
    "host": "localhost",
    "port": 5432,
}

PROJECT_ROOT = Path(__file__).resolve().parents[2]
IMAGES_ROOT = PROJECT_ROOT / "project" / "data" / "images" / "processed"
AUDIO_ROOT = PROJECT_ROOT


app = FastAPI(
    title="Music Archive Cover API",
    description="Fuzzy search API for retrieving track metadata and artwork covers.",
    version="2.0.0",
)

app.mount(
    "/images",
    StaticFiles(directory=str(IMAGES_ROOT)),
    name="images",
)

app.mount(
    "/audio",
    StaticFiles(directory=str(AUDIO_ROOT)),
    name="audio",
)


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def normalize_query(value: str) -> str:
    return value.strip().lower()


def build_image_url(path_value):
    if not path_value:
        return None

    path_value = str(path_value)
    filename = Path(path_value).name

    if "small" in path_value:
        return f"/images/small/{filename}"

    if "medium" in path_value:
        return f"/images/medium/{filename}"

    if "large" in path_value:
        return f"/images/large/{filename}"

    return f"/images/{filename}"

def build_audio_url(path_value):
    if not path_value:
        return None

    clean_path = str(path_value).lstrip("./")
    encoded_path = quote(clean_path, safe="/")
    return f"/audio/{encoded_path}"


def get_confidence(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def format_track(row, rank=None):
    total_score = float(row["total_score"])

    data = {
        "id": row["id"],
        "artist": row["id3_artist"],
        "title": row["id3_title"],
        "scores": {
            "artist": round(float(row["artist_score"]), 4),
            "title": round(float(row["title_score"]), 4),
            "total": round(min(total_score, 1.0), 4),
        },
        "confidence": get_confidence(total_score),
        "artwork_available": bool(row["artwork_small"] or row["artwork_medium"] or row["artwork_large"]),

       "audio_url": build_audio_url(row["path"]),

         "artwork": {
            "small": build_image_url(row["artwork_small"]),
            "medium": build_image_url(row["artwork_medium"]),
            "large": build_image_url(row["artwork_large"]),
        },
    }

    if rank is not None:
        data["rank"] = rank

    return data


SEARCH_SQL = """
SELECT
    id,
    path,
    id3_artist,
    id3_title,
    artwork_small,
    artwork_medium,
    artwork_large,

    similarity(search_artist, %s) AS artist_score,
    similarity(search_title, %s) AS title_score,
    similarity(search_text, %s) AS text_score,

    CASE
        WHEN search_artist ILIKE '%%' || %s || '%%' THEN 0.20
        ELSE 0
    END AS artist_bonus,

    CASE
        WHEN search_title ILIKE '%%' || %s || '%%' THEN 0.25
        ELSE 0
    END AS title_bonus,

    (
        similarity(search_artist, %s) * 0.30 +
        similarity(search_title, %s) * 0.35 +
        similarity(search_text, %s) * 0.20 +

        CASE
            WHEN search_artist ILIKE '%%' || %s || '%%' THEN 0.20
            ELSE 0
        END +

        CASE
            WHEN search_title ILIKE '%%' || %s || '%%' THEN 0.25
            ELSE 0
        END
    ) AS total_score

FROM tracks
WHERE
    search_artist %% %s
    OR search_title %% %s
    OR search_text %% %s
    OR search_artist ILIKE '%%' || %s || '%%'
    OR search_title ILIKE '%%' || %s || '%%'

ORDER BY total_score DESC
LIMIT %s;
"""


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Music Archive Cover API",
        "version": "2.0.0",
        "database": "music_archive_phase2",
        "endpoints": [
            "/health",
            "/cover",
            "/cover/candidates",
            "/docs",
        ],
    }


@app.get("/health")
def health_check():
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM tracks;")
            total_tracks = cur.fetchone()[0]

        return {
            "status": "healthy",
            "database": "connected",
            "tracks": total_tracks,
        }

    finally:
            conn.close()


@app.get("/cover")
def get_cover(
    artist: str = Query(..., description="Artist name"),
    title: str = Query(..., description="Track title"),
):
    artist_query = normalize_query(artist)
    title_query = normalize_query(title)

    conn = get_db_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                SEARCH_SQL,
                (
                    artist_query,
                    title_query,
                    f"{artist_query} {title_query}",
                    artist_query,
                    title_query,
                    artist_query,
                    title_query,
                    f"{artist_query} {title_query}",
                    artist_query,
                    title_query,
                    artist_query,
                    title_query,
                    f"{artist_query} {title_query}",
                    artist_query,
                    title_query,
                    1,
                ),
            )
            row = cur.fetchone()

        if not row:
            return {
                "found": False,
                "status": "no_match",
                "message": "No matching cover found.",
                "query": {
                    "artist": artist,
                    "title": title,
                },
            }

        total_score = float(row["total_score"])

        if total_score < MIN_SCORE:
            return {
                "found": False,
                "status": "below_threshold",
                "message": "No reliable matching cover found.",
                "threshold": MIN_SCORE,
                "best_score": round(total_score, 4),
                "query": {
                    "artist": artist,
                    "title": title,
                },
            }

        return {
            "found": True,
            "status": "reliable_match",
            "query": {
                "artist": artist,
                "title": title,
            },
            "match": format_track(row),
        }

    finally:
        conn.close()


@app.get("/cover/candidates")
def get_cover_candidates(
    artist: str = Query(..., description="Artist name"),
    title: str = Query(..., description="Track title"),
    limit: int = Query(5, ge=1, le=20, description="Number of candidates to return"),
):
    artist_query = normalize_query(artist)
    title_query = normalize_query(title)

    conn = get_db_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                SEARCH_SQL,
                (
                     artist_query,
                     title_query,
                     f"{artist_query} {title_query}",
                     artist_query,
                     title_query,
                     artist_query,
                     title_query,
                     f"{artist_query} {title_query}",
                     artist_query,
                     title_query,
                     artist_query,
                     title_query,
                     f"{artist_query} {title_query}",
                     artist_query,
                     title_query,
                     limit,
                ),
            )
            rows = cur.fetchall()

        candidates = [
            format_track(row, rank=index + 1)
            for index, row in enumerate(rows)
            if float(row["total_score"]) >= MIN_SCORE
        ]

        return {
            "query": {
                "artist": artist,
                "title": title,
            },
            "status": "candidates_found" if candidates else "no_reliable_candidates",
            "threshold": MIN_SCORE,
            "count": len(candidates),
            "recommendation": (
                "Use candidate with highest total_score."
                if candidates
                else "No candidate passed the reliability threshold."
            ),
            "candidates": candidates,
        }

    finally:
            conn.close()


@app.get("/demo", response_class=HTMLResponse)
def demo_page(user: str = Depends(check_demo_access)):
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Music Archive Cover Search</title>
    <style>
        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: radial-gradient(circle at top, #1f1147, #050816 55%, #020617);
            color: #ffffff;
            min-height: 100vh;
            padding: 40px;
        }

        .container {
            max-width: 1050px;
            margin: auto;
        }
       
       .header {
           position: relative;
           text-align: center;
           margin-bottom: 40px;
           padding-top: 30px 40px 36px;
           border-bottom: 1px solid rgba(139; 92, 246, 0.45);
        }

       .brand-logo {
           position: absolute;
           left: 30px;
           top: 24px;
           height: 64px;
           width: auto;
       }

       .header-content {
           text-align: center;
           max-width: 900px;
           margin: 0 auto;
       }

       .api-docs {
            position: absolute;
            right: 30px;
            top: 24px;
            padding: 12px 20px;
            border: 1px solid rgba(139, 92, 246, 0.5);
            border-radius: 12px;
            color: white;
            text-decoration: none;
            font-weight: 600;
            transition: all .2s ease;
       }
       
       .api-docs:hover {
            background: rgba(139, 92, 246, 0.15);
            border-color: #8b5cf6;
       }

       h1 {
           font-size: 46px;
           line-height: 1.15
           letter-spacing:0.5px;
           font-weight: 700; 
       }

       .subtitle {
           color: #a5b4fc;
           margin-top: 10px;
           font-size: 18px;
       }

       .search-box {
           display: flex;
           gap: 14px;
           background: rgba(15, 23, 42, 0.88);
           padding: 18px;
           border-radius: 18px;
           border: 1px solid rgba(99, 102, 241, 0.45);
           box-shadow: 0 0 35px rgba(79, 70, 229, 0.35);
        }

        input {
           flex: 1;
           padding: 15px;
           font-size: 16px;
           border-radius: 12px;
           border: 1px solid #334155;
           border-radius: 8px;
           background: #020617;
           color: white;
        }

        button {
           padding: 15px 28px;
           border: none;
           font-size: 16px;
           border-radius: 12px;
           background: linear-gradient(135deg, #06b6d4, #7c3aed);
           color: white;
           border: none;
           font-weight: bold;
           cursor: pointer;
        }


        .result {
            margin-top: 35px;
        }

        .player-card {
            display: grid;
            grid-template-columns: 380px 1fr;
            gap: 32px;
            background: rgba(15, 23, 42, 0.92);
            border: 1px solid rgba(6, 182, 212, 0.35);
            border-radius: 24px;
            padding: 28px;
            box-shadow: 0 0 45px rgba(6, 182, 212, 0.18);
        }

        .cover {
           width: 380px;
            height: 380px;
            object-fit: cover;
            border-radius: 20px;
            background: #020617;
            box-shadow: 0 0 30px rgba(124, 58, 237, 0.45);
        }

        .placeholder {
            width: 380px;
            height: 380px;
            border-radius: 20px;
            background: linear-gradient(135deg, #111827, #312e81);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #94a3b8;
            text-align: center;
        }
        
           .fallback-logo {
            width: 96px;
            height: 96px;
            border-radius: 50%;
            background: linear-gradient(135deg, #06b6d4, #7c3aed);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 34px;
            font-weight: 900;
            letter-spacing: 2px;
            margin-bottom: 18px;
            box-shadow: 0 0 35px rgba(124, 58, 237, 0.55);
       }

           .fallback-text {
            color: #c4b5fd;
            font-size: 16px;
            font-weight: bold;
       }

       .label {
            color: #22d3ee;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-size: 12px;
            font-weight: bold;
        }

        .track-title {
            font-size: 32px;
            font-weight: bold;
            margin-top: 10px;
        }

        .artist {
            font-size: 22px;
            color: #c4b5fd;
            margin: 8px 0 18px;
        }
    
       .badges {
            margin-bottom: 20px;

       .badge {
            display: inline-block;
            padding: 7px 12px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: bold;
            margin-right: 8px;
        }

        .high { background: #064e3b; color: #6ee7b7; }
        .medium { background: #78350f; color: #fde68a; }
        .low { background: #7f1d1d; color: #fecaca; }

        .meta {
            color: #cbd5e1;
            line-height: 1.7;
            font-size: 15px;

         audio {
            width: 100%;
            max-width: 340px;
            height: 34px;
            margin-top: 16px;
            border-radius: 10px;
            outline: none;
            opacity: 0.95;
            
        }
 
         audio:focus {
            outline: none;
        }

        .not-found {
            background: rgba(127, 29, 29, 0.75);
            border: 1px solid #ef4444;
            color: #fee2e2;
            padding: 20px;
            border-radius: 16px;
        }


           .url {
            margin-top: 14px;
            color: #94a3b8;
            font-size: 12px;
            word-break: break-all;
        }

         .archive-status {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 10px;
          margin: 18px 0;
        }

         .archive-status div {
          padding: 10px;
          border-radius: 12px;
          background: rgba(255,255,255,0.06);
          color: #cbd5e1;
          font-size: 13px;
          text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
    <img class="brand-logo" src="/images/sunshine-live-logo.png" alt="Sunshine Live Logo">

    <div class="header-content">
        <h1>Music Archive Cover Search</h1>
        <div class="subtitle">Cover retrieval · metadata search · audio preview</div>
    </div>

    <a class="api-docs" href="/docs" target="_blank">API Docs</a>
</div>

        <div class="search-box">
            <input id="artist" placeholder="Artist name">
            <input id="title" placeholder="Track title">
            <button onclick="searchCover()">Search</button>
        </div>

        <div id="result" class="result"></div>
    </div>

    <script>
        async function searchCover() {
            const artist = document.getElementById("artist").value.trim();
            const title = document.getElementById("title").value.trim();
            const resultDiv = document.getElementById("result");

            if (!artist || !title) {
                resultDiv.innerHTML = '<div class="not-found">Please enter both artist and title.</div>';
                return;
            }

            resultDiv.innerHTML = '<div class="not-found">Searching archive...</div>';

            const response = await fetch(`/cover?artist=${encodeURIComponent(artist)}&title=${encodeURIComponent(title)}`);
            const data = await response.json();
            const candidatesResponse = await fetch(
    `/cover/candidates?artist=${artist}&title=${title}&limit=5`
);

const candidatesData = await candidatesResponse.json();
            if (!data.found) {
                resultDiv.innerHTML = `
                    <div class="not-found">
                        <strong>No reliable match found.</strong><br>
                        ${data.message || "Try another artist or title."}<br>
                        Best score: ${data.best_score || "n/a"}
                    </div>
                `;
                return;
            }

            const match = data.match;
            const artwork = match.artwork.large || match.artwork.medium || match.artwork.small;

            const coverHtml = artwork
                ? `<img class="cover" src="${artwork}" alt="Cover artwork">`
                : `<div class="placeholder">
        <div class="fallback-logo">SL</div>
        <div class="fallback-text">Artwork Enrichment Needed</div>
   </div>`;

            const audioHtml = match.audio_url
                ? `<audio controls src="${match.audio_url}"></audio>`
                : `<div class="url">No audio preview available</div>`;

            resultDiv.innerHTML = `
                <div class="player-card">
                    ${coverHtml}

                    <div>
                        <div class="label">Best Match</div>
                        <div class="track-title">${match.title}</div>
                        <div class="artist">${match.artist}</div>

                        <div class="badges">
                            <span class="badge ${match.confidence}">
                                ${match.confidence.toUpperCase()} CONFIDENCE
                            </span>
                            <span class="badge ${match.artwork_available ? "high" : "low"}">
    ${match.artwork_available ? "ARTWORK AVAILABLE" : "NEEDS ARTWORK ENRICHMENT"}
</span>
                        </div>
    <div class="archive-status">
         <div>Audio: ${match.audio_url ? "Available" : "Missing"}</div>
         <div>Artwork: ${match.artwork_available ? "Available" : "Needs Enrichment"}</div>
         <div>Metadata: Verified</div>
</div>
                        ${audioHtml}


<details class="tech-details">
    <summary>Developer Information</summary>
    <div class="meta">
        Track ID: ${match.id}<br>
        Total score: ${match.scores.total}<br>
        Artist score: ${match.scores.artist}<br>
        Title score: ${match.scores.title}<br>
        Audio available: ${match.audio_url ? "Yes" : "No"}<br>
        Artwork available: ${match.artwork_available ? "Yes" : "No"}
    </div>
</details>

                    </div>
                </div>
            `;
        }
    </script>
</body>
</html>
"""

                        
       
            

       
           

       
                
                    
           
                                
                                           
                         
        
             
        
                
                   

                  

              

                                       
                            
                            
                       

                        
                         
