# -*- coding: utf-8 -*-
"""
Created on Tue Apr 26 18:30:34 2022
@author: mwooten3

Purpose: To convert atl08 .csv files to .shp via ogr2ogr
    

Process: Iterate input directory and try to convert each .csv to .shp


"""

import os
import glob

def csvToShp(csv, shp, lonField="lon", latField="lat", sEpsg=4326, tEpsg=4326):
    
    if os.path.isfile(shp):
        return
    
    # use -clipsrc global in case lat/lon values are outside bounds (4326 only)
    cmd = 'ogr2ogr -s_srs EPSG:{} -t_srs EPSG:{} '.format(sEpsg, tEpsg) + \
          '-oo X_POSSIBLE_NAMES={}* '.format(lonField)                  + \
          '-oo Y_POSSIBLE_NAMES={}* '.format(latField)                  + \
          '-f "ESRI Shapefile" -clipsrc -180 -90 180 90 {} {}'.format(shp, csv)
    
    print("\n{}".format(cmd))
    os.system(cmd)
    
    return

def main(args):
    
    # no point in not hardcoding right now
    
    inDir =  '/adapt/nobackup/people/mwooten3/3DSI/ATL08_v005/extracted/'
    outDir = '/adapt/nobackup/people/mwooten3/3DSI/ATL08_v005/extracted/_shp/'
    
    inputs = glob.glob(os.path.join(inDir, '*csv'))
    print("Processing {} input .csv files...".format(len(inputs)))
    
    for inCsv in inputs:
        
        outShp = inCsv.replace(inDir, outDir).replace('.csv', '.shp')
        
        csvToShp(inCsv, outShp, lonField="lon_20m", latField="lat_20m")
        
        
    
    return

    
if __name__ == "__main__":
    
    import argparse
    parser = argparse.ArgumentParser()
    
    # Example arguments
    """
    # Example arguments
    parser.add_argument("-eb", "--exampleStr", type=str,
                    help="This is an example string argument", default = "ex") 
    
    parser.add_argument("-eb", "--exampleBool", action='store_true', 
                help="Example boolean arg that becomes True when flag passed") 
    """
    
    args = vars(parser.parse_args())
    
    main(args)
