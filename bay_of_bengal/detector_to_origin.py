from pathlib import Path
from datetime import datetime, timedelta
import json

import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

from opendrift.readers import reader_netCDF_CF_generic
from opendrift.models.openoil import OpenOil


# ============================================================
# PATHS
# ============================================================

BASE = Path(r"D:\Opendrift")

CURRENTS_FILE = (
    BASE / "bay_of_bengal_currents.nc"
)

WIND_FILE = (
    BASE / "bay_of_bengal_wind.nc"
)

INPUT_FILE = (
    BASE
    / "bay_of_bengal"
    / "spill_detection_result.json"
)

OUTPUT_DIR = (
    BASE
    / "bay_of_bengal"
    / "phase4_4_output"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


BACKWARD_FILE = (
    OUTPUT_DIR
    / "backward_trajectory.nc"
)

RESULT_FILE = (
    OUTPUT_DIR
    / "origin_result.json"
)

MAP_FILE = (
    OUTPUT_DIR
    / "origin_density_map.png"
)


# ============================================================
# CONFIGURATION
# ============================================================

LOOKBACK_HOURS = 8

NUMBER_OF_PARTICLES = 200

SEED_RADIUS_M = 1000

TIME_STEP_SECONDS = 900

OUTPUT_STEP_SECONDS = 3600

OIL_TYPE = "HEIDRUN AARE 2023"


# ============================================================
# HAVERSINE
# ============================================================

def haversine_km(
    lat1,
    lon1,
    lat2,
    lon2
):

    R = 6371.0

    lat1 = np.radians(lat1)
    lat2 = np.radians(lat2)

    dlat = np.radians(
        lat2 - lat1
    )

    dlon = np.radians(
        lon2 - lon1
    )

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
# LOAD DETECTOR RESULT
# ============================================================

print("=" * 70)
print("PHASE 4.4 - DETECTOR → OPENOIL ORIGIN PIPELINE")
print("=" * 70)

print("\nLoading detector result...")

if not INPUT_FILE.exists():

    raise FileNotFoundError(
        f"Detector result not found:\n{INPUT_FILE}"
    )


with open(
    INPUT_FILE,
    "r"
) as f:

    spill = json.load(f)


# ============================================================
# VALIDATE DETECTOR RESULT
# ============================================================

required_fields = [
    "spill_detected",
    "latitude",
    "longitude",
    "timestamp"
]


for field in required_fields:

    if field not in spill:

        raise ValueError(
            f"Missing detector field: {field}"
        )


if not spill["spill_detected"]:

    print(
        "\nNo oil spill detected."
    )

    print(
        "Origin reconstruction will not run."
    )

    raise SystemExit(0)


spill_lat = float(
    spill["latitude"]
)

spill_lon = float(
    spill["longitude"]
)

timestamp_string = (
    spill["timestamp"]
)


# ============================================================
# COORDINATE VALIDATION
# ============================================================

if not -90 <= spill_lat <= 90:

    raise ValueError(
        f"Invalid latitude: {spill_lat}"
    )


if not -180 <= spill_lon <= 180:

    raise ValueError(
        f"Invalid longitude: {spill_lon}"
    )


# ============================================================
# PARSE TIMESTAMP
# ============================================================

spill_time = datetime.fromisoformat(
    timestamp_string
)


# ============================================================
# PRINT DETECTOR RESULT
# ============================================================

print("\n" + "=" * 70)
print("DETECTOR RESULT")
print("=" * 70)

print(
    f"\nSpill detected : "
    f"{spill['spill_detected']}"
)

print(
    f"Latitude       : "
    f"{spill_lat}"
)

print(
    f"Longitude      : "
    f"{spill_lon}"
)

print(
    f"Timestamp      : "
    f"{spill_time}"
)


# ============================================================
# LOAD ENVIRONMENTAL READERS
# ============================================================

print("\n" + "=" * 70)
print("LOADING ENVIRONMENTAL DATA")
print("=" * 70)

reader_currents = (
    reader_netCDF_CF_generic.Reader(
        str(CURRENTS_FILE)
    )
)

reader_wind = (
    reader_netCDF_CF_generic.Reader(
        str(WIND_FILE)
    )
)


# ============================================================
# DETERMINE COMMON ENVIRONMENTAL WINDOW
# ============================================================

environment_start = max(
    reader_currents.start_time,
    reader_wind.start_time
)

environment_end = min(
    reader_currents.end_time,
    reader_wind.end_time
)


print(
    f"\nEnvironmental data:"
)

print(
    f"{environment_start}"
)

print(
    f"→ {environment_end}"
)


# ============================================================
# CHECK SPILL TIME
# ============================================================

spill_time_np = np.datetime64(
    spill_time
)

environment_start_np = np.datetime64(
    environment_start
)

environment_end_np = np.datetime64(
    environment_end
)


if (
    spill_time_np < environment_start_np
    or
    spill_time_np > environment_end_np
):

    raise ValueError(
        "\nDetector timestamp is outside "
        "the available environmental-data window.\n"
        f"Detector time: {spill_time}\n"
        f"Available: {environment_start} → "
        f"{environment_end}"
    )


# ============================================================
# CHECK BACKWARD WINDOW
# ============================================================

origin_time = (
    spill_time
    - timedelta(
        hours=LOOKBACK_HOURS
    )
)


origin_time_np = np.datetime64(
    origin_time
)


if origin_time_np < environment_start_np:

    raise ValueError(
        "\nNot enough environmental data "
        "for the requested lookback.\n"
        f"Spill time: {spill_time}\n"
        f"Requested lookback: "
        f"{LOOKBACK_HOURS} hours\n"
        f"Earliest required time: "
        f"{origin_time}\n"
        f"Available from: "
        f"{environment_start}"
    )


# ============================================================
# TIME INFORMATION
# ============================================================

print("\n" + "=" * 70)
print("BACKWARD WINDOW")
print("=" * 70)

print(
    f"\nSpill time  : "
    f"{spill_time}"
)

print(
    f"Origin time : "
    f"{origin_time}"
)

print(
    f"Lookback    : "
    f"{LOOKBACK_HOURS} hours"
)


# ============================================================
# CREATE OPENOIL
# ============================================================

oil = OpenOil(
    loglevel=20
)

oil.add_reader(
    [
        reader_currents,
        reader_wind
    ]
)


# ============================================================
# SEED DETECTED SPILL
# ============================================================

print("\n" + "=" * 70)
print("SEEDING DETECTED SPILL")
print("=" * 70)

oil.seed_elements(
    lon=spill_lon,
    lat=spill_lat,
    radius=SEED_RADIUS_M,
    number=NUMBER_OF_PARTICLES,
    time=spill_time,
    z=0,
    oil_type=OIL_TYPE
)


# ============================================================
# BACKWARD SIMULATION
# ============================================================

print("\nRunning backward OpenOil...")

total_steps = int(
    LOOKBACK_HOURS
    * 3600
    / TIME_STEP_SECONDS
)

oil.run(
    end_time=origin_time,
    time_step=-TIME_STEP_SECONDS,
    time_step_output=OUTPUT_STEP_SECONDS,
    outfile=str(BACKWARD_FILE)
)


# ============================================================
# LOAD TRAJECTORY
# ============================================================

print("\nLoading backward trajectory...")

ds = xr.open_dataset(
    BACKWARD_FILE
)

lon = ds["lon"].values

lat = ds["lat"].values

times = ds["time"].values


# ============================================================
# EARLIEST POSITIONS
# ============================================================

origin_lon = lon[:, -1]

origin_lat = lat[:, -1]


valid = (
    np.isfinite(origin_lon)
    &
    np.isfinite(origin_lat)
)


origin_lon = origin_lon[valid]

origin_lat = origin_lat[valid]


print(
    f"\nValid particles: "
    f"{len(origin_lon)}"
)


if len(origin_lon) < 10:

    raise RuntimeError(
        "Too few valid particles for "
        "origin-density calculation."
    )


# ============================================================
# PARTICLE STATISTICS
# ============================================================

print("\n" + "=" * 70)
print("BACKTRACKED PARTICLE CLOUD")
print("=" * 70)

print(
    f"\nLatitude:"
)

print(
    f"{origin_lat.min():.6f}"
    f" → "
    f"{origin_lat.max():.6f}"
)

print(
    f"\nLongitude:"
)

print(
    f"{origin_lon.min():.6f}"
    f" → "
    f"{origin_lon.max():.6f}"
)


# ============================================================
# KDE
# ============================================================

print("\nCalculating origin density...")

values = np.vstack(
    [
        origin_lon,
        origin_lat
    ]
)

kde = gaussian_kde(
    values
)


# ============================================================
# GRID
# ============================================================

padding = 0.02

grid_lon = np.linspace(
    origin_lon.min() - padding,
    origin_lon.max() + padding,
    150
)

grid_lat = np.linspace(
    origin_lat.min() - padding,
    origin_lat.max() + padding,
    150
)

mesh_lon, mesh_lat = np.meshgrid(
    grid_lon,
    grid_lat
)

grid_points = np.vstack(
    [
        mesh_lon.ravel(),
        mesh_lat.ravel()
    ]
)

density = kde(
    grid_points
).reshape(
    mesh_lon.shape
)


# ============================================================
# RELATIVE DENSITY
# ============================================================

relative_density = (
    density
    / density.max()
)


# ============================================================
# MAXIMUM DENSITY
# ============================================================

max_index = np.unravel_index(
    np.argmax(relative_density),
    relative_density.shape
)

max_lat = float(
    mesh_lat[max_index]
)

max_lon = float(
    mesh_lon[max_index]
)


# ============================================================
# HIGH-DENSITY REGION
# ============================================================

def density_region(
    density_grid,
    lon_grid,
    lat_grid,
    fraction
):

    flat = density_grid.ravel()

    order = np.argsort(
        flat
    )[::-1]

    sorted_density = (
        flat[order]
    )

    cumulative = np.cumsum(
        sorted_density
    )

    index = np.searchsorted(
        cumulative,
        fraction * cumulative[-1]
    )

    selected = order[
        :index + 1
    ]

    selected_lat = (
        lat_grid.ravel()[selected]
    )

    selected_lon = (
        lon_grid.ravel()[selected]
    )

    threshold = (
        sorted_density[index]
        / density_grid.max()
    )

    return {
        "latitude_min":
            float(selected_lat.min()),

        "latitude_max":
            float(selected_lat.max()),

        "longitude_min":
            float(selected_lon.min()),

        "longitude_max":
            float(selected_lon.max()),

        "relative_density_threshold":
            float(threshold)
    }


region_50 = density_region(
    density,
    mesh_lon,
    mesh_lat,
    0.50
)

region_80 = density_region(
    density,
    mesh_lon,
    mesh_lat,
    0.80
)


# ============================================================
# RESULTS
# ============================================================

print("\n" + "=" * 70)
print("DETECTOR → ORIGIN RESULT")
print("=" * 70)

print(
    f"\nCandidate origin:"
)

print(
    f"Latitude  : "
    f"{max_lat:.6f}"
)

print(
    f"Longitude : "
    f"{max_lon:.6f}"
)


print(
    "\n50% high-density region:"
)

print(
    f"Latitude : "
    f"{region_50['latitude_min']:.6f}"
    f" → "
    f"{region_50['latitude_max']:.6f}"
)

print(
    f"Longitude: "
    f"{region_50['longitude_min']:.6f}"
    f" → "
    f"{region_50['longitude_max']:.6f}"
)


print(
    "\n80% high-density region:"
)

print(
    f"Latitude : "
    f"{region_80['latitude_min']:.6f}"
    f" → "
    f"{region_80['latitude_max']:.6f}"
)

print(
    f"Longitude: "
    f"{region_80['longitude_min']:.6f}"
    f" → "
    f"{region_80['longitude_max']:.6f}"
)


# ============================================================
# SAVE JSON
# ============================================================

result = {

    "spill_detection": {
        "spill_detected":
            bool(spill["spill_detected"]),

        "latitude":
            spill_lat,

        "longitude":
            spill_lon,

        "timestamp":
            timestamp_string
    },

    "environment": {
        "data_start":
            str(environment_start),

        "data_end":
            str(environment_end)
    },

    "backward_simulation": {
        "lookback_hours":
            LOOKBACK_HOURS,

        "origin_time":
            str(origin_time),

        "particles":
            NUMBER_OF_PARTICLES,

        "valid_particles":
            int(len(origin_lon))
    },

    "candidate_origin": {
        "latitude":
            max_lat,

        "longitude":
            max_lon,

        "relative_density":
            1.0
    },

    "region_50_percent":
        region_50,

    "region_80_percent":
        region_80,

    "limitations": [
        "Candidate origin is a model-based estimate.",
        "Relative density is not calibrated probability.",
        "Real-world accuracy requires validation against "
        "independent spill events."
    ]
}


with open(
    RESULT_FILE,
    "w"
) as f:

    json.dump(
        result,
        f,
        indent=4
    )


# ============================================================
# MAP
# ============================================================

plt.figure(
    figsize=(12, 9)
)

levels = np.linspace(
    0,
    1,
    20
)

plt.contourf(
    mesh_lon,
    mesh_lat,
    relative_density,
    levels=levels
)

plt.scatter(
    origin_lon,
    origin_lat,
    s=12,
    alpha=0.40,
    label="Backtracked particles"
)

plt.scatter(
    max_lon,
    max_lat,
    marker="X",
    s=250,
    linewidths=2,
    label="Candidate origin"
)

plt.scatter(
    spill_lon,
    spill_lat,
    marker="*",
    s=250,
    linewidths=2,
    label="Detected spill"
)

plt.xlabel(
    "Longitude"
)

plt.ylabel(
    "Latitude"
)

plt.title(
    "SpillTrace - Detector to Backtracked Origin"
)

plt.legend()

plt.grid(
    True,
    alpha=0.3
)

plt.tight_layout()

plt.savefig(
    MAP_FILE,
    dpi=200
)

plt.show()


# ============================================================
# CLOSE
# ============================================================

ds.close()


# ============================================================
# COMPLETE
# ============================================================

print("\n" + "=" * 70)
print("PHASE 4.4 COMPLETE")
print("=" * 70)

print(
    "\nSaved:"
)

print(
    BACKWARD_FILE
)

print(
    RESULT_FILE
)

print(
    MAP_FILE
)