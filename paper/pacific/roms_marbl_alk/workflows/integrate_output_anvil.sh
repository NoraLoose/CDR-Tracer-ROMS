#!/bin/bash
#SBATCH -A ees250133
#SBATCH --partition=wholenode
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH -J integrate
#SBATCH -o logs/integrate.%j.out
#SBATCH -e logs/integrate.%j.err

# Load conda module
module load conda
conda activate romstools-test

# The experiment name comes from the first sbatch argument
EXP_NAME=$1

if [ -z "$EXP_NAME" ]; then
    echo "Usage: sbatch extract.slurm EXP_NAME"
    exit 1
fi

# Run the Python script with the experiment name
srun -n 1 python integrate_output.py $EXP_NAME 2000
srun -n 1 python integrate_output.py $EXP_NAME 2001

