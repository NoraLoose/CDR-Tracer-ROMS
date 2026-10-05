#!/bin/bash
#SBATCH -A m4632
#SBATCH -C cpu
#SBATCH -q debug
#SBATCH -t 00:30:00
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --job-name=vertical_profile
#SBATCH --output=logs/vertical_profile_%j.out
#SBATCH --error=logs/vertical_profile_%j.err

module load conda
conda activate deficit-tracer

python compute_vertical_profile.py --exp JP8 --date 20000201
python compute_vertical_profile.py --exp VI8 --date 20000201
python compute_vertical_profile.py --exp BC8 --date 20000201
python compute_vertical_profile.py --exp EC8 --date 20000201

python compute_vertical_profile.py --exp JP8 --date 20000701
python compute_vertical_profile.py --exp VI8 --date 20000701
python compute_vertical_profile.py --exp BC8 --date 20000701
python compute_vertical_profile.py --exp EC8 --date 20000701

python compute_vertical_profile.py --exp JP8 --date 20001231
python compute_vertical_profile.py --exp VI8 --date 20001231
python compute_vertical_profile.py --exp BC8 --date 20001231
python compute_vertical_profile.py --exp EC8 --date 20001231

python compute_vertical_profile.py --exp JP8 --date 20011231
python compute_vertical_profile.py --exp VI8 --date 20011231
python compute_vertical_profile.py --exp BC8 --date 20011231
python compute_vertical_profile.py --exp EC8 --date 20011231


