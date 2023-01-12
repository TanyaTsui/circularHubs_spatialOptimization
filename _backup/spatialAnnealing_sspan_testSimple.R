library(spsann)
library(sf)
library(dplyr)

# Load and pre-process the data
data(meuse.grid, package = "sp") # data frame
boundary <- meuse.grid # data frame 
sp::coordinates(boundary) <- c("x", "y") # spatial point data frame 
sp::gridded(boundary) <- TRUE # spatial pixel dataframe
boundary <- rgeos::gUnaryUnion(as(boundary, "SpatialPolygons")) # spatial polygons
candi <- meuse.grid[, 1:2]
# ^ candidate sites - all rows, first 2 columns - coordinates of meuse grid 

# ----- annealing settings ------ 
# for some reason, initial temperature of 300-350 works better
schedule <- scheduleSPSANN(  
  initial.temperature = 300, x.max = 1540, y.max = 2060,
  x.min = 0, y.min = 0, cellsize = 40)

# ----- write function to find locations with the most copper ---- 
mostCopper <- function (points, plotit=FALSE) {
  # read meuse data 
  data(meuse)
  meuse <- meuse %>% 
    st_as_sf(coords = c('x', 'y'))
  
  # calculate 
  points <- points %>% 
    as.data.frame(points) %>% 
    st_as_sf(coords = c('x', 'y'))
  buffer <- st_buffer(points, 500)
  copper <- meuse[buffer,]
  copperSum <- sum(copper$copper)
  
  # plot
  if (plotit == TRUE) {
    plot(st_geometry(meuse))
    plot(st_geometry(copper), col='red', add=TRUE)
    plot(st_geometry(buffer), add=TRUE)
  }
  
  return(1 - copperSum) 
}

# ----- Execute the simulated annealing algorithm ----- 
res <- optimUSER(
  # 'points = 3' automatically makes df of 3 rows with columns 'id', 'x', and 'y'. 
  points = 3, fun = mostCopper, candi = candi, schedule = schedule,
  plotit = TRUE, boundary = boundary
) 


# ----- Evaluate the optimized sample configuration ----- 
objSPSANN(res)
countPPL(res, candi = candi, lags = lags)
plot(res, boundary = boundary)

resPoints <- st_as_sf(res$points, coords = c('x', 'y'))
class(resPoints)

data(meuse)
meuse <- meuse %>% 
  st_as_sf(coords = c('x', 'y'))
plot(st_geometry(meuse))
plot(st_geometry(resPoints), col='red', add=TRUE)
plot(st_geometry(st_buffer(resPoints, 500)), add=TRUE)
