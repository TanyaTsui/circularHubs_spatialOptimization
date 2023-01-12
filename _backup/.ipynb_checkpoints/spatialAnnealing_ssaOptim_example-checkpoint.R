## Not run: 
# handy tutorial about gstat: 
# https://cran.r-project.org/web/packages/gstat/vignettes/gstat.pdf 

# load libraries: 
library(intamapInteractive)
library(intamap)
library(gstat)

# load data:
# load meuse dataset from the gstat package, see https://cran.r-project.org/web/packages/gstat/vignettes/gstat.pdf
data(meuse) 
# set coordinates from columns x and y to 
# create spatial object out of meuse
coordinates(meuse) = ~x+y
# load meuse dataset as a grid 
data(meuse.grid)
# make spatial points dataframe 
coordinates(meuse.grid) = ~x+y
# spatial pixel dataframe (gridded structure)
gridded(meuse.grid) = TRUE
# make copy of meuse.grid 
predGrid = meuse.grid

# estimate variograms (OK/UK):
vgModel = vgm(1, "Exp", 300, 1)
vfitOK = fit.variogram(variogram(zinc~1, meuse), vgModel)
vfitUK = fit.variogram(variogram(zinc~x+y, meuse), vgModel)
vfitRK = fit.variogram(variogram(zinc~dist+ffreq+soil, meuse), vgModel)

# study area of interest:
bb = bbox(predGrid)
boun = SpatialPoints(data.frame(x=c(bb[1,1],bb[1,2],bb[1,2],bb[1,1],bb[1,1]),
                                y=c(bb[2,1],bb[2,1],bb[2,2],bb[2,2],bb[2,1])))
Srl = Polygons(list(Polygon(boun)),ID = as.character(1))
candidates = SpatialPolygonsDataFrame(SpatialPolygons(list(Srl)),
                                      data = data.frame(ID=1))

# add 20 more points assuming OK model (SSA method):
optimOK <- ssaOptim(meuse, meuse.grid, candidates = candidates, covariates = "over",
                    nDiff = 20, action = "add", model = vfitOK, nr_iterations = 10000, 
                    formulaString = zinc~1, nmax = 40, countMax = 200)

# add 20 more points assuming UK model (SSA method):
optimUK <- ssaOptim(meuse, meuse.grid, candidates = candidates, covariates = "over",
                    nDiff = 20, action = "del", model = vfitUK, nr_iterations = 10000, 
                    formulaString = zinc~x+y, nmax = 40, countMax = 200)

# add 20 more points with auxiliary variables (SSA method):
optimRK <- ssaOptim(meuse, meuse.grid, candidates = candidates, covariates = "over",
                    nDiff = 20, action = "add", model = vfitRK, nr_iterations = 10000, 
                    formulaString = zinc~dist+ffreq+soil, nmax = 40, countMax = 200)

## End(Not run)