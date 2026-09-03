#!/usr/bin/env python 3

"""
hrdiagram.py
Niamh O Toole 01/11/2025

Description:
This script works with HST observations of NGC 1261 taken with 
the WFPC2 in the F336W and F555W filters. The primary goal is to 
create a Hertzsprung-Russell Diagram. The script contains functions 
for cosmic ray removal, star-finding, and photometry, before finally,
plotting the HR Diagram. 

Usage:
Run the script and it will return the HR Diagrams, along with other
plots from the other steps.

"""

import argparse
import numpy as np
import matplotlib.pyplot as plt
from glob import glob
from astropy.io import fits, ascii
from scipy.optimize import curve_fit
import scipy.ndimage as ndi
from astropy.stats import sigma_clipped_stats
from photutils.datasets import load_star_image
from photutils.detection import DAOStarFinder
from astropy.visualization import SqrtStretch
from astropy.visualization.mpl_normalize import ImageNormalize
from photutils.aperture import CircularAperture
from photutils.aperture import CircularAnnulus, ApertureStats, aperture_photometry

def cosmic_ray_removal(filelist, kind="median", axis=0):
    """
    Load the data array from each FITS file,
    combine the images into a stacked image,
    apply a median function to the stacked image 
    to produce a single combined image with cosmic
    rays removed.
    """
    
    # check if the filelist is empty and raise an error if it is
    if not filelist:
        raise ValueError("Filelist is empty.")
        
    # create an empty list for the image data
    data = []
    images = []
    # iterate over the files
    for file in filelist:
        with fits.open(file) as hdul:       # open each file
            primary_hdr = hdul[0].header
            image_data = hdul[1].data       # get the calibrated data from extension 1
            header = hdul[1].header
            data.append(image_data)
    
    stacked_image = np.asarray(data)
       
    # apply a median function to the stacked image
    if kind == "median":
        image = np.median(stacked_image, axis=axis) # axis=0 flattens the array along the column
        return image
    else:
        return ValueError(f"Unsupported combination function: {kind}")
    
def sigma_clipping(image, sigma):
    """
    A function to estimate the background and background noise
    of an image using sigma-clipped statistics.
    
    Parameters:
    -----------
    image: 'array'
        The image data for which the background needs to be estimated
        
    Returns:
    --------
    mean: 'float'
        clipped mean background value of image
    median: 'float'
        median pixel value
    std: 'float'
        clipped standard deviation, this is the background noise
    """
    mean, median, std = sigma_clipped_stats(image, sigma=sigma)
    return mean, median, std

def star_finding(image, median, std, image_name):
    """
    A function to find stars in an image using DAOStarFinder
    
    Parameters:
    -----------
    image: 'array'
        The image data
    median: 'float'
        The median pixel value of the image
    std: 'float'
        The background noise
        
    Returns:
    --------
    reduced_sources: astropy table
        A table of the stars found containing their x- and y-coordinates
        and other information such as the flux and roundness
    positions: 'array'
        An array of the x- and y-coordinates of the stars
    apertures: photutils apertures
        circular apertures centered on each of the stars
    
    """
    
    # use DAOStarFinder to find the stars and subtract the background
    # stars must have FWHMs of around 3 pixels, this specifies how wide the star can be
    # stars must be 6-sigma brighter than the background
    daofind = DAOStarFinder(fwhm=3.0, threshold=6.0*std)
    
    # create a mask to exclude the bad pixels at the edges of the image
    mask = np.zeros(image.shape, dtype=bool)
    
    mask[0:800, 0:35] = True
    mask[0:45, 0:800] = True
    
    # find the stars by subtracting the background from the image data
    # apply the mask defined above
    sources = daofind(image - median, mask=mask)
    
    # create a new mask to exclude sources that have negative flux
    # and sources that are too round
    mask = ((sources["flux"] > 0) 
            & (sources["roundness2"] >= -0.5)
            & (sources["roundness2"] <= 0.5)
    )
    
    # apply the mask to the sources found above
    reduced_sources = sources[mask]
    
    # plot the sources found
    # create an array of the x- and y-coordinates of all the stars found
    positions = np.transpose((reduced_sources["xcentroid"], reduced_sources["ycentroid"]))
    
    # create a circular apertures at the center of each star's position, with a radius of 4 pixels
    apertures = CircularAperture(positions, r=4.0)
    
    # normalize the image
    norm = ImageNormalize(stretch=SqrtStretch())
    
    # set the figure size
    plt.figure(figsize=(9, 7))
    # plot the image in greyscale
    plt.imshow(image, cmap="Greys", norm=norm, origin="lower", interpolation="nearest")
    # overlay the apertures in blue
    apertures.plot(color="blue", lw=1.5, alpha=0.5)
    plt.title(f"{image_name} Image with Apertures")
    plt.legend(["apertures"], loc="lower left")
    plt.savefig("image_with_apertures.png")
    plt.show()
    
    return positions, apertures

