from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr
from typing import Dict, Tuple, Optional

# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------

import os, socket
_host = socket.gethostname()
if "nersc" in _host or "perlmutter" in _host or os.path.exists("/global/cfs/projectdirs"):
    BASE_PATH = "/global/cfs/projectdirs/m4746/Users/nora/DeficitTracer/experiments/pacific/"
    SCRATCH_BASE = "/pscratch/sd/n/nloose/DeficitTracer/experiments/pacific/roms/"
else:  # Anvil
    BASE_PATH = "/anvil/projects/x-ees250129/x-nloose/DeficitTracer/experiments/pacific/"
    SCRATCH_BASE = "/anvil/scratch/x-nloose/DeficitTracer/experiments/pacific/roms/"

# -------------------------------------------------------------------
# Utilities
# -------------------------------------------------------------------

def get_base_dir(ref: str) -> Path:
    if ref == "alk":
        return Path(BASE_PATH) / "roms_marbl_alk"
    elif ref == "dic":
        return Path(BASE_PATH) / "roms_marbl_dic"
    else:
        raise ValueError("ref must be 'alk' or 'dic'")

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
# Sensitivity Builders
# -------------------------------------------------------------------

def mid_month_days(year: int) -> np.ndarray:
    """Return days since 2000-01-01 for the exact midpoint of each month in the given year."""
    origin = pd.Timestamp("1995-01-01")
    days = []
    for m in range(1, 13):
        start = pd.Timestamp(f"{year}-{m:02d}-01")
        end = pd.Timestamp(f"{year}-{m+1:02d}-01") if m < 12 else pd.Timestamp(f"{year+1}-01-01")
        mid = start + (end - start) / 2
        days.append((mid - origin).total_seconds() / 86400)
    return np.array(days, dtype=float)


def build_constant(field: xr.DataArray, year: int) -> xr.DataArray:
    """Repeat constant spatial field daily."""
    daily_time = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    return xr.DataArray(
        np.stack([field.values for _ in daily_time]),
        dims=["itime", "eta_rho", "xi_rho"],
        name=field.name,
    )


# -------------------------------------------------------------------
# External-data helpers (CESM, OceanSODA → ROMS grid)
# -------------------------------------------------------------------

def lateral_fill_vars(ds, spatial_dims, iter_dim=None):
    """Lateral-fill dDICdCO2 and dDICdALK over land.

    Creates ddic_dco2 and ddic_dalk in *ds* (originals kept for plotting).

    Parameters
    ----------
    spatial_dims : tuple of str
        e.g. ("nlat", "nlon") for CESM or ("lat", "lon") for OceanSODA.
    iter_dim : str or None
        If None the mask is taken from the first slice (time-invariant, CESM).
        If given (e.g. "time", "month") a fresh mask is built per slice
        (time-varying, OceanSODA).
    """
    from roms_tools.fill import LateralFill

    pairs = [("dDICdCO2", "ddic_dco2"), ("dDICdALK", "ddic_dalk")]

    if iter_dim is None:
        first = {d: 0 for d in ds[pairs[0][0]].dims if d not in spatial_dims}
        mask = xr.where(ds[pairs[0][0]].isel(first).isnull(), 0, 1)
        fill = LateralFill(mask, dims=spatial_dims)
        for src, dst in pairs:
            ds[dst] = fill.apply(ds[src]).fillna(0.0)
    else:
        for src, dst in pairs:
            filled = []
            for idx in ds[iter_dim]:
                slc = ds[src].sel({iter_dim: idx})
                mask = xr.where(slc.isnull(), 0, 1)
                fill = LateralFill(mask, dims=spatial_dims)
                filled.append(fill.apply(slc).fillna(0.0))
            ds[dst] = xr.concat(filled, dim=iter_dim)

    return ds


def regrid_to_roms(ds, ds_target=None):
    """Bilinear regrid onto the ROMS target grid."""
    import xesmf

    if ds_target is None:
        ds_target = xr.open_dataset(Path(BASE_PATH) / "INPUT" / "pacmed12_grd.nc")
        ds_target = ds_target.rename({"lat_rho": "lat", "lon_rho": "lon"})

    regridder = xesmf.Regridder(
        ds, ds_target, "bilinear",
        unmapped_to_nan=False, periodic=True, reuse_weights=False,
    )
    return regridder(ds, keep_attrs=True)


def expand_climatology(ds, years, month_dim="month"):
    """Tile a monthly climatology to mid-month dates for *years*."""
    times = []
    month_indices = []
    for year in years:
        for m in range(1, 13):
            start = pd.Timestamp(f"{year}-{m:02d}-01")
            end = (pd.Timestamp(f"{year}-{m+1:02d}-01") if m < 12
                   else pd.Timestamp(f"{year+1}-01-01"))
            times.append(start + (end - start) / 2)
            month_indices.append(m)

    ds_out = ds.sel({month_dim: xr.DataArray(month_indices, dims="time")})
    ds_out["time"] = pd.DatetimeIndex(times)
    return ds_out


def save_per_year(ds, exp, years, time_dim="time"):
    """Add ddic_dco2_time (days since 1995-01-01) and write per-year files."""
    origin = np.datetime64("1995-01-01")
    ds["ddic_dco2_time"] = xr.DataArray(
        (ds[time_dim] - origin) / np.timedelta64(1, "D"),
        dims=[time_dim],
    )
    for year in years:
        ds_year = ds.sel({time_dim: str(year)}).drop_vars(time_dim)
        if "month" in ds_year:
            ds_year = ds_year.drop_vars("month")

        target_dir = Path(SCRATCH_BASE) / f"exp{exp}/INPUT"
        target_dir.mkdir(parents=True, exist_ok=True)
        ds_year.to_netcdf(target_dir / f"roms_surf_flux_{year}.nc")


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



