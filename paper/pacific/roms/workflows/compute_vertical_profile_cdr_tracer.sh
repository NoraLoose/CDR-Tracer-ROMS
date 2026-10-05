#!/bin/bash
#SBATCH -A m4632
#SBATCH -C cpu
#SBATCH -q debug
#SBATCH -t 00:30:00
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --job-name=vertical_profile_cdr_tracer
#SBATCH --output=logs/vertical_profile_cdr_tracer_%j.out
#SBATCH --error=logs/vertical_profile_cdr_tracer_%j.err

module load conda
conda activate deficit-tracer

for DATE in 20000201 20000701 20001231 20011231; do
    for EXP in JP8 VI8 BC8 EC8; do
        python compute_vertical_profile_cdr_tracer.py --exp $EXP --date $DATE
    done
done
