#!/bin/bash
#SBATCH -A m4632
#SBATCH -C cpu
#SBATCH -q regular
#SBATCH -t 04:00:00
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --job-name=max_ph_cdr
#SBATCH --output=logs/max_ph_cdr_%j.out
#SBATCH --error=logs/max_ph_cdr_%j.err

module load conda
conda activate deficit-tracer

# Usage: sbatch compute_max_ph_cdr_tracer.sh [EXP] [MODE] [YEAR ...]
EXP=${1:-0}
MODE=${2:-dor}
shift 2 2>/dev/null || shift $#
YEARS=("$@")
if [ ${#YEARS[@]} -eq 0 ]; then
    YEARS=(2000 2001)
fi

for YEAR in "${YEARS[@]}"; do
    python compute_max_ph_cdr_tracer.py --exp "$EXP" --mode "$MODE" --year "$YEAR"
done
