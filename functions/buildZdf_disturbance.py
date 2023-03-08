# -*- coding: utf-8 -*-
"""

Given a raster extent and corresponding epsg, build a 
 geodataframe of overlapping DISTURBANCE PATCHES
 
Function uses the Landsat stack footprint file and some conversions to get df

Process:
- Get list of landsat files from footprints given extent
- build vrt of Landsat files
- gdal_calc to remove 0 and 50
- gdal_polygonize to convert to .shp
- return geodataframe of .shp

Process looks a lot different from atl08
 
"""
import os
import time

import pandas as pd
import geopandas as gpd

import numpy as np

from shapely.geometry import box, MultiPolygon

#from functions import calculateElapsedTime
from Raster import Raster 


# filter out RuntimeWarnings, due to geopandas/fiona read file spam
# https://stackoverflow.com/questions/64995369/geopandas-warning-on-read-file
import warnings
warnings.filterwarnings("ignore",category=RuntimeWarning)
from shapely.errors import ShapelyDeprecationWarning
warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning) 

# I think this can be set here, we do not need them outside of using to 
#  build the initial Landsat stack dataframe
# Made footprints .shp of Landsat age year .tif files for ea and na
indexShpDir = '/explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022/_stackFootprints'


# /explore/nobackup/people/pmontesa/userfs02/data/icesat2/atl08.005/boreal_ea_20m

# Given an extent/epsg build a geodataframe of ATL08 shots including attributes
def buildZdf(rasterExtent, rasterEpsg, tmpDir, region='na'):
    
    start = time.time()
    
    # Get index .shp according to region
    indexShp = os.path.join(indexShpDir, 'Landsat_ageYear_{}.shp'.format(region))
    
    # Get polygon extent in a gdf, in source/csv epsg (default 4326)
    extentPoly = getExtentGdf(rasterExtent, rasterEpsg)
    
    
    # Get list of Landsat .tif files overlapping rasterExtent
    # diff in projections taken care of (somewhat, raise err if diff for now)
    #start2 = time.time()
    inputFiles = getZonalIndexList(indexShp, extentPoly)
    # make sure list not empty
    if len(inputFiles) == 0:
        print("\nThere were no Landsat files from {} within stack.".format(indexShp))
        return None        

    start3 = time.time()
    
    # Using list of files, build large geodataframe of input zones
    print("Building gdf with {} inputs from {}".format(len(inputFiles), 
                                                                      indexShp))
    
    # Get disturbance patches within extent from list
    zdf = generateDisturbancePatches(inputFiles, extentPoly, tmpDir)

    # Check if zdf is empty for nice exit
    if len(zdf.index) == 0:
        print("\nThere were no valid shots within stack. Exiting")
        return None
   
    #print("time to make GDF:")
    #print(calculateElapsedTime(start3, time.time()))
    
    print(" Created GDF with {} points for stack".format(len(zdf.index)))
    end = time.time()
    print(" Elapsed time: {}\n".format(calculateElapsedTime(start, end)))
    
    return zdf

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

