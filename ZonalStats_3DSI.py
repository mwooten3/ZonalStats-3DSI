# -*- coding: utf-8 -*-
"""
Created on Fri Dec 3 10:53:09 2021
@author: mwooten3

Another redo of Zonal Stats for ATL08 v5, using Geopandas and .h5 files 
rather tham converting .h5 to .csv to .shp and making large .gdb

Call this ZonalStats_v3/ZonalStats_3DSI.py to differentiate from previous iterations of ZS

1/18/23: Attempting to add last minute disturbance-based zonal stats


PROCESS - still TBD:
    - Set some 3DSI-specific variables
    - Build ZonalDataFrame for a zonal type/intersecting raster
    - Peform point or zonal stats using vector zonal data and underlying raster
    - Write results to various outputs

Thoughts:
    - Classes ? Still use RasterStack.py, prob no need for ZFC.py. 
    - New classes?: ATL08 shot (attributes from cols, method convert to polygon); GPD DF?
    
    
Example call for one GLiHT stack:
    python ZonalStats_3DSI.py -r /adapt/nobackup/people/pmontesa/userfs02/projects/3dsi/stacks/zonal_gliht/AK_20180703_Kenai_FHP5/AK_20180703_Kenai_FHP5_stack.vrt 
    -z ATL08-20m -o /adapt/nobackup/people/mwooten3/3DSI/ZonalStats_v3/test-ATL08-20m__GLiHT__ZonalStats.csv
    -mode zonal -log

Results will be appended to bigOutput (.csv, .shp, database*)
And also saved as .csv (or .shp) individually

NOTES (1/6/23 and on):
- does NOT work for 100m segments due to shp file in buildZdf_atl08v5.py
- does NOT work for ea runs due to directory pointed to in buildZdf_atl08v5.py
- to run EA and/or 100m segments, update the directory and shp path respectively

- to use in old way (diff .shp as input - build func for this named zonal type would be simple shp read to gdf)

"""
import os, sys
#import numpy as np
import argparse
import time
#import platform
#from functions import calculateElapsedTime

from osgeo import ogr#gdal, osr#, ogr
#from osgeo.osr import SpatialReference
#from osgeo.osr import CoordinateTransformation

#from RasterStats import RasterStats#PointStats#, ZonalStats

from RasterStack import RasterStack
from ZonalDataFrame import ZonalDataFrame

# RISKY!
#warnings.filterwarnings("ignore",category=RuntimeWarning)

baseDir = '/explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022'
overwrite = False

def calculateElapsedTime(start, end, unit = 'minutes'):
    
    # start and end = time.time()
    
    if unit == 'minutes':
        elapsedTime = round((time.time()-start)/60, 4)
    elif unit == 'hours':
        elapsedTime = round((time.time()-start)/60/60, 4)
    else:
        elapsedTime = round((time.time()-start), 4)  
        unit = 'seconds'
        
    #print("\nEnd: {}\n".format(time.strftime("%m-%d-%y %I:%M:%S %p")))
    #print(" Elapsed time: {} {}\n".format(elapsedTime, unit))
    
    return "{} {}".format(elapsedTime, unit)

# Not sure about this   
#* MOVE ? cant figure out how to make sense of this shit bc say i remove 
# stuff from the df in here, it doesn't mean it will be updated on the zdf object 
def checkZdfResults(zdf, activity):

    #* TD get number of features after ZDF class: cdf.nRows/Features
    print("\nnumber Zonal features after {}: {}".format(activity, len(zdf.index)))

    if zdf.empty:
        print("\nThere were 0 features after {}. Exiting ({})".format(activity, time.strftime("%m-%d-%y %I:%M:%S")))
        return None

    #print(" n features now = {}".format(len(zdf.index)))
    return 'continue'

#* Need a better logging method!
def logOutput(logfile, mode):

    sys.stdout = open(logfile, mode)

    return sys.stdout

