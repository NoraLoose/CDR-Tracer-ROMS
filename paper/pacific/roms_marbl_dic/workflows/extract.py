import sys
from pathlib import Path
import shutil
import xarray as xr

if len(sys.argv) != 2:
    sys.exit("Usage: extract.py EXP_NAME")

exp_name = sys.argv[1]

# Directories
base_dir = Path("/pscratch/sd/n/nloose/DeficitTracer/experiments/pacific/roms_marbl_dic")
input_dir = base_dir / exp_name / "OUTPUT/JOINED"
output_dir = Path("../") / exp_name / "OUTPUT" / "JOINED"
output_dir.mkdir(parents=True, exist_ok=True)

# Groups
filter_group = "pacmed_his"
copy_groups = ["pacmed_bgc", "pacmed_bgc_dia"]

vars_to_keep = ["zeta", "C_CONSERVED", "ocean_time"]

# ---------------------------------------------------------
# Filter only pacmed_his
# ---------------------------------------------------------
files = sorted(input_dir.glob(f"{filter_group}.*.nc"))
for infile in files:
    outfile = output_dir / infile.name

    if outfile.exists():
        print(f"[SKIP] {outfile} already exists")
        continue

    print(f"[FILTER] {infile} -> {outfile}")
    with xr.open_dataset(infile) as ds:
        keep = [v for v in vars_to_keep if v in ds.variables]
        filtered = ds[keep].load()
        filtered.to_netcdf(outfile)

# ---------------------------------------------------------
# Direct copy for pacmed_bgc and pacmed_bgc_dia
# ---------------------------------------------------------
for group in copy_groups:
    files = sorted(input_dir.glob(f"{group}.*.nc"))

    for infile in files:
        outfile = output_dir / infile.name

        if outfile.exists():
            print(f"[SKIP] {outfile} already exists")
            continue

        print(f"[COPY]  {infile} -> {outfile}")
        shutil.copy2(infile, outfile)

print("[DONE] All files processed.")