# From a list of disturbance .tif files, get gdf of valid patches
# Hardcode some stuff
#* This overwrites ? maybe
def generateDisturbancePatches(inputFiles, extentPoly, tmpDir):
    
    ageYearCol = 'ageYear' # to match log file (for polygonize)
    
    # To use -te, convert to crs of first inputFile (utm)
    toCrs = Raster(inputFiles[0]).epsg()
    (xmin, ymin, xmax, ymax) = extentPoly.to_crs(epsg=toCrs).total_bounds
    
    # output filenames
    outVrt = os.path.join(tmpDir, 'Landsat_age.vrt') # 1
    outCalc = os.path.join(tmpDir, 'Landsat_disturbances_age.tif') # 2
    outShp = outCalc.replace('.tif', '.shp') # 3
    
    # Check final output file first - twice but fine
    if os.path.isfile(outShp):
        
        print("\n\t{} already exists".format(outShp))  
        
        return gpd.read_file(outShp)
    
    
    # 1. Build .vrt - cannot name with stack bc stupidity
    # sometimes UTM proj might not be same for all Landsat tiles
    # -tap -tr 10 10 doesn't really add time (outside of creating files), and improves geolocation a ton (see onenote p90)
    if not os.path.isfile(outVrt):
        cmd = 'gdalbuildvrt -tap -tr 10 10 -allow_projection_difference -te {} {} {} {} {} {}'.format(xmin, ymin, xmax, ymax,
                                                outVrt, ' '.join(inputFiles))
        #cmd = 'gdalbuildvrt {} {}'.format(outVrt, ' '.join(inputFiles)) 
        # -te {} {} {} {} -resolution user -tr 30 30 error was te in 4326 not proj. 
        print("\n\tCreating {}".format(outVrt))
        print("\t{}".format(cmd))
        os.system(cmd)     
    else:
        print("\n\t{} already exists".format(outVrt))        
    
    # 2. gdal_calc.py to convert 0 and 50 to NoData 
    ## also specify extent and convert to Byte/255 
    # **might do int16/-99 if zstat issues (uses -99 prob)
    outND = 255 # or -99
    outType = 'Byte' # or 'Int16'
    
    if not os.path.isfile(outCalc):
        cmd = 'gdal_calc.py --quiet --calc="{}*(A==0) + {}*(A==50) + A*((A>0) & (A<50))" -A \
                {} --outfile={} --type={} --NoDataValue={}'.format(outND, outND, 
                                                outVrt, outCalc, outType, outND)
        print("\n\tCreating {}".format(outCalc))
        print("\t{}".format(cmd))
        os.system(cmd)
    else:
        print("\n\t{} already exists".format(outVrt))
        
    # 3. Convert disturbances .tif into .shps
    
    outLyr = os.path.basename(outShp).replace('.shp', '')
    
    if not os.path.isfile(outShp): # likely not needed, if this did anything we'd be having bigger probs
        cmd = 'gdal_polygonize.py -q {} {} {} {}'.format(outCalc, outShp, outLyr, ageYearCol)

        print("\n\tCreating {}".format(outShp))
        print("\t{}".format(cmd))
        os.system(cmd)
    
    else:
        print("\n\t{} already exists".format(outShp))  
    
    
    # Read .shp into gdf
    return gpd.read_file(outShp)


# Given an .csv file with lat/lon fields (EPSG 4326), and an extent or extent 
# polygon/gdf (optional), return a geodataframe with points as geometry
# srcEpsg is the projection of the .csv's lat/lon EPSG
# Copying bbox terminology from gpd.read_file()
def csvToGdf(csv, lonField = 'lon', latField = 'lat', bbox = None, 
                                             srcEpsg = 4326, drop_20m = False):
    
    #import warnings
    #from shapely.errors import ShapelyDeprecationWarning
    #warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning) 
    #start = time.time()
        
    # Read .csv into regular dataframe - 
    # .csv should have a latitude and longitude columns - default is 'lat'/'lon'
    df = pd.read_csv(csv)
    
    #* TD for 20m vs 100m segment stuff: At this point I can drop any 20m 
    #  specific columns and remove duplicates, leaving us with 100m df
    # if drop_20m:
    #    df = get100mDf(df) # remove columns and duplicates to get 100m df
        
    # For whatever reason this was not caught earlier, but occasionally a lat/lon
    # point will be very large/no data? This should be fixed in extraction code,
    # but for now, remove them
    df = df.loc[(df[latField] != 3.402823466385289e+38)]
    
    # Pre-filter to speed things up
    # If bbox is supplied, go ahead and filter geographically on tabular data 
    
    # 1/6/23: This will not really work if stack crosses antimeridian/aka is multipolygon
    if bbox is not None:# and bbox.type[0] == 'Polygon':
        
        # First, project coords to match .csv, if need be
        if bbox.crs.to_epsg() != srcEpsg:
            bbox = bbox.to_crs(epsg = srcEpsg)
            
        # Get bbox extent and pre-filter df
        (xmin, ymin, xmax, ymax) = bbox.total_bounds
        df = df.loc[(df[lonField] >= xmin) & (df[lonField] <= xmax) & 
                    (df[latField] >= ymin) & (df[latField] <= ymax)]


    # This might be empty, just return None
    if df.empty:
        #print("{} empty after pre-filtering".format(csv))
        return None 
    
    geometry = gpd.points_from_xy(np.asarray(df[lonField]), 
                    np.asarray(df[latField]))
    #print(geometry)
    #import pdb; pdb.set_trace()
    
    gdf = gpd.GeoDataFrame(df, geometry = geometry, 
                                                crs = 'EPSG:{}'.format(srcEpsg))
    """
    gdf = gpd.GeoDataFrame(df, geometry = 
            gpd.points_from_xy(np.asarray(df[lonField]), 
                    np.asarray(df[latField])), crs = 'EPSG:{}'.format(srcEpsg))
    """    
    
    # If bbox is supplied, filter again via geopandas to remove rows outside
    # extent that didn't get removed earlier
    if bbox is not None:
        gdf = gpd.overlay(gdf, bbox, how='intersection')
        
    if gdf.empty:
        #print("{} empty after filtering".format(csv))
        return None      

    return gdf


