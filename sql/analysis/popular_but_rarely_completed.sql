-- Question: Which games are popular but rarely completed?
-- Popularity: SteamSpy owners estimate (midpoint of the owners_low/owners_high range).
-- Completion: average global achievement completion %, requiring >= 5 tracked
-- achievements per game (same small-sample guard used in achievement_completion_rates.sql).
-- "Popular but rarely completed" is defined relative to this dataset: owners
-- estimate at or above the median, AND completion rate at or below the median.

WITH popularity AS (
    SELECT a.appid, a.name,
           ROUND((o.owners_low + o.owners_high) / 2.0) AS owners_estimate
    FROM ownership_stats o
             JOIN apps a ON a.appid = o.appid
),
     completion AS (
         SELECT a.appid,
                COUNT(*) AS achievements_tracked,
                ROUND(AVG(ac.global_completion_pct), 1) AS avg_completion_pct
         FROM achievement_stats ac
                  JOIN apps a ON a.appid = ac.appid
         GROUP BY a.appid
         HAVING COUNT(*) >= 5
     ),
     combined AS (
         SELECT p.name, p.owners_estimate, c.achievements_tracked, c.avg_completion_pct
         FROM popularity p
                  JOIN completion c ON c.appid = p.appid
     )
SELECT name, owners_estimate, achievements_tracked, avg_completion_pct
FROM combined
WHERE owners_estimate >= (SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY owners_estimate) FROM combined)
  AND avg_completion_pct <= (SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY avg_completion_pct) FROM combined)
ORDER BY owners_estimate DESC, avg_completion_pct ASC;