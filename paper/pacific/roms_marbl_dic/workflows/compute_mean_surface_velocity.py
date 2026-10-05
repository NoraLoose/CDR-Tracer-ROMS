#!/usr/bin/env python3
"""Precompute the time-mean surface velocity and speed field over years 2000-2001
from the physics-only control run, used by ../../concentration_differences.ipynb.

Interpolates u/v from the top s_rho level onto the rho grid, then saves the
time-mean u, time-mean v, and time-mean speed (mean of the instantaneous
speed, not the speed of the time-mean vector) as a small netCDF file so the
notebook doesn't need to reload all the daily files each time it runs.
"""
import glob
from pathlib import Path
from typing import Sequence

import numpy as np
import xarray as xr
from roms_tools import Grid


def to_rho_u(field):
    """Interpolate a field on xi_u onto xi_rho (edge points reuse the nearest xi_u value)."""
    padded = field.pad(xi_u=(1, 1), mode="edge")
    result = 0.5 * (padded.isel(xi_u=slice(0, -1)) + padded.isel(xi_u=slice(1, None)))
    return result.rename(xi_u="xi_rho")


def to_rho_v(field):
    """Interpolate a field on eta_v onto eta_rho (edge points reuse the nearest eta_v value)."""
    padded = field.pad(eta_v=(1, 1), mode="edge")
    result = 0.5 * (padded.isel(eta_v=slice(0, -1)) + padded.isel(eta_v=slice(1, None)))
    return result.rename(eta_v="eta_rho")


def process(grid: Grid, physics_dir: Path, years: Sequence[str], output_file: Path) -> None:
    if output_file.exists():
        print(f"[SKIP] {output_file} already exists.")
        return

    files = sorted(
        f for year in years for f in glob.glob(str(physics_dir / f"pacmed_his.{year}*.nc"))
    )
    print(f"[PROCESS] Averaging {len(files)} daily snapshots in {', '.join(years)}...")

    ds = xr.open_mfdataset(
        files, preprocess=lambda d: d[["u", "v"]].isel(s_rho=-1), combine="nested", concat_dim="time"
    )

    u_rho = to_rho_u(ds.u)
    v_rho = to_rho_v(ds.v)
    speed = np.sqrt(u_rho**2 + v_rho**2)

    mask = grid.ds.mask_rho
    ds_out = xr.Dataset({
        "u_mean": u_rho.mean(dim="time").where(mask),
        "v_mean": v_rho.mean(dim="time").where(mask),
        "speed_mean": speed.mean(dim="time").where(mask),
    }).compute()

    output_file.parent.mkdir(parents=True, exist_ok=True)
    ds_out.to_netcdf(output_file)
    print(f"[DONE] Saved {output_file}")


def main() -> None:
    grid_file = Path("../../INPUT/pacmed12_grd.nc")
    physics_dir = Path("../expVI8/OUTPUT/JOINED_full/")
    output_file = Path("../expCTRL/MEAN_VELOCITY/mean_surface_velocity.nc")

    print(f"[INFO] Loading grid from {grid_file}")
    grid = Grid.from_file(grid_file, theta_s=6.0, theta_b=6.0, hc=250.0, N=100)

    process(grid, physics_dir, ["2000", "2001"], output_file)


if __name__ == "__main__":
    main()
