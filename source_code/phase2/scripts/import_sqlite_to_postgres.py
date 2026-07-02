import sqlite3
import psycopg2
from psycopg2.extras import execute_batch


SQLITE_DB = "project/data/database/music_archive_complete.db"

POSTGRES_CONFIG = {
    "dbname": "music_archive_phase2",
    "user": "Aliona",
    "host": "localhost",
    "port": 5432,
}


def to_bool(value):
    if value is None:
        return False

    value = str(value).strip().lower()

    return value in {"true", "1", "yes", "y"}


def normalize_text(value):
    if value is None:
        return ""

    return str(value).strip().lower()


def main():
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    pg_conn = psycopg2.connect(**POSTGRES_CONFIG)
    pg_cur = pg_conn.cursor()

    rows = sqlite_cur.execute("SELECT * FROM tracks").fetchall()

    print(f"Rows found in SQLite: {len(rows)}")

    insert_sql = """
    INSERT INTO tracks (
        path,
        filename,
        folder_context,
        id3_title,
        id3_artist,
        id3_album,
        parsed_artist,
        parsed_title,
        is_mix,
        metadata_source,
        confidence,
        error,
        batch_source,
        artwork_found,
        artwork_original,
        artwork_small,
        artwork_medium,
        artwork_large,
        artwork_mime,
        search_artist,
        search_title,
        search_text
    )
    VALUES (
        %(path)s,
        %(filename)s,
        %(folder_context)s,
        %(id3_title)s,
        %(id3_artist)s,
        %(id3_album)s,
        %(parsed_artist)s,
        %(parsed_title)s,
        %(is_mix)s,
        %(metadata_source)s,
        %(confidence)s,
        %(error)s,
        %(batch_source)s,
        %(artwork_found)s,
        %(artwork_original)s,
        %(artwork_small)s,
        %(artwork_medium)s,
        %(artwork_large)s,
        %(artwork_mime)s,
        %(search_artist)s,
        %(search_title)s,
        %(search_text)s
    )
    ON CONFLICT (path) DO UPDATE SET
        filename = EXCLUDED.filename,
        folder_context = EXCLUDED.folder_context,
        id3_title = EXCLUDED.id3_title,
        id3_artist = EXCLUDED.id3_artist,
        id3_album = EXCLUDED.id3_album,
        parsed_artist = EXCLUDED.parsed_artist,
        parsed_title = EXCLUDED.parsed_title,
        is_mix = EXCLUDED.is_mix,
        metadata_source = EXCLUDED.metadata_source,
        confidence = EXCLUDED.confidence,
        error = EXCLUDED.error,
        batch_source = EXCLUDED.batch_source,
        artwork_found = EXCLUDED.artwork_found,
        artwork_original = EXCLUDED.artwork_original,
        artwork_small = EXCLUDED.artwork_small,
        artwork_medium = EXCLUDED.artwork_medium,
        artwork_large = EXCLUDED.artwork_large,
        artwork_mime = EXCLUDED.artwork_mime,
        search_artist = EXCLUDED.search_artist,
        search_title = EXCLUDED.search_title,
        search_text = EXCLUDED.search_text,
        updated_at = CURRENT_TIMESTAMP
    """

    records = []

    for row in rows:
        artist = row["id3_artist"] or row["parsed_artist"] or ""
        title = row["id3_title"] or row["parsed_title"] or ""

        search_artist = normalize_text(artist)
        search_title = normalize_text(title)
        search_text = normalize_text(f"{artist} {title}")

        records.append({
            "path": row["path"],
            "filename": row["filename"],
            "folder_context": row["folder_context"],
            "id3_title": row["id3_title"],
            "id3_artist": row["id3_artist"],
            "id3_album": row["id3_album"],
            "parsed_artist": row["parsed_artist"],
            "parsed_title": row["parsed_title"],
            "is_mix": to_bool(row["is_mix"]),
            "metadata_source": row["metadata_source"],
            "confidence": row["confidence"],
            "error": row["error"],
            "batch_source": row["batch_source"],
            "artwork_found": to_bool(row["artwork_found"]),
            "artwork_original": row["artwork_original"],
            "artwork_small": row["artwork_small"],
            "artwork_medium": row["artwork_medium"],
            "artwork_large": row["artwork_large"],
            "artwork_mime": row["artwork_mime"],
            "search_artist": search_artist,
            "search_title": search_title,
            "search_text": search_text,
        })

    execute_batch(pg_cur, insert_sql, records, page_size=500)

    pg_conn.commit()

    pg_cur.execute("SELECT COUNT(*) FROM tracks")
    total = pg_cur.fetchone()[0]

    pg_cur.execute("SELECT COUNT(*) FROM tracks WHERE artwork_found = TRUE")
    with_artwork = pg_cur.fetchone()[0]

    pg_cur.execute("SELECT COUNT(*) FROM tracks WHERE artwork_small IS NOT NULL AND artwork_small != ''")
    with_small = pg_cur.fetchone()[0]

    print("Import completed")
    print(f"Rows in PostgreSQL: {total}")
    print(f"Tracks with artwork: {with_artwork}")
    print(f"Tracks with small WebP: {with_small}")

    sqlite_conn.close()
    pg_cur.close()
    pg_conn.close()


if __name__ == "__main__":
    main()

