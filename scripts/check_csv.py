# combine node-specific .csv files into one

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
import numpy as np



# params to change
zonalType = 'Disturbance'#'ATL08-20m'
stackType = 'SGM-boreal'#'joined-SGM-boreal' # Landsat-ea, Landsat-boreal, SGM-na, SGM-ea, joined-SGM-boreal
col = 'patchSize_m2'

icsv = '/explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022/{}__{}__stats.csv'.format(zonalType, stackType)
#icsv = '/panfs/ccds02/nobackup/people/mwooten3/3DSI/ZonalStats_2022/ATL08-20m__joined-SGM-boreal__stats.csv'

# older median file:
#icsv = '/explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022/Disturbance/SGM_median/Disturbance__SGM-boreal__stats.csv'
#col = 'CHM_sr05_median'

print("Input: {}".format(icsv))
print("Column: {}".format(col))

os.system('date')

outhist = icsv.replace('__stats.csv', '__{}__hist.png'.format(col))

df = pd.read_csv(icsv)

# histogram 

# ok:
#bins0 = [-.01, 0, .01, .50, 
#        1, 2, 3, 4, 5, 10, 15, 20, 100, 200]
#rint(df[col].value_counts(bins = bins0))

# try this - only way i can seem to make it work
#bins0 = np.linspace(0,50,50)
bins0 = np.linspace(0,df[col].max(),50)

ax = df[col].hist(bins=bins0, histtype='stepfilled')#, density=True)
#ax = df[col].hist(histtype='stepfilled', density=True)
#import pdb; pdb.set_trace()

ax.set_title('Frequency of CHM Values within Disturbances')
#xlabel = 'CHM {} (meters)'.format((col).split('_')[2])
xlabel = 'Patch Size (meters)'

#print(xlabel)
ax.set_xlabel(xlabel)
ax.set_ylabel('Density')

fig = ax.get_figure()
fig.savefig(outhist)

# try to bin
#df['CHM_sr05_median'].value_counts(normalize=True)

#import pdb; pdb.set_trace()

bins = [df[col].min(), -400, -300, -200, -100, -.01, 0, .01, .50, 
        1, 2, 3, 4, 5, 10, 15, 20, 100, 500, 1000, 2000, 4000, 10000, 
                                                    df[col].max()]
        
#labels = [str(b) for b in bins]
#df['grade'] = pd.cut(x = df['CHM_sr05_median'], bins = bins, labels = labels, 
 #                                            include_lowest = True)
print(df[col].value_counts(bins = bins, sort = False))

# less bins
bins2 = [df[col].min(), -400, -.01, 0, .1, .50, 
        1, 2, 3, 4, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 100, 200, 
                                                    df[col].max()]
print(df[col].value_counts(bins = bins2, sort = False))

# even less 
bins3 = [df[col].min(), -400, -.01, 0, 40,
                                                    df[col].max()]
print(df[col].value_counts(bins = bins3, sort = False))

# try above bins with %
pct = df[col].value_counts(bins = bins3, sort = False, normalize=True).mul(100).round(1).astype(str) + '%'
print(pct)
        
os.system('date')


