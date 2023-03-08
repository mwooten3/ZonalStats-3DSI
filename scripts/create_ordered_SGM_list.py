"""
JK: disregard notes. process is same but we want to RANDOMIZE based on shp size
-- otherwise nodes will be uneven. less cons than below


want to order SGM inputs so that ones with lots of disturbances are last in the
input list, so that they are more likely to be passed to ngaproc201/202 (last in 
                                                        the hardcoded node list)
                                                        
                                                                                                
Given an input text list of SGM disturbance .shp and SGM .tif directory, create 
a list of the SGM .tif files that are in the same order      

# Create SGM shp list outside of script --> just need once

# randomize .shp list with SGM filenames to match SGM files - create outside of script like:
# ls -Sr /explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022/Disturbance/SGM/na/*/_temp/Landsat_disturbances_age.shp | shuf 
# > /explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022/_inputLists/random-ls_SGM-na_shp.txt

"""
import os, glob

# Inputs - change
region = 'ea'

if region == 'na':
    stackDir = '/explore/nobackup/people/pmontesa/userfs02/projects/3dsi/stacks/Out_SGM'
else:
    stackDir = '/explore/nobackup/people/pmontesa/userfs02/projects/3dsi/stacks/Out_EA'    

# should be same
shpList = '/explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022/_inputLists/random-ls_SGM-{}_shp.txt'.format(region)

outList = '/explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022/_inputLists/ls_SGM-{}.txt'.format(region)


#/explore/nobackup/people/pmontesa/userfs02/projects/3dsi/stacks/Out_SGM/*/*_sr05_4m-sr05-min_1m-sr05-max_dz_eul_warp.tif

with open(shpList, 'r') as sl:
    shps = [s.strip() for s in sl.readlines()]
    
# overwite
if os.path.isfile(outList):
    os.remove(outList)
    
for shp in shps:
   # import pdb; pdb.set_trace()

    sgmName = os.path.dirname(shp).split('/')[-2] # get dir before _temp
    
    sgmFile = glob.glob(os.path.join(stackDir, '*', '{}.tif'.format(sgmName)))[0]
    
    with open(outList, 'a') as ol:
        ol.write('{}\n'.format(sgmFile))
    
    

