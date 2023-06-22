#! /usr/bin/env python

# -*- coding: utf-8 -*-
"""
Created on Wed Jan 26 18:57:46 2022
@author: mwooten3
"""

# Given a directory with extracted/filtered ATL08 v5 .csv files, create a 
#  .shp that represents the spatial footprints of the .csv files

# PROCESS:
## 1. Run through all .csv files in a given directory (not running in parallel 
##    because these operations should be fast and can't really write to .shp in parallel)
## 2. Get min/max extent for a given .csv file and build extent df
## 3. Write shape from bbox to .shp

# 1/20: Created from extract_filter_atl08_v005.py and edited to just get 
    # min/max extent and save to index .csv file

import h5py
#from osgeo import gdal
import numpy as np
import pandas as pd
import geopandas as gpd
#import subprocess

import os, glob

import argparse

import time
#from datetime import datetime

from shapely.geometry import box, MultiPolygon

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
    print("Elapsed time: {} {}".format(elapsedTime, unit))
    
    return None

# Given an extracted icesat2 .csv file, return a dict with min/max lat/lon and 
#  some other fields:
def get_bbox_from_csv(incsv, latField, lonField):
    
    df = pd.read_csv(incsv)
    
    # These .csv files may have extraneous nodata values (tho i thought we were filtering these? ASK PAUL)
    # Remove these rows
    df = df[(df[latField] >= -90) & (df[latField] <= 90)]
    df = df[(df[lonField] >= -180) & (df[lonField] <= 180)]
    
    try:
        xmin = float(df[lonField].min())
        ymin = float(df[latField].min())
        xmax = float(df[lonField].max())
        ymax = float(df[latField].max())
        
    except KeyError:
        print("   Problem with getting lat or lon field from file {}".format(incsv))
        return None
    
    return {'ATL08_path': incsv, 'ATL08_name': os.path.basename(incsv).strip('.csv'), 
                        'xmin': xmin, 'ymin': ymin, 'xmax': xmax, 'ymax': ymax}  

# Footprinting logic
# All logic associated with converting a dataframe with files and their bbox to a footprints feature class

## helper footprint code:
def createGeometry(row):

    from shapely.geometry import Point
    
    row["geometry"] = Point(row["lon"],row["lat"])
    
    return row


# Get multipolygon list for subset with large xmin/xmax difference. List should be same size
def get_multipoly_list(df, latField, lonField):
    
    mpList = []

    # Iterate the ATL08 files in multipolygon df and read in each files' .csv
    #for atl in df['ATL08_fpath']:
    for row in df.itertuples(index=False):

        #incsv = os.path.join(row.ATL08_fpath, '{}.csv'.format(row.ATL08_fname))
        #atl_df = get_lat_lon_df(fp)
        
        # just read the ATL08_fpath which is the .csv we want in a df
        atl_df = pd.read_csv(row.ATL08_fpath)

        # Split into two dataframes based on difference from stddev - use median, idk why
        sub_df1 = atl_df[(abs(atl_df[lonField] - atl_df[lonField].median())) 
                                                       > atl_df[lonField].std()]
        sub_df2 = atl_df[(abs(atl_df[lonField] - atl_df[lonField].median())) 
                                                      <= atl_df[lonField].std()]
        
        #import pdb;pdb.set_trace()
        
        # For each dataframe, get new min/max extents to create polygons
        poly1 = box(sub_df1[lonField].min(), sub_df1[latField].min(), 
                    sub_df1[lonField].max(), sub_df1[latField].max())
        poly2 = box(sub_df2[lonField].min(), sub_df2[latField].min(), 
                    sub_df2[lonField].max(), sub_df2[latField].max())
        
        mpList.append(MultiPolygon([poly1, poly2]))
        
    return mpList
    
# these two functions are for debugging (specifically for cross-meridian/pole files)
def exportDfToShp(df, outShp):
    
    #points = [Point(row.lon, row.lat) for row in df]
    df = df.apply(createGeometry,axis=1)
    gdf = gpd.GeoDataFrame(df,crs=4326)
    
    gdf.to_file(filename=outShp, driver="ESRI Shapefile")
    
