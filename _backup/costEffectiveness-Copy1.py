from geovoronoi import voronoi_regions_from_coords
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon

def readDataType(points, infoGrid): 
    print('points: ')
    print(type(points))
    print(points)
    print('/n')
    print(type(infoGrid))
    print(infoGrid)
    print('/n/n')
    
    return 0

def testFunction(points, infoGridDf): 
  
    # -------- IMPORT PACKAGES ------- 
    import numpy as np
    import pandas as pd
    import geopandas as gpd
    from shapely.ops import unary_union
    from shapely.geometry import Polygon
    
  
    # -------- MAKE POINTS GDF -------- 
    try: # assuming points is a dataframe 
      points = gpd.GeoDataFrame(
          points, geometry=gpd.points_from_xy(points.x, points.y), 
          crs='EPSG:28992'
      )
    except: # assuming points is an np array 
      points = gpd.GeoDataFrame(
          points, geometry=gpd.points_from_xy(points[:,1], points[:,2]), 
          crs='EPSG:28992'
      )

    # ---------  MAKE INFOGRID GDF -----------
    infoGrid = infoGridDf.copy()
    infoGrid = gpd.GeoDataFrame(
      infoGrid, geometry=gpd.points_from_xy(infoGrid.x, infoGrid.y), 
      crs='EPSG:28992'
    )
    
    # ---------- SIMPLE FUNCTION -------------- 
    # find how much material can be collected within a 5000m radius 
    
    # calculate sumSupply for each point
    points['pointBuffer'] = points.geometry.buffer(5000) 
    def calcSumSUpply(x): 
        # x = geometry of buffer
        inBuffer = infoGrid[infoGrid.geometry.within(x)]
        sumSupply = inBuffer.totKgSupply.sum()
        return sumSupply
    points['sumSupply'] = points.pointBuffer.map(lambda x: calcSumSUpply(x))

    # return sum of totKgSupply within buffered areas 
    sumSupply = points.sumSupply.sum()
    
    return 0 - sumSupply
    

# --------- ASSIGN HUBS TO INFOGRID CELLS ---------
def assignHubsToGridCells(points, infoGrid): 
    # make gdfs 
    points = gpd.GeoDataFrame(
        points, geometry=gpd.points_from_xy(points[:,1], points[:,2]), 
        crs='EPSG:28992'
    )
    points.rename(columns={0: 'hubName', 1: 'x', 2: 'y'}, inplace=True)
    infoGrid = gpd.GeoDataFrame(
      infoGrid, geometry=gpd.points_from_xy(infoGrid.x, infoGrid.y), 
      crs='EPSG:28992'
    )
    points.hubName = points.hubName.map(lambda x: int(x))
    points.set_index('hubName', inplace=True)
    
    # coords: array of coordinates for open hubs
    coords = np.array(points[['x', 'y']])
    
    # area_shape: polygon surrounding amsterdam (just make a square for now)
    minx, miny, maxx, maxy = infoGrid.total_bounds # get bounding box of infoGrid 
    area_shape = Polygon([(minx, miny), (minx, maxy), (maxx, maxy), (maxx,miny)]).buffer(50)
    
    # make voronoi regions and pts
    region_polys, region_pts = voronoi_regions_from_coords(coords, area_shape)
    
    # match hubName in hubRegions to hubsOpen 
    hubRegions = gpd.GeoDataFrame({'hubName': region_polys.keys(), 'geometry': region_polys.values()})
    hubRegions = hubRegions.set_crs('EPSG:28992')
    hubRegions = gpd.sjoin(hubRegions, points)
    hubRegions = hubRegions[['index_right', 'geometry']]
    hubRegions.rename(columns={'index_right': 'hubName'}, inplace=True)
    
    # assign each infoGrid cell to the nearest open hub 
    def findHubName(x):
        # x = Point 
        hubName = hubRegions[hubRegions.geometry.contains(x)].iloc[0].hubName
        return hubName
    infoGrid_hubsAssigned = infoGrid.copy()
    infoGrid_hubsAssigned['hubName'] = infoGrid_hubsAssigned.geometry.map(lambda x: findHubName(x))
    
    return infoGrid_hubsAssigned

