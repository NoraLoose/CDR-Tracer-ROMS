#!/bin/bash
#SBATCH -A m4632
#SBATCH -C cpu
#SBATCH -q regular
#SBATCH -t 2:00:00
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --job-name=typical_state_alk_dic
#SBATCH --output=logs/typical_state_alk_dic_%j.out
#SBATCH --error=logs/typical_state_alk_dic_%j.err

# Load modules
module load conda
conda activate deficit-tracer

python compute_typical_state_for_alk_dic_diagram.py
