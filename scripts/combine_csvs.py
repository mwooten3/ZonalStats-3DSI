# combine node-specific .csv files into one
#* BE SURE TO REVIEW CODE BEFORE RUNNING. LOTS OF WEIRD THINGS HARDCODED

# FOR SGM, process goes like this:
# 1. Run zonal stats code
# 2. combine_csv's 2x: with stackType = SGM-na/ea
# 3. Run join_SGM_Landsat 2x: for ea and na
# 4. combine_csv's 1x: with stackType = joined-SGM-boreal

# For Landsat:
# 1. Run zonal stats
# 2. combine_csv's 2x: with stackType = Landsat-na/Landsat-ea
# 3. combine_csv's 1x with stackType = Landsat-boreal

import os, glob
import geopandas as gpd
import pandas as pd


# params to change
zonalType = 'Disturbance'#'ATL08-20m'
stackType = 'SGM-na' # Landsat-na, Landsat-ea, Landsat-boreal, SGM-na, SGM-ea, SGM-boreal, joined-SGM-boreal (for old icesat based SGM), 
node = 'forest' #ilab or forest (eventually could be both) - should not matter

toShp = True # will turn to False if creating big boreal file (keep shp separate) (ie if boreal in stackType)

# 3/4/23: Standard way is to get outputs from node outputs and write to output. 
#          Edited block below to work with accidentall appending 90p and 98p+ runs together merges all indiv. files

# PAY ATTENTION TO 3 VARS - cdir, ocsv, incsvs
# from nodeZonal (ea/regular):
#cdir = '/explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022/_nodeZonalOutputs'
# from individual (na/ea):
cdir = '/explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022/Disturbance/SGM/{}'.format(stackType.split('-')[1]) # eg SGM/na

#ocsv = '/explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022/{}__{}__stats.csv'.format(zonalType, stackType) # older
ocsv = '/explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022/Disturbance/SGM/{}__{}__stats.csv'.format(zonalType, stackType)

os.system('date')

# Get list of csv files
if 'boreal' not in stackType: # regular combine (all forest/whatever nodes)
    # 3/4/23: Also editing block below to fix accident
    # from nodeZonal (ea/regular):
    #incsvs = glob.glob(os.path.join(cdir, '{}__{}__*Stats__*2??.csv'.format(zonalType,
                                                                    #stackType)))
    # from individual (na/ea):
    incsvs = glob.glob(os.path.join(cdir, '*', '*zonalStats.csv'))
    
# if working with joined SGM data
elif 'joined' in stackType: # it will be joined-SGM-reg so split needs adjusting
    toShp = False # for now
    cdir = '/explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022/' # files will be in here
    incsvs = glob.glob(os.path.join(cdir, '{}__joined-{}*.csv'.format(zonalType,
                                                       stackType.split('-')[1])))
    
else: # just want both na and ea to combine into boreal
    toShp = False # dont write to shp    
    cdir = '/explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022/' # files will be in here
    incsvs = glob.glob(os.path.join(cdir, '{}__{}*.csv'.format(zonalType,
                                                       stackType.split('-')[0])))


print("\nCombining {} .csv files into {}".format(len(incsvs), ocsv))

#for c in incsvs: print('\t{}'.format(c))
print('')

df = pd.concat(map(pd.read_csv, incsvs), ignore_index=True)

# slow and need to fix the actual stack and node .csv's, but works for now
# also need to fix .shp process - just append stack .shp's for dist
if zonalType == 'Disturbance':
    
    df['mmddyyyy'] = df['mmddyyyy'].astype(str).str.zfill(8)
        
    toShp = False

print(df)
print('')

# Remove potentially unwanted files from columns to write
write_cols = df.columns.to_list()
if 'polyGeom' in write_cols:
    write_cols.remove('polyGeom') # dont remove completely from df so we can write shp
#import pdb; pdb.set_trace()
df.to_csv(ocsv, index=False, header=True, columns = write_cols)
print("\nWrote {} rows to {}".format(len(df.index), ocsv))


os.system('date')

# fails for Disturbance
if toShp:
    oshp = ocsv.replace('.csv', '.shp')
    print('Writing to {}'.format(oshp))

    gdf = gpd.GeoDataFrame(df, 
              geometry=gpd.points_from_xy(df.lon_20m, df.lat_20m)).set_crs(4326)

    gdf.to_file(oshp)
    
    print('Done')
    os.system('date')