# ---------- CALCULATE CO2 REDUCTION ------------- 
# assign hubs to grid cells 
def calcTotCo2Reduction(pointsArray, infoGrid_hubsAssigned): 
    points = gpd.GeoDataFrame(
            pointsArray, geometry=gpd.points_from_xy(pointsArray[:,1], pointsArray[:,2]), 
            crs='EPSG:28992'
        )
    points.rename(columns={0: 'hubName'}, inplace=True)
    
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

# ---------- CALCULATE TRANSPORTATION EMISSIONS ------------- 
def calcTotTransportationEmissions(pointsArray, infoGrid_hubsAssigned, cost_matrix): 
    # assign hubs to grid cells 
    points = gpd.GeoDataFrame(
            pointsArray, geometry=gpd.points_from_xy(pointsArray[:,1], pointsArray[:,2]), 
            crs='EPSG:28992'
        )
    points.rename(columns={0: 'hubName'}, inplace=True)
    
    # calculate transportation emissions for one hub 
    def calcTransportationEmissions(hubName, infoGrid_hubsAssigned, cost_matrix): 
        infoHub = infoGrid_hubsAssigned[infoGrid_hubsAssigned.hubName == hubName]
        transEmissionsCoef = 1 # dummy 

        # find locations of demand and supply 
        hubDemand = infoHub[infoHub.totKgDemand > 0]
        hubSupply = infoHub[infoHub.totKgSupply > 0]
        
        # calc totDist and matKg for supply and demand 
        # cost_matrix[origin (clients), destination (facilities)]
        totDistSupply = cost_matrix[list(hubSupply.index), hubName].sum()
        matKgSupply = infoGrid_hubsAssigned.totKgSupply.sum() # is currently just sum of totKgSupply, without taking into account each trip 
        totDistDemand = cost_matrix[hubDemand.index, hubName].sum()
        matKgDemand = infoGrid_hubsAssigned.totKgDemand.sum()

        # calculate transportation emissions 
        transportationEmissions = transEmissionsCoef * (totDistSupply * matKgSupply + totDistDemand * matKgDemand)
        # TODO: better model this - see comments on calcTransportationCost

        return transportationEmissions

    # sum transportation emissions all hubs
    points['transEmissions'] = points.hubName.map(lambda x: calcTransportationEmissions(x, infoGrid_hubsAssigned, cost_matrix))
    totTransEmissions = points.transEmissions.sum()
    
    return totTransEmissions

# ---------- CALCULATE TRANSPORTATION COSTS ------------- 
def calcTotTransportationCost(pointsArray, infoGrid_hubsAssigned, cost_matrix): 
    # assign hubs to grid cells 
    points = gpd.GeoDataFrame(
            pointsArray, geometry=gpd.points_from_xy(pointsArray[:,1], pointsArray[:,2]), 
            crs='EPSG:28992'
        )
    points.rename(columns={0: 'hubName'}, inplace=True)
    
    # calculate transportation cost for one hub
    def calcTransportationCost(hubName, infoGrid_hubsAssigned, cost_matrix):
        infoHub = infoGrid_hubsAssigned[infoGrid_hubsAssigned.hubName == hubName]
        transPriceCoef = 50 # dummy number - 

        # find locations of demand and supply 
        hubDemand = infoHub[infoHub.totKgDemand > 0]
        hubSupply = infoHub[infoHub.totKgSupply > 0]

        # calc totDist and matKg for supply and demand 
        # cost_matrix[origin (clients), destination (facilities)]
        totDistSupply = cost_matrix[list(hubSupply.index), hubName].sum()
        matKgSupply = infoGrid_hubsAssigned.totKgSupply.sum() # is currently just sum of totKgSupply, without taking into account each trip 
        totDistDemand = cost_matrix[hubDemand.index, hubName].sum()
        matKgDemand = infoGrid_hubsAssigned.totKgDemand.sum()

        # calc transportation cost 
        transportationCost = transPriceCoef * (totDistSupply * matKgSupply + totDistDemand * matKgDemand)
        transportationCost

        return transportationCost
    
    # sum transportation emissions all hubs
    points['transCost'] = points.hubName.map(lambda x: calcTransportationCost(x, infoGrid_hubsAssigned, cost_matrix))
    totTransCost = points.transCost.sum()
    
    return totTransCost


