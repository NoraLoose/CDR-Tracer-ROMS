## CDR tracer method for ROMS

This repo is a standalone extraction of the CDR tracer method for ROMS: given
a control run of ROMS coupled to MARBL, it builds everything needed to run
ROMS *alone* with ocean-based CDR interventions (OAE, DOR) carried as passive
tracers, without recoupling to MARBL for every intervention.

The top-level `code_*/` and `workflows/` contain just the pieces needed to set
up and run the CDR tracer method itself. The as-run setup of the Pacific
experiments in Loose et al. (in review, JAMES), including the ROMS/MARBL
truth experiments the method is validated against, is in
[`paper/`](paper/README.md). The figures are made in
[CDR-Tracer-Paper](https://github.com/NoraLoose/CDR-Tracer-Paper), and the
CESM version of the method is in
[CDR-Tracer-CESM](https://github.com/NoraLoose/CDR-Tracer-CESM).

## Source code

Use `ucla-roms`, branch `cdr-tracers`. This branch only contains what's
needed for the CDR tracer method, and should coincide with
https://github.com/CWorthy-ocean/ucla-roms/pull/242 (Dafydd's rehash of the
originally submitted https://github.com/CWorthy-ocean/ucla-roms/pull/209). If
you have trouble with the untested `cdr-tracers` branch or #242, fall back to
branch `deficit-tracer-dor-oae` on NoraLoose's fork (note: that branch also
carries the truth-experiment code, i.e. full ROMS/MARBL coupling).

As usual, there is a `code/` directory that overrides source code at compile
time. Here there are two: `code_dor/` for CDR tracer experiments representing
DOR interventions, `code_oae/` for OAE interventions. The only difference
between them is `tracers.opt`; there's no need to keep them separate, and you
can mix and match DOR/OAE tracer definitions within one `tracers.opt` if you
want both intervention types in a single run.

These top-level `code_*/` directories hold only the four files that encode the
CDR tracer method (`cppdefs.opt`, `param.opt`, `surf_flux.opt`,
`tracers.opt`); everything else (output frequency, forcing file conventions,
build files) is domain-specific and comes from your own setup. The paper's
Pacific runs used `paper/pacific/roms/code_dor/` and `code_oae/`, which
contain these same four files unchanged plus that domain-specific set.

The tracer naming convention in `tracers.opt` is `{LOC}{AMPL}_{KIND}`, e.g.
`VI7_DEFICIT`:
- `LOC`: intervention location (`VI` = Vancouver Island, `BC` = Baja
  California, `EC` = Ecuador, `JP` = Japan)
- `AMPL`: intervention amplitude label (`7`, `8`, `10`, spanning three orders
  of magnitude of total DIC removed / alkalinity added)
- `KIND`: `CONSERVED` (passive, no air-sea exchange - i.e. $c_{\delta\text{ALK}}$
  for OAE, or a no-exchange reference tracer for DOR), `DEFICIT` (DOR's
  $c_{\delta\text{DIC}}$, damped by air-sea gas exchange, no ALK partner), or
  `OAE_DEF` (OAE's $c_{\delta\text{DIC}}$, paired with its `CONSERVED` partner
  via `itrc_alk_pair` so gas exchange is evaluated consistently)

Adding a new location or amplitude means adding tracer entries to
`tracers.opt` (and bumping `nt_passive` in `param.opt`), and making sure the
forcing files built below (`workflows/make_tracer_surface_flux.ipynb`,
`workflows/make_input.ipynb`) produce matching fields.

## Workflow

1. Run a control simulation with ROMS coupled to MARBL. In practice this
   doesn't need to be a dedicated run: MARBL's dual carbonate-chemistry
   capability returns both the perturbed and unperturbed carbonate state
   from a single integration, so any single ROMS/MARBL run can serve as the
   control. It must output daily `ALK_ALT_CO2`, `DIC_ALT_CO2`, `TEMP`,
   `SALT`, `PO4`, `SiO3`.
2. Extract the needed surface fields from the control run's joined output:
   `workflows/extract_surface_ctrl.py` / `.sh`.
3. Compute daily carbonate sensitivities $\beta = \partial\text{DIC}/\partial\text{CO}_2$
   and $\eta = \partial\text{DIC}/\partial\text{ALK}$ offline with `pyCO2SYS`:
   `workflows/carbonate.py` (the sensitivity calculation itself) and
   `workflows/compute_carbonate_sensitivity_ctrl.py` / `.sh` (driver, one
   month at a time).
4. Build the $\beta$/$\eta$ ROMS forcing file from the diagnosed
   sensitivities: `workflows/make_carbonate_sensitivity.ipynb`, backed by
   `workflows/sensitivities.py`.
5. Build the intervention surface-flux forcing (the Gaussian-shaped release
   fields at each location/amplitude that get read in as `S_DIC`/`S_ALK`):
   `workflows/make_tracer_surface_flux.ipynb`.
6. Build the remaining passive-tracer inputs: river forcing without BGC
   tracers (for the physics-only run), the tracer surface-flux forcing
   wrapped into the `CONSERVED`/`DEFICIT`/`OAE_DEF` tracer names ROMS
   expects, and zero-valued lateral boundary conditions (interventions here
   don't reach the domain boundaries): `workflows/make_input.ipynb`.
7. Compile and run ROMS (physics only, no MARBL) with `code_dor/` or
   `code_oae/` on the `cdr-tracers` branch. Since passive tracers don't feed
   back onto the physics, this run's physical trajectory is identical to the
   control by construction.
8. (Optional, offline) Reconstruct the perturbed state from the CDR tracer
   output: `[DIC]^pert = [DIC]^ctrl + c_deltaDIC`,
   `[ALK]^pert = [ALK]^ctrl + c_deltaALK`, using `[DIC]^ctrl`/`[ALK]^ctrl`
   saved from the control run in step 1. Carbonate variables such as pH can
   then be computed from the perturbed state with `pyCO2SYS`.

## Notes on paths

The scripts and notebooks under `workflows/` use placeholder paths
(`/path/to/scratch/...`, `/path/to/archive/...`) standing in for this
project's actual NERSC storage locations - fill in your own run directories
before using them. `/path/to/scratch/...` is meant for a purgeable scratch
filesystem (e.g. NERSC `/pscratch`): treat anything under it as a working
location you refresh per run, not a permanent reference. `/path/to/archive/...`
is meant for a persistent project filesystem (e.g. NERSC `/global/cfs/...`);
anything meant to persist, such as example output for a collaborator to look
at, should live there instead. Any netCDF files copied into this repo directory
for that purpose are covered by `.gitignore` and won't be committed.
