#!/usr/bin/env python3
"""Precompute the domain-total vertical DOR delta-DIC inventory profile for one experiment,
used by ../../concentration_differences.ipynb (plot_vertical_mixing_profiles).

The model's native s_rho levels are terrain-following: the same s_rho index sits at very
different physical depths in different water columns (shallow over the shelf, deep in the
open ocean), so summing "at s_rho index k" across the domain mixes together contributions
from different depths -- there is no single depth that index k corresponds to. To get a real
depth profile, we instead pick a fixed-depth grid (every dz_target meters) and, for each
column, put the tracer mass on that fixed grid via the standard trick for turning a linear
interpolation into a mass-conserving remap: build the cumulative (dz-weighted) column mass
down to each sigma-layer interface, linearly interpolate that cumulative mass -- in physical
depth, which varies horizontally with local bathymetry/zeta -- onto the fixed target depth
edges, and difference consecutive edges to get the mass in each fixed-depth bin. This gives
the same result a conservative remap would for piecewise-constant sigma-layer data, using
only plain linear interpolation (mask_edges=True keeps a column from contributing beyond its
own local depth range). Finally sums over the horizontal domain and divides by dz_target to
give mmol/m.

Saves a small netCDF file so the notebook doesn't need to reload the full daily bgc/his
output each time it runs.
"""
import argparse
from pathlib import Path

import numpy as np
import xarray as xr
import xgcm
from roms_tools import Grid
from roms_tools.vertical_coordinate import compute_depth


def cell_area(grid: Grid) -> xr.DataArray:
    """Ocean cell area (m^2) at each horizontal grid point."""
    return (1 / (grid.ds.pm * grid.ds.pn)).where(grid.ds.mask_rho)


def layer_thickness(depth_w: xr.DataArray) -> xr.DataArray:
    """Local layer thickness (m) at each s_rho level, from interface depths on s_w."""
    return (depth_w.isel(s_w=slice(0, -1)) - depth_w.isel(s_w=slice(1, None))).rename(s_w="s_rho")


def domain_profile_on_depth_grid(
    grid: Grid,
    conc: xr.DataArray,
    depth_w: xr.DataArray,
    target_depth_edges: np.ndarray,
    dz_target: float,
) -> xr.DataArray:
    """Domain-total mmol/m profile of a tracer on a fixed-depth grid.

    See module docstring for the cumulative-mass / linear-interpolation approach.
    """
    dz = layer_thickness(depth_w)
    mass_per_layer = (conc * dz).drop_vars("s_rho", errors="ignore").rename(s_rho="s_w")

    # Cumulative mass (mmol/m^2) from the seafloor (0 at the bottom interface) up to each
    # sigma-layer interface -- decreases monotonically with depth, reaching the full column
    # total at the sea surface.
    cum_mass = mass_per_layer.cumsum(dim="s_w")
    cum_mass = xr.concat(
        [xr.zeros_like(cum_mass.isel(s_w=0)), cum_mass], dim="s_w"
    ).drop_vars("s_w", errors="ignore")
    # xr.concat keeps the two pieces' original chunks (size 1 + size N) instead of merging
    # them, but s_w must be a single chunk since it's a core dim for xgcm's transform below.
    cum_mass = cum_mass.chunk({"s_w": -1})

    xgrid = xgcm.Grid(
        grid.ds, coords={"s_w": {"center": "s_w"}}, periodic=False, autoparse_metadata=False
    )
    cum_mass_target = xgrid.transform(
        cum_mass,
        "s_w",
        target=target_depth_edges,
        target_data=depth_w.rename("depth"),
        method="linear",
        mask_edges=True,
    )
    bin_mass = -cum_mass_target.diff("depth")  # cumulative mass decreases with depth
    bin_mass = bin_mass.assign_coords(depth=0.5 * (target_depth_edges[:-1] + target_depth_edges[1:]))

    area = cell_area(grid)
    return (bin_mass * area).sum(dim=["eta_rho", "xi_rho"]) / dz_target


def process(
    grid: Grid, hc: float, exp_dir: Path, date: str, output_file: Path, dz_target: float = 5.0
) -> None:
    if output_file.exists():
        print(f"[SKIP] {output_file} already exists.")
        return

    print(f"[PROCESS] {exp_dir.name} @ {date}...")

    bgc = xr.open_dataset(exp_dir / f"OUTPUT/JOINED/pacmed_bgc.{date}113008.nc").isel(time=0)
    his = xr.open_dataset(exp_dir / f"OUTPUT/JOINED/pacmed_his.{date}113008.nc").isel(time=0)

    delta_dic = bgc.DIC - bgc.DIC_ALT_CO2
    depth_w = compute_depth(his.zeta, grid.ds.h, hc, grid.ds.Cs_w, grid.ds.sigma_w)

    # Fixed-depth bin edges (m, positive down), with a small buffer above z=0 for locations
    # where zeta > 0, and spanning the full water column so no mass is lost off the bottom.
    target_depth_edges = np.arange(-5.0, float(grid.ds.h.max()) + dz_target, dz_target)

    # xgcm's transform turns each column's ~100 s_rho levels into len(target_depth_edges)
    # fixed-depth levels (thousands, for a domain with several-km-deep water), so a chunk
    # that's a comfortable size *before* the transform can be 1-2 orders of magnitude too
    # big *after* it. xarray's "auto" chunking only looks at the pre-transform array and
    # doesn't know about that expansion, which is what OOM'd this job -- so size the chunks
    # ourselves for a bounded post-transform footprint instead.
    max_chunk_bytes = 64 * 1024**2  # ~64 MiB per chunk after the vertical transform
    n_depth = len(target_depth_edges) - 1
    chunk_side = max(1, int(np.sqrt(max_chunk_bytes / (n_depth * 8))))
    chunks = {"eta_rho": chunk_side, "xi_rho": chunk_side}
    delta_dic = delta_dic.chunk(chunks)
    depth_w = depth_w.chunk(chunks)

    inventory = domain_profile_on_depth_grid(grid, delta_dic, depth_w, target_depth_edges, dz_target)

    ds_out = xr.Dataset({"dic_dor": inventory})
    ds_out["depth_dor"] = ds_out["depth"]
    ds_out = ds_out.compute()

    output_file.parent.mkdir(parents=True, exist_ok=True)
    ds_out.to_netcdf(output_file)
    print(f"[DONE] Saved {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute the domain-total vertical DOR dDIC inventory profile.")
    parser.add_argument("--exp", required=True, help="Experiment name (e.g., JP8)")
    parser.add_argument("--date", required=True, help="Release date (YYYYMMDD)")
    args = parser.parse_args()

    exp_dir = Path(f"../exp{args.exp}/")
    grid_file = Path("../../INPUT/pacmed12_grd.nc")
    theta_s, theta_b, hc, N = 6.0, 6.0, 250.0, 100

    print(f"[INFO] Loading grid from {grid_file}")
    grid = Grid.from_file(grid_file, theta_s=theta_s, theta_b=theta_b, hc=hc, N=N)

    output_file = exp_dir / f"OUTPUT/VERTICAL_PROFILE/vertical_profile_{args.date}.nc"
    process(grid, hc, exp_dir, args.date, output_file)


if __name__ == "__main__":
    main()
