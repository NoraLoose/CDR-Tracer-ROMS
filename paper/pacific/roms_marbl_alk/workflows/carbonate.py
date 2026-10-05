import xarray as xr
import PyCO2SYS as pyco2
from roms_tools import Grid, ROMSOutput
from pathlib import Path
from typing import Tuple

def load_bgc_phys(grid: Grid, bgc_path: str, phys_path: str = None) -> xr.Dataset:
    """Load BGC dataset and optionally add physical variables."""
    roms_output = ROMSOutput(grid=grid, path=bgc_path, use_dask=True)
    ds = roms_output.ds

    if phys_path is not None:
        phys_output = ROMSOutput(
            grid=grid,
            path=phys_path,
            adjust_depth_for_sea_surface_height=True,
            use_dask=True,
        )
        assert (ds.ocean_time == phys_output.ds.ocean_time).all()
        ds["temp"] = phys_output.ds["temp"]
        ds["salt"] = phys_output.ds["salt"]

    # Mask spatial variables
    mask = grid.ds.mask_rho
    spatial_vars = [v for v in ds.data_vars if set(ds[v].dims) & {"eta_rho", "xi_rho"}]
    for v in spatial_vars:
        ds[v] = ds[v].where(mask)

    # Load all relevant variables into memory
    for var in ["ALK_ALT_CO2", "DIC_ALT_CO2", "salt", "temp", "PO4", "SiO3"]:
        if var in ds:
            ds[var].load()

    return ds



def compute_sensitivities(
    ds: xr.Dataset,
    ds_ctrl: xr.Dataset,
    alk_varname: str,
    dic_varname: str,
) -> Tuple[xr.DataArray, xr.DataArray]:
    """
    Compute carbonate sensitivities using PyCO2SYS.

    beta = dDIC / dCO2
    eta  = dDIC / dALK

    Assumes `ds` contains only surface variables
    (e.g., ds = ds.isel(s_rho=-1)).

    Parameters
    ----------
    ds : xr.Dataset
        Dataset containing surface ALK and DIC.
    ds_ctrl : xr.Dataset
        Control dataset providing salt, temperature, PO4, SiO3.
    alk_varname : str
        Name of alkalinity variable in `ds`.
    dic_varname : str
        Name of DIC variable in `ds`.

    Returns
    -------
    beta : xr.DataArray
        dDIC / dCO2 sensitivity.
    eta : xr.DataArray
        dDIC / dALK sensitivity.
    """
    required_ctrl_vars = ("salt", "temp", "PO4", "SiO3")
    for var in required_ctrl_vars:
        if var not in ds_ctrl:
            raise KeyError(f"`ds_ctrl` is missing required variable '{var}'")

    if alk_varname not in ds or dic_varname not in ds:
        raise KeyError("ALK or DIC variable not found in `ds`")

    rho_factor = 1000.0 / 1025.0  # mmol/m3 → µmol/kg

    ALK = ds[alk_varname] * rho_factor
    DIC = ds[dic_varname] * rho_factor

    csys = pyco2.sys(
        par1=ALK,
        par2=DIC,
        par1_type=1,
        par2_type=2,
        salinity=ds_ctrl.salt,
        temperature=ds_ctrl.temp,
        total_silicate=ds_ctrl.SiO3 * rho_factor,
        total_phosphate=ds_ctrl.PO4 * rho_factor,
    )

    iso_q = csys["isocapnic_quotient"]

    beta = (
        csys["dic"]
        - (csys["HCO3"] + 2.0 * csys["CO3"]) / iso_q
    ) / csys["CO2"]

    eta = 1.0 / iso_q

    return beta, eta
