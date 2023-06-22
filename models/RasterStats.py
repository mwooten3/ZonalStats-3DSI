# -*- coding: utf-8 -*-
"""
Created on Thu Feb  3 22:41:54 2022
@author: mwooten3

Given a geopandas dataframe, raster, and label/stats dictionary (optional),
    return dataframe with the stats, appended or otherwise


Cribbed RasterStats name from rasterstats package because it's the only name 
    that really makes sense
    - https://github.com/perrygeo/python-rasterstats
    - This code mainly wraps around rasterstats package but does a few extra
      things to return a nice geopandas dataframe rather than dict/etc
    - Also adds some methods/options for writing to .csv/.shp
    - Specific for 3DSI work
    
NOTE:
    layers expects dictionary where key = layerN, value = [layerName, [statsList]]
           if no layerDict is supplied, default is {1: ['1', defaultStats]}
"""
import os

import geopandas as gpd

from rasterstats import zonal_stats, point_query

from models.Raster import Raster

#* TD TO DO
# Add optional arguments dict e.g. allTouched, columnsToKeep, etc.
# more on columnsToKeep: to obtain atl08
    # info we should theoretically be able to join with auxiliary stacks
    #* Dont need to code it like this yet but test the option to pass along
    # keep columns (all - default (including atl08), none - meaning only stat
    # columns and unique ID (default), list - meaning select from ). This will 
    # be appended with newColumns list then used to return df subset w cols

# See https://pythonhosted.org/rasterstats/manual.html#zonal-statistics
DEFAULT_STATS = ['majority', 'mean', 'median' 'min', 'max', 'std']

#VALID_STATS_MODES = ['point', 'zonal']

VALID_RASTER_EXTENSIONS = ['.tif', '.vrt'] # for now

#--------------------------------------------------------------------------
# getDefaultLayerDict
#--------------------------------------------------------------------------
# default layerDict --> {1: ['L1', [defaultStats]], 2: ['L2', [defaultStats]]}
def getDefaultLayerDict(nLayers):
    
    layerDict = {}
    
    for i in range(nLayers):
        layerDict[int(i+1)] = ['L{}'.format(str(i+1)), DEFAULT_STATS]
        
    return layerDict

#--------------------------------------------------------------------------
# checkArgs
#--------------------------------------------------------------------------
def checkArgs(inGdf, inRaster):
    
    if not isinstance(inGdf, gpd.GeoDataFrame):
        raise RuntimeError("First argument must be a geodataframe")
        
    if os.path.splitext(inRaster)[1]  not in VALID_RASTER_EXTENSIONS:
        raise RuntimeError("Raster argument does not have a valid extension")
        
#--------------------------------------------------------------------------
# PointStats()
#  Given a geodataframe with point geometry/other possible attributes
#  and an overlapping raster, return a geodataframe with the raster value
#  for each row in a new column (one column per layer/band of raster)
#--------------------------------------------------------------------------
def PointStats(zonalDf, raster, layerDict = None):
    
    checkArgs(zonalDf, raster)
    
    rasterObj = Raster(raster)
    rasterEpsg = rasterObj.epsg()
    
    # If layerDict is not supplied, make default using number of bands
    if not layerDict:
        layerDict = getDefaultLayerDict(rasterObj.nLayers)
        
    # Convert df to raster projection if need be
    srcGdfEpsg = zonalDf.crs.to_epsg()
    if int(srcGdfEpsg) != int(rasterEpsg):
        print("Converting input zonal df to stack extent (EPSG:{})\n".format(rasterEpsg))
        zonalDf = zonalDf.to_crs(epsg = rasterEpsg)  

    #* TD: We expect the output GDF to be in the same srs as the input. reproject back after
    
    print("Computing point statistics using:")
    print(" Input Raster: {}".format(raster))
    print(" Input Vector: {}".format(zonalDf))
    print("")
    
    outDf = zonalDf.copy() # Make copy for output to prevent pandas slicing error

    # Iterate through layers, run zonal stats and add columns to dataframe 
    # layerDict is now --> key: [layerName, statsString]
    newColumns = [] # For list of new columns added to the dataframe
    for layerN in layerDict:
        
        layerName = layerDict[layerN][0]
        newColumns.append(layerName)

        print("\n Layer/band {} ({})".format(layerN, layerName))
        
        # Compute point stats and add them to dataframe
        # 1/6/23: For whatever reason, if you don't set interpolate to 
        #         nearest, pq will return averages/weird/wrong values
        outDf[layerName] = point_query(zonalDf, raster, band=layerN,
                                         nodata=rasterObj.noDataValue, 
                                                interpolate='nearest')
    
    del zonalDf
   
    # Remove any rows whose columns from the PQ were ALL NaN (IOW don't get rid 
    # of row just because one column/layer was NaN), only if they all are NaN
    outDf = outDf.dropna(how = 'all', subset = newColumns)
    
    # Replace all NaN with our NoData value
    if rasterObj.noDataValue:
        outDf = outDf.fillna(rasterObj.noDataValue)

    # Lastly convert back to initial projection
    if int(srcGdfEpsg) != int(outDf.crs.to_epsg()):
        print("\nConverting input zonal df back to original extent (EPSG:{})\n".format(srcGdfEpsg))
        outDf = outDf.to_crs(epsg = srcGdfEpsg)  
    
    return outDf

