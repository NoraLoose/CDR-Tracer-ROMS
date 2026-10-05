import sys
from pathlib import Path
import xarray as xr

if len(sys.argv) != 2:
    sys.exit("Usage: extract.py EXP_NAME")

exp_name = sys.argv[1]

# Directories
base_dir = Path("/pscratch/sd/n/nloose/DeficitTracer/experiments/pacific/roms_marbl_dic")
input_dir = base_dir / exp_name / "OUTPUT/JOINED"
output_dir = Path("../") / "expCTRL/SURFACE/"
output_dir.mkdir(exist_ok=True)

groups = ["pacmed_bgc", "pacmed_his"]
vars_to_keep = ["temp", "salt", "ALK_ALT_CO2", "DIC_ALT_CO2", "PO4", "SiO3", "ocean_time"]

for group in groups:
    # Collect all joined NetCDF files for this group
    files = sorted(input_dir.glob(f"{group}.*.nc"))

    for infile in files:
        outfile = output_dir / infile.name
        if outfile.exists():
            print(f"[SKIP] {outfile} already exists")
            continue

        print(f"[FILTER] {infile} -> {outfile}")
        with xr.open_dataset(infile) as ds:
            keep_vars = [v for v in vars_to_keep if v in ds.variables]
            filtered = ds[keep_vars].isel(s_rho=-1).load()  # ensure data is in memory before writing
            filtered.to_netcdf(outfile)

print("[DONE] All files filtered.")

