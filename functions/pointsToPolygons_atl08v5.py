# -*- coding: utf-8 -*-
"""
pointsToSegments(gdf, segWidth=11, segLength=100, returnSrcPrj = True):
  Given a pandas geodataframe with ATL08 point geometry, return 
   a geodataframe with polygons representing the ATL08 segments
  
  segWidth/length: default is for 100m segments (11m x 100m); supply segLength 
   if points in gdf came from 20m or 30m atl08 centroids
   
  returnSrcPrj: default is to return the dataframe in the native projection,
   set False to return the geodataframe in local UTM projection

* Couple notes:
* Input has to have more than one icesat shot (from the same track), otherwise 
   ground direction cannot be calculated
 
* Also note that as of now this should only be used for a group of ATL08 shots
   that are within/near the same UTM zone. Functions rely on UTM/meter 
   projection for calculations
"""

import os

import numpy as np
#import pandas as pd

#from osgeo import ogr, osr
#from osgeo.osr import SpatialReference
#from osgeo.osr import CoordinateTransformation

#from concurrent.futures import ProcessPoolExecutor#, ThreadPoolExecutor
#from multiprocessing import Pool, cpu_count
#from itertools import repeat

###############################################################################
# new funcs for using geodataframe

# Convert point gdf to gdf with IS2 segment polygons
def pointsToSegments(gdf, segWidth = 11, segLength = 100, returnSrcPrj = True):
    
    # calculategrounddirection() fails if there is only one footprint in df
    if len(gdf.index) <= 1:
        raise RuntimeError("\n Input df {} has fewer than two rows. Exiting")
        return None
    
    # Convert gdf to UTM, but first store native proj
    if returnSrcPrj: 
        srcEpsg = gdf.crs.to_epsg()
    gdf = gdfToUtm(gdf)
    
    # Now with UTM, we can use Eric Guenther's code to do calculations...

    # test write input to shp
    #gdf.to_file('test/point-test.shp')  

    # Generate list of degrees - need lists for this function   
    xx = np.asarray(gdf.geometry.x)
    yy = np.asarray(gdf.geometry.y)
    dd = calculategrounddirection(xx,yy)

    # Make polygons from calcs and store in new column in gdf
    gdf['polyGeom'] = list(map(lambda d, x, y: \
                        getPolyGeom(d, x, y, segWidth, segLength), dd, xx, yy))

    # try to speed things up?
    """
    nWorkers = cpu_count()
    # concurrent.futures way too slow for small job (see notes)
    #with ThreadPoolExecutor(max_workers=nWorkers) as executor:
    #with ProcessPoolExecutor(max_workers=nWorkers) as executor:
    #    gdf['polyGeom'] = list(executor.map(lambda d, x, y: \
    #                   getPolyGeom(d, x, y, segWidth, segLength), dd, xx, yy))
    
    # try multiprocessing
    # multiple inputs does not work with pool.map()
    # this works but is only slightly faster if geodataframe contains at least 
    # a certain number of points, which for now we should never have
    params = zip(dd, xx, yy, repeat(segWidth), repeat(segLength))
    with Pool(processes = nWorkers) as pool:
        gdf['polyGeom'] = list(pool.starmap(getPolyGeom, iterable = params))
    """
    
    gdf.set_geometry('polyGeom', inplace = True)
    gdf.drop('geometry', axis=1, inplace = True) # gpd doesn't like two geom cols  
    
    # test write input to shp
    #gdf.to_file('test/poly-test.shp')

    # Convert back to native CRS
    if returnSrcPrj:
        return gdf.to_crs(epsg = srcEpsg)
    
    return gdf
    
def gdfToUtm(gdf):
   
    # Be lazy and just get UTM zone that overlaps entire gdf the most for now
    #* Change this for for dataframes that span large areas
    try:
        return gdf.to_crs(epsg = gdf.estimate_utm_crs().to_epsg())
        
    except (AttributeError, RuntimeError) as e:
        print('update pyproj! ({})'.format(e))
        utmEpsg = getUtmEpsg(gdf.total_bounds)
        return gdf.to_crs(epsg = utmEpsg)
    

    
# Given meter coords, deg. of rotation, and length/width, return Polygon object
def getPolyGeom(deg, x, y, width=11, length=20):
    
    from shapely.geometry import Point, Polygon
    
    #xul, yul, xur, yur, xll, yll, xlr, ylr  = \
    #                                calculatecorners(deg, x, y, width, length)
    coords = calculatecorners(deg, x, y, width, length)
    
    return Polygon([Point(i,j) for i,j in coords])
    
