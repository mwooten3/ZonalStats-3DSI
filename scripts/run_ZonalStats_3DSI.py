# -*- coding: utf-8 -*-
"""
Created on Wed Feb  9 14:07:21 2022
@author: mwooten3

From a zonal type and stack type, run ZonalStats

Inputs: 
    stackType [SGM, LVIS, GLiHT, Landsat, Auxiliary for now]
    zoneType  [ATL08-v5, GLAS for now]
"""
import os
import time
import argparse
import platform

import numpy as np

from RasterStack import RasterStack
from FeatureClass import FeatureClass

# Some global vars
mainDir = '/explore/nobackup/people/mwooten3/3DSI/ZonalStats_2022'
runScript = '/home/mwooten3/code/3DSI_ZonalStats_v3/ZonalStats_3DSI.py'

#validStackTypes = ['GLiHT', 'Auxiliary', 'Landsat', 'GLiHT-old', 'LVIS-old']#, 'SGM', 'LVIS']
validStackTypes = ['Landsat', 'SGM']
validZonalTypes = ['ATL08-20m', 'ATL08-100m', 'Disturbance']#, 'GLAS', 'Disturbance', 'ATL08', TBD]
validStatsTypes = ['point', 'zonal']

overwrite = False
# arg in input now region = 'NA' # NA (default) or EA - just changes the 

# This works by taking a list of nodes and splitting up an overall list evenly
#  among the nodes. The script will run the list 

def getVarsDict(stackType, zonalType, statsType, region):
 
    """
    if stackType == 'SGM':
        inputList = os.path.join(mainDir, '_lists', 'ls_SGM.txt')
    elif stackType == 'LVIS':
        inputList = os.path.join(mainDir, '_lists', 'ls_LVIS.txt')
    elif stackType == 'GLiHT':
        inputList = os.path.join(mainDir, '_lists', 'ls_GLiHT.txt')
    """
    # Do not need to sanitize other inputs as we have already done that, just the list
    
    # Get raster stack list from stack type        
    inputList = os.path.join(mainDir, '_inputLists', 'ls_{}-{}.txt'.format(stackType, region))
    if not os.path.exists(inputList):
        raise RuntimeError("List {} for stack type {} (region {}) does not exist".\
                                                  format(inputList, stackType, region))

    # Get directory of .csv files for zonalType (ATL08-v5 only for now)  
    # 1/6/23 do not need zonalDir anymore - this is done in 
    if zonalType == 'ATL08':
        zonalDir = None#'/explore/nobackup/people/pmontesa/userfs02/data/icesat2/atl08.005/boreal_na_20m'
        
        
    #elif GLAS (may never need to run with GLAS)
        
    #* TBD on node-specific outputs or not
    #* TBD on how to handle option for .csv/FC/DB
    # 1/6/23: Write to node specific .csv files to avoid corruption issues
    aggOut = os.path.join(mainDir, '_nodeZonalOutputs',
       '{}__{}-{}__{}Stats__{}.csv'.format(zonalType, stackType, region, 
                                           statsType, platform.node()))
    
    #* Edit vars if region is EU - TBD for v3
    """
    if region == 'EU':
        inputZonal = inputZonal.replace('na', 'eu')
        outCsv = outCsv.replace('{}__'.format(zonalType), '{}-EU__'.format(zonalType))
    """
    varsDict = {'inList': inputList, 'aggregateOutput': aggOut}
    
    return varsDict

