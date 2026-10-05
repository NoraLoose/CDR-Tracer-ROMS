#!/bin/bash
#SBATCH -A m4632
#SBATCH -C cpu
#SBATCH -q debug
#SBATCH -t 00:30:00
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --job-name=max_ph
#SBATCH --output=logs/max_ph_%j.out
#SBATCH --error=logs/max_ph_%j.err

module load conda
conda activate deficit-tracer

EXP_NAME=$1

if [ -z "$EXP_NAME" ]; then
    echo "Usage: sbatch compute_max_ph.sh EXP_NAME"
    exit 1
fi

python compute_max_ph.py --exp $EXP_NAME --year 2000
python compute_max_ph.py --exp $EXP_NAME --year 2001
