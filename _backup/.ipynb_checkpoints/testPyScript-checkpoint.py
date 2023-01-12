import geopandas as gpd
import pandas as pd 

def read_infoGrid(file): 
    # file = 'data/infoGrid_ams.shp'
    test = gpd.read_file(file)
    test.totKgSuppl = test.totKgSuppl * 2
    test = test[['index', 'totKgSuppl']]
    return test

def change_infoGrid(infoGrid): 
    infoGrid = infoGrid.iloc[:, 0:3]
    return infoGrid