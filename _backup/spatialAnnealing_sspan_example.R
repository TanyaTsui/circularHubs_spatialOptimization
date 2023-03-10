library(spsann)

## Not run: 
# This example takes more than 5 seconds
require(sp)
require(SpatialTools)
data(meuse.grid)
candi <- meuse.grid[, 1:2]
schedule <- scheduleSPSANN(chains = 1, initial.temperature = 30,
                           x.max = 1540, y.max = 2060, x.min = 0, 
                           y.min = 0, cellsize = 40)

# Define the objective function - number of points per lag distance class
objUSER <-
  function (points, lags, n_lags, n_pts) {
    dm <- SpatialTools::dist1(points[, 2:3])
    ppl <- vector()
    for (i in 1:n_lags) {
      n <- which(dm > lags[i] & dm <= lags[i + 1], arr.ind = TRUE)
      ppl[i] <- length(unique(c(n)))
    }
    distri <- rep(n_pts, n_lags)
    res <- sum(distri - ppl)
  }
lags <- seq(1, 1000, length.out = 10)

# Run the optimization using the user-defined objective function
set.seed(2001)
timeUSER <- Sys.time()
resUSER <- optimUSER(points = 10, fun = objUSER, lags = lags, n_lags = 9,
                     n_pts = 10, candi = candi, schedule = schedule, 
                     plotit = TRUE)
timeUSER <- Sys.time() - timeUSER

# Run the optimization using the respective function implemented in spsann
set.seed(2001)
timePPL <- Sys.time()
resPPL <- optimPPL(points = 10, candi = candi, lags = lags, 
                   schedule = schedule, plotit = TRUE)
timePPL <- Sys.time() - timePPL

# Compare results
timeUSER
timePPL
lapply(list(resUSER, resPPL), countPPL, candi = candi, lags = lags)
objSPSANN(resUSER) - objSPSANN(resPPL)

## End(Not run)