#* v3 New layer dict is only number:name as we are only doing PQ or majority here
#   Actually, if we want to do something other than majority/PQ, the stats can 
#   be a third column in key. Otherwise, do majority (or PQ if point mode specified)
def buildLayerDict(stackObject): 

    stackKey = stackObject.stackKey() # could be None if No log
    layerDict = {}
    
    # 1/6/23 make default zonal stat be median because we will only be using zonal stats with SGM stacks (so, not categorical data)
    #defaultZonalStats = ['majority'] # does not have to be list, can be space-delimited string
    defaultZonalStats = ['median']
    
    # If there is no Log, build layerDict like --> {1: ['1', defaultStats]}
    if not stackKey:
        
        nLayers = stackObject.nLayers
        
        for i in range(nLayers):
            layerDict[int(i+1)] = [str(i+1), defaultZonalStats]
    
        return layerDict
  
    # If there is a Log, read stackKey into list
    with open(stackKey, 'r') as sil:
        stackList = [s.strip('\n') for s in sil.readlines()]
    
    # layerDict --> key = layerN, value = [layerName, [statsList]]
    # stackKey should now be just the layerN,layerName
    for layer in stackList: 
        
        layerN    = int(layer.split(',')[0])
        layerName = layer.split(',')[1].strip()
        
        # See if there is a third+ column(s) with a string of stats
        # If not, use default
        try:
            zonalStats = layer.split(',')[2:]
        except IndexError:
            zonalStats = defaultZonalStats
            
        layerDict[layerN] = [layerName, zonalStats]

    return layerDict

