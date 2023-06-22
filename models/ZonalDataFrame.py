#!/usr/bin/env python
"""
Created on Tue Mar 24 02:03:17 2020
@author: mwooten3

ZonalDataFrame builds and describes a geopandas dataframe of vector 
data for 3DSI ZonalStats v3 given an overlapping raster

Actual dataframe accessed via .data attribute, e.g.:
    
    from ZonalDataFrame import ZonalDataFrame
    zonalGeoDataFrame = ZonalDataFrame(zonalType, extent, extentEpsg).data

Options for zonalType (*=ready, others maybe eventually): 
    ATL08-100m*       (ATL08 v005 100m segments) - ready but no .csv 's
    ATL08-20m*        (ATL08 v005 20m segments)  - ready but only have .csvs in alaska as of now
    ATL08             (ATL08 older version segments) - might never need?
    Disturbance (or terraPulse, standage, etc. TBD)
    GLAS
    Other       (could really be anything just need a method for building)

ZDF class:
    - add methods/attributes like: 
        nRows/Features
        name (pass name, or *base off dir base and extent)

"""

import os

from osgeo import ogr, osr

import geopandas as gpd

from rasterstats import zonal_stats

from models.RasterStats import ZonalStats
from models.FeatureClass import FeatureClass
from models.Raster import Raster

# NOTE: Path to ATL08 v5 .csv files is hardcoded below and may need to be changed

#------------------------------------------------------------------------------
# class ZonalDataFrame
#------------------------------------------------------------------------------
class ZonalDataFrame(object):
    
    # 1/6/23: Making zonal type have na or ea
    VALID_ZONAL_TYPES = ['ATL08-20m', 'ATL08-100m', 'ATL08', 
                                                         'GLAS', 'Disturbance']
    
    # Given some (required and optional) information, build a geodataframe
    #  for 3DSI zonal stats work. Assume extent of lat/lon fields is dd
    # Optionally, pass a gdf already built? but why?
    #--------------------------------------------------------------------------
    # __init__
    #--------------------------------------------------------------------------
    def __init__(self, zonalType, extent, extentEpsg, tmpDir=None, region='na', 
                                                            existingGdf = None):
        
        # First ensure passed zonal name is valid
        if zonalType not in ZonalDataFrame.VALID_ZONAL_TYPES:
            
            raise RuntimeError("{} not a valid zonal type".format(zonalType))
            
        self.zonalType    = zonalType
        self.region       = region
        self.tempDir      = tmpDir

        # 1/6/23: hardcode this depending on zonalType
        # only works for run now (atl08 v5 20m segments)
        if self.zonalType == 'ATL08-20m':
            if self.region == 'na':
                self.zonalDir = '/explore/nobackup/people/pmontesa/userfs02/data/icesat2/atl08.005/boreal_na_20m'
            elif self.region == 'ea':
                self.zonalDir = '/explore/nobackup/people/pmontesa/userfs02/data/icesat2/atl08.005/boreal_ea_20m'

        self.rasterExtent = extent # Extent of the ZDF = raster we are interested in
        self.rasterEpsg   = extentEpsg
        
        # Does it make since to automatically build dataframe upon instantiation?
        # If one is not passed, build it
        if not existingGdf:
            self.data = self.buildZonalDataFrame()
        # If one is passed, check to see if it's GDF
        # This is stupid right? lol who knows
        else:
            if isinstance(existingGdf, gpd.GeoDataFrame):
                self.data = existingGdf
            else:
                raise RuntimeError("existingGdf parameter was passed but is not a geodataframe object")
        
        # Set some attributes from dataframe properties
        # Do this as a method instead because self.data may change
        #self.setFeatureAttributes() - this should happen after every time updating .data
        #and the below (+others) can go in that func
        #self.nFeatures = len(self.data.index)
        #self.columns   = self.data.columns
            
    #--------------------------------------------------------------------------
    # buildZonalDataFrame()
    #  Actually build the ZDF by choosing the appropriate build function
    #  NOTE that these dataframes are points. To get polygons, run zdf.toPolygon()
    #--------------------------------------------------------------------------  
    def buildZonalDataFrame(self):
        
        if self.zonalType == 'ATL08-20m':
            from functions.buildZdf_atl08v5 import buildZdf
            return buildZdf(self.rasterExtent, self.rasterEpsg, self.zonalDir, segLength = 20)
        
        elif self.zonalType == 'ATL08-100m':
            from functions.buildZdf_atl08v5 import buildZdf
            return buildZdf(self.rasterExtent, self.rasterEpsg, self.zonalDir, segLength = 100)
        
        elif self.zonalType == 'Disturbance':
            from functions.buildZdf_disturbance import buildZdf
            return buildZdf(self.rasterExtent, self.rasterEpsg, self.tempDir, 
                                                                    self.region)
         
        else:
            print("Build function for {} does not yet exist.".format(self.zonalType))
            return None

    """
    #--------------------------------------------------------------------------
    # checkResults()
    #  Check number of features after performing a activity and print
    #--------------------------------------------------------------------------
    def checkResults(self, activity):
    
        #* TD get number of features after ZDF class: cdf.nRows/Features
        print("\nnumber Zonal features after {}: {}".format(activity, len(zdf.index)))
    
        if zdf.empty:
            print("\nThere were 0 features after {}. Exiting ({})".format(activity, time.strftime("%m-%d-%y %I:%M:%S")))
            return None
    
        #print(" n features now = {}".format(len(zdf.index)))
        return 'continue'
    """
    
    #--------------------------------------------------------------------------
    # pointsToPolygon()
    #  Convert the point geodataframe to polygons
    #  Method depends on what we are converting
    #--------------------------------------------------------------------------
    def pointsToPolygon(self):
        
        from functions.pointsToPolygons_atl08v5 import pointsToSegments
        
        # keep utm projected gdf for both
        if self.zonalType == 'ATL08-20m':
            gdf = pointsToSegments(self.data, segLength = 20, 
                                                          returnSrcPrj = False)

        elif self.zonalType == 'ATL08-100m':
            gdf = pointsToSegments(self.data, segLength = 100, 
                                                          returnSrcPrj = False)
 
        else:
            print("toPolygon function for {} does not yet exist.".format(self.zonalType))
            return None
        
        self.data = gdf
        
        # Reset other attributes:
        #* TD remove from init
        #self.nFeatures = len(self.data.index)
        #self.columns   = self.data.columns
 
    #--------------------------------------------------------------------------
    # pointStats()
    #  Given a raster, get point stats for each vector feature in ZDF
    #--------------------------------------------------------------------------
    def pointStats(self, raster, layerDict = None):
        
        from RasterStats import PointStats
        
        pointStatsDf = PointStats(self.data, raster, layerDict)
        
        return pointStatsDf

    #--------------------------------------------------------------------------
    # zonalStats()
    #  Given a raster, get zonal stats for each vector feature in ZDF
    #--------------------------------------------------------------------------
    def zonalStats(self, raster, layerDict = None):
        
        zonalStatsDf = ZonalStats(self.data, raster, layerDict)
        
        return zonalStatsDf

    def nFeatures(self):
        
        return len(self.data.index)
    
    def columns(self):
        
        return self.data.columns
      
    #--------------------------------------------------------------------------
    # setName()
    #  Set name attribute of ZDF
    #--------------------------------------------------------------------------           
    def setName(self, name):
        
        self.name = name
        
        
        
        
