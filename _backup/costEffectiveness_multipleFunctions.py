'''
inputs: 
points - (df) of candidate sites, with columns ['id', 'x', 'y']
infoGrid - (gdf) grid of study area, with columns ['index', 'totKgSup', 'totKgDem', 'geometry']

processing: 
calculate cost effectiveness of placing circular hubs at 'points'

returns: 
cost effectiveness value - in euros/tCO2eq reduction
'''

# assign hubs to grid cells 
# TODO: change hubsOpen to points - (df) of candidate sites, with columns ['id', 'x', 'y']
def assignHubsToGridCells(hubsOpen, infoGrid): 
    from geovoronoi import voronoi_regions_from_coords

    # coords: array of coordinates for open hubs
    hubsOpen['lon'] = hubsOpen.geometry.x
    hubsOpen['lat'] = hubsOpen.geometry.y
    coords = np.array(hubsOpen[['lon', 'lat']])

    # area_shape: polygon surrounding amsterdam (just make a square for now)
    minx, miny, maxx, maxy = infoGrid.total_bounds # get bounding box of infoGrid 
    area_shape = Polygon([(minx, miny), (minx, maxy), (maxx, maxy), (maxx,miny)]).buffer(50)

    # make voronoi regions and pts
    region_polys, region_pts = voronoi_regions_from_coords(coords, area_shape)

    # match hubName in hubRegions to hubsOpen 
    hubRegions = gpd.GeoDataFrame({'hubName': region_polys.keys(), 'geometry': region_polys.values()})
    hubRegions = hubRegions.set_crs('EPSG:28992')
    hubRegions = gpd.sjoin(hubRegions, hubsOpen)
    hubRegions = hubRegions[['hubName_right', 'geometry']]
    hubRegions.rename(columns={'hubName_right': 'hubName'}, inplace=True)

    # assign each infoGrid cell to the nearest open hub 
    def findHubName(x):
        # x = Point 
        hubName = hubRegions[hubRegions.geometry.contains(x)].iloc[0].hubName
        return hubName
    infoGrid_hubsAssigned = infoGrid.copy()
    infoGrid_hubsAssigned['hubName'] = infoGrid_hubsAssigned.geometry.map(lambda x: findHubName(x))
    
    return infoGrid_hubsAssigned

# ----- FUNCTIONS FOR CREATING STATS FOR ONE HUB -----

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
def calcStorageCost(hubName, infoGrid_hubsAssigned, kgPerM3=600, percLogistics=30, throughPut=12): 
    
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
    landPrice = hubCandidates[hubCandidates.hubName == hubName].pricePerSqm.iloc[0] 
    
    # calculate storage cost 
    storageCost = landPrice * storageCoef * matKgStored

    # TODO: make differentiation between long and short term storage 
    return storageCost

# calculate transportation cost for one hub
def calcTransportationCost(hubName, infoGrid_hubsAssigned):
    infoHub = infoGrid_hubsAssigned[infoGrid_hubsAssigned.hubName == hubName]
    transPriceCoef = 50 # dummy number - 
    
    # find locations of demand and supply 
    hubDemand = infoHub[infoHub.totKgDemand > 0]
    hubSupply = infoHub[infoHub.totKgSupply > 0]
    
    # calc totDist and matKg for supply and demand 
    totDistSupply = hubSupply.distance(hubCandidates[hubCandidates.hubName == hubName].geometry.iloc[0]).sum() 
    # TODO: is currently euclidean distance, need to take into account street network
    matKgSupply = infoGrid_hubsAssigned.totKgSupply.sum() # is currently just sum of totKgSupply, without taking into account each trip 
    totDistDemand = hubDemand.distance(hubCandidates[hubCandidates.hubName == hubName].geometry.iloc[0]).sum()
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
def calcTransportationEmissions(hubName, infoGrid_hubsAssigned): 
    infoHub = infoGrid_hubsAssigned[infoGrid_hubsAssigned.hubName == hubName]
    transEmissionsCoef = 1 # dummy 
    
    # find locations of demand and supply 
    hubDemand = infoHub[infoHub.totKgDemand > 0]
    hubSupply = infoHub[infoHub.totKgSupply > 0]
    
    # calc totDist and matKg for supply and demand 
    totDistSupply = hubSupply.distance(hubCandidates[hubCandidates.hubName == hubName].geometry.iloc[0]).sum() 
    # TODO: is currently euclidean distance, need to take into account street network
    matKgSupply = infoGrid_hubsAssigned.totKgSupply.sum() # is currently just sum of totKgSupply, without taking into account each trip 
    totDistDemand = hubDemand.distance(hubCandidates[hubCandidates.hubName == hubName].geometry.iloc[0]).sum()
    matKgDemand = infoGrid_hubsAssigned.totKgDemand.sum()
       
    # calculate transportation emissions 
    transportationEmissions = transEmissionsCoef * (totDistSupply * matKgSupply + totDistDemand * matKgDemand)
    # TODO: better model this - see comments on calcTransportationCost
    
    return transportationEmissions

# -------- COST EFFECTIVENESS CALCULATION ------ 
# calculate cost effectiveness of one solution (with multiple open hubs)
# TODO: remove sol from input (to match format of function in optimUSER)
def calcCostEffectiveness(sol, hubCandidates, infoGrid): 
    '''
    INPUT: 
    sol = [1,0,0,0,0] = list of open / close for hubs
    hubCandidates = gdf of candidate hubs 

    OUTPUT: 
    cost effectiveness of sol  
    '''

    # identify open (or 'chosen') facilities 
    hubsOpen = hubCandidates.copy() 
    hubsOpen.open = sol 
    hubsOpen = hubsOpen[hubsOpen.open == 1] # select open hubs according to sol 
    infoGrid_hubsAssigned = assignHubsToGridCells(hubsOpen, infoGrid, plot=False)
        
    # calculate costs and emissions for each open hub
    def calcComponents(hubName): 
        # calculate sub-functions 
        storageCost = calcStorageCost(hubName, infoGrid_hubsAssigned)
        transportationCost = calcTransportationCost(hubName, infoGrid_hubsAssigned)
        co2Reduction = calcCo2Reduction(hubName, infoGrid_hubsAssigned)
        transportationEmissions = calcTransportationEmissions(hubName, infoGrid_hubsAssigned)
        return storageCost, transportationCost, co2Reduction, transportationEmissions

    hubsOpen['subValues'] = hubsOpen.hubName.map(lambda x: calcComponents(x))
    for i,v in enumerate(['storageCost', 'transportationCost', 'co2Reduction', 'transportationEmissions']): 
        hubsOpen[v] = hubsOpen.subValues.map(lambda x: x[i])
    hubsOpen.drop(columns=['lon', 'lat', 'subValues'], inplace=True)

    # calculate cost effectiveness 
    storageCost = hubsOpen.storageCost.sum()
    transportationCost = hubsOpen.transportationCost.sum()
    co2Reduction = hubsOpen.co2Reduction.sum()
    transportationEmissions = hubsOpen.transportationEmissions.sum()

    costEffectiveness = (storageCost + transportationCost) / (co2Reduction - transportationEmissions)

    return costEffectiveness