# Load and pre-process the data
data(meuse.grid, package = "sp") # data frame
boundary <- meuse.grid # data frame 
sp::coordinates(boundary) <- c("x", "y") # spatial point data frame 
sp::gridded(boundary) <- TRUE # spatial pixel dataframe
boundary <- rgeos::gUnaryUnion(as(boundary, "SpatialPolygons")) # spatial polygons
candi <- meuse.grid[, 1:2]
# ^ candidate sites - all rows, first 2 columns - coordinates of meuse grid 

# Set control parameters

# annealing settings 
schedule <- scheduleSPSANN(  
  initial.temperature = 30, x.max = 1540, y.max = 2060,
  x.min = 0, y.min = 0, cellsize = 40)

# user-defined objective: set as function 'objUSER' 
objUSER <- function (points, lags, n_lags, n_pts) {
  # points = matrix of coordinates (not a number)
  # dm = distance matrix of coordinates
  print(head(points))
  print(class(points))
  dm <- SpatialTools::dist1(points[, 2:3])
  
  ppl <- vector() # ppl = logical(0) (FALSE)
  for (i in 1:n_lags) { # n_lags = 9
    # n = array showing items in distance matrix between the two lag values
    # e.g. lag[1]=1, lag[2]=112, so showing items on dm between 1 and 112
    n <- which(dm > lags[i] & dm <= lags[i + 1], arr.ind = TRUE)
    # unique(c(n)) = points that are within 
    ppl[i] <- length(unique(c(n)))
  }
  
  # distri = repeat [n_pts], [n_lag] times = e.g. (10,10,10,10)
  # res = 
  distri <- rep(n_pts, n_lags) 
  res <- sum(distri - ppl) 
}
# set lags 
lags <- seq(1, 1000, length.out = 10)
set.seed(2001)

# Execute the simulated annealing algorithm
res <- optimUSER(
  points = 3, fun = objUSER, lags = lags, n_lags = 9,
  n_pts = 100, candi = candi, schedule = schedule,
  plotit = TRUE, boundary = boundary)
# points = n black dots 
# n_pts = ?? 
