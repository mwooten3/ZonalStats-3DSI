"""
Script to join SGM .csv file with Landsat files on unique ID

Join must be done or else SGM file is useless without age data

Notes:
- join by unique id
- remove duplicate cols. 
- keep SGM geometry (polygon)
- only keep areas of overlap. Rows without both SGM and are are useless

Doing this by region then can run combine_csvs

NOTE: To write shapefile, read SGM .shp not .csv, join Landsat df to it
- Skipping for now in interest of speed
- See https://gis.stackexchange.com/questions/349244/merging-a-geodataframe-and-pandas-dataframe-based-on-a-column
- polyGeom might actually be in final SGM output (removed geometry but mayeb not this)
-- if so, keep it there, writing a joined polygon .shp will be a lot easier
"""

import os

import pandas as pd
import geopandas as gpd

ddir = '/explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022'
zonalType = 'ATL08-20m'
region = 'ea'

keyCol = 'id_unique'

# csv1 = Landsat, csv2= SGM
csv1 = os.path.join(ddir, '{}__Landsat-{}__stats.csv'.format(zonalType, region))
csv2 = os.path.join(ddir, '{}__SGM-{}__stats.csv'.format(zonalType, region))

ocsv = csv2.replace('SGM-{}'.format(region), 'joined-SGM-{}'.format(region))

# TEST WITH SMALL outputs
#WV03_20150510_104001000B5CD900_104001000BADC600_sr05_4m-sr05-min_1m-sr05-max_dz_eul_warp.tif
#h590v146_age_year_n0_m1_stack.vrt
#csv1 = '/explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022/ATL08-20m/Landsat/na/h590v146_age_year_n0_m1/ATL08-20m__h590v146_age_year_n0_m1__pointStats.csv'
#csv2 = '/explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022/ATL08-20m/SGM/na/WV03_20150510_104001000B5CD900_104001000BADC600_sr05_4m-sr05-min_1m-sr05-max_dz_eul_warp/ATL08-20m__WV03_20150510_104001000B5CD900_104001000BADC600_sr05_4m-sr05-min_1m-sr05-max_dz_eul_warp__zonalStats.csv'

os.system('date')

print("\nJoining {} and {} with {}".format(csv1, csv2, keyCol))
print("Output: {}\n".format(ocsv))

df1 = pd.read_csv(csv1)
df2 = pd.read_csv(csv2)

print("Read .csv into dataframe ({} and {} rows)".format(len(df1.index), 
                                                         len(df2.index)))
os.system('date')

# First, get columns we want to keep from SGM .csv
sgm_cols = df2.columns.difference(df1.columns).to_list()

# Must add id_unique (keyCol) back
sgm_cols.append(keyCol)

# inner join will keep only rows with matching keys (uIDs)
df  = df1.merge(df2[sgm_cols], on=keyCol, how='inner')
#import pdb; pdb.set_trace()

# Remove any weird unwanted columns 
if 'Unnamed: 0' in df.columns: # this may only matter with test (small landsat file)
    
    use_cols = df.columns.to_list()
    use_cols.remove('Unnamed: 0')
    
    df = df[use_cols]    
    

df.to_csv(ocsv, index=False)
print("\nWrote {} intersecting rows to {}".format(len(df.index), ocsv))
os.system('date')




