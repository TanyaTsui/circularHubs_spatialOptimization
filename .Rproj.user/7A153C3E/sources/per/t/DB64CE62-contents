library(spsann)
library(sf)
library(dplyr)
library(reticulate)
library(ggplot2)
use_condaenv('C:/Users/tpytsui/Miniconda/envs/geo_env') 


# ------ Read data (pre-processed in Python) ------
# candidate sites 
candiInfo <- st_read('data/candiInfo_ams.shp')
candi <- candiInfo %>% 
  st_coordinates() %>% 
  as.data.frame() %>% 
  rename('x' = 'X', 'y' = 'Y')

# future supply and demand
infoGrid <- st_read('data/infoGrid_ams.shp')

# first guesses for optimization algorithm 
firstGuesses <- read.csv('data/firstGuesses_ams.csv')
# convert firstGuesses$candiIndexes from comma separated str to vector 
strToVector <- function(x) {
  return(as.numeric(strsplit(x,',')[[1]]))
}
firstGuesses$candiIndexes <- lapply(firstGuesses$candiIndexes, strToVector)

# -------- define starting guesses -------- 
nHubs <- 45
candiIndex <- unlist(firstGuesses[nHubs, "candiIndexes"])
startingPoints <- candi[candiIndex, ]
startingPoints$id <- as.numeric(rownames(startingPoints))
startingPoints <- relocate(startingPoints, id)


# ---------- import costEffectiveness.py ---------------
source_python('costEffectiveness.py')
testFunction <- function(points) {
  testValue <- calcTotCostEffectiveness(points)
  return(testValue)
}

# ----- annealing schedule ------ 
schedule <- scheduleSPSANN(
  initial.temperature = 500
) 

# ----- Execute the simulated annealing algorithm ----- 
# make starting gdf of points (instead of letting optimUSER randomly select)
res <- optimUSER(
  points = startingPoints, fun = testFunction, 
  schedule = schedule, candi = candi, 
  plotit = TRUE
) 
resPoints <- st_as_sf(res$points, coords = c('x', 'y'))
st_write(resPoints, 'results/resPoints_45.shp')

# ------ plot results ----- 
# re-read data to avoid R from crashing
# candidate sites 
candiInfo <- st_read('data/candiInfo_ams.shp')
candi <- candiInfo %>% 
  st_coordinates() %>% 
  as.data.frame() %>% 
  rename('x' = 'X', 'y' = 'Y')
infoGrid <- st_read('data/infoGrid_ams.shp')

# I don't think I need this code below - check later 
infoGrid_plot <- infoGrid %>% 
  st_as_sf(coords = c('x', 'y')) %>% 
  st_set_crs(st_crs(resPoints))
candiInfo_plot <- candiInfo %>% 
  st_set_crs(st_crs(resPoints))
startingPoints_plot <- startingPoints %>% 
  st_as_sf(coords = c('x', 'y')) %>% 
  st_set_crs(st_crs(resPoints))

# plot 
ggplot() + 
  geom_sf(data = infoGrid_plot, aes(size=totKgDeman), color='darkgrey') + 
  geom_sf(data = candiInfo_plot, color='red', size=1, pch=15) + 
  geom_sf(data = resPoints, color='red', size=5, pch=15) + 
  geom_sf(data = startingPoints_plot, color='black', size=10, pch=7)