##############################################################################
############ Older functions from ZonalFeatureClass, keep for now ############
        # prob can delete tho
##############################################################################
        
    #--------------------------------------------------------------------------
    # applyNoDataMask()
    #--------------------------------------------------------------------------    
    def applyNoDataMask(self, mask, transEpsg = None, outShp = None):
        
        # Expecting mask to be 0 and 1, with 1 where we want to remove data
        # This is specific to 3DSI and therefore is not kept in FeatureClass 
        
        # if transformEpsg is supplied, convert points to correct SRS before running ZS
        # if not supplied, will assume projection of mask and ZFC are the same
        
        # Get name output shp: 
        if not outShp:
            outShp = self.filePath.replace(self.extension, '__filtered-ND.shp')
        
        drv = ogr.GetDriverByName("ESRI Shapefile")
        ds = drv.Open(self.filePath, 1)
        layer = ds.GetLayer()
     
        # This will work even if not needed. If needed and not supplied, could fail
        outSrs = osr.SpatialReference()
        if transEpsg:
            outSrs.ImportFromEPSG(int(transEpsg))
        else:
            outSrs.ImportFromEPSG(int(self.epsg())) # If transformation EPSG not supplied, keep coords as is

        # 6/11 New filtering method - Add column to for rows we want to keep
        if 'keep' not in self.fieldNames():
            fldDef = ogr.FieldDefn('keep', ogr.OFTString)
            layer.CreateField(fldDef)
            
        # 10/28: If mask has coarse resolution, use allTouched = True
        allTouched = False
        if Raster(mask).resolution()[0] >= 30:
            allTouched = True

        # 6/11 - just count keep features, do no need FIDs
        #keepFIDs = []
        keepFeat = 0 
        for feature in layer:

            # Get polygon geometry and transform to outSrs just in case
            geom = feature.GetGeometryRef()
            geom.TransformTo(outSrs)

            # Then export to WKT for ZS             
            wktPoly = geom.ExportToIsoWkt()

            # Get info from mask underneath feature
            z = zonal_stats(wktPoly, mask, stats="mean", all_touched = allTouched)
            out = z[0]['mean']            
            if out >= 0.99 or out == None: # If 99% of pixels or more are NoData, skip
                feature.SetField('keep', 'no')
                continue
            
            # 6/11 - Else, set the new keep column to yes to filter later
            feature.SetField('keep', 'yes')
            layer.SetFeature(feature)
            
            #keepFIDs.append(feature.GetFID())
            keepFeat += 1

        # 6/11 - No longer doing filtering this way
        """         
        #if len(keepFIDs) == 0: # If there are no points remaining, return None
            #return None
       
        if len(keepFIDs) == 1: # tuple(listWithOneItem) wont work in Set Filter
            query = "FID = {}".format(keepFIDs[0])
            
        else: # If we have more than 1 item, call getFidQuery
            query = self.getFidQuery(keepFIDs)
        """

        # 6/11 New filtering method
        query = "keep = 'yes'"    
        layer.SetAttributeFilter(query)
        dsOut = drv.CreateDataSource(outShp)
        layerOutName = os.path.basename(outShp).replace('.shp', '')
        layerOut = dsOut.CopyLayer(layer, layerOutName)
        
        if not layerOut: # If CopyLayer failed for whatever reason
            print("Could not remove NoData polygons")
            return self.filePath
        
        ds = layer = dsOut = layerOut = feature = None
        
        # 10/28: Try to remove 'keep' field - 4/26/21 - comment out to keep consistent with NA outputs - 6/17 uncomment out again bc won't be consistent anyways
        fc = FeatureClass(outShp)
        fc.removeField('keep')
        
        return outShp

    #--------------------------------------------------------------------------
    # getFidQuery()
    #  Get the SQL query from a list of FIDs. For large FID sets,
    #  return a query that avoids SQL error from "FID IN (<largeTuple>)"
    #  List of FIDs will be split into chunks separated by OR
    #  6/11 - no longer need this
    #-------------------------------------------------------------------------- 
    def getFidQuery(self, FIDs, maxFeatures = 4800):
        
        nFID = len(FIDs)
        
        if nFID > maxFeatures: # Then we must combine multiple smaller queries
            
            import math
            nIter = int(math.ceil(nFID/float(maxFeatures)))

            query = 'FID IN'
            
            a = 0
            b = maxFeatures # initial bounds for first iter (0, maxFeat)
            
            for i in range(nIter):
                
                if i == nIter-1: # if in the last iteration
                    b = nFID
                    
                queryFIDs = FIDs[a:b]
                query += ' {} OR FID IN'.format(tuple(queryFIDs))
                
                a += maxFeatures # Get bounds for next iteration
                b += maxFeatures
                
            query = query.rstrip(' OR FID IN') 
            
        else:
            query = "FID IN {}".format(tuple(FIDs))    
    
        return query

    #--------------------------------------------------------------------------
    # filterAttributes()
    #--------------------------------------------------------------------------    
    def filterAttributes(self, filterStr, outShp = None):
        
        ogr.UseExceptions() # To catch possible error with filtering
        
        # Get name output shp: 
        if not outShp:
            outShp = self.filePath.replace(self.extension, '__filtered.shp')        
        
        # Get layer and filter the attributes
        drv = ogr.GetDriverByName("ESRI Shapefile")
        ds = drv.Open(self.filePath)
        layer = ds.GetLayer()
        
        try:
            layer.SetAttributeFilter(filterStr)
        except RuntimeError as e:
            print('Could not filter based on string "{}": {}'.format(filterStr, e))
            return self.filePath
        
        # Copy filtered layer to output and save
        drv = ogr.GetDriverByName("ESRI Shapefile")        
        dsOut = drv.CreateDataSource(outShp)
        layerOutName = os.path.basename(outShp).replace('.shp', '')
        layerOut = dsOut.CopyLayer(layer, layerOutName)

        if not layerOut: # If CopyLayer failed for whatever reason
            print('Could not filter based on string "{}"'.format(filterStr))
            return self.filePath
        
        return outShp
        
        