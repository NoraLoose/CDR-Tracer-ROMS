NP_XI=40; # from code/param.opt
NP_ETA=16;

cd INPUT/
mkdir PARTED/
for X in {\
roms_bry_2012.nc,roms_bry_bgc.nc,roms_frc.201112.nc,\
roms_frc_2012??.nc,roms_frc_bgc.nc,roms_grd.nc,\
rst.20120103120000.nc};do

    if [ -e PARTED/"${X/.nc}".0.nc ];then
        echo "INPUT/${X} appears to have already been partitioned. Continuing."
        continue
    else
    partit "${NP_XI}" "${NP_ETA}" "${X}";
    mv -v "${X/.nc}".?.nc PARTED/
    fi
done
cd ..
