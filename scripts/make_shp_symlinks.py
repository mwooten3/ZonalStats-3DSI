# For Dist/SGM rerun with 90th percentile, make symlinks for .shp data
# hard link (ln, no -s)
# nvm cp doesn't work so just move all contents


import glob
import os



shpExts = ['.shp', '.shx', '.prj', '.dbf']
# just mv all the files in temp

# ex file: /explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022/Disturbance/SGM_median/ea/GE01_20120615_1050410000D23D00_1050410000D08100_sr05_4m-sr05-min_1m-sr05-max_dz_eul_warp/_temp/Landsat_disturbances_age.shp

frmDir = '/explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022/Disturbance/SGM_median/?a/*/_temp/*shp'
files = glob.glob(frmDir)
tot = len(files)
c = 0

for frm in files:
    
    c+=1
    print('{}/{}'.format(c, tot))
    # test
    #if 'WV03_20150510_104001000B5CD900_104001000BADC600_sr05_4m-sr05-min_1m-sr05-max_dz_eul_warp' not in frm:
    #    continue
        
    # create dir
    os.system('mkdir -p {}'.format(os.path.dirname(frm).replace('SGM_median', 
                                                                        'SGM')))
    
    for ext in shpExts:
        
        frm2 = frm.replace('.shp', ext)
        
        #import pdb;pdb.set_trace()
        to = frm2.replace('SGM_median', 'SGM')
        
        cmd = 'cp -l {} {}'.format(frm2, to)
        print(cmd)
        os.system(cmd)
    
    print('')