# ---------- CALCULATE STORAGE COSTS -------------
def calcTotStorageCost(pointsArray, infoGrid_hubsAssigned, candiInfo): 
    # assign hubs to grid cells 
    points = gpd.GeoDataFrame(
            pointsArray, geometry=gpd.points_from_xy(pointsArray[:,1], pointsArray[:,2]), 
            crs='EPSG:28992'
        )
    points.rename(columns={0: 'hubName'}, inplace=True)
    points.hubName = points.hubName.map(lambda x: int(x))
        
    # calculate storage cost for one hub
    def calcStorageCost(hubName, infoGrid_hubsAssigned, candiInfo, kgPerM3=600, percLogistics=30, throughPut=12): 

        def calcStorCoef(kgPerM3, percLogistics, throughPut): 
            kg = kgPerM3 * 3 * (12/throughPut) # kg stored per m3 
            storCoef = (1+(percLogistics/100)) / kg 
            return storCoef

        infoHub = infoGrid_hubsAssigned[infoGrid_hubsAssigned.hubName == hubName]
        # sqm required to store 1 kg of material for 1 year
        storageCoef = calcStorCoef(kgPerM3, percLogistics, throughPut)

        # calculate matKgStored 
        totSupply = infoHub.totKgSupply.sum()
        totDemand = infoHub.totKgDemand.sum()
        matKgStored = totSupply if totDemand > totSupply else totDemand

        # find land price
        # pick housePrice in infoGrid cell closest to open hub
        landPrice = candiInfo.loc[hubName, 'pPerSqm'] 

        # calculate storage cost 
        storageCost = landPrice * storageCoef * matKgStored

        # TODO: make differentiation between long and short term storage 
        return storageCost
    
    # sum storage cost for all hubs
    points['storageCost'] = points.hubName.map(lambda x: calcStorageCost(x, infoGrid_hubsAssigned, candiInfo))
    totStorageCost = points.storageCost.sum()
    return totStorageCost

# ---------- CALCULATE COST EFFECTIVENESS ------------- 
def calcTotCostEffectiveness(pointsArray, infoGridFile, candiInfo, cost_matrix): 
    
    infoGrid_hubsAssigned = assignHubsToGridCells(pointsArray, infoGridFile)
    totStorageCost = calcTotStorageCost(pointsArray, infoGrid_hubsAssigned, candiInfo)
    totTransCost = calcTotTransportationCost(pointsArray, infoGrid_hubsAssigned, cost_matrix)
    totCo2Reduction = calcTotCo2Reduction(pointsArray, infoGrid_hubsAssigned)
    totTransEmissions = calcTotTransportationEmissions(pointsArray, infoGrid_hubsAssigned, cost_matrix)
    
    costEffectiveness = (totStorageCost + totTransCost) / (totCo2Reduction - totTransEmissions)
    
    return costEffectiveness 



