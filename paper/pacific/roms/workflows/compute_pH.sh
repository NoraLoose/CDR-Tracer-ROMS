#!/bin/bash
#SBATCH -A m4632
#SBATCH -C cpu
#SBATCH -q regular
#SBATCH -t 06:00:00
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --job-name=pH
#SBATCH --output=logs/pH_%A_%a.out
#SBATCH --error=logs/pH_%A_%a.err
#SBATCH --array=0-23

# Load modules
module load conda
conda activate deficit-tracer

# Usage: sbatch compute_pH.sh EXP_NAME dor|oae
EXP_NAME=$1
MODE=$2

if [ -z "$EXP_NAME" ] || [ -z "$MODE" ]; then
    echo "Usage: sbatch compute_pH.sh EXP_NAME dor|oae"
    exit 1
fi

YEARS=(2000 2001)
YEAR=${YEARS[$((SLURM_ARRAY_TASK_ID / 12))]}
MONTH=$(printf "%02d" $(( (SLURM_ARRAY_TASK_ID % 12) + 1 )))

python compute_pH.py --exp "$EXP_NAME" --year "$YEAR" --mode "$MODE" --months "$MONTH"

