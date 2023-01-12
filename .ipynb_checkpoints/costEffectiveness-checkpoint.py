from geovoronoi import voronoi_regions_from_coords
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon
import time

# ---------- READ REQUIRED FILES ---------- 
# input that remains constant at each iteration, prepped in dataPrep.ipynb
candiInfo = gpd.read_file('data/candiInfo_ams.shp')
infoGrid = gpd.read_file('data/infoGrid_ams.shp')
cost_matrix = np.load('data/costMatrix_ams.npy')

# modify column names
infoGrid = infoGrid.rename(columns={'totKgDeman': 'totKgDemand', 
                        'totKgSuppl': 'totKgSupply'})

# --------- ASSIGN HUBS TO INFOGRID CELLS ---------
def assignHubsToGridCells(points, infoGrid): 
    def findHub(infoGrid_index): 
        points_index = [int(x) for x in list(points.hubName)]
        dists = cost_matrix[infoGrid_index, points_index]
        idxmin = np.argmin(dists)
        chosenPoint = points_index[idxmin]
        return chosenPoint
    infoGrid['hubName'] = infoGrid.index.map(lambda x: findHub(x))
    return infoGrid 

# ---------- CALCULATE CO2 REDUCTION ------------- 
def calcTotCo2Reduction(points, infoGrid_hubsAssigned): 
    
    # calc co2 reduction for each hub 
    def calcCo2Reduction(hubName, infoGrid_hubsAssigned):  
        # hubName = infoGrid.hubName.iloc[0] # 17 
        infoHub = infoGrid_hubsAssigned[infoGrid_hubsAssigned.hubName == hubName] 
        # get info for grid cells covered by hub 
        co2Emissions = 50 # dummy number - tons of CO2eq emissions associated per kg of wood 
        totSupply = infoHub.totKgSupply.sum()
        totDemand = infoHub.totKgDemand.sum()
        matKgStored = totSupply # if totDemand > totSupply else totDemand
        co2Reduction = co2Emissions * matKgStored
        return co2Reduction
    
    # sum co2 reduction for all hubs 
    points['co2Reduction'] = points.hubName.map(lambda x: calcCo2Reduction(x, infoGrid_hubsAssigned))
    totCo2Reduction = points.co2Reduction.sum()
    return totCo2Reduction


# ---------- CALCULATE STORAGE COSTS -------------
def calcTotStorageCost(points, infoGrid_hubsAssigned, candiInfo): 
    # calculate storage cost for one hub
    def calcStorageCost(hubName): 
        def calcStorCoef(kgPerM3, percLogistics, throughPut): 
            kg = kgPerM3 * 3 * (12/throughPut) # kg stored per m3 
            storCoef = (1+(percLogistics/100)) / kg 
            return storCoef
        infoHub = infoGrid_hubsAssigned[infoGrid_hubsAssigned.hubName == hubName]
        
        # sqm required to store 1 kg of material for 1 year
        storageCoefLong = calcStorCoef(kgPerM3=600, percLogistics=30, throughPut=36)
        storageCoefShort = calcStorCoef(kgPerM3=600, percLogistics=30, throughPut=3)

        # calculate matKgStored 
        totSupply = infoHub.totKgSupply.sum()
        totDemand = infoHub.totKgDemand.sum()
        if totDemand >= totSupply: 
            matKgStoredLong = 0 
            matKgStoredShort = totSupply 
        elif totSupply > totDemand: 
            matKgStoredLong = totSupply - totDemand 
            matKgStoredShort = totDemand

        # find land price
        landPrice = candiInfo.loc[hubName, 'pPerSqm'] 

        # calculate storage cost 
        storageCost = landPrice * (storageCoefLong * matKgStoredLong + storageCoefShort * matKgStoredShort)
        return storageCost
    
    # sum storage cost for all hubs
    points['storageCost'] = points.hubName.map(lambda x: calcStorageCost(x))
    totStorageCost = points.storageCost.sum()
    return totStorageCost


