#!/usr/bin/env Rscript --vanilla
# Author: Cody Martin
# Email: ccmartin6@wisc.edu
# Current Institution: University of Wisconsin-Madison
#                      Department of Bacteriology
# Created while affiliated with:
#   Texas A&M University
#   Dr. Ry Young lab
#   Department of Biochemistry & Biophysics
#   Center for Phage Technology
# 
# Date: June 12, 2021

pkgs <- c("ggplot2", "ggprism", "ggrepel")
# Check if packages are installed
for (p in pkgs) {
  if(! p %in% installed.packages()){
    install.packages(p, dependencies = TRUE)
  }
}

# Load packages
invisible(lapply(pkgs, library, character.only=T))

# Set working directory
# should default to github repo
# change for your machine if needed
# setwd("~/Documents/CPT/N4/plate_reader")

# Read in data from command line argument
#file <- "output/testdata1_long_PROCESSED.csv"
args <- commandArgs(trailingOnly=T)
file <- args[1]
data <- read.csv(file)

# define custom offset to move line labels away from axis
offset <- max(data$Time)*0.065

# ggprism has custom defined vectors for 
# color and shape palettes, but if your 
# number of groups is too large, you will 
# get warning messages about you supplied
# too many different groups. We need to make 
# a vector that repeats the custom palettes
# multiple times to ensure that there are enough
# shapes and colors for a 96-well plate experiment.
cols_it <- rep(ggprism_data$colour_palettes$colors, 5)
shapes_it <- rep(ggprism_data$shape_palettes$complete$name, 5)

# make ggplot object
g <- ggplot(data, aes(x=Time, y=Mean)) +
  geom_line(aes(color=Group), size=1.25) +
  geom_point(aes(shape=Group), fill="black", size=2.5) +
  geom_errorbar(aes(ymin=Mean-SEM, 
                    ymax=Mean+SEM, 
                    color=Group),
                width=0.05
                ) +
  geom_text_repel(data=subset(data, Time == max(data$Time)), # labels next to lines
                  aes(label=Group, 
                      color=Group, 
                      x=Inf, # put label off plot
                      y=Mean), # put label at same height as last data point
                  direction="y",
                  xlim=c(max(data$Time)+offset, Inf), # offset labels
                  min.segment.length=Inf, # won't draw lines
                  hjust=0, # left justify
                  size=5,
                  fontface="bold") +
  scale_shape_manual(values=shapes_it) + # use prism defined shapes
  scale_color_manual(values=cols_it) +
  scale_y_continuous(limit=c(0,max(data$Mean)*1.1),
                     minor_breaks=seq(0,ceiling(max(data$Mean)*10)/10, 0.01),
                     guide="prism_minor",
                     expand=c(0,0)) + 
  scale_x_continuous(minor_breaks=seq(0,max(data$Time),by=1/3),
                     guide="prism_minor",
                     expand=c(0.025,0.025)) + 
  labs(x="Time (hr)",
       y="OD600") +
  theme_prism(border=T) + # theme like prism plot
  coord_cartesian(clip="off") +
  theme(aspect.ratio=1/1, 
        legend.position="none", 
        plot.margin=unit(c(1,5,1,1), "lines"))

# save plot as .png
save = paste0(strsplit(file, ".csv")[[1]], "_Rplot.png")
png(save, width=7.5, height=7.5, units="in", res=200)
g
invisible(dev.off())
print(paste0("Saved: ", save))