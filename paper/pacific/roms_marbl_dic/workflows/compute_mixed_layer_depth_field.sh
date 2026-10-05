#!/bin/bash
#SBATCH -A m4632
#SBATCH -C cpu
#SBATCH -q regular
#SBATCH -t 24:00:00
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --job-name=mld_field
#SBATCH --output=logs/mld_field_%j.out
#SBATCH --error=logs/mld_field_%j.err

module load conda
conda activate deficit-tracer

python compute_mixed_layer_depth_field.py