def main(args):
    
        # Unpack arguments   
    inRaster   = args['rasterStack']
    #inZonalDir = args['zonalDir'] # or should this be removed/replaced with index shp
    zonalType  = args['zonalType'] # This will be passed as argument to script now
    aggOutput  = args['aggregateOutput']
    logOut     = args['logOutput']
    statsType  = args['statsMode']
    
    #* NEED TO SANITIZE INPUTS

    #region = 'EU' # or NA (default) still TBD about splitting into regions or not
    #if region == 'EU': baseDir = os.path.join(baseDir, 'EU')
    
    ogr.UseExceptions() # Unsure about this, but pretty sure we want errors to cause exceptions
    # "export CPL_LOG=/dev/null" -- to hide warnings, must be set from shell or in bashrc

    # Start clock
    start = time.time()
    
    # Set main directory - this MAY depend on region and statsMode (only the latter for now)
    #* NEW: output could be point stats or zonal stats (for now at least)
    if statsType not in ['point', 'zonal']: 
        print( "Raster stats mode {} not recognized. Exiting".format(statsType))
        return None

    # Stack args/variables
    stack   = RasterStack(inRaster)

    # Get some variables from inputs
    stackExtent = stack.extent()
    stackEpsg   = stack.epsg()
    stackName   = stack.stackName

    # Output directory: baseDir / zonalType (ATL08_na or GLAS_buff30m) --> stackType / <region> / stackName
    outDir    = stack.outDir(os.path.join(baseDir, zonalType))
    
    # Create directory where big aggregate output is supposed to go:
    os.system('mkdir -p {}'.format(os.path.dirname(aggOutput)))

    # Set up stack-specific vars
    stackCsv = os.path.join(outDir, '{}__{}__{}Stats.csv'.format(zonalType, stackName, statsType))
    stackShp = stackCsv.replace('.csv', '.shp') #- done in RasterStats.py
 
    # Start stack-specific log if doing so
    logFile = stackCsv.replace('.csv', '__Log.txt')
    # First, if overwrite is off, check if Log already exists
    if not overwrite:
        if os.path.isfile(logFile):
            print("\tFile {} already exists. Skipping".format(logFile))
            return None
    
    if logOut: 

        sys.stdout = logOutput(logFile, mode = "a")
        sys.stdout.flush()
        
    # 1/6/23: hardcode region var retrieval from raster filepath - now in RasterStack.py    
    # Build the zonal dataframe
    # inZones is the ZonalDataFrame *object*
    # inZones.data is the actual geodataframe
    # 1/6/23: send region to ZDF to tell it where to find ATL08 .csv
    # 
    inZones = ZonalDataFrame(zonalType, stackExtent, stackEpsg, 
                             tmpDir = stack.tempDir(), region=stack.region())

        # inZones will be the ATL08(/GLAS?) geodataframe, not shapefile
    # for now, do everything in here. May eventually move logic to ZDF.py
    # Given a directory of files and an extent/extent srs, build Geopandas DF with attributes
   # inZones = buildZonalDataFrame(zonalType, stackExtent, stackEpsg)
        
    if inZones.data is None:
        print("0 valid shots over stack. Exiting")
        return None # If None, no valid shots over Raster so exit

    # Make name specific for zonalType/stackName combo to assign to ZDF
    # Prob not necessary anymore 
    # Now can access name via zdf.name
    inZones.setName('{}_{}'.format(zonalType, stackName))    
        
    # print some info
    print("BEGIN: {}\n".format(time.strftime("%m-%d-%y %I:%M:%S")))
    print("Input zonal type: {}".format(zonalType))
    print("Input raster stack: {}".format(inRaster))
    print("Output stack .csv: {}".format(stackCsv))
    print("Output aggregate .csv/.shp: {}".format(aggOutput))
    print(" n layers in stack = {}".format(stack.nLayers))
    print(" n zonal features = {}\n".format(inZones.nFeatures())) #* ZDF/inZones.nFeatures only if ZDF stuff happensbefore this block
    
    #* INSERT FILTERING LOGIC HERE?
    #* INSERT NODATA MASKING HERE?? or quicker to skip and mask later
    #* Any filtering/masking/altering of the dataframe should be done in zdf 
    #  where attributes etc of object can be updated 
    
    #* TD Check feature count after filtering/masking

    # Get stack key dictionary    
    layerDict = buildLayerDict(stack) # {layerNumber: [layerName, statString]}

    # Call zonal stats or point query
    #* Pass columns from original dataframe that we want to keep in output
    #* - if Aux, pass All; else, pass None; option to pass a list as well (from atl08)
    if statsType == 'zonal':

        # only convert to polygon for ATL08 - *TD this should actually be in buildZdf prob
        if 'ATL08' in zonalType:
            inZones.pointsToPolygon() # Now inZones.data is gdf with polygons
            
        rasterStatsDf = inZones.zonalStats(stack.filePath, layerDict)
        
    else:
        rasterStatsDf = inZones.pointStats(stack.filePath, layerDict)
        
    #elif statsMode == 'polygon':
        #* We need to convert the points into footprint polygons - see ATL to .shp code
       # rasterStatsDf = ZonalStats(inZones.data, stack.filePath, layerDict)
    print("\nNumber of rows after zonal stats = {}".format(len(rasterStatsDf)))

    #* TD Check feature count after RasterStats
     
    #* ADD ANY OTHER FIELDS AT THIS TIME
    # stackName/Path, others from old code ?
    rasterStatsDf = rasterStatsDf.assign(rasterStack = stack.baseName) # Same value for all rows so we can use assign
    
    #import pdb; pdb.set_trace()
    # 1/18/23: For disturbance Chris wants date in mmddyyy WV03_20150510_1040010
    # ALso add/edit a couple other things
    if zonalType == 'Disturbance':
        
        bname = stack.baseName
        date = '{}{}{}'.format(bname.split('_')[1][4:6], 
                               bname.split('_')[1][6:8], 
                               bname.split('_')[1][0:4]).zfill(8)
        rasterStatsDf = rasterStatsDf.assign(mmddyyyy = date) 
        
        # 1/18/23: Also need to get lat/lon! But in decimal degrees
        # get x then convert to 4326 to avoid warning

        rasterStatsDf["lon"] = rasterStatsDf.centroid.to_crs(4326).x
        rasterStatsDf["lat"] = rasterStatsDf.centroid.to_crs(4326).y
        
        # ADD patch size
        rasterStatsDf['patchSize_m2'] = rasterStatsDf.area.astype(int)
        
        """        # Will add column name change if stats only contains percentile_XX
        if 'CHM_sr05_percentile_90' in rasterStatsDf.columns.to_list():
            rasterStatsDf.rename({'CHM_sr05_percentile_90': 'CHM_sr05_p90'}, 
                                                 inplace = True, axis='columns')"""
        # Replace any column with percentile in it
        for col in rasterStatsDf.columns.to_list():
            if '_percentile_' in col:
                newCol = col.replace('_percentile_', '_p')
                rasterStatsDf.rename({col: newCol}, 
                                                 inplace = True, axis='columns')
    
    # 1/6/23: hardcode conversion of 2 columns to int
    if stack.stackType() == 'Landsat': # just for Landsat stack type
        rasterStatsDf['ageYear'] = rasterStatsDf['ageYear'].round().astype('int')
        rasterStatsDf['ecoreg']  = rasterStatsDf['ecoreg'].round().astype('int')

    # 1/6/23: Do not write geometry column to csv
    useCols = [col for col in rasterStatsDf.columns.tolist() if col != 'geometry']

    # 1/6/23: Go ahead and remove rows where terrapulse data is 0 (nonforest) or nodata (-99 in this case)
    if stack.stackType() == 'Landsat': # only if Landsat stack
        rasterStatsDf = rasterStatsDf[(rasterStatsDf['ageYear'] != 0) & 
                                (rasterStatsDf['ageYear'] != stack.noDataValue)]
    #elif stack.stackType() == 'SGM': # remove no data or already done?
    
    print("\nNumber of rows after removing NoData/non-forest from ageYear = {}".format(len(rasterStatsDf)))
    
    if len(rasterStatsDf) == 0:
        print("  0 rows after more filtering. Exiting")
        return


    # Write output to individual .csv and .shp
    #* TD add overwrite option ? that will only apply to indiv .shp/.csv [check before processing AND before writing in case stack is run on two machines at once eg]
    print("\nWriting {} rows to {}".format(len(rasterStatsDf.index), stackCsv))
    rasterStatsDf.to_csv(stackCsv, columns=useCols, index=False)
    print("\nWriting {} features to {}".format(len(rasterStatsDf.index), stackShp))    
    rasterStatsDf.to_file(filename=stackShp, driver="ESRI Shapefile")

    # Write output to aggregate .csv
    #* TD: 
    #* This might just become separate process to merge all of the .csv files into one
        # where we do like we used to do and write to a node-specific .csv
    #* Consider asking SO for a solution, everything so far does not take into account other hosts 
    #* TD: If aggOutput is .csv, write to csv - default for now; 
    #      if FC, to_file (and choose driver via FeatureClass.py)
    #      if DB, to_postgis (and choose table based on zonal/stack type/etc) https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoDataFrame.to_postgis.html
    #      make function for each output data type 
    #      put functions in ZDF? then can be like if aggOutput.endswith('cdv'): zdf.toCsv(), .toFC(), .toDB() 
    
    # Test file existence; if DNE, write; otherwise, append
    if not os.path.isfile(aggOutput):
        print("\nWriting {} rows to {}".format(len(rasterStatsDf.index), aggOutput))
        rasterStatsDf.to_csv(aggOutput, index=False, columns=useCols)        
    else:
        #* Need to check that columns are the same - so yeah, maybe split the below step up into an append_csv() function or something to add extra checks
        print("\nAppending {} rows to {}".format(len(rasterStatsDf.index), aggOutput))
        rasterStatsDf.to_csv(aggOutput, mode = 'a', index=False, header=False, columns=useCols)
        
        #* For now, don't check for duplicates. After running Alaska subset, time how long it takes to check vs. not (make copy of agg .csv first bc without checking dups it will append and write dups)
        # pd.read_csv('file').append(df).drop_duplicates().to_csv('file') # maybe this should be edited to just read/check uniqueID? might not be any faster tho

    totalTime = calculateElapsedTime(start, time.time())
    
    #* temp - write n rows to .csv so we can check. 1/6/23: Also write stack name and elapsed time
    nRows = len(rasterStatsDf.index)
    with open(aggOutput.replace('.csv', '__checkCount.csv'), 'a') as of:
        of.write('{},{},{}\n'.format(stackName, nRows, totalTime))
        
    print("\nEND: {}\n".format(time.strftime("%m-%d-%y %I:%M:%S")))
    print(" Elapsed time: {}\n".format(totalTime))



    # Filtering GDF:
    # Option for additional attribute filtering
    # ??? Maybe ??? Remove rows with unique IDs that are already in output .csv/db??
    # Convert geometry to EPSG of stack? - may need to wait on polygon step, but likely not

# Zonal Stats:
# If point option: send GDF, stack, and labels/stats dict to PointQuery
# If polygon option: convert points into polygons and send GDF, stack, and labels/stats dict to Zonal Stats
    
# Other possible args: include df attributes, write to .csv/.shp/db?
    
# Return a dataframe from zonal stats
    
# Add any other fields 
    
# Append dataframe to output .csv/db/whatever 
    return
    
    
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--rasterStack", type=str, required=True, help="Input raster stack")
    parser.add_argument("-z", "--zonalType", type=str, required=True, help="Zonal type (ATL08-20m or ATL08-100m for now")
    parser.add_argument("-o", "--aggregateOutput", type=str, required=True, help="Output for all stacks. Must be a .csv file, .gdb/.shp, or database (coming soon)")
    parser.add_argument("-log", "--logOutput", action='store_true', help="Log the output")
    parser.add_argument("-mode", "--statsMode", type=str, required=True, help="'polygon' for zonal stats (default??) or 'point' for point query")
    
    args = vars(parser.parse_args())

    main(args)