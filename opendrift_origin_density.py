import json

import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

from scipy.stats import gaussian_kde


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = "oil_backward_2_1.nc"

OUTPUT_JSON = "origin_density_2_2.json"
OUTPUT_IMAGE = "origin_density_map_2_2.png"

# Resolution of the density map
GRID_SIZE = 100


# ============================================================
# LOAD BACKWARD TRAJECTORY
# ============================================================

print("\n" + "=" * 70)
print("LOADING BACKWARD TRAJECTORY")
print("=" * 70)

ds = xr.open_dataset(
    INPUT_FILE,
    decode_coords=False
)

lon = ds["lon"].values
lat = ds["lat"].values
times = ds["time"].values


# ============================================================
# GET EARLIEST BACKTRACKED POSITIONS
# ============================================================

# The backward simulation has decreasing time:
#
# 18:00
# 17:00
# ...
# 10:00
#
# Therefore the last time index is the earliest
# backtracked position.

origin_lon = lon[:, -1]
origin_lat = lat[:, -1]


# ============================================================
# REMOVE INVALID PARTICLES
# ============================================================

valid = (
    np.isfinite(origin_lon)
    & np.isfinite(origin_lat)
)

origin_lon = origin_lon[valid]
origin_lat = origin_lat[valid]


print("\nValid particles:", len(origin_lon))

print(
    "Latitude range:",
    f"{origin_lat.min():.5f}",
    "→",
    f"{origin_lat.max():.5f}"
)

print(
    "Longitude range:",
    f"{origin_lon.min():.5f}",
    "→",
    f"{origin_lon.max():.5f}"
)


# ============================================================
# CREATE 2D KERNEL DENSITY ESTIMATE
# ============================================================

print("\nCalculating particle density...")


# Combine longitude and latitude
positions = np.vstack([
    origin_lon,
    origin_lat
])


# KDE estimates density based on the distribution
# of the backtracked particles.
kde = gaussian_kde(positions)


# ============================================================
# CREATE GRID
# ============================================================

lon_padding = 0.05
lat_padding = 0.05

lon_min = origin_lon.min() - lon_padding
lon_max = origin_lon.max() + lon_padding

lat_min = origin_lat.min() - lat_padding
lat_max = origin_lat.max() + lat_padding


grid_lon = np.linspace(
    lon_min,
    lon_max,
    GRID_SIZE
)

grid_lat = np.linspace(
    lat_min,
    lat_max,
    GRID_SIZE
)


grid_lon_mesh, grid_lat_mesh = np.meshgrid(
    grid_lon,
    grid_lat
)


grid_positions = np.vstack([
    grid_lon_mesh.ravel(),
    grid_lat_mesh.ravel()
])


density = kde(grid_positions)

density = density.reshape(
    grid_lon_mesh.shape
)


# ============================================================
# NORMALIZE DENSITY
# ============================================================

# This is a RELATIVE density score.
# It is NOT a calibrated probability.

density_relative = (
    density / density.max()
)


# ============================================================
# FIND MAXIMUM-DENSITY LOCATION
# ============================================================

max_index = np.unravel_index(
    np.argmax(density),
    density.shape
)

max_lat = float(
    grid_lat_mesh[max_index]
)

max_lon = float(
    grid_lon_mesh[max_index]
)

max_density = float(
    density[max_index]
)


print("\n" + "=" * 70)
print("MAXIMUM-DENSITY ORIGIN")
print("=" * 70)

print(
    f"Latitude  : {max_lat:.5f}"
)

print(
    f"Longitude : {max_lon:.5f}"
)

print(
    f"Relative density : 1.000"
)


# ============================================================
# CALCULATE DENSITY-MASS REGIONS
# ============================================================

# Treat each grid cell's density as proportional to
# the amount of particle support in that cell.

cell_density = density.ravel()

sorted_indices = np.argsort(
    cell_density
)[::-1]

sorted_density = cell_density[
    sorted_indices
]

density_mass = (
    sorted_density /
    sorted_density.sum()
)

