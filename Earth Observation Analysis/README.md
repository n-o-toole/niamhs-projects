## Earth Observation Analysis

This folder features some work I have done in Python analysing Earth Observation images. The Python files are SENTINEL2.ipynb and earth_observation.py.
The rest of the files are results from this work, various graphs and plots that were produced.

SENTINEL 2.ipynb is a notebook where I worked on analysing and extracting features from Sentinel-2 images. The images featured different islands and the work included converting pixel distances to actual distances to measure land area and using thresholds, removing noise, and extracting contours to create a masked image of the islands to isolate it from the background. The folder also features a Python script (earth_observations.py) that was used to analyse images of a forest that experienced a wildfire. The Normalised Burn Ratio (NBR) was measured for each pixel in the images and this was plotted to show the changes over time as the forest was burned and the vegetation changed. Similarly, images of a lake were analysed to assess water quality over time. The Normalized Difference Turbidity Index (NDTI) was measured and plotted to illustrate this. The plots produced are included in the folder.
