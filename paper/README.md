# Pacific ROMS/MARBL experiments from Loose et al. (in review, JAMES)

This directory is the as-run setup of the 12 km Pacific ROMS experiments in the paper: the
ROMS/MARBL control run, the 24 ROMS/MARBL truth experiments, and the ROMS CDR tracer runs. The
files are copied unchanged from the working repository where the runs were made, so they still
contain the original NERSC (Perlmutter) and Purdue (Anvil) paths. The rest of this repository
(top-level `code_*/` and `workflows/`) is a cleaned-up version of the same method with
placeholder paths. Start there if you want to apply the method, and here if you want to see
exactly how the paper's runs were set up.

The notebooks that turn this output into the paper's figures are in
[CDR-Tracer-Paper](https://github.com/NoraLoose/CDR-Tracer-Paper).

## Model code

| Component | Repository | Commit |
|---|---|---|
| ROMS | [NoraLoose/ucla-roms](https://github.com/NoraLoose/ucla-roms), branch `deficit-tracer-dor-oae` | TODO(Nora): confirm. Branch tip is `f131d2a` (2026-03-17). The executables in the run directories were built on 2025-12-29 and 2026-02-12. |
| MARBL | [NoraLoose/MARBL](https://github.com/NoraLoose/MARBL) | TODO(Nora): confirm `marbl0.45.0` (`6e6b2f7`) or branch `deficit-tracer` (`b7071ca`) |

`deficit-tracer-dor-oae` contains both the CDR tracer code and the full ROMS/MARBL coupling
used for the truth experiments. The method-only branch `cdr-tracers` (see the top-level README)
does not.

The base Pacific configuration (grid `pacmed12_grd.nc`, physical forcing, boundary conditions,
and the spun-up initial state) was not generated in this repository.
TODO(Nora): say where it comes from.

## Layout

```
pacific/
├── make_tracer_surface_flux.ipynb   Gaussian intervention fluxes for the four release locations
├── partition.sh
├── roms/              CDR tracer runs (ROMS physics only, passive CDR tracers)
│   ├── code_dor/, code_oae/         compile-time overrides (cppdefs, tracers, ...)
│   ├── *.in.template*, run*.sh      namelist templates and run scripts
│   └── workflows/                   input generation, β/η forcing, and post-processing
├── roms_marbl_alk/    OAE truth runs (ROMS/MARBL)
│   ├── code/, marbl_*               compile-time overrides and MARBL settings
│   └── workflows/
└── roms_marbl_dic/    DOR truth runs and the control run (ROMS/MARBL)
    ├── code/, marbl_*
    └── workflows/
```

Scripts named `*_anvil.*` are the variants used for runs on Purdue's Anvil; the others are for
NERSC Perlmutter.

## Experiment names

**Truth runs** (`roms_marbl_alk/exp<LOC><AMP>`, OAE; `roms_marbl_dic/exp<LOC><AMP>`, DOR):

| Directory label | Paper label |
|---|---|
| `JP`, `VI`, `BC`, `EC` | J (Japan), V (Vancouver Island), B (Baja California), E (Ecuador) |
| `10`, `7`, `8` | amplitude 10, 100, 1000 (e.g. `JP8` → J1000) |

`roms_marbl_dic/expCTRL` is the control run. The amplitude-1000 OAE truth runs also exist with
a `_perlmutter` suffix (`roms_marbl_alk/exp<LOC>8_perlmutter`), with the matching CDR tracer
output in `roms/exp0/OUTPUT_oae_perlmutter`. The surface-field figures (Figs. 4–6, 8) use these.

**CDR tracer runs** (`roms/exp<N>`, one run per carbonate sensitivity configuration, Table 2 of
the paper). `make_carbonate_sensitivity.ipynb` builds the β/η forcing for each:

| Paper config | Directory | β, η from |
|---|---|---|
| REF | `exp0` | daily ROMS/MARBL control |
| MON | `exp1` | monthly mean of daily β, η |
| MEAN | `exp2` | long-term (2000–2001) mean of daily β, η |
| CESM | `exp3` | CESM/MARBL state |
| CONST | `exp6` | long-term and spatial mean |
| SODA-mon | `exp8` | OceanSODA-ETHZ, monthly |
| SODA-clim | `exp9` | OceanSODA-ETHZ, climatology |

Each CDR tracer run holds all locations and amplitudes as separate tracers. DOR and OAE runs use
`code_dor/` and `code_oae/` respectively and write to `OUTPUT_dor/` and `OUTPUT_oae/`.

## Order of operations

1. **Control run.** Run ROMS/MARBL (`roms_marbl_dic/`, `expCTRL`) with daily output of
   `ALK_ALT_CO2`, `DIC_ALT_CO2`, `TEMP`, `SALT`, `PO4`, `SiO3`.
2. **β, η.** Extract surface fields (`roms_marbl_dic/workflows/extract_surface_ctrl.*`) and
   compute β and η (`compute_carbonate_sensitivity_ctrl.*`, plus the `_from_monthly`/`_from_mean`
   variants for the order-of-operations comparison in the SI). Then build the forcing for each
   configuration with `roms/workflows/make_carbonate_sensitivity.ipynb`.
3. **Intervention forcing.** `make_tracer_surface_flux.ipynb`, then `make_input.ipynb` in each of
   `roms/`, `roms_marbl_alk/`, `roms_marbl_dic/` workflows.
4. **Runs.** Compile in `code*/` and launch with `run.sh` / `run_restart.sh`. Join the per-rank
   output with `workflows/join.*`.
5. **Post-processing** (all in the respective `workflows/`):
   - `integrate_output.*`: domain-integrated CO2 uptake → efficiency curves
   - `compute_carbonate_sensitivity.*`: β, η in the truth runs (Fig. 6)
   - `compute_vertical_profile*`, `compute_mass_footprint.py`: inventory profiles and plume
     footprints (Fig. 4)
   - `compute_pH*`, `compute_max_ph*`: surface pH and its maximum (Fig. 9)
   - `compute_mean_surface_velocity.*`, `compute_mixed_layer_depth_field.*`: control-run
     currents and mixed layer depth (Figs. 4, S13–S15)
   - `compute_typical_state_for_alk_dic_diagram.*`: background state for Fig. 3(a,b)
