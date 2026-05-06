-- Build the office-actions gold set for PriorArt Pal eval.
--
-- Source: patents-public-data.uspto_oce_office_actions.* — public USPTO
-- Office of Chief Economist research dataset. Anonymized at the examiner
-- level; covers office actions through ~late 2010s (verify current
-- coverage in BigQuery's table metadata).
--
-- Output schema (one row per (rejected claim, cited prior-art patent)):
--   - app_id            application number being rejected
--   - claim_num         the rejected claim number
--   - claim_text        the actual claim text being rejected (from
--                       patents.publications via app_id join)
--   - rejection_type    '102' / '103' / '101' / '112'
--   - cited_pub_no      the prior-art patent the examiner cited
--   - art_unit          examiner art unit (for filtering to AV-relevant)
--   - mailing_date      when the office action was mailed
--
-- Run in BigQuery Console; export results as JSON (local file) ->
-- evals/datasets/office_actions_v1.json. Then a Python script
-- transforms to JSONL and merges with patent text.
--
-- Cost estimate: ~5–15 GB scanned depending on filters. Comfortable
-- inside the 1 TB/month free tier.

-- NOTE: Verify exact table/column names in BigQuery's Explorer panel
-- before running — the OCE dataset has been reorganized periodically.
-- Common table names below; adjust if your version differs.

WITH
  -- Office actions filtered to AV-relevant art units. The vehicle
  -- autonomy / navigation TC (Technology Center) is 3600 / 3660 etc.
  -- Filter by art unit if you want a tighter slice; or filter
  -- downstream by joining cited_pub_no's CPC codes.
  oa AS (
    SELECT
      app_id,
      mail_dt,
      tc_art_unit,
      examiner_id  -- Anonymized in the dataset.
    FROM `patents-public-data.uspto_oce_office_actions.office_actions`
    WHERE mail_dt >= '2015-01-01'
      AND mail_dt <  '2024-01-01'
  ),

  -- Rejections cited within those office actions.
  rej AS (
    SELECT
      r.app_id,
      r.mail_dt,
      r.rejection_fp,
      r.claim_no,
      r.header_paragraph_id,
      r.alleged_to_be_anticipated,
      r.alleged_to_be_obvious
    FROM `patents-public-data.uspto_oce_office_actions.rejections` AS r
    INNER JOIN oa USING (app_id, mail_dt)
    WHERE r.alleged_to_be_anticipated OR r.alleged_to_be_obvious
  ),

  -- Cited prior-art references within those rejections.
  cit AS (
    SELECT
      c.app_id,
      c.mail_dt,
      c.cited_appln_id,
      c.cited_pub_no,
      c.cited_kind_code
    FROM `patents-public-data.uspto_oce_office_actions.citations` AS c
    INNER JOIN rej USING (app_id, mail_dt)
    WHERE c.cited_pub_no IS NOT NULL
  ),

  -- Pull claim text for the rejected applications. We need the actual
  -- text of the claim being rejected so we can use it as the eval query.
  rej_with_claim_text AS (
    SELECT
      rej.app_id,
      rej.claim_no,
      rej.alleged_to_be_anticipated,
      rej.alleged_to_be_obvious,
      pub.publication_number AS rejected_pub_no,
      (
        SELECT t.text
        FROM UNNEST(pub.claims_localized) AS t
        WHERE t.language = 'en'
        LIMIT 1
      ) AS claims_text_full
    FROM rej
    LEFT JOIN `patents-public-data.patents.publications` AS pub
      ON pub.application_number = rej.app_id
      AND pub.country_code = 'US'
  )

SELECT
  rwc.app_id,
  rwc.claim_no,
  CASE
    WHEN rwc.alleged_to_be_anticipated THEN '102'
    WHEN rwc.alleged_to_be_obvious     THEN '103'
    ELSE 'other'
  END AS rejection_type,
  rwc.rejected_pub_no,
  rwc.claims_text_full,                 -- post-process to extract the specific claim_no
  cit.cited_pub_no,
  oa.tc_art_unit,
  oa.mail_dt
FROM rej_with_claim_text AS rwc
INNER JOIN cit
  ON cit.app_id = rwc.app_id
INNER JOIN oa
  ON oa.app_id = rwc.app_id AND oa.mail_dt = cit.mail_dt
-- Tighten to autonomy-relevant art units (verify TC mapping in BigQuery).
-- TC 3600 covers transportation; TC 2660s cover networking; pick the
-- subset matching your CPC slice (B60W*, G05D1/0*, G01C21*, G08G1*).
WHERE oa.tc_art_unit BETWEEN 3661 AND 3669  -- guess; verify
  AND rwc.claims_text_full IS NOT NULL
ORDER BY oa.mail_dt DESC
LIMIT 5000;

-- Post-processing notes (in Python after export):
--   1. Parse claims_text_full to extract just the rejected claim by claim_no
--      (same regex used in scripts/extract_independent_claims.py)
--   2. Look up the cited_pub_no's claims/title/abstract from the patent
--      corpus we already pulled (or refetch via BigQuery)
--   3. Emit one record per (rejected_claim_text, cited_pub_no) pair as
--      evals/datasets/office_actions_v1.jsonl
