#!/usr/bin/env python3
import argparse
from pathlib import Path
import xarray as xr
import PyCO2SYS as pyco2
from roms_tools import Grid, ROMSOutput

def compute_pH(ds: xr.Dataset, delta_ALK=None, delta_DIC=None):
    """Compute pH using PyCO2SYS."""

    ALK_ctrl = ds.ALK_ALT_CO2
    DIC_ctrl = ds.DIC_ALT_CO2

    if delta_ALK is None:
        delta_ALK = 0
    if delta_DIC is None:
        delta_DIC = 0

    ALK_pert = ALK_ctrl + delta_ALK
    DIC_pert = DIC_ctrl + delta_DIC

    kwargs = dict(
        par1_type=1,
        par2_type=2,
        salinity=ds.salt,
        temperature=ds.temp,
        total_silicate=ds.SiO3 * 1000 / 1025,
        total_phosphate=ds.PO4 * 1000 / 1025,
    )

    # perturbed system
    csys_pert = pyco2.sys(
        par1=ALK_pert * 1000 / 1025,
        par2=DIC_pert * 1000 / 1025,
        **kwargs,
    )

    return csys_pert["pH"]

def process_month(mode: str, grid: Grid, outputs_dir: Path, year: str, month: str) -> None:
    """Process a single (year, month) combination and write pH."""

    pH_dir = outputs_dir / "pH/"
    pH_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = pH_dir / f"pH_{year}{month}.nc"
    if output_file.exists():
        print(f"[SKIP] {output_file} already exists.")
        return

    print(f"[PROCESS] Computing pH for {year}-{month}...")

    # Control
    ctrl_dir = "roms_marbl_alk" if mode == "oae" else "roms_marbl_dic"
    roms_output = ROMSOutput(
        grid=grid,
        path=str(outputs_dir / f"../../../{ctrl_dir}/expCTRL/SURFACE/pacmed_bgc.{year}{month}*.nc"),
        use_dask=True,
    )
    phys_output = ROMSOutput(
        grid=grid,
        path=str(outputs_dir / f"../../../{ctrl_dir}/expCTRL/SURFACE/pacmed_his.{year}{month}*.nc"),
        adjust_depth_for_sea_surface_height=True,
        use_dask=True,
    )

    assert (roms_output.ds.ocean_time == phys_output.ds.ocean_time).all()

    # Add physical variables to bgc dataset
    roms_output.ds["temp"] = phys_output.ds["temp"]
    roms_output.ds["salt"] = phys_output.ds["salt"]

    ds_ctrl = roms_output.ds

    spatial_vars = [v for v in ds_ctrl.data_vars if set(ds_ctrl[v].dims) & {"eta_rho", "xi_rho"}]
    for v in spatial_vars:
        ds_ctrl[v] = ds_ctrl[v].where(grid.ds.mask_rho)

    print(ds_ctrl)
    
    ds_ctrl.load()
    
    pH = compute_pH(ds_ctrl)
    
    ds_pH = xr.Dataset(
        {
            "ocean_time": ds_ctrl["ocean_time"],
            "pH_ctrl": xr.DataArray(
                pH, dims=["time", "eta_rho", "xi_rho"]
            ),
        }
    )
    
    # Perturbation
    roms_output = ROMSOutput(
        grid=grid,
        path=str(outputs_dir / f"JOINED/pacmed_his.{year}{month}*.nc"),
        use_dask=True,
    )

    exps = ["VI7", "VI8", "VI10", "BC7", "BC8", "BC10", "EC7", "EC8", "EC10", "JP7", "JP8", "JP10"]
    
    for exp in exps:
        if mode == "dor":
            delta_DIC = - roms_output.ds[f"{exp}_DEFICIT"].isel(s_rho=-1).where(grid.ds.mask_rho)
            delta_ALK = None
        if mode == "oae":
            delta_DIC = - roms_output.ds[f"{exp}_OAE_DEF"].isel(s_rho=-1).where(grid.ds.mask_rho)
            delta_ALK = roms_output.ds[f"{exp}_CONSERVED"].isel(s_rho=-1).where(grid.ds.mask_rho)

        print(delta_DIC)
        print(delta_ALK)
        
        delta_DIC.load()
        if delta_ALK is not None:
            delta_ALK.load()

        pH = compute_pH(ds_ctrl, delta_ALK=delta_ALK, delta_DIC=delta_DIC)
        ds_pH[f"pH_{exp}"] = xr.DataArray(
                pH, dims=["time", "eta_rho", "xi_rho"]
            )
    
    ds_pH.to_netcdf(output_file)
    print(f"[DONE] Saved {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute pH for multiple months."
    )
    parser.add_argument("--year", required=True, help="Year (YYYY)")
    parser.add_argument(
        "--months",
        nargs="+",
        default=[f"{m:02d}" for m in range(1, 13)],
        help="Months to process (e.g., 01 02 03). Default: all months.",
    )
    parser.add_argument(
        "--exp",
        default="CTRL",
        help="Experiment name (default: CTRL)",
    )
    parser.add_argument(
        "--mode",
        default="dor",
        help="Mode or forcing type (oae | dor).",
    )
    args = parser.parse_args()

    year = args.year
    months = args.months
    exp = args.exp
    mode = args.mode

    outputs_dir = Path(f"../exp{exp}/OUTPUT_{mode}/")
    grid_file = Path(f"../../INPUT/pacmed12_grd.nc")

    print(f"[INFO] Loading grid from {grid_file}")
    grid = Grid.from_file(grid_file, theta_s=6.0, theta_b=6.0, hc=250.0, N=100)

    for month in months:
        process_month(mode, grid, outputs_dir, year, month)


if __name__ == "__main__":
    main()
