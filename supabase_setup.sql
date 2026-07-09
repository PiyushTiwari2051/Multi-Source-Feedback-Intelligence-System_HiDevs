-- SQL migration script to set up the reviews table in Supabase (PostgreSQL)
-- You can copy-paste and run this script directly in the Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    text TEXT NOT NULL,
    rating INTEGER,
    review_date TEXT,
    sentiment_label TEXT,
    sentiment_score REAL,
    category TEXT,
    priority_score REAL,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable row-level security (RLS) optionally:
-- ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;

-- If RLS is enabled, you will need to define policies for reading and writing data,
-- e.g. allowing anonymous read/write or service-role bypass:
-- CREATE POLICY "Allow public read" ON reviews FOR SELECT TO anon USING (true);
-- CREATE POLICY "Allow public insert" ON reviews FOR INSERT TO anon WITH CHECK (true);