'''
inputs: 
points - (numpy.ndarray) of candidate sites generated by spsann, with columns ['id', 'x', 'y']
<class 'numpy.ndarray'>
[[6.00000000e+00 1.40147278e+05 4.85147205e+05]
 [5.50000000e+01 1.23536593e+05 4.88606474e+05]
 [1.37000000e+02 9.89731085e+04 4.74291608e+05]]
 
infoGrid - (pandas.DataFrame) of study area, with columns ['X', 'totKgSupply', 'totKgDemand', 'x', 'y']
<class 'pandas.core.frame.DataFrame'>
       X   totKgSupply   totKgDemand              x              y
0      0  0.000000e+00  0.000000e+00  135034.635722  493256.830049
1      1  0.000000e+00  0.000000e+00  131034.635722  493256.830049
2      2  8.944132e+07  9.931876e+07  131034.635722  495256.830049

processing: 
calculate cost effectiveness of placing circular hubs at 'points'

returns: 
cost effectiveness value - in euros/tCO2eq reduction
'''
# -------- COST EFFECTIVENESS CALCULATION ------ 
# calculate cost effectiveness of one solution (with multiple open hubs)
# TODO: change inputs to (points, infoGrid)
def calcCostEffectiveness(pointsFromOptim, infoGridDf, ibis): 
  
    # -------- IMPORT PACKAGES ------- 
    from geovoronoi import voronoi_regions_from_coords
    import numpy as np
    import geopandas as gpd
    from shapely.geometry import Polygon


    # -------- MAKE POINTS GDF -------- 
    ibis.rename(columns={'pPerSqm': 'pricePerSqm'}, inplace=True)
    
    points = pointsFromOptim.copy()
    points = gpd.GeoDataFrame(
        points, geometry=gpd.points_from_xy(points.x, points.y), 
        crs='EPSG:28992'
    )
    points = points.merge(ibis[['RIN_NUMMER', 'pricePerSqm']], left_on='id', right_on='RIN_NUMMER')
    points = points[['id', 'x', 'y', 'pricePerSqm', 'geometry']]
    points.rename(columns={'id': 'hubName'}, inplace=True)
    
    
    # ---------  MAKE INFOGRID GDF -----------
    infoGrid = infoGridDf.copy()
    infoGrid = gpd.GeoDataFrame(
      infoGrid, geometry=gpd.points_from_xy(infoGrid.x, infoGrid.y), 
      crs='EPSG:28992'
    )
    
    # --------- ASSIGN HUBS TO INFOGRID CELLS --------- 
    
    # assign hubs to grid cells 
    def assignHubsToGridCells(points, infoGrid): 

        # coords: array of coordinates for open hubs
        points = gpd.GeoDataFrame(
            points, geometry=gpd.points_from_xy(points.x, points.y), 
            crs='EPSG:28992'
        )
        points = points.set_index('hubName')
        coords = np.array(points[['x', 'y']])

        # area_shape: polygon surrounding amsterdam (just make a square for now)
        minx, miny, maxx, maxy = infoGrid.total_bounds # get bounding box of infoGrid 
        area_shape = Polygon([(minx, miny), (minx, maxy), (maxx, maxy), (maxx,miny)]).buffer(50)

        # make voronoi regions and pts
        region_polys, region_pts = voronoi_regions_from_coords(coords, area_shape)

        # match hubName in hubRegions to hubsOpen 
        hubRegions = gpd.GeoDataFrame({'hubName': region_polys.keys(), 'geometry': region_polys.values()})
        hubRegions = hubRegions.set_crs('EPSG:28992')
        hubRegions = gpd.sjoin(hubRegions, points)
        hubRegions = hubRegions[['index_right', 'geometry']]
        hubRegions.rename(columns={'index_right': 'hubName'}, inplace=True)

        # assign each infoGrid cell to the nearest open hub 
        def findHubName(x):
            # x = Point 
            hubName = hubRegions[hubRegions.geometry.contains(x)].iloc[0].hubName
            return hubName
        infoGrid_hubsAssigned = infoGrid.copy()
        infoGrid_hubsAssigned['hubName'] = infoGrid_hubsAssigned.geometry.map(lambda x: findHubName(x))

        return infoGrid_hubsAssigned

    infoGrid_hubsAssigned = assignHubsToGridCells(points, infoGrid)    
    
    # -------- FUNCTIONS FOR CALCULATING COST EFFECTIVENESS COMPONENTS --------- 

    # calculate CO2 reduction for one hub
    def calcCo2Reduction(hubName, infoGrid_hubsAssigned):  
        # hubName = infoGrid.hubName.iloc[0] # 17 
        infoHub = infoGrid_hubsAssigned[infoGrid_hubsAssigned.hubName == hubName] 
        # get info for grid cells covered by hub 
        co2Emissions = 5000000000 # dummy number - tons of CO2eq emissions associated per kg of wood 
        totSupply = infoHub.totKgSupply.sum()
        totDemand = infoHub.totKgDemand.sum()
        matKgStored = totSupply if totDemand > totSupply else totDemand
        co2Reduction = co2Emissions * matKgStored
        return co2Reduction

    # calculate storage cost for one hub
    def calcStorageCost(hubName, infoGrid_hubsAssigned, points, kgPerM3=600, percLogistics=30, throughPut=12): 

        def calcStorCoef(kgPerM3, percLogistics, throughPut): 
            kg = kgPerM3 * 3 * (12/throughPut) # kg stored per m3 
            storCoef = (1+(percLogistics/100)) / kg 
            return storCoef

        infoHub = infoGrid_hubsAssigned[infoGrid_hubsAssigned.hubName == hubName]
        # sqm required to store 1 kg of material for 1 year
        storageCoef = calcStorCoef(kgPerM3, percLogistics, throughPut)

        # calculate matKgStored 
        totSupply = infoHub.totKgSupply.sum()
        totDemand = infoHub.totKgDemand.sum()
        matKgStored = totSupply if totDemand > totSupply else totDemand

        # find land price
        # pick housePrice in infoGrid cell closest to open hub
        landPrice = points[points.hubName == hubName].pricePerSqm.iloc[0] 

        # calculate storage cost 
        storageCost = landPrice * storageCoef * matKgStored

        # TODO: make differentiation between long and short term storage 
        return storageCost

    # calculate transportation cost for one hub
    def calcTransportationCost(hubName, infoGrid_hubsAssigned, points):
        infoHub = infoGrid_hubsAssigned[infoGrid_hubsAssigned.hubName == hubName]
        transPriceCoef = 50 # dummy number - 

        # find locations of demand and supply 
        hubDemand = infoHub[infoHub.totKgDemand > 0]
        hubSupply = infoHub[infoHub.totKgSupply > 0]

        # calc totDist and matKg for supply and demand 
        totDistSupply = hubSupply.distance(points[points.hubName == hubName].geometry.iloc[0]).sum() 
        # TODO: is currently euclidean distance, need to take into account street network
        matKgSupply = infoGrid_hubsAssigned.totKgSupply.sum() # is currently just sum of totKgSupply, without taking into account each trip 
        totDistDemand = hubDemand.distance(points[points.hubName == hubName].geometry.iloc[0]).sum()
        matKgDemand = infoGrid_hubsAssigned.totKgDemand.sum()

        # calc transportation cost 
        transportationCost = transPriceCoef * (totDistSupply * matKgSupply + totDistDemand * matKgDemand)

        # TODO: better model this - the hub will not travel to all supply and demand locations...right? 
            # the hub would travel to all supply locations but not all demand locations. 
            # it would travel to all supply locations to collect materials to be stored. 
            # if demand > supply, it would only travel to demand locations that it can satisfy with material stock. 
            # if this is not modelled properly transport emissions will always greatly excees CO2 reduction (i think)

        return transportationCost

    # calculate transportation emissions for one hub 
    def calcTransportationEmissions(hubName, infoGrid_hubsAssigned, points): 
        infoHub = infoGrid_hubsAssigned[infoGrid_hubsAssigned.hubName == hubName]
        transEmissionsCoef = 1 # dummy 

        # find locations of demand and supply 
        hubDemand = infoHub[infoHub.totKgDemand > 0]
        hubSupply = infoHub[infoHub.totKgSupply > 0]

        # calc totDist and matKg for supply and demand 
        totDistSupply = hubSupply.distance(points[points.hubName == hubName].geometry.iloc[0]).sum() 
        # TODO: is currently euclidean distance, need to take into account street network
        matKgSupply = infoGrid_hubsAssigned.totKgSupply.sum() # is currently just sum of totKgSupply, without taking into account each trip 
        totDistDemand = hubDemand.distance(points[points.hubName == hubName].geometry.iloc[0]).sum()
        matKgDemand = infoGrid_hubsAssigned.totKgDemand.sum()

        # calculate transportation emissions 
        transportationEmissions = transEmissionsCoef * (totDistSupply * matKgSupply + totDistDemand * matKgDemand)
        # TODO: better model this - see comments on calcTransportationCost

        return transportationEmissions

    # ---------- COST EFFECTIVENESS CALCULATION -------- 
    # calculate costs and emissions for each open hub
    def calcComponents(hubName): 
        # calculate sub-functions 
        storageCost = calcStorageCost(hubName, infoGrid_hubsAssigned, points)
        transportationCost = calcTransportationCost(hubName, infoGrid_hubsAssigned, points)
        co2Reduction = calcCo2Reduction(hubName, infoGrid_hubsAssigned)
        transportationEmissions = calcTransportationEmissions(hubName, infoGrid_hubsAssigned, points)
        return storageCost, transportationCost, co2Reduction, transportationEmissions

    points['subValues'] = points.hubName.map(lambda x: calcComponents(x))
    for i,v in enumerate(['storageCost', 'transportationCost', 'co2Reduction', 'transportationEmissions']): 
        points[v] = points.subValues.map(lambda x: x[i])
    points.drop(columns=['subValues'], inplace=True)

    # calculate cost effectiveness 
    storageCost = points.storageCost.sum()
    transportationCost = points.transportationCost.sum()
    co2Reduction = points.co2Reduction.sum()
    transportationEmissions = points.transportationEmissions.sum()
    
    costEffectiveness = (storageCost + transportationCost) / (co2Reduction - transportationEmissions)

    return costEffectiveness
