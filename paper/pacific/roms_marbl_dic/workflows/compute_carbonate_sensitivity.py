#!/usr/bin/env python3
import argparse
from pathlib import Path
import xarray as xr
from roms_tools import Grid
import carbonate

def process_month(grid: Grid, outputs_dir: Path, dir_ctrl: Path, year: str, month: str):
    """Compute carbonate sensitivity for a single month."""
    beta_dir = outputs_dir.parent / "BETA"
    beta_dir.mkdir(parents=True, exist_ok=True)

    output_file = beta_dir / f"carbonate_sensitivity_{year}{month}.nc"
    if output_file.exists():
        print(f"[SKIP] {output_file} already exists.")
        return

    print(f"[PROCESS] Computing carbonate sensitivity for {year}-{month}...")

    # Load experiment dataset
    ds = carbonate.load_bgc_phys(
        grid,
        bgc_path=str(outputs_dir / f"pacmed_bgc.{year}{month}*.nc")
    )

    # Load control dataset (for control variables)
    ds_ctrl = carbonate.load_bgc_phys(
        grid,
        bgc_path=str(dir_ctrl / f"pacmed_bgc.{year}{month}*.nc"),
        phys_path=str(dir_ctrl / f"pacmed_his.{year}{month}*.nc")
    )

    ds = ds.isel(s_rho=-1)
    
    # Compute sensitivities
    beta, eta = carbonate.compute_sensitivities(
        ds,
        ds_ctrl,
        "ALK",
        "DIC",
    )

    # Save output
    ds_carbonate_sensitivity = xr.Dataset(
        {
            "ocean_time": ds["ocean_time"],
            "dDICdCO2": xr.DataArray(beta, dims=["time", "eta_rho", "xi_rho"]),
            "dDICdALK": xr.DataArray(eta, dims=["time", "eta_rho", "xi_rho"]),
        }
    )

    ds_carbonate_sensitivity.to_netcdf(output_file)
    print(f"[DONE] Saved {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Compute carbonate sensitivity for multiple months.")
    parser.add_argument("--year", required=True, help="Year (YYYY)")
    parser.add_argument("--months", nargs="+", default=[f"{m:02d}" for m in range(1, 13)],
                        help="Months to process (e.g., 01 02 03). Default: all months.")
    parser.add_argument("--exp", default="CTRL", help="Experiment name (default: CTRL)")
    args = parser.parse_args()

    dir_ctrl = Path("../expCTRL/SURFACE/")
    outputs_dir = Path(f"../exp{args.exp}/OUTPUT/JOINED/")
    grid_file = Path("../expCTRL/pacmed12_grd.nc")

    print(f"[INFO] Loading grid from {grid_file}")
    grid = Grid.from_file(grid_file, theta_s=6.0, theta_b=6.0, hc=250.0, N=100)

    for month in args.months:
        process_month(grid, outputs_dir, dir_ctrl, args.year, month)


if __name__ == "__main__":
    main()