# ---------- CALCULATE TRANSPORTATION COSTS ------------- 
def calcTotTransportationCost(points, infoGrid_hubsAssigned, cost_matrix): 
    
    # calculate transportation cost for one hub
    def calcTransportationCost(hubName):
        infoHub = infoGrid_hubsAssigned[infoGrid_hubsAssigned.hubName == hubName]
        
        # see data/transportation/tansCostPerKm_middelStukgoed.csv 
        euroPerKm = 1.55 # cost per km of transporting 12 tonnes of material 
        euroPerKmPerKg = 1.55 / 12 / 1000
        transPriceCoef = euroPerKmPerKg

        # find locations of demand and supply 
        hubDemand = infoHub[infoHub.totKgDemand > 0]
        hubSupply = infoHub[infoHub.totKgSupply > 0]

        # calc totDist and matKg for supply and demand 
        # cost_matrix[origin (clients), destination (facilities)]
        totDistSupply = cost_matrix[hubSupply.index, hubName].sum()
        matKgSupply = infoGrid_hubsAssigned.totKgSupply.sum() 
        # is currently just sum of totKgSupply, without taking into account each trip 
        totDistDemand = cost_matrix[hubDemand.index, hubName].sum()
        matKgDemand = infoGrid_hubsAssigned.totKgDemand.sum()

        # calc transportation cost 
        transportationCost = transPriceCoef * (totDistSupply * matKgSupply + totDistDemand * matKgDemand)
        transportationCost

        return transportationCost
    
    # sum transportation emissions all hubs
    points['transCost'] = points.hubName.map(lambda x: calcTransportationCost(x))
    totTransCost = points.transCost.sum()
    return totTransCost


# ---------- CALCULATE TRANSPORTATION EMISSIONS ------------- 
def calcTotTransportationEmissions(points, infoGrid_hubsAssigned, cost_matrix): 
    
    # calculate transportation emissions for one hub 
    def calcTransportationEmissions(hubName): 
        infoHub = infoGrid_hubsAssigned[infoGrid_hubsAssigned.hubName == hubName]
        
        # incorporating transEmissionsCoef
        KgCo2PerKm = 0.5243 # kg CO2 emissions per km of 16t of material 
        TonsCo2PerKm = KgCo2PerKm / 1000 
        transEmissionsCoef = TonsCo2PerKm / 16000 

        # find locations of demand and supply 
        hubDemand = infoHub[infoHub.totKgDemand > 0]
        hubSupply = infoHub[infoHub.totKgSupply > 0]
        
        # calc totDist and matKg for supply and demand 
        # cost_matrix[origin (clients), destination (facilities)]
        totDistSupply = cost_matrix[list(hubSupply.index), hubName].sum()
        matKgSupply = infoGrid_hubsAssigned.totKgSupply.sum() 
        # is currently just sum of totKgSupply, without taking into account each trip 
        totDistDemand = cost_matrix[hubDemand.index, hubName].sum()
        matKgDemand = infoGrid_hubsAssigned.totKgDemand.sum()

        # calculate transportation emissions 
        transportationEmissions = transEmissionsCoef * (totDistSupply * matKgSupply + totDistDemand * matKgDemand)
        # TODO: better model this - see comments on calcTransportationCost

        return transportationEmissions

    # sum transportation emissions all hubs
    points['transEmissions'] = points.hubName.map(lambda x: calcTransportationEmissions(x))
    totTransEmissions = points.transEmissions.sum()
    return totTransEmissions


# ---------- CALCULATE COST EFFECTIVENESS ------------- 
def calcTotCostEffectiveness(pointsArray): 
    
    timeStart = time.time() 
    # make points gdf   
    points = gpd.GeoDataFrame(
            pointsArray, geometry=gpd.points_from_xy(pointsArray[:,1], pointsArray[:,2]), 
            crs='EPSG:28992'
        ).rename(columns={0: 'hubName', 1: 'x', 2: 'y'})
    points.hubName = points.hubName.map(lambda x: int(x)-1) # -1 because index in R starts at 1, not 0
    timePoints = time.time()

    # assign hubs to grid cells 
    infoGrid_hubsAssigned = assignHubsToGridCells(points, infoGrid)
    timeAssignHubs = time.time()

    # calculate sub-components
    totCo2Reduction = calcTotCo2Reduction(points, infoGrid_hubsAssigned)
    timeCo2 = time.time()
    totStorageCost = calcTotStorageCost(points, infoGrid_hubsAssigned, candiInfo)
    timeStorage = time.time()
    totTransCost = calcTotTransportationCost(points, infoGrid_hubsAssigned, cost_matrix)
    timeTransCost = time.time() 
    totTransEmissions = calcTotTransportationEmissions(points, infoGrid_hubsAssigned, cost_matrix)
    timeTransEmissions = time.time()

    # calculate cost effectiveness 
    costEffectiveness = (totStorageCost + totTransCost) / (totCo2Reduction - totTransEmissions)
    timeCostEff = time.time()
    
    # print('''
    # points: {}
    # assign hubs: {}
    # co2: {}
    # storage: {}
    # transCost: {}
    # transEmiss: {}
    # '''.format(
    #     timePoints - timeStart, 
    #     timeAssignHubs - timePoints, 
    #     timeCo2 - timeAssignHubs, 
    #     timeStorage - timeCo2, 
    #     timeTransCost - timeStorage, 
    #     timeTransEmissions - timeTransCost 
    # ))
            
    return costEffectiveness 
