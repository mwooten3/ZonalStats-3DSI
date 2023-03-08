# -*- coding: utf-8 -*-
"""
Created on Tue Mar 24 02:03:17 2020
@author: mwooten3

# *NOTE*: This version is specific for Zonal Stats version 3, see HRSI
    directory/repo for v2 (ATL08 v003) version code
    
RasterStack describes a raster geoTIFF or VRT with mutliple layers
Inherits from Raster,
With methods designed specifically for 3DSI Zonal Stats process

RasterStack inherits the following from Raster:
    self.filePath; self.extension; self.baseName; self.baseDir; self.dataset
    self.noDataValue; self.ogrDataType; self.ogrGeotransform; self.ogrProjection
    self.nColumns; self.nRows; self.nLayers   
    
    convertExtent(self, targetEpsg)
    epsg(self)
    extent(self)
    extractBand(self, bandN, outTif = None)
    toArray(self) 
"""

import os

from Raster import Raster

#------------------------------------------------------------------------------
# class RasterStack
#------------------------------------------------------------------------------
class RasterStack(Raster):
    
    #--------------------------------------------------------------------------
    # __init__
    #--------------------------------------------------------------------------
    def __init__(self, filePath):
        
        # Initialize the base class
        super(RasterStack, self).__init__(filePath)
        
        """
        # Check that the file is TIF or VRT            
        if self.extension != '.vrt' and self.extension != '.tif':
            raise RuntimeError('{} is not a VRT or TIF file'.format(filePath))
        """
        
        self.stackName = self.baseName.strip('_stack')  
        self.filePath  = filePath

    #--------------------------------------------------------------------------
    # noDataLayer()
    #--------------------------------------------------------------------------
    def noDataLayer(self):
        
        noDataLayer = self.filePath.replace('stack.vrt', 'mask.tif')
        
        if os.path.isfile(noDataLayer):
            return noDataLayer
        
        else:
            return None
        
    #--------------------------------------------------------------------------
    # outDir()
    #--------------------------------------------------------------------------
    def outDir(self, baseDir):

        # zonalStatsDir --> zonalType --> DSM/LVIS/GLiHT --> stackIdentifier
        # 1/6/23: Adding region
        outDir = os.path.join(baseDir, self.stackType(), self.region(), 
                                                                 self.stackName)
        
        os.system('mkdir -p {}'.format(outDir))
        
        self.outDir = outDir
        
        return outDir
    
    #--------------------------------------------------------------------------
    # tempDir()
    # temp directory (for dis)
    #--------------------------------------------------------------------------
    def tempDir(self):

        tempDir = os.path.join(self.outDir, '_temp')
        
        os.system('mkdir -p {}'.format(tempDir))
        
        return tempDir

    #--------------------------------------------------------------------------
    # region() - for 3DSI work only
    #--------------------------------------------------------------------------
    def region(self):
        
        # each stack will belong to NA or EA. Default is NA as all stacks are
        # in NA. Only Landsat (as of now) might be in EA. Maybe SGM as well
        
        # 1/6/23: hardcode region var retrieval from raster filepath
        region = 'na' # default region is na

        if '/EA/' in self.filePath: # for Landsat
            region = 'ea'

        if 'Out_EA' in self.filePath: # 1/6/23: Temporary, for SGM stacks
            region = 'ea'
            
        return region
        
    #--------------------------------------------------------------------------
    # stackKey() - for 3DSI work only
    #--------------------------------------------------------------------------
    def stackKey(self):
        
        #* TD: possibly this can check supplied 
        # layers file (need to make this input
        # as a flag in main() part of Raster/
        # GeometryStats.main() an/or functions)))
        
        # Old way, Log.txt beside the input .vrt
        #stackKey = self.filePath.replace('.vrt', '_Log.txt')
        
        # New way, one file per stack type 
        keyDir = '/explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022/_stackLayerKeys'
        stackKey = os.path.join(keyDir, '{}_layers.txt'.format(self.stackType()))
        
        if os.path.isfile(stackKey):
            return stackKey
        
        else:
            return None
        
    #--------------------------------------------------------------------------
    # stackType()
    #--------------------------------------------------------------------------
    def stackType(self):
        
        # SGM, LVIS, GLiHT, Landsat, Auxiliary
        # only one updated is GLiHT
        
        if 'Out_SGM' in self.baseDir or 'Out_EA' in self.baseDir: # TEMP UNTIL WILL FIXES STACKDIRs
            return 'SGM'
        
        elif 'zonal_lvis' in self.baseDir:
            return 'LVIS'

        elif 'out_lvis' in self.baseDir:
            return 'LVIS-old' # v2 stack
        
        elif 'zonal_gliht' in self.baseDir:
            return 'GLiHT'
        
        elif 'out_gliht' in self.baseDir: 
            return 'GLiHT-old' # v2 stack
        
        #elif 'zonal_landsat' in self.baseDir:
        # new stacks as of 1/6/23 do not have zonal_landsat in name
        elif 'age_year' in self.baseDir: 
            return 'Landsat'
        
        elif 'zonal_aux' in self.baseDir:
            return 'Auxiliary'
        
        else:
            return None
        
    #--------------------------------------------------------------------------
    # xmlLayer()
    #--------------------------------------------------------------------------
    def xmlLayer(self):
        
        xmlLayer = self.filePath.replace('_stack.vrt', '.xml')
        
        if os.path.isfile(xmlLayer):
            return xmlLayer
        
        else:
            return None    
        
        