def getNodeFiles(inFiles, nodeRange, nodeBase):
    
    node = platform.node()
             
    nodeList = ['{}{}'.format(nodeBase, str(r).zfill(3)) for r in 
           range(int(nodeRange.split('-')[0]), int(nodeRange.split('-')[1])+1)]
    
    #* TEMP EDIT 1/19/23 - hardcode nodeList for Dist/SGM diff reruns
    #nodeList = ['ngaproc201', 'ngaproc202', 'ilab201', 'ilab202', 'ilab203', 'ilab204',
     #          'ilab205', 'ilab206', 'ilab207', 'ilab208', 'ilab209', 'ilab210',
     #          'forest209', 'forest210']
    #nodeList = ['forest201', 'forest202', 'forest203', 'forest204', 'forest207', 
    #                                                   'forest209', 'forest210']
    #nodeList = ['forest201', 'forest202', 'forest203', 'forest204', 'forest205', 'forest207', 'forest209']
    #nodeList = ['ilab208', 'ngaproc201']

    # For new SGM disturbance (p90) results, append 2 nga proc to nodes list
    nodeList.extend(['ngaproc201', 'ngaproc202'])
    
    #nodeList = ['forest201', 'ilab201', 'ilab202', 'ilab203', 
    #            'ilab204', 'ilab205', 'ilab206', 'ilab207', 'ilab208', 'ilab209', 'ilab210']
    
    
    
    # Check with user to be sure node list is expected
    inp = input("Running on {} nodes: {}. OK to continue? 'y' to run, 'n' to cancel ".format(len(nodeList), ', '.join(nodeList)))
    if inp == 'y':
        pass # continue on
    else:
        return [] # Empty list, program will exit
          
    try:
        i = nodeList.index(node)
    except ValueError:
        inp = input("Current node {} is not in list. Run all {} inputs? Enter 'y' to run or 'n' to cancel ".format(node, len(inFiles)))
        if inp == 'y':
            return inFiles
        else:
            return [] # Empty list, program will exit

    splitLists = np.array_split(inFiles, len(nodeList))    
    
    # Get list for node
    runFiles = splitLists[i]

    return runFiles      

def getStackList(inTxtList, nodeRange, nodeBase, splitList):
    
    with open(inTxtList, 'r') as it:
        inFiles = [r.strip() for r in it.readlines()]

    if splitList:       
        runFiles = getNodeFiles(inFiles, nodeRange, nodeBase)
    else:
        runFiles = inFiles   
        
    return runFiles
    
# Unpack and validate input arguments
def unpackValidateArgs(args):
    
    # Unpack args
    stackType  = args['stackType']
    zonalType  = args['zonalType']
    statsType  = args['statsType']
    nodeRange  = args['nodeRange']
    region     = args['region']
    noSplit    = args['noSplit'] # do not split list if passed
#    nodeBase   = args['nodeBase']
#    runPar     = args['parallel']

    # Validate inputs   
    if stackType not in validStackTypes:
        err = "Stack type must be one of: " + \
                        "{}".format(", ".join(validStackTypes)) 
        raise RuntimeError(err)
    
    # either ATL08-v5 or ATL08 is accepted - no more
    #if zonalType.startswith('ATL08'):
     #   zonalType = 'ATL08'
    if zonalType not in validZonalTypes:        
        err = "Zonal type must be one of: " + \
                        "{}".format(", ".join(validZonalTypes)) 
        raise RuntimeError(err)
    
    if statsType not in ['point', 'zonal']:
        err = "Statistics mode must be one of: " + \
                        "{}".format(", ".join(validStatsTypes)) 
        raise RuntimeError(err)        
      
    if nodeRange:        
        try:
            int(nodeRange.split('-')[0])
            int(nodeRange.split('-')[1])
        except:
            raise RuntimeError("Range must be supplied like: 101-110")
    
    # 1/6/23 get region
    if region not in ['na', 'ea']:
        raise RuntimeError("Region must be na (N. America) or ea (Eurasia)")
        
    # 1/6/23 configure split
    split = True # default
    if noSplit:
        split = False        
    
    # Only return vars that are referenced more than once in main()
    return stackType, zonalType, statsType, region, split

