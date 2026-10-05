#!/usr/bin/env python3
"""Precompute the typical (time- and spatial-mean) control-run background state
used by ../../alk-dic-diagram.ipynb.

Loads the same surface fields as compute_carbonate_sensitivity_from_mean_ctrl.py,
takes the time mean, then the spatial mean, and saves the resulting scalar
temperature, salinity, PO4, SiO3, ALK_ALT_CO2, and DIC_ALT_CO2 to a small
netCDF file so the notebook doesn't need to reload the full daily output.

Also saves the time-mean (but not spatially averaged) ALK_ALT_CO2 and
DIC_ALT_CO2 fields, so the notebook can mark the region of ALK-DIC space
actually covered by the Pacific mean state.
"""
from pathlib import Path
import carbonate
import xarray as xr
from roms_tools import Grid


def process(grid: Grid, outputs_dir: Path) -> None:

    output_file = outputs_dir / "../BETA/typical_state_for_alk_dic_diagram.nc"
    if output_file.exists():
        print(f"[SKIP] {output_file} already exists.")
        return

    print("[PROCESS] Computing typical background state...")

    bgc_path = str(outputs_dir / "pacmed_bgc.2000*.nc")
    phys_path = str(outputs_dir / "pacmed_his.2000*.nc")
    ds_2000 = carbonate.load_bgc_phys(grid, bgc_path, phys_path)

    bgc_path = str(outputs_dir / "pacmed_bgc.2001*.nc")
    phys_path = str(outputs_dir / "pacmed_his.2001*.nc")
    ds_2001 = carbonate.load_bgc_phys(grid, bgc_path, phys_path)

    ds = xr.concat([ds_2000, ds_2001], dim="time")

    ds_time_mean = ds.mean(dim="time")
    ds_typical = ds_time_mean.mean(dim=["eta_rho", "xi_rho"])

    output = ds_typical[["temp", "salt", "PO4", "SiO3", "ALK_ALT_CO2", "DIC_ALT_CO2"]]
    output["ALK_ALT_CO2_field"] = ds_time_mean["ALK_ALT_CO2"]
    output["DIC_ALT_CO2_field"] = ds_time_mean["DIC_ALT_CO2"]

    output.to_netcdf(output_file)
    print(f"[DONE] Saved {output_file}")


def main() -> None:

    outputs_dir = Path("../expCTRL/SURFACE/")
    grid_file = Path("../expCTRL/pacmed12_grd.nc")

    print(f"[INFO] Loading grid from {grid_file}")
    grid = Grid.from_file(grid_file, theta_s=6.0, theta_b=6.0, hc=250.0, N=100)

    process(grid, outputs_dir)


if __name__ == "__main__":
    main()
