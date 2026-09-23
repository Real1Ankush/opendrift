import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# CONFIGURATION
# ============================================================

AIS_FILE = "ais_sample.csv"

# ------------------------------------------------------------
# Origin estimate from Phase 2.2
# ------------------------------------------------------------

ORIGIN_LAT = 59.97270
ORIGIN_LON = 4.78601

ORIGIN_TIME = pd.Timestamp(
    "2015-11-15 19:00:00",
    tz="UTC"
)

# ------------------------------------------------------------
# 50% high-density origin region from Phase 2.2
# ------------------------------------------------------------

REGION_LAT_MIN = 59.90507
REGION_LAT_MAX = 60.01920

REGION_LON_MIN = 4.71261
REGION_LON_MAX = 4.90836

# ------------------------------------------------------------
# Candidate search window
# ------------------------------------------------------------

TIME_WINDOW_HOURS = 4


# ============================================================
# HAVERSINE DISTANCE
# ============================================================

def haversine_km(lat1, lon1, lat2, lon2):

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

    c = 2 * np.arctan2(
        np.sqrt(a),
        np.sqrt(1 - a)
    )

    return R * c


# ============================================================
# BEARING CALCULATION
# ============================================================

def calculate_bearing(lat1, lon1, lat2, lon2):

    lat1 = np.radians(lat1)
    lat2 = np.radians(lat2)

    dlon = np.radians(lon2 - lon1)

    x = np.sin(dlon) * np.cos(lat2)

    y = (
        np.cos(lat1) * np.sin(lat2)
        - np.sin(lat1)
        * np.cos(lat2)
        * np.cos(dlon)
    )

    bearing = np.degrees(
        np.arctan2(x, y)
    )

    return (bearing + 360) % 360


# ============================================================
# CIRCULAR ANGLE DIFFERENCE
# ============================================================

def angle_difference(a, b):

    difference = abs(a - b)

    return min(
        difference,
        360 - difference
    )


# ============================================================
# LOAD AIS DATA
# ============================================================

print("=" * 70)
print("PHASE 3.2 - AIS TRAJECTORY MATCHING")
print("=" * 70)

print("\nLoading AIS data...")

df = pd.read_csv(AIS_FILE)

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    utc=True
)

df = df.sort_values(
    ["mmsi", "timestamp"]
)

print(
    f"AIS observations loaded: {len(df)}"
)

print(
    f"Unique vessels: {df['mmsi'].nunique()}"
)


# ============================================================
# STEP 1 - SPATIAL FILTER
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

candidate_mmsi = spatial["mmsi"].unique()

print(
    f"Observations inside 50% origin region: "
    f"{len(spatial)}"
)

print(
    f"Candidate vessels: "
    f"{len(candidate_mmsi)}"
)

for mmsi in candidate_mmsi:

    vessel = df[
        df["mmsi"] == mmsi
    ].iloc[0]

    print(
        f"  {mmsi} - "
        f"{vessel['vessel_name']} - "
        f"{vessel['ship_type']}"
    )


# ============================================================
# STEP 2 - TEMPORAL FILTER
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

filtered = df[
    (df["mmsi"].isin(candidate_mmsi))
    & (df["timestamp"] >= start_time)
    & (df["timestamp"] <= end_time)
].copy()

print(
    f"Time window:"
)

print(
    f"  {start_time}"
)

print(
    f"  {end_time}"
)

print(
    f"\nObservations after filtering: "
    f"{len(filtered)}"
)


# ============================================================
# STEP 3 - TRAJECTORY ANALYSIS
# ============================================================

print("\n" + "=" * 70)
print("STEP 3 - TRAJECTORY ANALYSIS")
print("=" * 70)

results = []


