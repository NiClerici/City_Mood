// ============================================================
// mongo_analytics_query.js  –  Analytics Query (Schritt 9)
//
// Berechnet den durchschnittlichen Mood-Score pro Stadt für
// die letzten 30 Tage und gibt eine Entscheidungsempfehlung
// zurück (analog zur SQL-Analyse-Query).
//
// Verwendete Keywords (15+):
//   $match, $gte, $lte, $group, $avg, $min, $max, $sum, $first,
//   $project, $round, $subtract, $multiply, $cond, $sort,
//   $limit, $lookup, $unwind, $addFields
//
// Run with:
//   mongosh city_mood mongo_analytics_query.js
// ============================================================

// Date range: last 30 days
var now    = new Date();
var cutoff = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

var cutoffStr = cutoff.toISOString().slice(0, 10) + " 00:00:00";
var nowStr    = now.toISOString().slice(0, 10)    + " 23:59:59";

print("=== City Mood Analytics – last 30 days ===");
print("Range: " + cutoffStr + " → " + nowStr + "\n");

var results = db.mood_snapshots.aggregate([

  // 1. $match – filter to last 30 days
  { $match: {
    timestamp: { $gte: cutoffStr, $lte: nowStr }
  }},

  // 2. $group – aggregate per city
  { $group: {
    _id:         "$city.name",
    avg_mood:    { $avg:   "$scores.mood_score" },
    avg_weather: { $avg:   "$scores.weather_score" },
    avg_sbb:     { $avg:   "$scores.sbb_score" },
    avg_traffic: { $avg:   "$scores.traffic_score" },
    max_mood:    { $max:   "$scores.mood_score" },
    min_mood:    { $min:   "$scores.mood_score" },
    count:       { $sum:   1 },
    city_info:   { $first: "$city" }
  }},

  // 3. $addFields – round all averages
  { $addFields: {
    avg_mood:    { $round: ["$avg_mood",    4] },
    avg_weather: { $round: ["$avg_weather", 4] },
    avg_sbb:     { $round: ["$avg_sbb",     4] },
    avg_traffic: { $round: ["$avg_traffic", 4] },
    max_mood:    { $round: ["$max_mood",    4] },
    min_mood:    { $round: ["$min_mood",    4] }
  }},

  // 4. $lookup – join cities collection for lat/lon (cross-collection join)
  { $lookup: {
    from:         "cities",
    localField:   "_id",
    foreignField: "name",
    as:           "city_master"
  }},

  // 5. $unwind – flatten city_master array
  { $unwind: { path: "$city_master", preserveNullAndEmptyArrays: true } },

  // 6. $project – shape final output with decision rule
  { $project: {
    _id:              0,
    city:             "$_id",
    latitude:         "$city_master.latitude",
    longitude:        "$city_master.longitude",
    avg_mood:         1,
    avg_weather:      1,
    avg_sbb:          1,
    avg_traffic:      1,
    mood_variability: { $round: [{ $subtract: ["$max_mood", "$min_mood"] }, 4] },
    mood_percent:     { $round: [{ $multiply: ["$avg_mood", 100] }, 1] },
    measurement_count: "$count",

    // Decision rule: recommend city if avg_mood >= 0.70
    recommendation: { $cond: {
      if:   { $gte: ["$avg_mood", 0.70] },
      then: "Empfohlen",
      else: { $cond: {
        if:   { $gte: ["$avg_mood", 0.50] },
        then: "Neutral",
        else: "Nicht empfohlen"
      }}
    }},

    // Dominant factor: which score contributes most to the mood
    dominant_factor: { $cond: {
      if:   { $and: [{ $gte: ["$avg_weather", "$avg_sbb"] }, { $gte: ["$avg_weather", "$avg_traffic"] }] },
      then: "Wetter",
      else: { $cond: {
        if:   { $gte: ["$avg_sbb", "$avg_traffic"] },
        then: "SBB",
        else: "Verkehr"
      }}
    }}
  }},

  // 7. $sort – best mood first
  { $sort: { avg_mood: -1 } },

  // 8. $limit – all 10 cities (show full ranking)
  { $limit: 10 }

]).toArray();

// ----------------------------------------------------------------
// Print results
// ----------------------------------------------------------------
print(JSON.stringify(results, null, 2));

print("\n=== Entscheidungsempfehlung ===");
results.forEach(function(r) {
  print(r.city + " | Mood: " + (r.mood_percent) + "% | " + r.recommendation + " | Hauptfaktor: " + r.dominant_factor);
});

print("\nTotal cities analysed: " + results.length);
