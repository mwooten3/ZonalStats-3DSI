# -*- coding: utf-8 -*-
"""

Given a raster extent and corresponding epsg, build a 
 geodataframe of overlapping ATL08 points
 
Function uses the .csv files where ATL08 data was extracted/filtered from .h5,
 and a footprints .shp of the .h5 files
"""
import os
import time
import glob

import pandas as pd
import geopandas as gpd

import numpy as np

from shapely.geometry import box, MultiPolygon

#from functions import calculateElapsedTime

# filter out RuntimeWarnings, due to geopandas/fiona read file spam
# https://stackoverflow.com/questions/64995369/geopandas-warning-on-read-file
import warnings
warnings.filterwarnings("ignore",category=RuntimeWarning)
from shapely.errors import ShapelyDeprecationWarning
warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning) 

# Use scripts/create_atl08_v005_20m_index-footprints.py to create:
indexShp = '/explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022/ATL08/_fileFootprints/ATL08__boreal_all_20m__footprints.shp'

# Given an extent/epsg build a geodataframe of ATL08 shots including attributes
def buildZdf(rasterExtent, rasterEpsg, zonalDir, segLength = 20):
    
    start = time.time()
    
    # Check some inputs:
    if segLength not in [20, 100]:
        raise RuntimeError("Segment length for ATL08 zonal type must be 20 or 100")
    
    # Get polygon extent in a gdf, in source/csv epsg (default 4326)
    extentPoly = getExtentGdf(rasterExtent, rasterEpsg)
    #print("time to make extent polygon gdf:")
    #print(calculateElapsedTime(start, time.time()))

    # Get directory where .csv files are located and set lat/lon field names
    #* As of 05/2022 only 20m segment data has been processed for a small area
    #* REALLY, running the extract/filter code to get separate csv's for 100m 
    #  segments is redundant because that info is alrady contained in 20m
    #  segment files. Instead, can we use the 20m .csv files then just add a
    #  step to drop 20m-specific columns then remove duplicates? Seems easiest
    #  way, but don't bother trying because we may not care about 100m anyways.
    # In any case, be sure the geodataframe uses the 100m segment lat/lon for
    #  the geometry, otherwise pointToPolygons atl08 won't work
    
    if segLength == 20:      
        lonField, latField = 'lon_20m', 'lat_20m'
        drop_20m = False
        
    elif segLength == 100:
        lonField, latField = 'lon', 'lat'     
        drop_20m = True
    
    # Get list of .csv files overlapping rasterExtent
    # .csv files must have lat/lon field - default 4326 but later could 
    # do transformations if need be. Should not need this as this function is
    # specific to ATL08 (v005)
    start2 = time.time()
    inputFiles = getZonalIndexList(indexShp, zonalDir, extentPoly)

    
    # Using list of files, build large geodataframe of input zones
    print("Building gdf with {} inputs in {}".format(len(inputFiles), zonalDir))

    start3 = time.time()
    
    # This assumes input files are .csv with lat/lon            
    try: # this will throw ValueError if all DFs are empty
        zdf = pd.concat(map(lambda inFile: csvToGdf(inFile, bbox=extentPoly,
            lonField = lonField, latField = latField, drop_20m = drop_20m), 
                                                                   inputFiles))
    
    except ValueError:
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
    
    return "{} {}".format(elapsedTime, unit)

  
def getCsvFullPath(bname, zonalDir):    

    # Zonal dir will have either only 20m segment .csv's or only 100m
    search = glob.glob(os.path.join(zonalDir, '{}*.csv'.format(bname)))
    
    if len(search) == 0:
        return 'DNE'
     
    return search[0]

# Given an ATL08 .csv file with lat/lon fields (EPSG 4326), and an extent or  
# extent polygon/gdf (optional), return a geodataframe with points as geometry
# srcEpsg is the projection of the .csv's lat/lon EPSG
def csvToGdf(csv, lonField = 'lon', latField = 'lat', bbox = None, 
                                             srcEpsg = 4326, drop_20m = False):
        
    # Read .csv into regular dataframe - 
    # .csv should have a latitude and longitude columns - default is 'lat'/'lon'
    df = pd.read_csv(csv)
          
    # Occasionally a lat/lon point will be very large/no data.
    # This should be fixed in extraction code, but for now, remove them
    df = df.loc[(df[latField] != 3.402823466385289e+38)]
    
    # Pre-filter to speed things up
    # If bbox is supplied, go ahead and filter geographically on tabular data 
    
    # 1/6/23: This won't throw an error, but just will not really work in the 
    #          rare case that stack extent crosses antimeridian/is multipolygon
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
    
    gdf = gpd.GeoDataFrame(df, geometry = geometry, crs = 'EPSG:{}'.format(srcEpsg))
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
    
# From an index .shp, get list of file basenames and build list of fullpaths to 
# read into big zonal GDF. Also supply extent in GPD dataframe, in epsg:4326 
def getZonalIndexList(indexShp, zonalDir, extentPolyGdf):
    
    # Read index .shp into gdf, using bbox which means no need to intersect
    indexGdf = gpd.read_file(indexShp, bbox=extentPolyGdf)
    
    # ATL_path is now included in .shp as ATL08_path
    return indexGdf.loc[(indexGdf['ATL08_path'] != 'DNE')]['ATL08_path'].tolist()