"""
scripts from code in paul's HRSI
Part I: Functions to convert a list of UTM points into ICESat2 polygons
# GLAM, Applied Research Laboratories at the University of Texas
# @author: Eric Guenther

    Notes:

    # Example: White Sands Missle Range, WGS/UTM Zone 13
#    easting = np.array([370674.2846469 ,
#       370664.88296774,
#       370655.48708123,])
#    
#    northing = np.array([3640352.68651837,
#       3640452.21808673,
#       3640552.17262566,])
    
    # 2. Reproject ATL08 points to UTM Easting and Northings then run this
    createshapefiles(easting, northing, 14, 100, utmEpsg, "atl08_example.shp")
"""

# calculateangle - Eric
def calculateangle(x1,x2,y1,y2):
    if (x2 - x1) == 0:
        slope = np.inf
    else:
        slope = (y2 - y1)/(x2 - x1)
    degree = np.rad2deg(np.arctan(slope))
    
    return degree

# calculategrounddirection - Eric
def calculategrounddirection(xx,yy):
    degree = np.zeros(len(xx))
    for i in range(0,len(xx)):
        if i == 0:
            degree[i] = calculateangle(xx[i], xx[i+1], yy[i], yy[i+1])
        elif i == (len(xx))-1:
            degree[i]  = calculateangle(xx[i-1], xx[i], yy[i-1], yy[i])
        else:
            degree[i]  = calculateangle(xx[i-1], xx[i+1], yy[i-1], yy[i+1])
    return degree
    
# rotatepoint - Eric
def rotatepoint(degree,xpos,ypos):
    angle = np.deg2rad(degree)
    xrot = (xpos * np.cos(angle)) - (ypos * np.sin(angle)) 
    yrot = (xpos * np.sin(angle)) + (ypos * np.cos(angle))
    return xrot, yrot

# calculatecorners - Eric
def calculatecorners(degree,xcenter,ycenter,width,height):
    # Set corner values

    xul = -width / 2
    yul = height / 2
    xur = width / 2
    yur = height / 2
    xll = -width / 2
    yll = -height / 2
    xlr = width / 2
    ylr = -height / 2
    
    # Rotate based on the angle degree
    xul, yul = rotatepoint((degree-90),xul,yul)
    xur, yur = rotatepoint((degree-90),xur,yur)
    xll, yll = rotatepoint((degree-90),xll,yll)
    xlr, ylr = rotatepoint((degree-90),xlr,ylr)
    
    # Add corner values to centeroid
    xul = xcenter + xul
    yul = ycenter + yul
    xur = xcenter + xur
    yur = ycenter + yur
    xll = xcenter + xll
    yll = ycenter + yll
    xlr = xcenter + xlr
    ylr = ycenter + ylr
    
    # return as list of tuples instead for gpd
    #return xul, yul, xur, yur, xll, yll, xlr, ylr
    return [(xul, yul), (xur, yur), (xlr, ylr), (xll, yll)]

   