#--------------------------------------------------------------------------
# ZonalStats()
#  Given a geodataframe with polygon geometry/other possible attributes
#  and an overlapping raster, return a geodataframe with the raster stats
#  for each row in a new column (one column per band per raster/stat combo)
#--------------------------------------------------------------------------
def ZonalStats(zonalDf, raster, layerDict = None):
    
    checkArgs(zonalDf, raster)
    
    #* TD Argument to determine which columns from input DF to keep
    allTouched = True
    
    rasterObj = Raster(raster)
    rasterEpsg = rasterObj.epsg()
    
    # If layerDict is not supplied, make default using number of bands/default stats
    if not layerDict:
        layerDict = getDefaultLayerDict(rasterObj.nLayers)
    
    # Convert df to raster projection if need be
    srcGdfEpsg = zonalDf.crs.to_epsg()
    if int(srcGdfEpsg) != int(rasterEpsg):
        print("Converting input zonal df to stack extent (EPSG:{})\n".format(rasterEpsg))
        zonalDf = zonalDf.to_crs(epsg = rasterEpsg)    
    
    print("Computing zonal statistics using:")
    print(" Input Raster: {}".format(raster))
    print(" Input Vector: {}".format(zonalDf))
    print("") #* TD print other args/info
    
    outDf = zonalDf.copy() # Make copy for output to ignore pandas slicing error
    
    newColumns = [] # For list of new columns added to the dataframe
    for layerN in layerDict:
        
        layerName = layerDict[layerN][0]

        # If layerDict was created with default or in 3DSI code, this will work.
        # But if layerDict was passed, and there are no stats in layerDict
        try:
            statsList = layerDict[layerN][1]
            
        except IndexError:
            statsList = DEFAULT_STATS
            
        # statsList could just be string, in which case we need to make it a list
        ## putting this here allows flexibility for default stats to be a string
        if isinstance(statsList, str):
            statsList = [statsList]

        print("\n Layer {} ({}): {}".format(layerN, layerName, statsList))

        # try hardcoding NoData val of -99
        zonalStats = zonal_stats(zonalDf, raster, all_touched = allTouched,
                                                   stats=statsList, band=layerN, 
                                                   nodata=rasterObj.noDataValue)
        
        # This returns a list of dictionaries, with a where key = stat and value = layer
        # Iterate through stats and add columns to dataframe
        for stat in statsList:
            
            colName = '{}_{}'.format(layerName, stat)
            newColumns.append(colName)
            
            outDf[colName] = [d[stat] for d in zonalStats]
            
    del zonalDf
    
    # Remove any rows whose columns from the PQ were ALL NaN (IOW don't get rid 
    # of row just because one column/layer was NaN), only if they all are NaN
    outDf = outDf.dropna(how = 'all', subset = newColumns)
    
    # Replace all NaN with our NoData value
    if rasterObj.noDataValue:
        outDf = outDf.fillna(rasterObj.noDataValue)
                                               
    # Lastly convert back to initial projection
    if int(srcGdfEpsg) != int(outDf.crs.to_epsg()):
        print("\nConverting input zonal df back to original extent (EPSG:{})\n".format(srcGdfEpsg))
        outDf = outDf.to_crs(epsg = srcGdfEpsg)  
    
    return outDf
