-- Client search: exact when every query word occurs in the record, else a typo tier with trigrams.
-- psycopg named parameters: q (prepared query), limit. Every literal percent sign is doubled, comments included.
WITH q AS (
  SELECT string_agg(DISTINCT tok, ' ')                       AS norm,
         array_agg(DISTINCT pat)                             AS pats,
         (array_agg(pat ORDER BY length(tok) DESC, tok))[1]  AS longest
  FROM regexp_split_to_table(public.search_normalize(%(q)s::text), '[\s,;]+') AS tok,
       LATERAL (SELECT '%%' || replace(replace(replace(tok, '\', '\\'), '%%', '\%%'), '_', '\_') || '%%' AS pat) AS p
  WHERE tok <> ''
),
hits AS (
  SELECT c.*, true AS exact FROM q JOIN clients c ON c.search_text LIKE q.longest AND c.search_text LIKE ALL (q.pats)
),
near AS (
  SELECT c.*, false AS exact FROM q JOIN clients c ON q.norm <%% c.search_text
  WHERE length(regexp_replace(q.norm, '[^[:alnum:]]', '', 'g')) >= 5 AND NOT EXISTS (SELECT 1 FROM hits)
)
SELECT c.id,
       CASE WHEN c.exact THEN 'exact' ELSE 'fuzzy' END AS match_type,
       CASE WHEN c.exact THEN 0.5 + 0.5 * s.best ELSE 0.49 * s.best END AS score,
       c.first_name, c.last_name, c.email, c.description, c.social_links  -- API columns
FROM (SELECT * FROM hits UNION ALL SELECT * FROM near) c, q,
     LATERAL (SELECT public.search_normalize(c.first_name || ' ' || c.last_name)   AS name,
                     public.search_normalize(c.email)                              AS email,
                     public.search_normalize(c.description)                        AS descr) f,
     LATERAL (SELECT greatest(      word_similarity(q.norm, f.name),
                              0.7 * word_similarity(q.norm, f.email),
                              0.5 * word_similarity(q.norm, f.descr)) AS best) s
ORDER BY score DESC, c.last_name, c.first_name, c.id
LIMIT %(limit)s;
