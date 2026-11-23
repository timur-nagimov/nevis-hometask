-- The schema of research/_design/spec-final.md section 4, copied from
-- research/testrun/plan/sql/001_init.sql (its lines 2-45), plus the app_meta table of section 13.2 B5.
-- Applied once by app.db.migrate, in one transaction, under an advisory lock.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- case- and accent-insensitive form used for client search (schema-qualified body: dump/restore safe)
CREATE FUNCTION public.search_normalize(text) RETURNS text
  LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
  RETURN casefold(public.unaccent('public.unaccent'::regdictionary, normalize($1, NFKC)) COLLATE "pg_unicode_fast");

-- punctuation -> spaces, identically for documents and queries, independent of the database locale
CREATE FUNCTION public.strip_punct(text) RETURNS text
  LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
  RETURN regexp_replace($1 COLLATE "pg_unicode_fast", '[^[:alnum:]]+', ' ', 'g');

CREATE TABLE clients (
  id uuid PRIMARY KEY DEFAULT uuidv7(),
  first_name text NOT NULL, last_name text NOT NULL, email text NOT NULL,
  description text NOT NULL DEFAULT '', social_links text[] NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  search_text text GENERATED ALWAYS AS (public.search_normalize(
      first_name || ' ' || last_name || ' ' || email || ' ' || description)) STORED
);
CREATE INDEX clients_search_text_trgm_idx ON clients USING gin (search_text gin_trgm_ops);

CREATE TABLE documents (
  id uuid PRIMARY KEY DEFAULT uuidv7(),
  client_id uuid NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  title text NOT NULL, content text NOT NULL,
  tags text[] NOT NULL DEFAULT '{}',      -- shown in the API: names of the matched concepts
  tags_text text NOT NULL DEFAULT '',     -- searched: each matched concept with its alternative phrasings
  summary text NOT NULL, summary_method text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  fts_text tsvector GENERATED ALWAYS AS (to_tsvector('english', public.strip_punct(title || ' ' || content))) STORED,
  fts tsvector GENERATED ALWAYS AS (to_tsvector('english',
      public.strip_punct(tags_text || ' ' || title || ' ' || content))) STORED     -- tags first
);
CREATE INDEX documents_client_id_idx ON documents (client_id);

CREATE TABLE document_chunks (
  document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  chunk_no int NOT NULL,                  -- 0..n-1 content chunks; -1 = the tags chunk
  embedding vector(768) NOT NULL,
  PRIMARY KEY (document_id, chunk_no)
);

-- What the stored vectors and tags were built with (13.2 B5). At most one row: `id` can only be 1.
-- Step 3 writes the row at start-up when the table is empty and logs a warning when it differs.
CREATE TABLE app_meta (
  id int PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  model_revision text NOT NULL,         -- Hugging Face revision of the embedding model
  tokenizer_settings jsonb NOT NULL,    -- truncation and padding the embedder used
  concepts_sha256 text                  -- sha256 of the concept map; NULL when concept tagging is off
);
