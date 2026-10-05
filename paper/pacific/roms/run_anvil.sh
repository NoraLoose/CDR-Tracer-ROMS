#!/bin/bash
#SBATCH -A ees250133
#SBATCH --partition=wholenode
#SBATCH --time=48:00:00
#SBATCH --nodes=5
#SBATCH --ntasks-per-node=128
#SBATCH --job-name=roms-run
#SBATCH --output=logs/roms_run_tmp_%j.out
#SBATCH --error=logs/roms_run_tmp_%j.err

export SLURM_CPUS_PER_TASK=1
export SLURM_TRES_PER_TASK=1

set -euo pipefail
source /anvil/projects/x-ees250129/x-nloose/DeficitTracer/.ROMSMARBL_anvil

# ----------------------
# Configuration and Checks
# ----------------------
# Ensure exactly two arguments
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <TARGET_DIR> <dor|oae>"
  exit 1
fi

RUN_NAME="$1"
CODE_TYPE="$2"

PACIFIC_PATH="/anvil/scratch/x-nloose/DeficitTracer/experiments/pacific/"
BASE_PATH="$PACIFIC_PATH/roms/"
TARGET_DIR="$BASE_PATH/$1"

# Print job info
echo "Starting ROMS run in directory: $TARGET_DIR"
echo "Job ID: $SLURM_JOB_ID"
echo "Running on $(hostname) with $(nproc) CPUs"


# Select code and output directories
case "$CODE_TYPE" in
  dor)
    CODE_DIR="code_dor"
    OUTPUT_DIR="OUTPUT_dor"
    ;;
  oae)
    CODE_DIR="code_oae"
    OUTPUT_DIR="OUTPUT_oae"
    ;;
  *)
    echo "ERROR: CODE_TYPE must be 'dor' or 'oae'"
    exit 1
    ;;
esac

mkdir -p "$TARGET_DIR/$OUTPUT_DIR"

# ----------------------
# Environment Setup
# ----------------------

# Copy executable into target dir
cp "$CODE_DIR/roms" "$TARGET_DIR/roms"

# Generate input file inside target dir
sed "s|\$TARGET_DIR|$TARGET_DIR|g; \
     s|\$BASE_PATH|$BASE_PATH|g; \
     s|\$PACIFIC_PATH|$PACIFIC_PATH|g; \
     s|\$OUTPUT_DIR|$OUTPUT_DIR|g" \
     pacmed12km_Y2000-2005.in.template.shortened > "$TARGET_DIR/roms.in"


# ----------------------
# Model Execution
# ----------------------
cd "$TARGET_DIR"

echo "Launching ROMS..."
srun -n 640 ./roms ./roms.in > output.log

# ----------------------
# Move SLURM Logs
# ----------------------

mv "$SLURM_SUBMIT_DIR/roms_run_tmp_${SLURM_JOB_ID}.out" "roms_run_${SLURM_JOB_ID}.out"
mv "$SLURM_SUBMIT_DIR/roms_run_tmp_${SLURM_JOB_ID}.err" "roms_run_${SLURM_JOB_ID}.err"

echo "✅ ROMS run completed. Output written to $TARGET_DIR/output.log"
