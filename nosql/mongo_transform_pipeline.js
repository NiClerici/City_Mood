// ============================================================
// mongo_transform_pipeline.js  –  ELT Transformation (Schritt 8)
//
// Joins the five raw collections (cities, weather, sbb, traffic,
// mood_scores) into one denormalized document per snapshot and
// writes the result to the 'mood_snapshots' collection via $out.
//
// Run with:
//   mongosh city_mood mongo_transform_pipeline.js
// ============================================================

print("=== ELT Transform: building mood_snapshots ===\n");

// ----------------------------------------------------------------
// Step 1: join weather ← sbb ← traffic ← cities, compute scores,
//         write to mood_snapshots
// ----------------------------------------------------------------

db.weather.aggregate([

  // 1. Join SBB data on same city_id + timestamp
  {
    $lookup: {
      from: "sbb",
      let: { cid: "$city_id", ts: "$timestamp" },
      pipeline: [
        { $match: { $expr: { $and: [
          { $eq: ["$city_id", "$$cid"] },
          { $eq: ["$timestamp", "$$ts"] }
        ]}}}
      ],
      as: "sbb_data"
    }
  },

  // 2. Only keep snapshots where SBB data exists
  { $match: { "sbb_data.0": { $exists: true } } },
  { $unwind: "$sbb_data" },

  // 3. Join Traffic data on same city_id + timestamp
  {
    $lookup: {
      from: "traffic",
      let: { cid: "$city_id", ts: "$timestamp" },
      pipeline: [
        { $match: { $expr: { $and: [
          { $eq: ["$city_id", "$$cid"] },
          { $eq: ["$timestamp", "$$ts"] }
        ]}}}
      ],
      as: "traffic_data"
    }
  },

  // 4. Only keep snapshots where Traffic data exists
  { $match: { "traffic_data.0": { $exists: true } } },
  { $unwind: "$traffic_data" },

  // 5. Join City master data on city_id
  {
    $lookup: {
      from: "cities",
      localField: "city_id",
      foreignField: "city_id",
      as: "city_data"
    }
  },
  { $unwind: "$city_data" },

  // 6. Compute individual scores (same formula as MySQL stored procedure)
  //    weather_score = CLAMP(1 - weathercode/100,  0, 1)
  //    sbb_score     = CLAMP(1 - delay_count*3/300, 0, 1)
  //    traffic_score = CLAMP(currentSpeed / freeFlowSpeed, 0, 1)
  //    mood_score    = 0.4*weather + 0.3*sbb + 0.3*traffic
  {
    $addFields: {
      "scores.weather_score": {
        $min: [1, { $max: [0,
          { $subtract: [1, { $divide: ["$weathercode", 100] }] }
        ]}]
      },
      "scores.sbb_score": {
        $min: [1, { $max: [0,
          { $subtract: [1,
            { $divide: [{ $multiply: ["$sbb_data.delay_minutes", 3] }, 300] }
          ]}
        ]}]
      },
      "scores.traffic_score": {
        $cond: {
          if: { $gt: ["$traffic_data.free_flow_speed", 0] },
          then: {
            $min: [1, { $max: [0,
              { $divide: ["$traffic_data.current_speed", "$traffic_data.free_flow_speed"] }
            ]}]
          },
          else: 0
        }
      }
    }
  },

  // 7. Compute composite mood_score from individual scores
  {
    $addFields: {
      "scores.mood_score": {
        $round: [
          { $add: [
            { $multiply: [0.4, "$scores.weather_score"] },
            { $multiply: [0.3, "$scores.sbb_score"] },
            { $multiply: [0.3, "$scores.traffic_score"] }
          ]},
          4
        ]
      },
      "scores.weather_score": { $round: ["$scores.weather_score", 4] },
      "scores.sbb_score":     { $round: ["$scores.sbb_score",     4] },
      "scores.traffic_score": { $round: ["$scores.traffic_score", 4] }
    }
  },

  // 8. Project final document shape (denormalized)
  {
    $project: {
      _id: 0,
      city: {
        name:      "$city_data.name",
        latitude:  "$city_data.latitude",
        longitude: "$city_data.longitude"
      },
      timestamp: "$timestamp",
      weather: {
        weathercode: "$weathercode",
        latitude:    "$latitude",
        longitude:   "$longitude"
      },
      sbb: {
        delay_count: "$sbb_data.delay_minutes"
      },
      traffic: {
        latitude:        "$traffic_data.latitude",
        longitude:       "$traffic_data.longitude",
        current_speed:   "$traffic_data.current_speed",
        free_flow_speed: "$traffic_data.free_flow_speed"
      },
      scores: 1,
      created_at: "$created_at"
    }
  },

  // 9. Write denormalized documents to mood_snapshots (replaces collection)
  { $out: "mood_snapshots" }

]);

print("mood_snapshots collection created.");
print("Documents: " + db.mood_snapshots.countDocuments());

// ----------------------------------------------------------------
// Step 2: Materialized View – mv_daily_mood
//         Daily averages per city (mirrors MySQL mv_daily_mood)
// ----------------------------------------------------------------

print("\nBuilding mv_daily_mood...");

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
      _id: 0,
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
  { $sort: { date: 1, city_name: 1 } },
  { $out: "mv_daily_mood" }
]);

print("mv_daily_mood collection created.");
print("Documents: " + db.mv_daily_mood.countDocuments());
print("\nTransformation complete.");
