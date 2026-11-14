-- Schema version 1. Applied once, when a new database file is created.
-- Dates and times are stored as ISO-8601 text in UTC (SQLite has no date type).

-- A text that was imported: a file or a YouTube video.
CREATE TABLE sources (
    id           INTEGER PRIMARY KEY,
    kind         TEXT NOT NULL CHECK (kind IN ('file', 'youtube')),
    ref          TEXT NOT NULL,          -- file path or URL
    title        TEXT,
    content_hash TEXT NOT NULL UNIQUE,   -- prevents importing the same text twice
    added_at     TEXT NOT NULL
);

-- One row per thing you could learn, stored under its base form.
-- "gave up", "giving up" and "give ... up" all point to the item (phrasal_verb, "give up").
CREATE TABLE items (
    id         INTEGER PRIMARY KEY,
    kind       TEXT NOT NULL CHECK (kind IN ('word', 'phrasal_verb', 'idiom')),
    lemma      TEXT NOT NULL,
    pos        TEXT,                     -- part of speech, e.g. NOUN, VERB
    zipf       REAL,                     -- frequency score: low = rare = harder
    status     TEXT NOT NULL DEFAULT 'new'
               CHECK (status IN ('new', 'known', 'ignored', 'learning')),
    created_at TEXT NOT NULL,
    UNIQUE (kind, lemma)
);

-- Where an item was seen: the original sentence and the exact form used in it.
CREATE TABLE occurrences (
    id           INTEGER PRIMARY KEY,
    item_id      INTEGER NOT NULL REFERENCES items (id) ON DELETE CASCADE,
    source_id    INTEGER NOT NULL REFERENCES sources (id) ON DELETE CASCADE,
    sentence     TEXT NOT NULL,
    surface_form TEXT NOT NULL,          -- e.g. "gave up" for the item "give up"
    UNIQUE (item_id, source_id, sentence)
);

-- An item you decided to learn, with your Turkish notes.
CREATE TABLE cards (
    id               INTEGER PRIMARY KEY,
    item_id          INTEGER NOT NULL UNIQUE REFERENCES items (id) ON DELETE CASCADE,
    meaning_tr       TEXT NOT NULL,
    example_sentence TEXT,
    pitfall_note     TEXT,               -- false friends, preposition traps, etc.
    created_at       TEXT NOT NULL
);

-- The current review schedule of a card (one row per card).
CREATE TABLE srs_state (
    card_id          INTEGER PRIMARY KEY REFERENCES cards (id) ON DELETE CASCADE,
    due_date         TEXT NOT NULL,      -- YYYY-MM-DD
    interval_days    INTEGER NOT NULL,
    ease             REAL NOT NULL,
    repetitions      INTEGER NOT NULL,
    lapses           INTEGER NOT NULL,
    last_reviewed_at TEXT
);

-- Every review ever done. Never updated, only appended to.
-- A different algorithm (FSRS) can later be initialised from this history.
CREATE TABLE reviews (
    id              INTEGER PRIMARY KEY,
    card_id         INTEGER NOT NULL REFERENCES cards (id) ON DELETE CASCADE,
    reviewed_at     TEXT NOT NULL,
    grade           INTEGER NOT NULL,
    interval_before INTEGER NOT NULL,
    interval_after  INTEGER NOT NULL
);

-- Indexes for the lookups the app does most often.
CREATE INDEX idx_items_status ON items (status);
CREATE INDEX idx_occurrences_item ON occurrences (item_id);
CREATE INDEX idx_srs_state_due ON srs_state (due_date);
CREATE INDEX idx_reviews_card ON reviews (card_id);
