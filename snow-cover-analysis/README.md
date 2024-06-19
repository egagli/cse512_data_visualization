## Snow Cover Analysis Final Project
#### How to launch the dashboard:
* Clone the repository
* Navigate to the notebooks/snow_dashboard.ipynb
* Create an empty environment by running: conda create --name <myenv>  
* Activate the new environment by running: conda activate <myenv>  
* Run the top cell of the notebook to pip install the necessary packages
* Restart the notebook kernel
* Run the notebook, explore the data!

#### Overview
The majority of the western United States relies on snow melt for water supply. Quantifying how much water will melt from the seasonal snowpack, referred to as snow water equivalent (SWE), is difficult due to lack of in situ observations and current limitations of snow remote sensing. A commonly used network of snow pillows, SNOTEL sites, exists throughout the western US but does not resolve the spatial and temporal distribution of snow, which is highly variable in space and time. SWE reanalysis products have been created to address this issue, but they back-calculate SWE so do not provide information about the current year. Here, we present a visual exploratory tool for water resources managers to estimate SWE in a novel way, using both a SWE reanalysis product and the SNOTEL networks.
#### How to use the visualization:
Here, we present a three-panel display:

**Left Panel:** This panel shows watershed polygons in the Upper Colorado River Basin. Selecting a watershed from the left panel triggers updates in the right and bottom panels.

**Bottom Panel:** This panel displays a time series graph of the sum of the Snow Water Equivalent (SWE) on April 1st (generally excepted as the date of peak SWE) of each year from 1990 to 2021. The graph provides an overview of the SWE trends over the selected period and allows for a direct comparison between the datasets. Hover over individual years to see the exact SWE totals.

**Right Panel:** This panel shows the spatial distribution of the SWE within the selected watershed. It includes the following features:

* Time Slider: Allows you to select and view SWE data for April 1st of the selected year.
* Split Maps: Enables comparison of two different gridded datasets. Here, we compare the spatial distribution of the calculated SWE data to the SWE reanalysis data sets.
This interactive layout allows for a comprehensive analysis of SWE data across different temporal and spatial scales.