for mmsi, vessel in filtered.groupby("mmsi"):

    vessel = vessel.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    if len(vessel) == 0:
        continue

    # --------------------------------------------------------
    # Distance from every AIS point to origin
    # --------------------------------------------------------

    vessel["distance_km"] = haversine_km(
        vessel["latitude"].values,
        vessel["longitude"].values,
        ORIGIN_LAT,
        ORIGIN_LON
    )

    # --------------------------------------------------------
    # Time difference from estimated origin time
    # --------------------------------------------------------

    vessel["time_difference_hours"] = (
        abs(
            vessel["timestamp"]
            - ORIGIN_TIME
        ).dt.total_seconds()
        / 3600
    )

    # --------------------------------------------------------
    # Check whether trajectory enters 50% region
    # --------------------------------------------------------

    inside_region = (
        (vessel["latitude"] >= REGION_LAT_MIN)
        & (vessel["latitude"] <= REGION_LAT_MAX)
        & (vessel["longitude"] >= REGION_LON_MIN)
        & (vessel["longitude"] <= REGION_LON_MAX)
    )

    entered_region = bool(
        inside_region.any()
    )

    region_observations = int(
        inside_region.sum()
    )

    # --------------------------------------------------------
    # Closest point
    # --------------------------------------------------------

    closest_idx = vessel[
        "distance_km"
    ].idxmin()

    closest = vessel.loc[
        closest_idx
    ]

    min_distance = float(
        closest["distance_km"]
    )

    closest_time_difference = float(
        closest["time_difference_hours"]
    )

    # --------------------------------------------------------
    # Approach / departure analysis
    # --------------------------------------------------------

    first_distance = float(
        vessel.iloc[0]["distance_km"]
    )

    last_distance = float(
        vessel.iloc[-1]["distance_km"]
    )

    approaching = (
        first_distance > min_distance
    )

    departing = (
        last_distance > min_distance
    )

    approach_ratio = 0

    if first_distance > 0:

        approach_ratio = (
            first_distance
            - min_distance
        ) / first_distance

    departure_ratio = 0

    if last_distance > 0:

        departure_ratio = (
            last_distance
            - min_distance
        ) / last_distance

    # --------------------------------------------------------
    # Speed analysis
    # --------------------------------------------------------

    mean_sog = float(
        vessel["sog"].mean()
    )

    closest_sog = float(
        closest["sog"]
    )

    if mean_sog > 0:

        speed_change_percent = (
            abs(closest_sog - mean_sog)
            / mean_sog
            * 100
        )

    else:

        speed_change_percent = 0

    # --------------------------------------------------------
    # Course analysis
    # --------------------------------------------------------

    course_changes = []

    for i in range(1, len(vessel)):

        previous_cog = float(
            vessel.iloc[i - 1]["cog"]
        )

        current_cog = float(
            vessel.iloc[i]["cog"]
        )

        course_changes.append(
            angle_difference(
                previous_cog,
                current_cog
            )
        )

    if course_changes:

        mean_course_change = float(
            np.mean(course_changes)
        )

        max_course_change = float(
            np.max(course_changes)
        )

    else:

        mean_course_change = 0

        max_course_change = 0

    # --------------------------------------------------------
    # Track continuity
    # --------------------------------------------------------

    if len(vessel) > 1:

        time_gaps = (
            vessel["timestamp"]
            .diff()
            .dropna()
            .dt.total_seconds()
            / 3600
        )

        median_gap = float(
            time_gaps.median()
        )

        continuous_points = int(
            (time_gaps <= 2).sum()
        )

    else:

        median_gap = np.nan

        continuous_points = 0

    # --------------------------------------------------------
    # Calculate bearing of vessel movement
    # --------------------------------------------------------

    if len(vessel) >= 2:

        movement_bearing = calculate_bearing(
            vessel.iloc[0]["latitude"],
            vessel.iloc[0]["longitude"],
            vessel.iloc[-1]["latitude"],
            vessel.iloc[-1]["longitude"]
        )

    else:

        movement_bearing = np.nan

    # --------------------------------------------------------
    # Distance score
    #
    # 0 km = 100
    # 50 km = 0
    # --------------------------------------------------------

    distance_score = max(
        0,
        min(
            100,
            100 * (
                1
                - min_distance / 50
            )
        )
    )

    # --------------------------------------------------------
    # Temporal score
    #
    # Exact origin time = 100
    # 4 hours = 0
    # --------------------------------------------------------

    temporal_score = max(
        0,
        min(
            100,
            100 * (
                1
                - closest_time_difference
                / TIME_WINDOW_HOURS
            )
        )
    )

    # --------------------------------------------------------
    # Region crossing score
    # --------------------------------------------------------

    if entered_region:

        region_score = 100

    else:

        region_score = 0

    # --------------------------------------------------------
    # Approach / departure score
    # --------------------------------------------------------

    if approaching and departing:

        approach_score = 100

    elif approaching or departing:

        approach_score = 60

    else:

        approach_score = 20

    # --------------------------------------------------------
    # Track continuity score
    # --------------------------------------------------------

    if len(vessel) <= 1:

        continuity_score = 0

    else:

        expected_intervals = len(vessel) - 1

        continuity_score = (
            continuous_points
            / expected_intervals
            * 100
        )

        continuity_score = min(
            100,
            continuity_score
        )

    # --------------------------------------------------------
    # Behavior score
    #
    # This is intentionally modest because speed/course
    # changes alone do NOT establish a source event.
    # --------------------------------------------------------

    behavior_score = 50

    if speed_change_percent >= 20:

        behavior_score += 20

    elif speed_change_percent >= 10:

        behavior_score += 10

    if max_course_change >= 30:

        behavior_score += 20

    elif max_course_change >= 15:

        behavior_score += 10

    behavior_score = min(
        100,
        behavior_score
    )

    # --------------------------------------------------------
    # Prototype trajectory-match score
    #
    # This is NOT a probability.
    # --------------------------------------------------------

    trajectory_score = (
        0.30 * distance_score
        + 0.20 * temporal_score
        + 0.20 * region_score
        + 0.15 * approach_score
        + 0.10 * continuity_score
        + 0.05 * behavior_score
    )

    # --------------------------------------------------------
    # Save vessel result
    # --------------------------------------------------------

    results.append({

        "mmsi":
            mmsi,

        "vessel_name":
            vessel.iloc[0]["vessel_name"],

        "ship_type":
            vessel.iloc[0]["ship_type"],

        "observations":
            len(vessel),

        "entered_50pct_origin_region":
            entered_region,

        "region_observations":
            region_observations,

        "min_distance_km":
            min_distance,

        "closest_timestamp":
            closest["timestamp"],

        "closest_time_difference_hours":
            closest_time_difference,

        "first_distance_km":
            first_distance,

        "last_distance_km":
            last_distance,

        "approaching_origin":
            approaching,

        "departing_origin":
            departing,

        "mean_sog":
            mean_sog,

        "closest_sog":
            closest_sog,

        "speed_change_percent":
            speed_change_percent,

        "mean_course_change":
            mean_course_change,

        "max_course_change":
            max_course_change,

        "median_time_gap_hours":
            median_gap,

        "movement_bearing":
            movement_bearing,

        "distance_score":
            distance_score,

        "temporal_score":
            temporal_score,

        "region_score":
            region_score,

        "approach_score":
            approach_score,

        "continuity_score":
            continuity_score,

        "behavior_score":
            behavior_score,

        "trajectory_match_score":
            trajectory_score
    })


