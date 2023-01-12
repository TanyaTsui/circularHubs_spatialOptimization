library(spsann)
library(sf)
library(dplyr)
library(reticulate)
library(ggplot2)
use_condaenv('C:/Users/tpytsui/Miniconda/envs/geo_env') 


# ------ Read data (pre-processed in Python) ------
# candi - (df) of candidate hubs, with columns x and y 
candiInfo <- st_read('data/ibisForOptim.shp')
candi <- candiInfo %>% 
  st_coordinates() %>% 
  as.data.frame() %>% 
  rename('x' = 'X', 'y' = 'Y')

# infoGrid - (gdf) of area, showing future supply and demand of materials 
infoGrid <- read.csv('data/infoGrid_ams.csv')

# try importing costEffectiveness function with reticulate 
source_python('costEffectiveness.py')

# testing simpler function 
testFunction <- function(points) {
  testValue <- calcTotCostEffectiveness(points)
  return(testValue)
}

# ----- annealing settings ------ 
schedule <- scheduleSPSANN(
  initial.temperature = 500
) 

# ----- Execute the simulated annealing algorithm ----- 
# make starting gdf of points (instead of letting optimUSER randomly select)
res <- optimUSER(
  # 'points = 3' automatically makes df of 3 rows with columns 'id', 'x', and 'y'. 
  points = 3, fun = testFunction, 
  # infoGrid = infoGrid, candiInfo = candiInfo, # points = points
  schedule = schedule, candi = candi, # boundary = boundary
  plotit = TRUE
) 



# ----- Evaluate the optimized sample configuration ----- 
objSPSANN(res)
countPPL(res, candi = candi, lags = lags)
plot(res)

resPoints <- st_as_sf(res$points, coords = c('x', 'y'))
resPoints


# ------ plot results ----- 
infoGrid_plot <- infoGrid %>% 
  st_as_sf(coords = c('x', 'y'))
candiInfo_plot <- candiInfo %>% 
  st_set_crs(st_crs(resPoints))
ggplot() + 
  geom_sf(data = infoGrid_plot, aes(size=totKgDemand), color='darkgrey') + 
  geom_sf(data = candiInfo_plot, color='red', size=1, pch=15) + 
  geom_sf(data = resPoints, color='red', size=5, pch=15)

