
"""
earth_observations.py
Niamh O Toole 22/11/2025

Description:
A python script to complete analysis of earth observation data.

Usage:
Run the script in the same directory as the files and plots and
results are returned.
"""
import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from glob import glob
import pandas as pd
import tifffile as tiff

def calculate_NBR(file):
    """
    A function that loads in images and calculates the NBR for each 
    pixel in each image
    
    Parameters:
    -----------
    file: data files
    
    Returns:
    --------
    NBR: numpy.array
        Array of NBR values for each pixel in each image
    """
    # load the image
    image = tiff.imread(file)
    
    # used Chatgpt here to figure out why NIR = image[0] didnt work
    # band 1 = NIR reflectance
    NIR = image[:, :, 0].astype(np.float32)
    
    # band 2 = SWIR reflectance
    SWIR = image[:, :, 1].astype(np.float32)
    
    # NBR = (NIR - SWIR) / (NIR + SWIR)
    NBR = (NIR - SWIR) / (NIR + SWIR)
    
    return NBR

def time_evolution(files):
    """
    A function to calculate the NBR for a set of images and stack the
    results.
    
    Parameters:
    -----------
    files: data files
    
    Retunrs:
    --------
    NBR_stack: numpy.stack
        3D array of the NBR values for all the images
    """
    # create a list to store the NBR values for each image
    NBR_list = []
    
    # loop through the files
    for file in files:
        # calculate the NBR using the function
        NBR = calculate_NBR(file)
        # append to the list
        NBR_list.append(NBR)
        
    # stack the lists to create a 3-D array with results for all images
    NBR_over_time = np.stack(NBR_list)
    
    return NBR_over_time

def time_evolution_plot(files, x_pixel, y_pixel):
    """
    A function to plot the time evolution of the NBR
    
    Parameters:
    -----------
    files: data files
    x_pixel, y_pixel: pixel at which the NBR is calculated
    
    Returns:
    --------
    Plot of the NBR of the pixel over time
    """
    # calculate the NBR for each pixel in each image and return a stack of the results
    NBR_over_time = time_evolution(files)
    
    # create array of time_indices
    time = np.arange(1, 50)
    
    # create a list for the NBR of the central pixels
    center_NBR = []
    
    # loop through the images and extract the NBR for the central pixel
    for t in time:
        NBR = NBR_over_time[t, x_pixel, y_pixel]
        center_NBR.append(NBR)
        
    # convert center_NBR to an array
    NBR_array = np.asarray(center_NBR)
        
    # plot the NBR of the central pixel over time
    plt.figure(figsize=(9, 7))
    plt.scatter(time, NBR_array)
    plt.title(f"Time evolution of NBR at pixel ({x_pixel}, {y_pixel})", fontsize=16)
    plt.xlabel("Time", fontsize=14)
    plt.ylabel("NBR", fontsize=14)
    plt.xticks(fontsize=10)
    plt.yticks(fontsize=10)
    plt.tight_layout()
    plt.savefig(f"Time_evolution_pixel_{x_pixel}_{y_pixel}.png")
    plt.show()
    
    return

def key_times_plot(NBR_over_time):
    """
    A function to plot the NBR at key times
    
    Parameters:
    -----------
    NBR_stack: numpy.stack
        array of the NBR to be plotted
        
    Returns:
    --------
    Plot of the NBR at key times
    """
    # define key times
    time_indices = [0, 9, 12, 14, 19, 21, 24, 29, 39, 49]

    # plot NBR at different times
    plt.figure(figsize=(10,20))
    for i, t in zip(np.arange(len(time_indices)), time_indices):
        plt.subplot(5, 2, i+1)
        plt.imshow(NBR_over_time[t], cmap='RdYlGn', vmin=-1, vmax=1)
        plt.colorbar(label='NBR')
        plt.title(f"NBR Day {t+1}")
        plt.axis('off')
    plt.tight_layout()
    plt.savefig("NBR_key_times.png")
    plt.show()
    
    return

def plot_delta_NBR(NBR_over_time):
    """
    A function to plot the change in NBR at key times
    
    Parameters:
    -----------
    NBR_stack: numpy.stack
        array of the NBR to be plotted
        
    Returns:
    --------
    Plot of delta NBR at key times
    """
    # extract NBR at key times
    pre_fire = NBR_over_time[1]
    event = NBR_over_time[12]
    during_fire = NBR_over_time[20]
    post_fire = NBR_over_time[40]
    
    # calculate delta NBR
    delta_NBR1 = pre_fire - post_fire
    delta_NBR2 = pre_fire - during_fire
    delta_NBR3 = during_fire - post_fire
    delta_NBR4 = pre_fire - event
    
    plt.figure(figsize=(15,15))
    plt.subplot(2, 2, 1)
    plt.imshow(delta_NBR1, cmap='bwr', vmin=-1, vmax=1)
    plt.colorbar(label='ΔNBR')
    plt.title("ΔNBR from Day 1 to Day 40 (Burn Severity)")
    plt.axis('off')

    plt.subplot(2, 2, 2)
    plt.imshow(delta_NBR4, cmap='bwr', vmin=-1, vmax=1)
    plt.colorbar(label='ΔNBR')
    plt.title("ΔNBR from Day 1 to Day 12 (Burn Severity)")
    plt.axis('off')

    plt.subplot(2, 2, 3)
    plt.imshow(delta_NBR2, cmap='bwr', vmin=-1, vmax=1)
    plt.colorbar(label='ΔNBR')
    plt.title("ΔNBR from Day 1 to Day 20 (Burn Severity)")
    plt.axis('off')

    plt.subplot(2, 2, 4)
    plt.imshow(delta_NBR3, cmap='bwr', vmin=-1, vmax=1)
    plt.colorbar(label='ΔNBR')
    plt.title("ΔNBR from Day 20 to Day 40 (Burn Severity)")
    plt.axis('off')
    plt.savefig("Delta_NBR_key_times.png")
    plt.show()
    
    return