## main footprint code:
def bbox_to_footprints(dfIn, outShp, latField, lonField, 
                                                overwrite=False, debug=False):
    
    print("\nBuilding footprints from bbox dataframe...")
    
    # Read existing output .shp to gdf if it exists
    # Refine input df based on files in gdf
    if os.path.isfile(outShp) and not overwrite:
        
        writeMode = "a" # append .shp not overwrite
        
        gdf = gpd.read_file(outShp) 
        print("\nOutput .shp ({}) has {} existing records and overwrite is off".format(outShp, len(gdf.index)))
        
        if debug: print("\n\tRead .shp into gdf: {}".format(time.strftime("%m-%d-%y %I:%M:%S %p")))
        
        # Get subset of df where the ATL08 filename is not in gdf (shp)
        df = dfIn[~dfIn['ATL08_path'].isin(gdf['ATL08_path'])]
        
        if debug: print("\n\tGot df for new files: {}".format(time.strftime("%m-%d-%y %I:%M:%S %p")))
        
        # free mem
        gdf = None # free mem
        dfIn = None
        
    else: # If it doesn't exist yet, just use entire dfIn 
        
        writeMode = "w"
        
        print("\nCreating output {}".format(outShp))
        df = dfIn.copy()
        dfIn = None       

    # Now check length of df to be sure there are new records:
    if len(df.index) == 0:
        print("\n No new ATL08 files to add to {}".format(outShp))
        return None

    else:
        print("\n Adding {} files to output .shp".format(len(df.index)))
        
    # Now we must deal with ATL08 files that cross the meridian and the poles by creating multipolygons
    # Idea is to build two df's: 1 has the regular polygons in geometry (and uses the box notation below), the other has multipolygons
    # Then they can be merged before building GDF
    diffThresh = 180
    df1 = df.loc[abs(df.xmin-df.xmax) < diffThresh] # keep regular polygons
    df2 = df.loc[abs(df.xmin-df.xmax) >= diffThresh] # try to fix polygons
    if debug: print("\n\tSplit into two dfs: {}".format(time.strftime("%m-%d-%y %I:%M:%S %p")))   
    
    # At this point, we cannot assume that both sub dataframes are non-empty 
    # so we need to test for that. We do know that at least one of them is non-empty though
    
    if len(df1.index) > 0:
        # For 'normal' df: Using the extent columns and box, build a polygon array and gdf
        polys1 = df1.apply(lambda row: box(row.xmin, row.ymin, row.xmax, row.ymax), axis=1)
        gdf1 = gpd.GeoDataFrame(df1, geometry = polys1, crs = 'EPSG:4326')
        if debug: print("\n\tCreated 'normal' gdf: {}".format(time.strftime("%m-%d-%y %I:%M:%S %p"))) 

    if len(df2.index) > 0:        
        # For possibly messed up polys: Call function to get multi polygons, build gdf
        polys2 = get_multipoly_list(df2, latField, lonField)
        gdf2 = gpd.GeoDataFrame(df2, geometry = polys2, crs = 'EPSG:4326')
        if debug: print("\n\tCreated 'mutlipoly' gdf: {}".format(time.strftime("%m-%d-%y %I:%M:%S %p"))) 
    
    # Then combine into one gdf, or create a copy if one subdf is empty
    if len(df1.index) > 0 and len(df2.index) > 0:
        gdf = pd.concat([gdf1, gdf2])
    elif len(df1.index) == 0: # remember only one subdf should be empty at a time
        gdf = gdf2.copy() # Output gdf is from df2 subset if df1 was empty
    elif len(df2.index) == 0: # these should be the only three cases
        gdf = gdf1.copy() # Output gdf is from df1 subset
        
    if debug: print("\n\tCombined into one gdf: {}".format(time.strftime("%m-%d-%y %I:%M:%S %p"))) 
    
    # Save to .shp - need to append mode if file was already there and we skipped already processed files
    gdf.to_file(filename=outShp, driver="ESRI Shapefile", mode=writeMode)
    print("\nWrote to .shp {} (Added {} features)".format(outShp, len(gdf.index))) 
    
    print("\nEnd: {}\n".format(time.strftime("%m-%d-%y %I:%M:%S %p")))
    
    return None
    
def create_atl08_index(args):

    print("\nBegin: {}\n".format(time.strftime("%m-%d-%y %I:%M:%S %p")))

    # Start clock
    start = time.time()
    
    #TEST = args.TEST
    
    indir = args.input
    outfc = args.output
    
    latField = args.latField
    lonField = args.lonField
    
    debug = False # just adding extra print statements
    overwrite = False # Not the right way but force overwrite tobe False for this
    
    #print("\nATL08 granule name: \t{}".format(Name))
    #print("Input dir: \t\t{}".format(inDir))

    # DONT DO THIS. If output file exists, it will be taken care of in footprinting
    #if os.path.isfile(outfc) and not overwrite: # File exists and we are not overwriting
        #print("{} exists so we are appending (no guarantee there won't be duplicates)".format(outCsv))
     #   return None # Do nothing
    
    #* NOTE: we expect .csv files to be structured like <indir>/<yyyy>/*csv
    incsvs = glob.glob(os.path.join(indir, '*', 'ATL08*.csv'))
    print("Footprinting {} .csv files (example file: {})".format(len(incsvs), 
                                                                     incsvs[0]))
    print( "Output feature class: {}\n".format(outfc))
    
    # From a list of input csvs, get extent index dataframe
    # This will replace reading extentIndex.csv into df like old footprint method
    # Create df where each file in list is a row with min/max lat and lon
    print("Extracting min/max lat and lon using fields {} & {}".format(latField, 
                                                                      lonField))
    bbox_df = pd.DataFrame(map(lambda f: 
                              get_bbox_from_csv(f, latField, lonField), incsvs))
    
    #* Now continue with footprints logic in a separate function
    bbox_to_footprints(bbox_df, outfc, latField, lonField, overwrite, debug=True)
    

    calculateElapsedTime(start, time.time(), 'seconds')
    
    
def main():                               

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type=str, 
                         help="Specify the input directory with the .csv files")
    parser.add_argument("-o", "--output", type=str, 
                                        help="Specify the output feature class")
    parser.add_argument("-lat", "--latField", type=str, default='lat',
                 help="Specify the field to use for latitude (default = 'lat')")
    parser.add_argument("-lon", "--lonField", type=str, default='lon',
                 help="Specify the field to use for longitude (default = 'lon')")

    args = parser.parse_args()
        
    create_atl08_index(args)

if __name__ == "__main__":
    main()
