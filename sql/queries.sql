-- queries.sql
-- Ten analytical queries for the Google Play Store project.
-- Covers every required type: summary stats, grouped analysis, top/bottom N,
-- trend analysis, multi-table JOINs, and three window functions.


-- ============================================================
-- Q1: Summary statistics across the catalogue
-- ============================================================
SELECT
    COUNT(*)                                              AS total_apps,
    ROUND(AVG(rating), 2)                                 AS avg_rating,
    SUM(installs)                                         AS total_installs,
    SUM(CASE WHEN type = 'Free' THEN 1 ELSE 0 END)        AS free_apps,
    SUM(CASE WHEN type = 'Paid' THEN 1 ELSE 0 END)        AS paid_apps,
    ROUND(AVG(CASE WHEN type = 'Paid' THEN price END), 2) AS avg_paid_price,
    ROUND(AVG(size_mb), 2)                                AS avg_size_mb
FROM apps;


-- ============================================================
-- Q2: Grouped analysis — top categories by total installs
-- ============================================================
SELECT
    c.category_name,
    COUNT(a.app_id)         AS num_apps,
    ROUND(AVG(a.rating), 2) AS avg_rating,
    SUM(a.installs)         AS total_installs,
    ROUND(AVG(a.price), 2)  AS avg_price
FROM apps a
JOIN categories c ON c.category_id = a.category_id
GROUP BY c.category_name
HAVING COUNT(a.app_id) >= 20
ORDER BY total_installs DESC
LIMIT 15;


-- ============================================================
-- Q3: Top 10 most-installed apps (with category)
-- ============================================================
SELECT
    a.app_name,
    c.category_name,
    a.installs,
    a.rating,
    a.reviews_count
FROM apps a
JOIN categories c ON c.category_id = a.category_id
ORDER BY a.installs DESC, a.reviews_count DESC
LIMIT 10;


-- ============================================================
-- Q4: Bottom 10 rated apps with ≥ 1000 reviews
-- ============================================================
SELECT
    a.app_name,
    c.category_name,
    a.rating,
    a.reviews_count,
    a.installs
FROM apps a
JOIN categories c ON c.category_id = a.category_id
WHERE a.rating IS NOT NULL
  AND a.reviews_count >= 1000
ORDER BY a.rating ASC, a.reviews_count DESC
LIMIT 10;


-- ============================================================
-- Q5: Trend analysis — apps updated per year
-- ============================================================
SELECT
    CAST(strftime('%Y', last_updated) AS INTEGER) AS year,
    COUNT(*)                                       AS apps_updated,
    ROUND(AVG(rating), 2)                          AS avg_rating
FROM apps
WHERE last_updated IS NOT NULL
GROUP BY year
ORDER BY year;


-- ============================================================
-- Q6: Multi-table JOIN — sentiment breakdown per category
-- ============================================================
SELECT
    c.category_name,
    COUNT(r.review_id)                                                       AS total_reviews,
    SUM(CASE WHEN r.sentiment = 'Positive' THEN 1 ELSE 0 END)                AS positive,
    SUM(CASE WHEN r.sentiment = 'Negative' THEN 1 ELSE 0 END)                AS negative,
    SUM(CASE WHEN r.sentiment = 'Neutral'  THEN 1 ELSE 0 END)                AS neutral,
    ROUND(100.0 * SUM(CASE WHEN r.sentiment = 'Positive' THEN 1 ELSE 0 END)
          / COUNT(r.review_id), 1)                                           AS positive_pct,
    ROUND(AVG(r.sentiment_polarity), 3)                                      AS avg_polarity
FROM categories c
JOIN apps    a ON a.category_id = c.category_id
JOIN reviews r ON r.app_id      = a.app_id
GROUP BY c.category_name
HAVING COUNT(r.review_id) >= 100
ORDER BY positive_pct DESC
LIMIT 15;


-- ============================================================
-- Q7: Window function — top 3 most-installed apps per category (RANK)
-- ============================================================
WITH ranked AS (
    SELECT
        c.category_name,
        a.app_name,
        a.installs,
        a.rating,
        RANK() OVER (
            PARTITION BY c.category_id
            ORDER BY a.installs DESC, a.reviews_count DESC
        ) AS rnk
    FROM apps a
    JOIN categories c ON c.category_id = a.category_id
)
SELECT category_name, app_name, installs, rating, rnk
FROM ranked
WHERE rnk <= 3
ORDER BY category_name, rnk;


-- ============================================================
-- Q8: Window function — each app vs. its category's average rating
-- ============================================================
SELECT
    a.app_name,
    c.category_name,
    a.rating,
    ROUND(AVG(a.rating) OVER (PARTITION BY c.category_id), 2)            AS category_avg_rating,
    ROUND(a.rating - AVG(a.rating) OVER (PARTITION BY c.category_id), 2) AS diff_from_avg
FROM apps a
JOIN categories c ON c.category_id = a.category_id
WHERE a.rating IS NOT NULL
  AND a.reviews_count >= 10000
ORDER BY diff_from_avg DESC
LIMIT 15;


-- ============================================================
-- Q9: Window function — cumulative installs across top categories
-- ============================================================
WITH cat_totals AS (
    SELECT
        c.category_name,
        SUM(a.installs) AS total_installs
    FROM apps a
    JOIN categories c ON c.category_id = a.category_id
    GROUP BY c.category_name
)
SELECT
    category_name,
    total_installs,
    SUM(total_installs) OVER (
        ORDER BY total_installs DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                                                          AS cumulative_installs,
    ROUND(100.0 * total_installs / SUM(total_installs) OVER (), 2)
                                                               AS pct_of_grand_total
FROM cat_totals
ORDER BY total_installs DESC
LIMIT 10;


-- ============================================================
-- Q10: Analytical question — do paid apps get more positive reviews than free ones?
-- ============================================================
SELECT
    a.type,
    COUNT(DISTINCT a.app_id)                                            AS apps_with_reviews,
    COUNT(r.review_id)                                                  AS total_reviews,
    ROUND(AVG(r.sentiment_polarity), 3)                                 AS avg_polarity,
    ROUND(AVG(r.sentiment_subjectivity), 3)                             AS avg_subjectivity,
    ROUND(100.0 * SUM(CASE WHEN r.sentiment = 'Positive' THEN 1 ELSE 0 END)
          / COUNT(r.review_id), 1)                                      AS positive_pct,
    ROUND(100.0 * SUM(CASE WHEN r.sentiment = 'Negative' THEN 1 ELSE 0 END)
          / COUNT(r.review_id), 1)                                      AS negative_pct,
    ROUND(AVG(a.rating), 2)                                             AS avg_star_rating
FROM apps a
JOIN reviews r ON r.app_id = a.app_id
WHERE r.sentiment IS NOT NULL
GROUP BY a.type;
