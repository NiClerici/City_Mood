// ============================================================
// mongo_performance.js  –  Performance-Optimierung (Schritt 10)
//
// Zeigt drei Optimierungsmassnahmen:
//   1. Ausführungsplan (explain) vor Indexierung
//   2. Indexe anlegen (single-field + compound)
//   3. Ausführungsplan nach Indexierung + Laufzeitvergleich
//   4. Materialized View (mv_daily_mood) via $out
//
// Run with:
//   mongosh city_mood mongo_performance.js
// ============================================================

print("=== MongoDB Performance-Optimierung ===\n");

// ----------------------------------------------------------------
// Helper: measure execution time of an aggregation
// ----------------------------------------------------------------
function timeAggregation(label, pipeline) {
  var start = Date.now();
  var count = db.mood_snapshots.aggregate(pipeline).toArray().length;
  var ms    = Date.now() - start;
  print(label + ": " + ms + " ms  (" + count + " docs)");
  return ms;
}

// ----------------------------------------------------------------
// The query we will optimize: average mood per city, last 30 days
// ----------------------------------------------------------------
var cutoff = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
               .toISOString().slice(0, 10) + " 00:00:00";

var analyticsPipeline = [
  { $match: { timestamp: { $gte: cutoff } } },
  { $group: {
    _id:      "$city.name",
    avg_mood: { $avg: "$scores.mood_score" },
    count:    { $sum: 1 }
  }},
  { $sort: { avg_mood: -1 } }
];

// ================================================================
// 1. EXPLAIN – BEFORE INDEXING (COLLSCAN expected)
// ================================================================
print("--- 1. Ausführungsplan VOR Indexierung ---");
var explainBefore = db.mood_snapshots.explain("executionStats").aggregate(analyticsPipeline);
var stageBefore   = explainBefore.stages
  ? explainBefore.stages[0].$cursor.executionStats.executionStages.stage
  : (explainBefore.queryPlanner
      ? explainBefore.queryPlanner.winningPlan.stage
      : "N/A");
print("Winning stage: " + stageBefore);
var msBefore = timeAggregation("Laufzeit OHNE Index", analyticsPipeline);

// ================================================================
// 2. INDEXES ANLEGEN
// ================================================================
print("\n--- 2. Indexe anlegen ---");

// 2a. Single-field index on timestamp (speeds up $match date filter)
db.mood_snapshots.createIndex(
  { timestamp: 1 },
  { name: "idx_timestamp" }
);
print("  Created: idx_timestamp (timestamp asc)");

// 2b. Compound index on city.name + timestamp (speeds up group-by + filter)
db.mood_snapshots.createIndex(
  { "city.name": 1, timestamp: 1 },
  { name: "idx_city_timestamp" }
);
print("  Created: idx_city_timestamp (city.name asc, timestamp asc)");

// 2c. Single-field index on mood_score (speeds up sort in analytics queries)
db.mood_snapshots.createIndex(
  { "scores.mood_score": -1 },
  { name: "idx_mood_score_desc" }
);
print("  Created: idx_mood_score_desc (scores.mood_score desc)");

// Show all indexes
print("\nAll indexes on mood_snapshots:");
db.mood_snapshots.getIndexes().forEach(function(idx) {
  print("  " + idx.name + "  " + JSON.stringify(idx.key));
});

// ================================================================
// 3. EXPLAIN – AFTER INDEXING (IXSCAN expected)
// ================================================================
print("\n--- 3. Ausführungsplan NACH Indexierung ---");
var explainAfter = db.mood_snapshots.explain("executionStats").aggregate(analyticsPipeline);
var stageAfter   = explainAfter.stages
  ? explainAfter.stages[0].$cursor.executionStats.executionStages.stage
  : (explainAfter.queryPlanner
      ? explainAfter.queryPlanner.winningPlan.stage
      : "N/A");
print("Winning stage: " + stageAfter);
var msAfter = timeAggregation("Laufzeit MIT Index ", analyticsPipeline);

print("\n--- Laufzeitvergleich ---");
print("  Ohne Index: " + msBefore + " ms");
print("  Mit Index:  " + msAfter  + " ms");
if (msBefore > 0) {
  var improvement = (((msBefore - msAfter) / msBefore) * 100).toFixed(1);
  print("  Verbesserung: " + improvement + "%");
}

// ================================================================
// 4. MATERIALIZED VIEW – mv_daily_mood (refresh)
// ================================================================
print("\n--- 4. Materialized View mv_daily_mood (refresh) ---");
var mvStart = Date.now();

db.mood_snapshots.aggregate([
  {
    $group: {
      _id: {
        city: "$city.name",
        date: { $substr: ["$timestamp", 0, 10] }
      },
      avg_mood:    { $avg: "$scores.mood_score" },
      avg_weather: { $avg: "$scores.weather_score" },
      avg_sbb:     { $avg: "$scores.sbb_score" },
      avg_traffic: { $avg: "$scores.traffic_score" },
      count:       { $sum: 1 }
    }
  },
  {
    $project: {
      _id:         0,
      city_name:   "$_id.city",
      date:        "$_id.date",
      avg_mood:    { $round: ["$avg_mood",    4] },
      avg_weather: { $round: ["$avg_weather", 4] },
      avg_sbb:     { $round: ["$avg_sbb",     4] },
      avg_traffic: { $round: ["$avg_traffic", 4] },
      count:       1,
      updated_at:  { $literal: new Date().toISOString().slice(0, 19).replace("T", " ") }
    }
  },
  { $sort: { date: -1, city_name: 1 } },
  { $out: "mv_daily_mood" }
]);

var mvMs = Date.now() - mvStart;
print("mv_daily_mood refreshed in " + mvMs + " ms");
print("Documents: " + db.mv_daily_mood.countDocuments());

// Index on mv_daily_mood for fast dashboard queries
db.mv_daily_mood.createIndex({ date: -1, city_name: 1 }, { name: "idx_mv_date_city" });
print("  Created: idx_mv_date_city on mv_daily_mood");

print("\nOptimierung abgeschlossen.");
