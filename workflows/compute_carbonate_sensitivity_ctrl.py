#!/usr/bin/env python3
import argparse
from pathlib import Path
import carbonate
import xarray as xr
from roms_tools import Grid
from sensitivities import CONTROL_DIR

def process_month(grid: Grid, surface_dir: Path, beta_dir: Path, year: str, month: str):
    """Compute carbonate sensitivity for a single month."""
    output_file = beta_dir / f"carbonate_sensitivity_{year}{month}.nc"
    if output_file.exists():
        print(f"[SKIP] {output_file} already exists.")
        return

    print(f"[PROCESS] Computing carbonate sensitivity for {year}-{month}...")

    bgc_path = str(surface_dir / f"pacmed_bgc.{year}{month}*.nc")
    phys_path = str(surface_dir / f"pacmed_his.{year}{month}*.nc")

    ds = carbonate.load_bgc_phys(grid, bgc_path, phys_path)

    beta, eta = carbonate.compute_sensitivities(ds, ds, "ALK_ALT_CO2", "DIC_ALT_CO2")

    ds_carbonate_sensitivity = xr.Dataset(
        {
            "ocean_time": ds["ocean_time"],
            "dDICdCO2": xr.DataArray(
                beta, dims=["time", "eta_rho", "xi_rho"]
            ),
            "dDICdALK": xr.DataArray(
                eta, dims=["time", "eta_rho", "xi_rho"]
            ),
        }
    )
    ds_carbonate_sensitivity.to_netcdf(output_file)
    print(f"[DONE] Saved {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Compute carbonate sensitivity for multiple months.")
    parser.add_argument("--year", required=True, help="Year (YYYY)")
    parser.add_argument("--months", nargs="+", default=[f"{m:02d}" for m in range(1, 13)], help="Months to process")
    parser.add_argument("--exp", default="CTRL", help="Experiment name")
    args = parser.parse_args()

    exp_dir = CONTROL_DIR / f"exp{args.exp}"
    surface_dir = exp_dir / "SURFACE"
    beta_dir = exp_dir / "BETA"
    beta_dir.mkdir(parents=True, exist_ok=True)
    grid_file = exp_dir / "pacmed12_grd.nc"

    print(f"[INFO] Loading grid from {grid_file}")
    grid = Grid.from_file(grid_file, theta_s=6.0, theta_b=6.0, hc=250.0, N=100)

    for month in args.months:
        process_month(grid, surface_dir, beta_dir, args.year, month)

if __name__ == "__main__":
    main()
