from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr
from typing import Dict, Optional

# -------------------------------------------------------------------
# Paths
#
# These point at this project's actual run directories on NERSC storage
# and are examples, not portable defaults - pscratch is purged
# periodically, so treat SCRATCH_BASE as a working location you refresh
# per run, not a permanent reference.
# -------------------------------------------------------------------

BASE_PATH = "/path/to/archive/pacific/"
SCRATCH_BASE = "/path/to/scratch/pacific/roms/"

# Control run: the single ROMS/MARBL run that beta/eta are diagnosed from.
CONTROL_DIR = Path(BASE_PATH) / "roms_marbl_dic"

# -------------------------------------------------------------------
# Utilities
# -------------------------------------------------------------------

def load_time_reference(year: int) -> xr.DataArray:
    """Load canonical ROMS time axis from exp0 forcing."""
    ref_file = Path(SCRATCH_BASE) / f"exp0/INPUT/roms_surf_flux_{year}.nc"
    ds_ref = xr.open_dataset(ref_file)

    if year == 2000:
        return ds_ref["ddic_dco2_time"].isel(itime=slice(1, None))
    return ds_ref["ddic_dco2_time"]


# -------------------------------------------------------------------
# Buffering
# -------------------------------------------------------------------

def add_time_buffer(beta, eta, time, buffer=None, buffer_days=100):
    """
    Add left/right/both buffers to a pair of DataArrays (beta, eta) and the time array.
    This guarantees beta and eta stay aligned along 'itime'.
    """
    if buffer is None:
        return beta, eta, time

    concat_beta = []
    concat_eta = []
    concat_time = []

    # --- left buffer
    if buffer in ["left", "both"]:
        concat_beta.append(beta.isel(itime=0).expand_dims({"itime": 1}))
        concat_eta.append(eta.isel(itime=0).expand_dims({"itime": 1}))
        concat_time.append(xr.DataArray([time.isel(itime=0) - buffer_days], dims="itime"))

    # --- original data
    concat_beta.append(beta)
    concat_eta.append(eta)
    concat_time.append(time)

    # --- right buffer
    if buffer in ["right", "both"]:
        concat_beta.append(beta.isel(itime=-1).expand_dims({"itime": 1}))
        concat_eta.append(eta.isel(itime=-1).expand_dims({"itime": 1}))
        concat_time.append(xr.DataArray([time.isel(itime=-1) + buffer_days], dims="itime"))

    beta_out = xr.concat(concat_beta, dim="itime")
    eta_out = xr.concat(concat_eta, dim="itime")
    time_out = xr.concat(concat_time, dim="itime")

    return beta_out, eta_out, time_out

# -------------------------------------------------------------------
# I/O
# -------------------------------------------------------------------

def write_roms_sensitivities(
    fields: Dict[str, xr.DataArray],
    target_dir: Path,
    year: int,
) -> xr.Dataset:
    """Write multiple sensitivity fields into ROMS forcing file."""

    ds = xr.Dataset(fields)

    # Metadata
    if "ddic_dco2_time" in ds:
        ds["ddic_dco2_time"].attrs.update({
            "long_name": "Time since reference date",
            "unit": "days",
        })
    if "ddic_dco2" in ds:
        ds["ddic_dco2"].attrs.update({
            "long_name": "dDIC/dCO2 carbonate sensitivity",
        })

    if "ddic_dalk" in ds:
        ds["ddic_dalk"].attrs.update({
            "long_name": "dDIC/dALK carbonate sensitivity",
        })

    if "itime" in ds.coords:
        ds = ds.drop_vars("itime") # if not dropped ROMS will get confused
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    out_file = target_dir / f"roms_surf_flux_{year}.nc"
    ds.to_netcdf(out_file)

    return ds


# -------------------------------------------------------------------
# High-level API
# -------------------------------------------------------------------

def create_sensitivity_forcing(
    beta: xr.DataArray,
    eta: xr.DataArray,
    year: int,
    exp: int,
    buffer: str | None = None,
    time: xr.DataArray | None = None,
) -> xr.Dataset:
    """
    beta = dDIC/dCO2
    eta  = dDIC/dALK
    """
    beta = beta.rename("ddic_dco2").fillna(0.0)
    eta  = eta.rename("ddic_dalk").fillna(0.0)

    if time is None:
        time = load_time_reference(year)
    else:
        time = time.rename({"time": "itime"}) if "time" in time.dims else time

    beta, eta, time = add_time_buffer(beta, eta, time, buffer)
    fields = {"ddic_dco2": beta, "ddic_dalk": eta, "ddic_dco2_time": time} # safer to not have ddic_dco2_time as a coordinate
    target_dir = Path(SCRATCH_BASE) / f"exp{exp}/INPUT"
    target_dir.mkdir(parents=True, exist_ok=True)

    return write_roms_sensitivities(fields, target_dir, year)