# ============================================================
# RESULTS DATAFRAME
# ============================================================

results = pd.DataFrame(results)

results = results.sort_values(
    "trajectory_match_score",
    ascending=False
).reset_index(drop=True)


# ============================================================
# DISPLAY RESULTS
# ============================================================

print("\n" + "=" * 70)
print("TRAJECTORY MATCH RESULTS")
print("=" * 70)

for index, row in results.iterrows():

    print(
        f"\nCandidate {index + 1}"
    )

    print(
        f"Vessel              : "
        f"{row['vessel_name']}"
    )

    print(
        f"MMSI                : "
        f"{row['mmsi']}"
    )

    print(
        f"Ship type           : "
        f"{row['ship_type']}"
    )

    print(
        f"Observations        : "
        f"{row['observations']}"
    )

    print(
        f"Entered 50% region  : "
        f"{row['entered_50pct_origin_region']}"
    )

    print(
        f"Region observations : "
        f"{row['region_observations']}"
    )

    print(
        f"Minimum distance    : "
        f"{row['min_distance_km']:.2f} km"
    )

    print(
        f"First distance      : "
        f"{row['first_distance_km']:.2f} km"
    )

    print(
        f"Last distance       : "
        f"{row['last_distance_km']:.2f} km"
    )

    print(
        f"Approaching         : "
        f"{row['approaching_origin']}"
    )

    print(
        f"Departing           : "
        f"{row['departing_origin']}"
    )

    print(
        f"Mean SOG            : "
        f"{row['mean_sog']:.2f} knots"
    )

    print(
        f"Closest SOG         : "
        f"{row['closest_sog']:.2f} knots"
    )

    print(
        f"Speed change        : "
        f"{row['speed_change_percent']:.1f}%"
    )

    print(
        f"Mean course change  : "
        f"{row['mean_course_change']:.1f}°"
    )

    print(
        f"Max course change   : "
        f"{row['max_course_change']:.1f}°"
    )

    print(
        f"Continuity score    : "
        f"{row['continuity_score']:.1f}"
    )

    print(
        f"Trajectory score    : "
        f"{row['trajectory_match_score']:.1f}"
    )