def detect_vegetation_change(files):
    """
    A function to autonomously check the data and provide a warning
    when a change in the vegetation is detected.
    
    Parameters:
    -----------
    files
    
    Returns:
    --------
    Prints average delta NBR and plots a graph that illustrates the method
    """
    # create a list to store the NBR values for each image
    NBR_list = []
    
    # loop through the files
    for file in files:
        # calculate the NBR using the function
        NBR = calculate_NBR(file)
        # append to the list
        NBR_list.append(NBR)
        
    # stack the lists to create a 3-D array with results for all images
    NBR_stack = np.stack(NBR_list)
    
    # create array of time indices
    time = np.arange(len(files) - 1)
    
    # create a list to store the delta NBR values
    delta_NBR = []
    
    # loop through the time indices and calculate delta NBR between each time
    for t in time:
        delta_NBR_initial = NBR_stack[0, 50, 50]
        delta_NBR_next = NBR_stack[t, 50, 50]
        delta_NBR.append(delta_NBR_initial - delta_NBR_next)
        
    avg = np.average(delta_NBR[:13])
    print(f"Average ΔNBR up to day 12 = {avg:.4f}")
        
    for delta in delta_NBR:
        if delta > 0.03 and delta < 0.1:
            print("ΔNBR above threshold!")
            break
    for delta in delta_NBR:
        if delta < -0.07:
            print("ΔNBR below threshold!")
            break
    
    # convert center_NBR to an array
    delta_NBR_array = np.asarray(delta_NBR)
        
    # plot the NBR of the central pixel over time
    plt.figure(figsize=(9, 7))
    plt.scatter(time, delta_NBR_array, label="$\Delta$NBR")
    plt.title("Time evolution of $\Delta$NBR", fontsize=16)
    plt.xlabel("Time", fontsize=14)
    plt.ylabel("$\Delta$NBR", fontsize=14)
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    plt.axhline(y=0.03, color='g', linestyle='--', label="Upper threshold")
    plt.axhline(y=-0.07, color='g', linestyle='--', label="Lower threshold")
    plt.axhline(y=-0.02, color='g', linestyle='-', label="Average")
    plt.tight_layout()
    plt.legend()
    plt.savefig("vegetation_change.png")
    plt.show()
    
    return

def plot_water_monitoring(file):
    """
    A function to plot NDTI and NDWI over time
    
    Parameters:
    -----------
    file: data file
    
    Returns:
    --------
    Plot of the NDTI and NDWI over time
    """
    # read the csv file
    water_monitoring = pd.read_csv(file)
    
    # format the time
    time_formatted = pd.to_datetime(water_monitoring["date"])
    water_monitoring.insert(1, "time_formatted", time_formatted)
    
    # extract data
    red = water_monitoring["band4_red"]
    green = water_monitoring["band3_green"]
    nir = water_monitoring["band8_nir"]
    
    # calculate NDTI and NDWI
    NDTI = (red - green) / (red + green)
    NDWI = (green - nir) / (green + nir)
    
    # insert NDTI and NDWI to table
    water_monitoring.insert(6, "NDTI", NDTI)
    water_monitoring.insert(7, "NDWI", NDWI)
    
    # find average NDTI and NDWI
    NDTI_avg = np.average(NDTI)
    NDWI_avg = np.average(NDWI)
    
    print(f"Average NDTI = {NDTI_avg:.3f}")
    print(f"Average NDWI = {NDWI_avg:.3f}")
    
    plt.figure(figsize=(20, 20))
    plt.subplot(2, 1, 1)
    plt.plot(water_monitoring["time_formatted"], water_monitoring["NDTI"])
    plt.title("NDTI vs Time", fontsize=16)
    plt.xlabel("Time", fontsize=14)
    plt.ylabel("NDTI", fontsize=14)
    plt.axhline(y=-0.095, color='r', linestyle='--', lw=0.8, label="Average NDTI")
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    plt.legend()
    
    plt.subplot(2, 1, 2)
    plt.plot(water_monitoring["time_formatted"], water_monitoring["NDWI"])
    plt.title("NDWI vs Time", fontsize=16)
    plt.xlabel("Time", fontsize=14)
    plt.ylabel("NDWI", fontsize=14)
    plt.axhline(y=0.625, color='r', linestyle='--', lw=0.8, label="Average NDWI")
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    plt.legend()
    plt.savefig("water_monitoring.png")
    plt.show()

    return

def main():
    # load in the images
    files = sorted(glob("*.tif"))
    # calculate the NBR for all the pixels in each image
    NBR_over_time = time_evolution(files)
    
    # plot the time evolution of the NBR at different pixels
    time_evolution_plot(files, 50, 50)
    time_evolution_plot(files, 30, 50)
    time_evolution_plot(files, 10, 10)
    time_evolution_plot(files, 90, 90)
    
    # plot the NBR at key times
    key_times_plot(NBR_over_time)
    
    # plot delta NBR at key times
    plot_delta_NBR(NBR_over_time)
    
    # run method for autonomously checking data and giving a warning for vegetation change
    detect_vegetation_change(files)
    
    # load water monitoring file
    water_monitoring = "water_monitoring.csv"
    
    # plot NDTI and NDWI over time
    plot_water_monitoring(water_monitoring)
    
if __name__ == "__main__":
    # there are no arguments to pass
    main()
