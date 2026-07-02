-- Phase 2 PostgreSQL Schema
-- Media Archive Backend Service
-- PostgreSQL + pg_trgm fuzzy search

CREATE EXTENSION IF NOT EXISTS pg_trgm;

DROP TABLE IF EXISTS tracks CASCADE;

CREATE TABLE tracks (
    id SERIAL PRIMARY KEY,

    path TEXT UNIQUE NOT NULL,
    filename TEXT,
    folder_context TEXT,

    id3_title TEXT,
    id3_artist TEXT,
    id3_album TEXT,

    parsed_artist TEXT,
    parsed_title TEXT,

    is_mix BOOLEAN DEFAULT FALSE,
    metadata_source TEXT,
    confidence TEXT,
    error TEXT,
    batch_source TEXT,

    artwork_found BOOLEAN DEFAULT FALSE,
    artwork_original TEXT,
    artwork_small TEXT,
    artwork_medium TEXT,
    artwork_large TEXT,
    artwork_mime TEXT,

    search_artist TEXT,
    search_title TEXT,
    search_text TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Basic indexes
CREATE INDEX idx_tracks_artist ON tracks (id3_artist);
CREATE INDEX idx_tracks_title ON tracks (id3_title);
CREATE INDEX idx_tracks_confidence ON tracks (confidence);
CREATE INDEX idx_tracks_artwork_found ON tracks (artwork_found);
CREATE INDEX idx_tracks_is_mix ON tracks (is_mix);

-- Fuzzy search indexes using pg_trgm
CREATE INDEX idx_tracks_artist_trgm
ON tracks USING GIN (search_artist gin_trgm_ops);

CREATE INDEX idx_tracks_title_trgm
ON tracks USING GIN (search_title gin_trgm_ops);

CREATE INDEX idx_tracks_search_text_trgm
ON tracks USING GIN (search_text gin_trgm_ops);

-- Helper function to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for updated_at
CREATE TRIGGER update_tracks_updated_at
BEFORE UPDATE ON tracks
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

