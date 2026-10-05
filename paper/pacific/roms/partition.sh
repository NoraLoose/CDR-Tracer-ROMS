#!/bin/bash

set -euo pipefail

# Usage check
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <target-directory>"
  exit 1
fi

BASE_PATH="/pscratch/sd/n/nloose/DeficitTracer/experiments/pacific/roms"
TARGET_DIR="$BASE_PATH/$1"

NP_XI=40  # From code/param.opt
NP_ETA=16
NP_TOTAL=$((NP_XI * NP_ETA))

# ----------------------
# Partition forcing files
# ----------------------
INPUT_DIR="$TARGET_DIR/INPUT"
mkdir -p "$INPUT_DIR/PARTED"

cd "$INPUT_DIR" || { echo "Directory $INPUT_DIR not found"; exit 1; }

FILES=(
  roms_surf_flux.nc
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
# Partition boundary file and tracer surface flux files
# ----------------------
BRY_DIR="$(dirname "$TARGET_DIR")/INPUT"   # go one level up from target and into INPUT
BRY_FILE="roms_bry_tracers.nc"
BRY_PARTED_DIR="$BRY_DIR/PARTED"

mkdir -p "$BRY_PARTED_DIR"

BRY_FILES=(
  "roms_bry_tracers_1999.nc"
  "roms_bry_tracers_2000.nc"
  "roms_bry_tracers_2021.nc"
  #"roms_tracer_surf_flux_1999.nc"
  #"roms_tracer_surf_flux_2000.nc"
  #"roms_tracer_surf_flux_2021.nc"
  #"pacmed12_riv.nc"
)

for BRY_FILE in "${BRY_FILES[@]}"; do
  BRY_PARTED_PATTERN="$BRY_PARTED_DIR/${BRY_FILE%.*}.*.nc"

  if [ ! -f "$BRY_DIR/$BRY_FILE" ]; then
    echo "Boundary file $BRY_DIR/$BRY_FILE not found. Skipping."
    continue
  fi

  # Check if partitioned files already exist
  if compgen -G "$BRY_PARTED_PATTERN" > /dev/null; then
    echo "$BRY_FILE appears to have already been partitioned. Skipping."
  fi

  if [[ "$BRY_FILE" == "pacmed12_riv.nc" ]]; then
    echo "Special case: duplicating $BRY_FILE into $NP_TOTAL partitions..."
    for i in $(seq -f "%03g" 0 $((NP_TOTAL-1))); do
      cp "$BRY_DIR/$BRY_FILE" "$BRY_PARTED_DIR/${BRY_FILE%.*}.$i.nc"
    done
  else
    echo "Partitioning $BRY_FILE..."
    pushd "$BRY_DIR" > /dev/null
    partit "$NP_XI" "$NP_ETA" "$BRY_FILE"
    mv -v "${BRY_FILE%.*}."*.nc "$BRY_PARTED_DIR/"
    popd > /dev/null
  fi
done

echo "✅ All done. Partitioned files are in $BRY_PARTED_DIR"
