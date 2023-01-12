which(LETTERS == "R")
which(c(T,F,T,NA,F,F,T))# > 1 3 7
which((1:12)%%2 == 0) # which are even?
str(which(1:10 > 3, arr.ind=TRUE))

which(1:10 > 3, arr.ind=FALSE)

( m <- matrix(1:12,3,4) )
which(m %% 3 == 0)
which(m %% 3 == 0, arr.ind=TRUE)
rownames(m) <- paste("Case",1:3, sep="_")
which(m %% 5 == 0, arr.ind=TRUE)

dim(m) <- c(2,2,3); m
which(m %% 3 == 0, arr.ind=FALSE)
which(m %% 3 == 0, arr.ind=TRUE)

vm <- c(m);  dim(vm) <- length(vm) #-- funny thing with  length(dim(..)) == 1
which(vm %% 3 == 0, arr.ind=TRUE)