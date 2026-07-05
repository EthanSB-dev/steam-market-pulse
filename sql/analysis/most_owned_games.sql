-- Question: What are the most owned games?
-- SteamSpy gives owners as a range (owners_low, owners_high) rather than an exact
-- number, since it's a statistical estimate, not a Steam-reported figure. We use
-- the midpoint of that range as a single sortable "owners_estimate."

SELECT a.name,
       o.owners_low,
       o.owners_high,
       ROUND((o.owners_low + o.owners_high) / 2.0) AS owners_estimate
FROM ownership_stats o
         JOIN apps a ON a.appid = o.appid
ORDER BY owners_estimate DESC
LIMIT 15;