#!/bin/bash

set -euo pipefail

# Usage check
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <target-directory>"
  exit 1
fi

BASE_PATH="/pscratch/sd/n/nloose/DeficitTracer/experiments/pacific/roms_marbl_dic"
TARGET_DIR="$BASE_PATH/$1"

NP_XI=40  # From code/param.opt
NP_ETA=16

# ----------------------
# Partition forcing files
# ----------------------
INPUT_DIR="$TARGET_DIR/INPUT"
mkdir -p "$INPUT_DIR/PARTED"

cd "$INPUT_DIR" || { echo "Directory $INPUT_DIR not found"; exit 1; }

FILES=(
  roms_frc_bgc_1999.nc
  roms_frc_bgc_2000.nc
  roms_frc_bgc_2021.nc
  roms_tracer_surf_flux_1999.nc
  roms_tracer_surf_flux_2000.nc
  roms_tracer_surf_flux_2021.nc
)

for X in "${FILES[@]}"; do
  PATTERN="PARTED/${X%.nc}.*.nc"

  # Check if any matching file exists
  if compgen -G "$PATTERN" > /dev/null; then
    echo "$X appears to have already been partitioned. Skipping."
    continue
  fi

  echo "Partitioning $X..."
  partit "$NP_XI" "$NP_ETA" "$X"
  mv -v "${X%.nc}".*.nc PARTED/
done

# ----------------------
# Partition boundary file
# ----------------------
BRY_DIR="$(dirname "$TARGET_DIR")/INPUT"   # go one level up from target and into INPUT
BRY_FILE="roms_bry_tracers.nc"
BRY_PARTED_DIR="$BRY_DIR/PARTED"
BRY_PARTED_PATTERN="$BRY_PARTED_DIR/roms_bry_tracers.*.nc"

mkdir -p "$BRY_PARTED_DIR"

if [ ! -f "$BRY_DIR/$BRY_FILE" ]; then
  echo "Boundary file $BRY_DIR/$BRY_FILE not found. Exiting."
  exit 1
fi

# Check if any partitioned file exists in the correct PARTED directory
if compgen -G "$BRY_PARTED_PATTERN" > /dev/null; then
  echo "$BRY_FILE appears to have already been partitioned. Skipping."
else
  echo "Partitioning $BRY_FILE..."
  pushd "$BRY_DIR" > /dev/null
  partit "$NP_XI" "$NP_ETA" "$BRY_FILE"
  mv -v roms_bry_tracers.*.nc "$BRY_PARTED_DIR/"
  popd > /dev/null
fi

echo "✅ All done. Partitioned files are in $BRY_PARTED_DIR"
