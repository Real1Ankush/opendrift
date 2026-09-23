import pandas as pd
import numpy as np
from math import radians, sin, cos, sqrt, atan2


# ============================================================
# CONFIGURATION
# ============================================================

AIS_FILE = "ais_sample.csv"

# From Phase 2.2
ORIGIN_LAT = 59.97270
ORIGIN_LON = 4.78601

# Estimated origin time for this test.
# This should eventually come directly from the OpenDrift run.
ORIGIN_TIME = pd.Timestamp("2015-11-15 19:00:00", tz="UTC")

# Search window around estimated origin time
TIME_WINDOW_HOURS = 4

# Spatial candidate region from Phase 2.2
REGION_LAT_MIN = 59.90507
REGION_LAT_MAX = 60.01920

REGION_LON_MIN = 4.71261
REGION_LON_MAX = 4.90836


# ============================================================
# HAVERSINE DISTANCE
# ============================================================

def haversine_km(lat1, lon1, lat2, lon2):
    """
    Calculate great-circle distance between two coordinates.
    """

    R = 6371.0

    lat1 = np.radians(lat1)
    lat2 = np.radians(lat2)

    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2) ** 2
    )

    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return R * c


# ============================================================
# LOAD AIS
# ============================================================

print("=" * 70)
print("PHASE 3 - AIS CORRELATION")
print("=" * 70)

print("\nLoading AIS data...")

df = pd.read_csv(AIS_FILE)

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    utc=True
)

print(f"AIS observations loaded: {len(df)}")
print(f"Unique vessels: {df['mmsi'].nunique()}")


# ============================================================
# SPATIAL FILTER
# ============================================================

print("\n" + "=" * 70)
print("STEP 1 - SPATIAL FILTER")
print("=" * 70)

spatial = df[
    (df["latitude"] >= REGION_LAT_MIN)
    & (df["latitude"] <= REGION_LAT_MAX)
    & (df["longitude"] >= REGION_LON_MIN)
    & (df["longitude"] <= REGION_LON_MAX)
].copy()

print(f"Observations inside 50% origin region: {len(spatial)}")
print(f"Candidate vessels: {spatial['mmsi'].nunique()}")

print("\nCandidate vessels:")

for mmsi, group in spatial.groupby("mmsi"):
    print(
        f"  {mmsi} - "
        f"{group.iloc[0]['vessel_name']} - "
        f"{group.iloc[0]['ship_type']}"
    )


# ============================================================
# TEMPORAL FILTER
# ============================================================

print("\n" + "=" * 70)
print("STEP 2 - TEMPORAL FILTER")
print("=" * 70)

start_time = (
    ORIGIN_TIME
    - pd.Timedelta(hours=TIME_WINDOW_HOURS)
)

end_time = (
    ORIGIN_TIME
    + pd.Timedelta(hours=TIME_WINDOW_HOURS)
)

temporal = spatial[
    (spatial["timestamp"] >= start_time)
    & (spatial["timestamp"] <= end_time)
].copy()

print(f"Time window:")
print(f"  {start_time}")
print(f"  {end_time}")

print(f"\nObservations after time filtering: {len(temporal)}")
print(f"Candidate vessels: {temporal['mmsi'].nunique()}")


# ============================================================
# DISTANCE TO ESTIMATED ORIGIN
# ============================================================

print("\n" + "=" * 70)
print("STEP 3 - DISTANCE TO ORIGIN")
print("=" * 70)

temporal["distance_km"] = haversine_km(
    temporal["latitude"].values,
    temporal["longitude"].values,
    ORIGIN_LAT,
    ORIGIN_LON
)

# Time difference from estimated origin time
temporal["time_difference_hours"] = (
    abs(
        temporal["timestamp"]
        - ORIGIN_TIME
    ).dt.total_seconds()
    / 3600
)


# ============================================================
# VESSEL LEVEL FEATURES
# ============================================================

vessel_features = []

for mmsi, group in temporal.groupby("mmsi"):

    group = group.sort_values("timestamp")

    closest_idx = group["distance_km"].idxmin()
    closest_row = group.loc[closest_idx]

    vessel_features.append({
        "mmsi": mmsi,
        "vessel_name": group.iloc[0]["vessel_name"],
        "ship_type": group.iloc[0]["ship_type"],

        "min_distance_km":
            closest_row["distance_km"],

        "closest_time":
            closest_row["timestamp"],

        "closest_sog":
            closest_row["sog"],

        "closest_cog":
            closest_row["cog"],

        "time_difference_hours":
            closest_row["time_difference_hours"],

        "observations":
            len(group)
    })


results = pd.DataFrame(vessel_features)


# ============================================================
# DISTANCE SCORE
# ============================================================

def distance_score(distance):

    # 0 km -> 100
    # 50 km -> 0

    score = 100 * (1 - distance / 50)

    return max(0, min(100, score))


results["distance_score"] = results[
    "min_distance_km"
].apply(distance_score)


# ============================================================
# TEMPORAL SCORE
# ============================================================

def temporal_score(hours):

    # Exact time -> 100
    # 4+ hours -> 0

    score = 100 * (
        1 - hours / TIME_WINDOW_HOURS
    )

    return max(0, min(100, score))


results["temporal_score"] = results[
    "time_difference_hours"
].apply(temporal_score)


# ============================================================
# TRACK PRESENCE SCORE
# ============================================================

def presence_score(observations):

    score = min(
        100,
        observations * 25
    )

    return score


results["presence_score"] = results[
    "observations"
].apply(presence_score)


# ============================================================
# FINAL CANDIDATE SCORE
# ============================================================

results["final_score"] = (
    0.50 * results["distance_score"]
    + 0.30 * results["temporal_score"]
    + 0.20 * results["presence_score"]
)


# ============================================================
# SORT
# ============================================================

results = results.sort_values(
    "final_score",
    ascending=False
).reset_index(drop=True)


# ============================================================
# DISPLAY
# ============================================================

print("\n" + "=" * 70)
print("PHASE 3 - VESSEL CANDIDATE RANKING")
print("=" * 70)

for index, row in results.iterrows():

    print(
        f"\nRank {index + 1}"
    )

    print(
        f"Vessel       : {row['vessel_name']}"
    )

    print(
        f"MMSI         : {row['mmsi']}"
    )

    print(
        f"Type         : {row['ship_type']}"
    )

    print(
        f"Min distance : "
        f"{row['min_distance_km']:.2f} km"
    )

    print(
        f"Time diff    : "
        f"{row['time_difference_hours']:.2f} hours"
    )

    print(
        f"Distance     : "
        f"{row['distance_score']:.1f}"
    )

    print(
        f"Temporal     : "
        f"{row['temporal_score']:.1f}"
    )

    print(
        f"Presence     : "
        f"{row['presence_score']:.1f}"
    )

    print(
        f"FINAL SCORE  : "
        f"{row['final_score']:.1f}"
    )


# ============================================================
# SAVE RESULTS
# ============================================================

results.to_csv(
    "phase3_vessel_candidates.csv",
    index=False
)

print("\n" + "=" * 70)
print("PHASE 3 COMPLETE")
print("=" * 70)

print("\nSaved:")
print("phase3_vessel_candidates.csv")