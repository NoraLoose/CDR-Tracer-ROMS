#!/usr/bin/env python3
"""Precompute the depth-integrated (2D) OAE delta-ALK / delta-DIC column-inventory footprints
for one experiment/date, used by ../../concentration_differences.ipynb (mean-speed 90%-mass
contour).

At each (eta_rho, xi_rho), integrates concentration x local layer thickness over the full
water column to get column-inventory densities (mmol/m2): sum_s_rho((ALK - ALK_ALT_CO2) * dz)
and sum_s_rho((DIC - DIC_ALT_CO2) * dz). Saves these 2D fields as a small netCDF file, so the
notebook doesn't need to reload the full daily bgc/his output each time it runs.
"""
import argparse
from pathlib import Path

import xarray as xr
from roms_tools import Grid
from roms_tools.vertical_coordinate import compute_depth


def layer_thickness(grid: Grid, hc: float, zeta: xr.DataArray) -> xr.DataArray:
    """Local layer thickness (m) at each s_rho level, from local zeta."""
    depth_w = compute_depth(zeta, grid.ds.h, hc, grid.ds.Cs_w, grid.ds.sigma_w)
    return (depth_w.isel(s_w=slice(0, -1)) - depth_w.isel(s_w=slice(1, None))).rename(s_w="s_rho")


def process(grid: Grid, hc: float, exp_dir: Path, date: str, output_file: Path) -> None:
    if output_file.exists():
        print(f"[SKIP] {output_file} already exists.")
        return

    print(f"[PROCESS] {exp_dir.name} @ {date}...")

    bgc = xr.open_dataset(exp_dir / f"OUTPUT/JOINED/pacmed_bgc.{date}113008.nc").isel(time=0)
    his = xr.open_dataset(exp_dir / f"OUTPUT/JOINED/pacmed_his.{date}113008.nc").isel(time=0)

    delta_alk = bgc.ALK - bgc.ALK_ALT_CO2
    delta_dic = bgc.DIC - bgc.DIC_ALT_CO2
    dz = layer_thickness(grid, hc, his.zeta)

    ds_out = xr.Dataset({
        "alk_oae": (delta_alk * dz).sum(dim="s_rho"),  # mmol/m2, depth-integrated
        "dic_oae": (delta_dic * dz).sum(dim="s_rho"),  # mmol/m2, depth-integrated
    }).compute()

    output_file.parent.mkdir(parents=True, exist_ok=True)
    ds_out.to_netcdf(output_file)
    print(f"[DONE] Saved {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute the depth-integrated OAE dALK/dDIC column-inventory footprints.")
    parser.add_argument("--exp", required=True, help="Experiment name (e.g., JP8)")
    parser.add_argument("--date", required=True, help="Release date (YYYYMMDD)")
    args = parser.parse_args()

    exp_dir = Path(f"../exp{args.exp}/")
    grid_file = Path("../../INPUT/pacmed12_grd.nc")
    theta_s, theta_b, hc, N = 6.0, 6.0, 250.0, 100

    print(f"[INFO] Loading grid from {grid_file}")
    grid = Grid.from_file(grid_file, theta_s=theta_s, theta_b=theta_b, hc=hc, N=N)

    output_file = exp_dir / f"OUTPUT/MASS_FOOTPRINT/mass_footprint_{args.date}.nc"
    process(grid, hc, exp_dir, args.date, output_file)


if __name__ == "__main__":
    main()