# ============================================================
# SAVE CSV
# ============================================================

output_file = (
    "phase3_vessel_trajectory_analysis.csv"
)

results.to_csv(
    output_file,
    index=False
)


# ============================================================
# VISUALIZATION
# ============================================================

print("\n" + "=" * 70)
print("CREATING AIS TRAJECTORY MAP")
print("=" * 70)

plt.figure(
    figsize=(12, 9)
)

# ------------------------------------------------------------
# Plot all candidate trajectories
# ------------------------------------------------------------

for mmsi, vessel in filtered.groupby("mmsi"):

    vessel = vessel.sort_values(
        "timestamp"
    )

    name = vessel.iloc[0]["vessel_name"]

    plt.plot(
        vessel["longitude"],
        vessel["latitude"],
        marker="o",
        linewidth=2,
        label=name
    )

    # Label first point
    plt.text(
        vessel.iloc[0]["longitude"],
        vessel.iloc[0]["latitude"],
        name,
        fontsize=9
    )


# ------------------------------------------------------------
# 50% origin region
# ------------------------------------------------------------

region_x = [
    REGION_LON_MIN,
    REGION_LON_MAX,
    REGION_LON_MAX,
    REGION_LON_MIN,
    REGION_LON_MIN
]

region_y = [
    REGION_LAT_MIN,
    REGION_LAT_MIN,
    REGION_LAT_MAX,
    REGION_LAT_MAX,
    REGION_LAT_MIN
]

plt.plot(
    region_x,
    region_y,
    linestyle="--",
    linewidth=2,
    label="50% origin region"
)


# ------------------------------------------------------------
# Maximum density origin
# ------------------------------------------------------------

plt.scatter(
    ORIGIN_LON,
    ORIGIN_LAT,
    marker="X",
    s=250,
    linewidths=2,
    label="Estimated origin"
)


# ------------------------------------------------------------
# Origin time annotation
# ------------------------------------------------------------

plt.text(
    ORIGIN_LON,
    ORIGIN_LAT,
    "  Estimated origin",
    fontsize=10
)


# ------------------------------------------------------------
# Map formatting
# ------------------------------------------------------------

plt.xlabel(
    "Longitude"
)

plt.ylabel(
    "Latitude"
)

plt.title(
    "AIS Vessel Trajectories vs Backtracked Oil Origin"
)

plt.grid(
    True,
    alpha=0.3
)

plt.legend()

plt.tight_layout()

map_file = (
    "phase3_ais_trajectory_map.png"
)

plt.savefig(
    map_file,
    dpi=200
)

plt.show()


# ============================================================
# COMPLETE
# ============================================================

print("\n" + "=" * 70)
print("PHASE 3.2 COMPLETE")
print("=" * 70)

print("\nSaved:")

print(
    output_file
)

print(
    map_file
)

print(
    "\nNOTE:"
)

print(
    "The trajectory_match_score is a prototype "
    "screening score, not a probability of responsibility."
)