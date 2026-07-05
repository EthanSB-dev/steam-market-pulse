-- Question: How does playtime vary by genre?
-- A game can belong to multiple genres, so we join through app_genres
-- rather than assuming one genre per game.

SELECT g.genre_name,
       COUNT(DISTINCT a.appid) AS games_in_genre,
       ROUND(AVG(o.avg_playtime_forever_minutes)) AS avg_playtime_minutes,
       ROUND(AVG(o.avg_playtime_forever_minutes) / 60.0, 1) AS avg_playtime_hours
FROM ownership_stats o
         JOIN apps a ON a.appid = o.appid
         JOIN app_genres ag ON ag.appid = a.appid
         JOIN genres g ON g.genre_id = ag.genre_id
GROUP BY g.genre_name
ORDER BY avg_playtime_hours DESC;