# From an extent and projection, get GDF in Lat/Lon coords
# srcEpsg is the projection of the stack extent representation
# dstEpsg is the projection of the lat/lon fields from .csv files #* (or )
    # Basically, creating a box in gdf using stack extent, then converting to
    # match the geometry of ATL08 points
def getExtentGdf(extent, srcEpsg, dstEpsg = 4326):
    
    # Create shape from extent:
    (xmin, ymin, xmax, ymax) = extent
    extentPoly = gpd.GeoSeries([box(xmin, ymin, xmax, ymax, ccw=True)])

    extentGdf = gpd.GeoDataFrame({'geometry': extentPoly},  
                                             crs='EPSG:{}'.format(srcEpsg))
    
    # Makes sense to reproject shape to lat/lon since ATL08 .csv geometry is lat/lon
    # Not necessary if it's already the same
    if extentGdf.crs.to_epsg() != dstEpsg:
        extentGdf = extentGdf.to_crs(epsg = dstEpsg)
        
    """    
    # 1/6/23: Sometimes a .vrt will cross the antimeridian. If so, need to
    #         make a multipolygon so script won't try to get all icesat shots 
    #         across the boreal. This only works if dstEpsg = 4326 (lat/lon)
    #    Turns out this doesn't really help when passing this to gpd functions
    if abs(float(extentGdf.bounds.maxx) - float(extentGdf.bounds.minx)) > 180:
        return extentGdf
        import pdb; pdb.set_trace()
        print("\nStack crosses anti-meridian. Splitting into multipolygon\n")
        # get polygon portion in Western hemisphere
        poly1 = box(-180, float(extentGdf.bounds.miny), 
                    float(extentGdf.bounds.minx), float(extentGdf.bounds.maxy))      
        # get polygon portion in Eastern hemisphere
        poly2 = box(float(extentGdf.bounds.maxx), float(extentGdf.bounds.miny), 
                    180, float(extentGdf.bounds.maxy))
        
        multipoly = MultiPolygon([poly1, poly2])
        extentGdf = gpd.GeoDataFrame({'geometry': [multipoly]},  
                                             crs='EPSG:{}'.format(dstEpsg))
    """
        
    return extentGdf
    

# From a raster extent and index .shp of Landsat paths, get overlapping Landsat images
# indexShp is in same proj so just keep it like this/hardcoded for now
def getZonalIndexList(indexShp, extentPolyGdf):
    
    # Read index .shp into gdf, using bbox which means no need to intersect
    indexGdf = gpd.read_file(indexShp, bbox=extentPolyGdf)

    # filename is just in location field
    return indexGdf['location'].tolist()