"""
# createshapefiles - from Eric, with minor additions MW
def createshapefiles(width, height, epsg, attributes, outfile):
    
    xx = np.asarray(attributes.utmLon)
    yy = np.asarray(attributes.utmLat)
    
    # Generate list of degrees
    degreelist = calculategrounddirection(xx,yy)
    
    # Define Esri Shapefile output
    driver = ogr.GetDriverByName('Esri Shapefile')
    
    # Name output shape file (foo.shp)
    ds = driver.CreateDataSource(outfile)
    
    # Define spatial reference based on EPSG code 
    # https://spatialreference.org/ref/epsg/
    srs = ogr.osr.SpatialReference()
    srs.ImportFromEPSG(epsg)
    
    # Create file with srs
    layer = ds.CreateLayer('', srs, ogr.wkbPolygon)
    
    # Create arbitary id field
    layer.CreateField(ogr.FieldDefn('id', ogr.OFTInteger))
    defn = layer.GetLayerDefn()
    
    addAttributeColumns(layer, attributes)
    
    # Create a new feature (attribute and geometry)
    for i in range(0,len(xx)):
        # Generate the corner points
        xul, yul, xur, yur, xll, yll, xlr, ylr  = \
        calculatecorners(degreelist[i],xx[i],yy[i],width,height)     
        
        # Create rectangle corners
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(xul, yul)
        ring.AddPoint(xur, yur)
        ring.AddPoint(xlr, ylr)
        ring.AddPoint(xll, yll)
        ring.AddPoint(xul, yul)
        
        # Create polygon from corners
        poly = ogr.Geometry(ogr.wkbPolygon)
        poly.AddGeometry(ring)
        
        # Export well-known binary
        wkb = poly.ExportToWkb()
        
        # Assign arbitary number to field ID
        feat = ogr.Feature(defn)
        feat.SetField('id', i)
        
        # Assign a row of attributes to attribute columns
        # pdf.at[i, col] is equivalent of pdf.iloc[[i]][col].values[0] but notworking consistently
        # thikn it doesnt work if you've removed any data from the df (ie the index no longer starts at 0)
        # With resetting the index after filtering, this should still work
        for col in attributes.columns: 
            feat.SetField(col, attributes.at[i, col])
                
        # Make a geometry, from Shapely object
        geom = ogr.CreateGeometryFromWkb(wkb)
        feat.SetGeometry(geom)
        
        # Write out geometry
        layer.CreateFeature(feat)
        
        # Remove ring and poly
        ring = poly = None
    
    # Remove feat and geom
    feat = geom = None
    
    # Save and close everything
    ds = layer = feat = geom = None   
###############################################################################
###############################################################################

    
###############################################################################
# old stuff from old 3dsi stuff  might want to reuse later

# add UTM coords to pandas dataframe
def addAttributesToDf(pdf, utmLonList, utmLatList, epsg, bname):
    
    # Add beam_type column
    pdf.loc[( (pdf.orb_orient == 1 ) & (pdf['gt'].str.contains('r')) ), "beam_type"] = 'Strong' 
    pdf.loc[( (pdf.orb_orient == 1 ) & (pdf['gt'].str.contains('l')) ), "beam_type"] = 'Weak'
    pdf.loc[( (pdf.orb_orient == 0 ) & (pdf['gt'].str.contains('r')) ), "beam_type"] = 'Weak'
    pdf.loc[( (pdf.orb_orient == 0 ) & (pdf['gt'].str.contains('l')) ), "beam_type"] = 'Strong'

    # Add UTM coordinates
    pdf['utmLon'] = utmLonList
    pdf['utmLat'] = utmLatList
    
    # Add EPSG code
    pdf['epsg']  = [epsg for i in range(0,len(utmLonList))]
    
    # Add full path to input h5 file
    pdf['ATLfile']  = [bname for i in range(0,len(utmLonList))]
    
    return None

# 1/19: Added this to Remove NoData rows from the dataframe
def filterRows(pdf):
    
    outDf = pdf[pdf.can_open != 3.402823466385289e+38] # Must be written exactly like this
    
    # After filtering we need to reset the index in the df
    # Drop the index column because it's just going to be moot when combined with others
    outDf.reset_index(drop=True, inplace=True)    
    
    nFiltered = len(pdf) - len(outDf)
    
    return outDf, nFiltered

# 1/19: Added this to fix the columns that were encoded improperly
def fixColumns(pdf):
    
    # Columns that have issues and the output types we want them as:
    # yr (int), m (int), d (int), gt (str)
    
    pdf['yr'] = pdf['yr'].str.strip("b'").astype("int")
    pdf['m'] = pdf['m'].str.strip("b'").astype("int")
    pdf['d'] = pdf['d'].str.strip("b'").astype("int")
    pdf['gt'] = pdf['gt'].str.strip("b'").astype("str")

    return pdf
"""

# Get largest overlapping UTM zone for a bounding box 
# - shouldn't need this with updated pyproj
def getUtmEpsg(extent_4326):
    
    from osgeo import ogr
    import tempfile
    
    # always supply coords in EPSG:4326 for now 
    # gpd/gdal extent order: ulx,lry,lrx,uly/xmin,ymin,xmax,ymax
    (ulx, lry, lrx, uly) = extent_4326
    extent = ' '.join(map(lambda i: str(i), extent_4326))
    
    # If we are outside of utm lat. shp bounds, reset to bound
    if uly >= 84.0: uly = 84.0
    if lry <= -80.0: lry = -80.0
    
    # Clip UTM to shp according to extent
    utmShp = '/adapt/nobackup/people/mwooten3/GeneralReference/' + \
                                        'UTM_Zone_Boundaries.shp'
    clipFile = tempfile.mkdtemp()
    
    cmd = 'ogr2ogr -clipsrc {} -f "ESRI Shapefile"'.format(extent) + \
                    ' -select "Zone_Hemi" "{}" "{}"'.format(clipFile, utmShp)
     
    os.system(cmd)
    
    # Read clipped shapefile
    driver = ogr.GetDriverByName("ESRI Shapefile")
    ds = driver.Open(clipFile, 0)
    layer = ds.GetLayer()

    # Find zone with largest area of overlap
    maxArea = 0
    for feature in layer:
        area = feature.GetGeometryRef().GetArea()
        if area > maxArea:
            maxArea = area
            zone, hemi = feature.GetField('Zone_Hemi').split(',')

    proj4 = '+proj=utm +zone={} +ellps=WGS84 +datum=WGS84 +units=m +no_defs'.format(zone)
    epsg = '326{}'.format(zone.zfill(2))
    if hemi.upper() == 'S':
        proj4 += ' +south' 
        epsg = '327{}'.format(zone.zfill(2))
        
    return epsg
    


def main(args):
    
    #gdf = read from args
    
    #return pointsToSegments(gdf)
    
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

