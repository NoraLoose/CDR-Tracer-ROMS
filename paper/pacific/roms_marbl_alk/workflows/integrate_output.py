#!/usr/bin/env python3
"""
Integrate ROMS biogeochemical (BGC) output files vertically and horizontally.

This script computes domain-integrated quantities (e.g., deltaDIC, C_CONSERVED)
for each month and writes them to NetCDF files.
"""

import sys
from pathlib import Path
import xarray as xr
from dask.diagnostics import ProgressBar
from roms_tools import Grid, ROMSOutput


def integrate_output(exp: str, year: str, month: str) -> None:
    """
    Integrate BGC output for a given experiment, year, and month.

    Parameters
    ----------
    exp : str
        Experiment name or ID (e.g., "SS2")
    year : str
        Year of data (e.g., "2000")
    month : str
        Month of data (e.g., "01")
    """
    grid_file = Path("../../INPUT/pacmed12_grd.nc")
    grid = Grid.from_file(grid_file, theta_s=6.0, theta_b=6.0, hc=250.0, N=100)

    input_dir = Path(f"../exp{exp}/OUTPUT/JOINED")
    output_dir = Path(f"../exp{exp}/OUTPUT/INTEGRATED")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"integrated.{year}{month}.nc"
    if output_file.exists():
        print(f"[SKIP] {output_file} already exists")
        return
    else:
        print(f"[PROCESS] Creating {output_file}")

    # Load datasets
    roms_output = ROMSOutput(
        grid=grid,
        path=str(input_dir / f"pacmed_bgc.{year}{month}*.nc"),
        use_dask=True
    )
    phys_output = ROMSOutput(
        grid=grid,
        path=str(input_dir / f"pacmed_his.{year}{month}*.nc"),
        use_dask=True
    )

    # Ensure time alignment
    if not (roms_output.ds.ocean_time == phys_output.ds.ocean_time).all():
        raise ValueError("Mismatch between BGC and physics ocean_time arrays")

    # Compute layer thickness h_rho
    phys_output._get_depth_coordinates(depth_type="interface", locations=["rho"])
    roms_output.ds["h_rho"] = (
        -phys_output.ds_depth_coords["interface_depth_rho"]
        .diff("s_w")
        .rename({"s_w": "s_rho"})
    )

    # Bring in conserved carbon tracer
    roms_output.ds["C_CONSERVED"] = phys_output.ds["C_CONSERVED"]

    # Compute cell area
    area = 1 / grid.ds.pm / grid.ds.pn

    ds = roms_output.ds
    ds_integrated = xr.Dataset()

    with ProgressBar():
        # Integrate ∆DIC (difference between DIC and DIC_ALT_CO2)
        ds_integrated["deltaDIC"] = (
            ((ds.DIC - ds.DIC_ALT_CO2) * ds["h_rho"] * area)
            .sum(dim=["s_rho", "eta_rho", "xi_rho"])
            .compute()
        )

        # Integrate conserved carbon
        ds_integrated["c_conserved"] = (
            (ds["C_CONSERVED"] * ds["h_rho"] * area)
            .sum(dim=["s_rho", "eta_rho", "xi_rho"])
            .compute()
        )

    ds_integrated.to_netcdf(output_file)
    print(f"[DONE] Saved {output_file}")


def main():
    """
    Command-line interface for integrating multiple months.

    Usage:
        python integrate_output_bgc.py EXP YEAR [MONTH1 MONTH2 ...]

    Example:
        python integrate_output_bgc.py SS2 2000 01 02 03
        python integrate_output_bgc.py SS2 2000        # all months
    """
    if len(sys.argv) < 3:
        sys.exit("Usage: python integrate_output_bgc.py EXP YEAR [MONTH1 MONTH2 ...]")

    exp = sys.argv[1]
    year = sys.argv[2]
    months = sys.argv[3:] or [f"{m:02d}" for m in range(1, 13)]

    for month in months:
        integrate_output(exp, year, month)


if __name__ == "__main__":
    main()