def perform_photometry(image, positions, apertures, image_name):
    """
    A function to perform photometry on an image with stars
    located and apertures defined by the coordinates of the stars.
    
    Parameters:
    -----------
    image: 'array'
        image data
    positions: 'array'
        An array of the x- and y-coordinates of the stars
    apertures: photutils apertures
        circular apertures centered on each of the stars
    
    Returns:
    --------
    star_data: Astropy Table
        A table of the stars in the image, columns include unique id
        of each star, the central pixel in x-axis, central pixel in
        y-axis, sum of the pixels inside each aperture (i.e. the flux),
        the total background noise.
    
    """
    # create an annulus around each of the stars with an inner radius of 5 and outer radius of 10
    # the annulus will measure the brightness around each star to find the background
    annulus = CircularAnnulus(positions, r_in=5, r_out=10)
    
    # plot the image with the apertures and annuli on top
    plt.figure()
    norm = ImageNormalize(stretch=SqrtStretch())
    plt.imshow(image, cmap="Greys", norm=norm, origin="lower")
    apertures.plot(color="blue", lw=1.5, alpha=0.5);
    annulus.plot(color="green", lw=1.5, alpha=0.5);
    plt.title(f"{image_name} Image with Apertures and Annuli")
    plt.legend(["apertures", "annuli"], loc="lower left")
    plt.savefig("image_with_annuli.png")
    plt.show()
    
    # use ApertureStats to find the background brightness using the annulus
    aperstats = ApertureStats(image, annulus)
    # find the mean of the background
    bkg_mean = aperstats.mean
    # find the area of each circular aperture
    aperture_area = apertures.area_overlap(image)
    # calculate the total background
    total_bkg = bkg_mean*aperture_area
    
    # perform the photometry using the aperture_photometry function
    # this sums up the pixel values in each aperture
    star_data = aperture_photometry(image, apertures)
    # append the total background values to the data table
    star_data["total_bkg"] = total_bkg
    
    # format the table
    for col in star_data.colnames:
        star_data[col].info.format = "%.8g"  # format the data to 8 significant figures
        
    ascii.write(star_data, f"{image_name}_star_data.dat", overwrite=True)
    
    return star_data

def flux_to_magnitudes(star_data):
    """
    A function to convert flux to apparent and absolute magnitudes.
    
    Parameters:
    -----------
    star_data: astropy table
        Data table for image
    
    Returns:
    --------
    absolute_magnitudes: 'list'
        List of the absolute magnitudes of the stars in the image
    
    """
    
    # define the zeropoint and exposure time
    zeropoint = -21.1
    exptime = 700.0
    
    # create an empty list for the apparent magnitudes
    apparent_magnitudes = []
    # iterate over the rows of the star_data table
    for line in star_data:
        flux = line["aperture_sum"]
        bkg = line["total_bkg"]
        apparent_magnitudes.append((-2.5*np.log10(abs(flux-bkg)/exptime))+zeropoint)
    
    # create an empty list for the absolute magnitudes
    absolute_magnitudes = []
    # iterate over the apparent magnitudes
    for magnitude in apparent_magnitudes:
        absolute_magnitudes.append((magnitude + 5 - 5 * np.log10(16.4e3)))
    
    return absolute_magnitudes

def hr_diagram(star_data1, star_data2):
    """
    A function to plot a Hertzsprung Russell diagram.
    
    Parameters:
    -----------
    star_data1: astropy table
        Data table for first image
    star_data2: astropy table
        Data table for second image
    
    Returns:
    --------
    2 HR Diagrams
    
    """
    # calculate the magnitudes for both images
    absolute_magnitudes1 = flux_to_magnitudes(star_data1)
    absolute_magnitudes2 = flux_to_magnitudes(star_data2)
    
    # calculate the color index
    colour_index = []
    # more sources were found for the second image so slice the data used for the second image so its the same length as the first
    for mag1, mag2 in zip(absolute_magnitudes1, absolute_magnitudes2[:len(star_data1)]):
        colour_index.append(mag1 - mag2)
        
    # plot the Hertzsprung Russell diagram with the colour index on the x-axis
    # and the absolute magnitudes of the sources in the first image on the y-axis
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.scatter(colour_index, absolute_magnitudes1, marker=".", color="black")
    ax.set_title("NGC 1261")
    ax.set_xlabel("$M_{f336w}$ - $M_{f555w}$")
    ax.set_ylabel("$M_{f336w}$")
    plt.savefig("f336w_hr_diagram.png")
    plt.show()
    
    # plot the Hertzsprung Russell diagram with the colour index on the x-axis
    # and the absolute magnitudes of the sources in the second image on the y-axis
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.scatter(colour_index, absolute_magnitudes2[:len(star_data1)], marker=".", color="black")
    ax.set_title("NGC 1261")
    ax.set_xlabel("$M_{f336w}$ - $M_{f555w}$")
    ax.set_ylabel("$M_{f555w}$")
    plt.savefig("f555w_hr_diagram.png")
    plt.show()
    
    return

def main():
    # filelists for both images
    filelist1 = glob("data\F336W\*.fits")
    filelist2 = glob("data\F555W\*.fits")
    
    # cosmic ray removal
    f336w = cosmic_ray_removal(filelist1)
    f555w = cosmic_ray_removal(filelist2)
    
    # sigma clipping
    f336w_mean, f336w_median, f336w_std = sigma_clipping(f336w, sigma=3.0)
    f555w_mean, f555w_median, f555w_std = sigma_clipping(f555w, sigma=3.0)
    
    # star finding
    f336w_positions, f336w_apertures = star_finding(f336w, f336w_median, f336w_std, image_name = "F336W")
    f555w_positions, f555w_apertures = star_finding(f555w, f555w_median, f555w_std, image_name = "F555W")
    
    # photometry
    f336w_star_data = perform_photometry(f336w, f336w_positions, f336w_apertures, image_name = "F336W")
    f555w_star_data = perform_photometry(f555w, f555w_positions, f555w_apertures, image_name = "F555W")
    
    # hr diagrams
    hr_diagram(f336w_star_data, f555w_star_data)
    
if __name__ == "__main__":
    # there are no arguments to pass
    main()
