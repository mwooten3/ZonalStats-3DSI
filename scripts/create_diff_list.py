"""
Sometimes a zonal stats run might get cut off (on purpose or accident)

If so, we may need a new list to run without attempting stacks we know
are empty

So this script checks an input stack list, and creates a subset list of 
stacks that do not have an output log file*

*because we wanna skip stacks that we already know have no data and keep only
stacks that have not even attempted to be run yet

**BE SURE to clean up output and don't stop runs mid-write to aggregate .csvs


This only really works for current 2022(/3) runs

"""
import os
import glob

zonalType = 'Disturbance'#'ATL08-20m'
stackName = 'SGM-ea'
statsType = 'zonal'

# May not necessarily be full/regularly named list (tho usually)
inlist = '/explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022/_inputLists/ls_{}__798.txt'.format(stackName)

outlist = inlist.replace('.txt', '__diff.txt')

checkdir = '/explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022/{0}/{1}/{2}'.format(zonalType, *stackName.split('-'))

print("Checking list {} against {} and writing to {}...".format(inlist, checkdir, outlist))

with open(inlist, 'r') as il:
    infiles = [l.strip() for l in il.readlines()]

c=0
for inf in infiles:
    
    bname = os.path.basename(inf).replace('.tif', '')
    
    checkF = os.path.join(checkdir, bname, '{}__{}__{}Stats__Log.txt'.format(zonalType, bname, statsType))
    #print(checkF)
    
    if os.path.isfile(checkF): 
        c+=1
        continue
        
    # if log file does not exist, write to .txt
    with open(outlist, 'a') as ol:
        ol.write('{}\n'.format(inf))
    
print("\nNumber files exist: {}".format(c))
    