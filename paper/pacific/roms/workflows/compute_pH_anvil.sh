#!/bin/bash
#SBATCH -A ees250133
#SBATCH --partition=wholenode
#SBATCH --time=48:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --job-name=pH
#SBATCH --output=logs/pH_%j.out
#SBATCH --error=logs/pH_%j.err

# Load modules
module load conda
conda activate deficit-tracer

# Usage: sbatch compute_pH.sh EXP_NAME dor|oae YEAR [YEAR ...]
EXP_NAME=$1
MODE=$2       # dor or oae
shift 2
YEARS=("$@")  # one or more years

if [ -z "$EXP_NAME" ] || [ -z "$MODE" ] || [ ${#YEARS[@]} -eq 0 ]; then
    echo "Usage: sbatch compute_pH.sh EXP_NAME dor|oae YEAR [YEAR ...]"
    exit 1
fi

for YEAR in "${YEARS[@]}"; do
    python compute_pH_anvil.py --exp "$EXP_NAME" --year "$YEAR" --mode "$MODE"
done