cumulative_mass = np.cumsum(
    density_mass
)


def get_density_region(target_mass):

    # Find the density threshold required to
    # include the requested amount of support.

    index = np.searchsorted(
        cumulative_mass,
        target_mass
    )

    threshold = sorted_density[
        min(index, len(sorted_density) - 1)
    ]

    selected = density >= threshold

    selected_lat = grid_lat_mesh[selected]
    selected_lon = grid_lon_mesh[selected]

    return {
        "target_mass": target_mass,
        "latitude_min": float(selected_lat.min()),
        "latitude_max": float(selected_lat.max()),
        "longitude_min": float(selected_lon.min()),
        "longitude_max": float(selected_lon.max()),
        "density_threshold_relative": float(
            threshold / max_density
        )
    }


region_50 = get_density_region(0.50)
region_80 = get_density_region(0.80)


# ============================================================
# PRINT REGIONS
# ============================================================

print("\n" + "=" * 70)
print("50% HIGH-DENSITY ORIGIN REGION")
print("=" * 70)

print(
    f"Latitude : "
    f"{region_50['latitude_min']:.5f}"
    f" → "
    f"{region_50['latitude_max']:.5f}"
)

print(
    f"Longitude: "
    f"{region_50['longitude_min']:.5f}"
    f" → "
    f"{region_50['longitude_max']:.5f}"
)


print("\n" + "=" * 70)
print("80% HIGH-DENSITY ORIGIN REGION")
print("=" * 70)

print(
    f"Latitude : "
    f"{region_80['latitude_min']:.5f}"
    f" → "
    f"{region_80['latitude_max']:.5f}"
)

print(
    f"Longitude: "
    f"{region_80['longitude_min']:.5f}"
    f" → "
    f"{region_80['longitude_max']:.5f}"
)


# ============================================================
# CREATE JSON RESULT
# ============================================================

result = {

    "source_file": INPUT_FILE,

    "particles": int(len(origin_lat)),

    "backtrack_time": {
        "start_observation": str(times[0]),
        "earliest_origin_time": str(times[-1])
    },

    "origin_density": {

        "maximum_density_point": {
            "latitude": max_lat,
            "longitude": max_lon,
            "relative_density": 1.0
        },

        "region_50_percent": region_50,

        "region_80_percent": region_80
    },

    "particle_bounds": {
        "latitude_min": float(origin_lat.min()),
        "latitude_max": float(origin_lat.max()),
        "longitude_min": float(origin_lon.min()),
        "longitude_max": float(origin_lon.max())
    },

    "note": (
        "Density values are relative particle-density "
        "support and are not calibrated probabilities."
    )
}


# ============================================================
# SAVE JSON
# ============================================================

with open(
    OUTPUT_JSON,
    "w"
) as f:

    json.dump(
        result,
        f,
        indent=4
    )


# ============================================================
# CREATE DENSITY MAP
# ============================================================

plt.figure(
    figsize=(10, 8)
)

plt.contourf(
    grid_lon_mesh,
    grid_lat_mesh,
    density_relative,
    levels=20
)

# Backtracked particles
plt.scatter(
    origin_lon,
    origin_lat,
    s=10,
    alpha=0.35,
    label="Backtracked particles"
)

# Maximum density point
plt.scatter(
    max_lon,
    max_lat,
    marker="X",
    s=150,
    label="Maximum-density point"
)

plt.xlabel("Longitude")
plt.ylabel("Latitude")

plt.title(
    "Backtracked Oil Origin Density"
)

plt.legend()

plt.grid(
    True,
    alpha=0.3
)

plt.tight_layout()

plt.savefig(
    OUTPUT_IMAGE,
    dpi=200
)

plt.show()


# ============================================================
# COMPLETE
# ============================================================

print("\n" + "=" * 70)
print("PHASE 2.2 COMPLETE")
print("=" * 70)

print("Saved:")
print(OUTPUT_JSON)
print(OUTPUT_IMAGE)