def main(args):

    # Unpack and validate arguments, store vars that are reference more than once
    stackType, zonalType, statsType, region, split = unpackValidateArgs(args)
    
    # Get other varsDict --> {inList; zonalDir; outCsv}
    varsDict = getVarsDict(stackType, zonalType, statsType, region) 

    # Get list of stacks to iterate
    stackList = getStackList(varsDict['inList'], args['nodeRange'], \
                             args['nodeBase'], split)
    
    # Get node-specific output .gdb
    #* TBD whether doing this or not. And it will be .csv not .gdb
    #outGdb = varsDict['outCsv'].replace('.csv', '-{}.gpkg'.format(platform.node()))

    #* This is untested/will not work as of now for v3
    if args['parallel']: # If running in parallel
        
        # Get list of output shp's that we are expecting based off stackList
        shps = [os.path.join(mainDir, zonalType, stackType, RasterStack(stack).stackName, 
                '{}__{}__zonalStats.shp'.format(zonalType, RasterStack(stack).stackName)) 
                                                        for stack in stackList]

        # Prepare inputs for parallel call:
        call = "lscpu | awk '/^Socket.s.:/ {sockets=$NF} END {print sockets}'"
        ncpu = os.popen(call).read().strip()
        ncpu = int(ncpu) - 1 # all CPUs minus 1
    
        parList = ' '.join(stackList)
        
        print("\nProcessing {} stack files in parallel...\n".format(len(stackList)))

        # Do not supply output GDB, just supply .csv
        parCall = '{} -rs '.format(runScript) + '{1} -z {2} -o {3} -log'
        cmd = "parallel --progress -j {} --delay 1 '{}' ::: {} ::: {} ::: {}". \
                format(ncpu, parCall, parList, varsDict['zonalDir'], 
                                                           varsDict['outCsv'])

        os.system(cmd)       

        # And update node-specific GDB if shp exists
        print("\n\nCreating {} with completed shapefiles ({})...".format(outGdb, 
                                           time.strftime("%m-%d-%y %I:%M:%S")))   
        for shp in shps:
            if os.path.isfile(shp):
                fc = FeatureClass(shp)
                if fc.nFeatures > 0: fc.addToFeatureClass(outGdb)        
                
    # Do not run in parallel
    else:   
        
        # Iterate through stacks and call
        print("\nProcessing {} stacks on {}...".format(len(stackList), 
                                                              platform.node()))
        
        c = 0
        for stack in stackList:
            
            c+=1
            print("\n{}/{}:".format(c, len(stackList)))

            # Check stack's output csv's, and skip if it exists and overwrite is False
            rs = RasterStack(stack)
            check = os.path.join(mainDir, zonalType, stackType, region, rs.stackName,
              '{}__{}__{}Stats.csv'.format(zonalType, rs.stackName, statsType))
            
            if not overwrite:
                if os.path.isfile(check):
                    print("\nOutputs for {} already exist\n".format(rs.stackName))
                    continue
            
            # Not running in parallel
            # 1/6/23: zonalType not zonalDir now
            cmd = 'python {} -r {} -z {} -o {} -b {} -mode {}'.format( \
                          runScript, stack, args['zonalType'],     \
                          varsDict['aggregateOutput'], mainDir, args['statsType'])
            logging = True #* TD add as arg
            if logging:
                cmd += ' -log'
            
            print(cmd)
            os.system(cmd) 
        
        
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument("zonalType", type=str,
                        help="Zonal type (ATL08-20m or ATL08-100m)")    
    parser.add_argument("stackType", type=str, 
                        help="Stack type ([])".format(' '.join(validStackTypes)))
    parser.add_argument("-mode", "--statsType", type=str, required=True, 
                        help="'zonal' for zonal stats (default??) or 'point' for point query")
    parser.add_argument("-reg", "--region", type=str, required=False, 
                        help="Region (na or ea)", default = 'na')
    parser.add_argument("-nb", "--nodeBase", type=str, default = 'forest',
                        help="Node base (default forest)", required=False)
    parser.add_argument("-nr", "--nodeRange", type=str, default = '201-210',
                        help="Node range (i.e. 201-201 or 201-210 (default))",
                                                            required=False)
    parser.add_argument("-par", "--parallel", action='store_true', 
                        help="Run in parallel")
    parser.add_argument("-noSplit", "--noSplit", action='store_true', 
                        help="Do not split input files among passed nodes")
    
    args = vars(parser.parse_args())

    main(args)

 