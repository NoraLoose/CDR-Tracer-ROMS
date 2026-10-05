#!/bin/bash
#SBATCH -A m4632
#SBATCH -C cpu
#SBATCH -q regular
#SBATCH -t 1:00:00
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --job-name=mean_surface_velocity
#SBATCH --output=logs/mean_surface_velocity_%j.out
#SBATCH --error=logs/mean_surface_velocity_%j.err

module load conda
conda activate deficit-tracer

python compute_mean_surface_velocity.py
