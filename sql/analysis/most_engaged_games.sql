-- Question: Which games have the most playtime/engagement across players?
-- Note: SteamSpy's playtime fields (average_forever, average_2weeks,
-- median_forever) were confirmed unusable for all 50 tracked games due to a
-- 2018 Steam privacy default change that broke SteamSpy's ability to sample
-- playtime data industry-wide (documented, not fixable on our end). Reframed
-- using average concurrent players from the official Steam API as the closest
-- trustworthy proxy for sustained engagement, at individual-game granularity
-- (see playtime_by_genre.sql for the genre-level rollup of the same metric).

SELECT a.name,
       ROUND(AVG(p.concurrent_players)) AS avg_concurrent_players,
       MAX(p.concurrent_players) AS peak_concurrent_players,
       COUNT(*) AS snapshots_collected
FROM player_snapshots p
         JOIN apps a ON a.appid = p.appid
GROUP BY a.name
ORDER BY avg_concurrent_players DESC
LIMIT 15;