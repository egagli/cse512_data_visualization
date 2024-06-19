#!pip -q install panel ipyleaflet ipywidgets_bokeh geopandas hvplot xarray_leaflet
import pandas as pd
import panel as pn
import holoviews as hv
import hvplot.pandas
import ipyleaflet
import geopandas as gpd
#import xarray_leaflet
from ipyleaflet import Map, CircleMarker, GeoJSON, LayerGroup, MarkerCluster, Popup
from holoviews.streams import Stream, param
import json

import xarray as xr
import panel as pn
import holoviews as hv
import ipyleaflet
import geopandas as gpd
from ipyleaflet import Map, GeoJSON
from holoviews.streams import Stream, param
import json
import folium
import folium.plugins
import matplotlib.pyplot as plt
# Initialize Panel extension
#pn.extension('plotly', 'ipywidgets')
#pn.extension('ipywidgets')

from leafmap import leafmap
import numpy as np
import branca
from ipywidgets import HTML

import html
import leafmap.foliumap as leafmap

pn.extension("ipywidgets", "folium", sizing_mode="stretch_width")

from shapely.geometry import shape, MultiPolygon
from threading import Timer
import asyncio

huc2_gdf = gpd.read_file('../data/huc2.geojson')

huc2_gdf['huc2'] = huc2_gdf['huc2'].astype('int32') 
huc2_14 = huc2_gdf[huc2_gdf['huc2']==14] 

huc10_gdf = gpd.read_file('../data/huc10_clusters_loc.geojson')
huc10_gdf.geometry = huc10_gdf.simplify(tolerance=0.01, preserve_topology=True)

huc10_swe = pd.read_csv('../data/swe_totals_ucrb.csv') 
huc10_swe = huc10_swe.rename(columns={'swe_snv_sum_m3':'Calculated SWE', 'swe_reanalysis_sum_m3':'Reanalysis SWE'}) 

swe_reanalysis = xr.open_dataset('../data/SWE_reanalysis_32yrs.nc',mask_and_scale=True)['SWE_Post'].rio.clip_box(miny=36,maxy=42,minx=-110,maxx=-100).where(lambda x: x>0).compute() 
swe_calculated = xr.open_dataset('../data/swe_calculated_snv.nc',mask_and_scale=True)['SWE_Post'].rio.write_crs('EPSG:32611').rio.reproject_match(swe_reanalysis).compute()

swe_reanalysis_coarsened = swe_reanalysis.coarsen(dim={'x':2,'y':2}, boundary='trim').mean().compute()
swe_calculated_coarsened = swe_calculated.coarsen(dim={'x':2,'y':2}, boundary='trim').mean().compute()

center = [huc10_gdf.to_crs('EPSG:4326').unary_union.centroid.y,huc10_gdf.to_crs('EPSG:4326').unary_union.centroid.x]



# Create the ipyleaflet map
def create_ipyleaflet_map():
    
    m = Map(center=center, zoom=6, scroll_wheel_zoom=True)

    # Add HUC2 GeoJSON layer
    huc10_layer = GeoJSON(
        data=json.loads(huc10_gdf.to_crs('EPSG:4326').to_json()),
        style={'color': 'black', 'weight': 2, 'fillColor': 'blue', 'fillOpacity': 0.1},
        hover_style={'fillColor': 'red', 'fillOpacity': 0.2},
        
        name='HUC10' # check
    )

    huc2_layer = GeoJSON(
        data=json.loads(huc2_14.to_crs('EPSG:4326').to_json()),
        style={'color': 'black', 'weight': 3, 'fillColor': 'none'},
        name='HUC2' # check
    )
    
    
    task = None

    def on_hover(event, feature, **kwargs):
        nonlocal task

        # Cancel the previous task if it's still running
        if task is not None:
            task.cancel()

        # Start a new task
        task = asyncio.create_task(add_popup(event, feature))

    async def add_popup(event, feature):
        # Add a delay before adding the popup
        await asyncio.sleep(0.1)

        properties = feature['properties']
        code = properties.get('huc10', 'Unknown')
        name = properties.get('name', 'Unknown')  # Assuming 'name' is the property containing the watershed name

        # Get the coordinates from the feature
        geometry = shape(feature['geometry'])
        if isinstance(geometry, MultiPolygon):
            # Use the representative point of the largest polygon
            largest_polygon = max(geometry, key=lambda polygon: polygon.area)
            coordinates = list(largest_polygon.representative_point().coords)[0]
        else:
            # Use the representative point of the polygon
            coordinates = list(geometry.representative_point().coords)[0]

        # Reverse the coordinates to [latitude, longitude]
        coordinates = coordinates[::-1]

        # Create a popup with the name and code
        message = HTML()
        message.value = f"Watershed Name: {name}<br>Code: {code}"
        popup = Popup(location=coordinates, child=message, close_button=False, auto_close=True, close_on_escape_key=True, auto_pan=False)

        # Remove existing popups
        for layer in m.layers:
            if isinstance(layer, Popup):
                m.remove_layer(layer)
                
            # Wait until the previous popup has been fully removed
        while any(isinstance(layer, Popup) for layer in m.layers):
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.1)

        # Add the new popup
        m.add_layer(popup)
        
# Add the hover handler to the GeoJSON layer
    huc10_layer.on_hover(on_hover)

    # Add click event to GeoJSON layer
    def on_click(event, feature, **kwargs):
        properties = feature['properties']
        code = properties.get('huc10', 'Unknown')
        #click_stream.event(code=code)
        click_stream.code = code
        click_stream.param.trigger('code')
        center = [huc10_gdf[huc10_gdf['huc10'] == code].geometry.centroid.y.values[0], huc10_gdf[huc10_gdf['huc10'] == code].geometry.centroid.x.values[0]]
        update_folium_map()
        print(f'HUC code clicked: {code}')  # Debugging statement

    huc10_layer.on_click(on_click)
    m.add_layer(huc2_layer)
    m.add_layer(huc10_layer)

    return m

def create_folium_map(year,code=None):
    m = leafmap.Map(center=center,zoom=6, zoom_control=False, draw_control=False, search_control=False, measure_control=False, fullscreen_control=False, attribution_control=False)
    #zoom_level = m.zoom
    
    if (year == 1990) & (code is None or code == ''):
        # DISPLAY COARSENED SPLITMAP
        print(f'default')
        m.split_map(left_layer=swe_reanalysis_coarsened.sel(Year=year), left_args={'vmin':0,'vmax':1,'cmap':'Blues','nodata':np.nan}, right_layer=swe_calculated_coarsened.sel(Year=1990-year),right_args={'vmin':0,'vmax':1,'cmap':'Blues','nodata':np.nan})
        m.add_gdf(huc2_14, layer_name='HUC2',zoom_to_layer=True, style={'color': 'black', 'weight': 2,'fillColor': 'blue', 'fillOpacity': 0.0},info_mode=None) 
    else:
        m.split_map(left_layer=swe_reanalysis.sel(Year=year), left_args={'vmin':0,'vmax':1,'cmap':'Blues','nodata':np.nan}, right_layer=swe_calculated.sel(Year=1990-year),right_args={'vmin':0,'vmax':1,'cmap':'Blues','nodata':np.nan})
        m.add_gdf(huc2_14, layer_name='HUC2',zoom_to_layer=True, style={'color': 'black', 'weight': 2,'fillColor': 'blue', 'fillOpacity': 0.0},info_mode=None)
    
    
    if code:
        m.add_gdf(huc10_gdf[huc10_gdf['huc10'] == code], layer_name='HUC10',zoom_to_layer=True, style={'color': 'black', 'weight': 2,'fillColor': 'blue', 'fillOpacity': 0.0},info_mode=None)
        #huc10_gdf[huc10_gdf['huc10'] == code].boundary.plot(color='black',linewidth=2)
    
    m.add('inspector')
    cm_swe= branca.colormap.linear.Blues_09.scale(0,1,max_labels=10).to_step(100)
    cm_swe.add_to(m)
    #m.add_colormap()
    return m


# Create the map
ipyleaflet_map = create_ipyleaflet_map()
# Define a stream to capture map clicks
class ClickStream(Stream):
    code = param.String(default='')

# Instantiate the click stream
click_stream = ClickStream()

def create_plot(code):
    print(f'Code received in create_plot: {code}')  # Debugging statement
    
    code_pass = False
    try:
        code = int(code)
        code_pass = True
        
    except:
        code = 1401000107
        #code_pass = True
        
    if code_pass:
        filtered_data = huc10_swe[huc10_swe['huc10_id'] == code]
        plot = filtered_data.hvplot.line(x='year', y=['Calculated SWE', 'Reanalysis SWE'],
                                        value_label='Total SWE in Watershed ($m^3$)',
                                        title=f"{filtered_data.iloc[0]['name']}")
        plot.opts(legend_position='bottom', legend_cols=2)
    else:
        # Create a blank NdOverlay object with the same dimensions as the line plot
        kdims = ['year']
        vdims = ['Calculated SWE', 'Reanalysis SWE']
        plot = hv.NdOverlay({0: hv.Curve([], kdims, vdims)})

        plot.opts(title='Select a HUC10 watershed on the left.',legend_position='bottom', legend_cols=2)


    return plot

# Define a DynamicMap that updates based on the click stream
dynamic_map = hv.DynamicMap(lambda code: create_plot(code), streams=[click_stream.param.code])



# Convert ipyleaflet map to Panel

def update_folium_map(event=None):
    if event:
        year = event.new
    else:
        year = year_slider.value_throttled
    new_folium_map = create_folium_map(year,code=click_stream.code)
    new_escaped_html = html.escape(new_folium_map.to_html())
    new_iframe_html = f'<iframe srcdoc="{new_escaped_html}" style="height:100%; width:100%" frameborder="0"></iframe>'
    folium_pane.object = new_iframe_html

folium_map = create_folium_map(1990)  # Start with the initial year
#folium_pane = pn.pane.plot.HTML(html.escape(folium_map.to_html()), height=400, width=400)
escaped_html = html.escape(folium_map.to_html())

# Create iframe embedding the escaped HTML and display it
iframe_html = f'<iframe srcdoc="{escaped_html}" style="height:100%; width:100%" frameborder="0"></iframe>'

# Display iframe in a Panel HTML pane
folium_pane = pn.pane.HTML(iframe_html, height=350, sizing_mode="stretch_width")

year_slider = pn.widgets.IntSlider(name='Year', format='0', start=1990, end=2021)
year_slider.param.watch(update_folium_map, 'value_throttled')



ipyleaflet_pane = pn.pane.IPyWidget(ipyleaflet_map, height=400, width=400)

# Create the layout
#layout = pn.Row(ipyleaflet_pane, pn.panel(dynamic_map, height=400, width=400),folium_pane,year_slider)

gspec = pn.GridSpec(sizing_mode='stretch_both')
gspec[0, 0] = pn.Column(ipyleaflet_pane, margin=(0, 0, 10, 0))
gspec[0, 1] = pn.Column(folium_pane, height=400, margin=(0, 0, 10, 0))
gspec[1, 1] = pn.Column(year_slider, height=50, margin=(0, 0, -55, 0))
gspec[1, 0] = pn.Column(pn.panel(dynamic_map,min_height=300, sizing_mode='stretch_both'), min_height=300, sizing_mode='stretch_both', margin=(0, 0, -95, 0))

# Create a custom template
template = pn.template.MaterialTemplate(
    title='Snow Dashboard          &#10052;    &#10052;    &#10052;'
    #favicon='../snow_favicon.ico'  
)
subtitle = pn.pane.Markdown(
   """
        ## Interactive Snow Dashboard: Explore snow water equivalent (SWE) data using a new estimation method!
          
        Snow is an important water resource in the Upper Colorado River Basin (UCRB). It delays the timing of runoff so that winter precipitation enters streams and reservoirs in the spring and summer, when demand for irrigation and drinking water is highest. Current-season estimates of snow water equivalent (SWE) - the amount of water stored in the snowpack - are critical to allocating water resources correctly. Water managers currently rely on point measurements (from the SNOTEL network) of SWE that are sparsely located throughout the UCRB, but the spatial variability of SWE makes point measurements inadequate representations of distributed SWE. Current methods can back-calculate distributed SWE once snow melts (called SWE Reanalysis), but are unable to accurately estimate current SWE. Water managers need new tools and datasets to calculate the total amount of SWE in each watershed before melt-out.  

        Here we present a novel method to estimate current-year SWE using historic SWE patterns and statistics. In previous work, we showed that the standard normal variates (Eq 1) are consistent within large regions. We calculated standard normal variates for April 1st SWE, and clustered to find regions in the UCRB that have similar standard normal variates. Using 30 years of SWE Reanalysis data, we calculate the 30-year mean and standard deviation of SWE at each Reanalysis grid cell. Then we use a nearby point measurement (from SNOTEL) of the current-year standard normal variate. We can rearrange Eq 1 so that we can calculate SWE at any gridcell. Then we can calculate the total SWE within each HUC10 watershed. (HUC10 watersheds are a certain sized watershed delineated by the U.S. Geological Survey.)  

        Equation 1.    $$Standard Normal Variate = \frac{SWE_{current year} - Mean_{30-year}}{Standard Deviation_{30-year}}$$  
        Equation 2. $$SWE_{current year} = Standard Normal Variate_{current year} * Standard Deviation_{30-year} + Mean_{30-year}$$  
  
        To use the dashboard, select a HUC10 watershed within the UCRB in the left panel. The Reanalysis and Calculated SWE gridded data will populate the right panel, and a timeseries of total watershed SWE on April 1 will populate the bottom panel. Water managers can hover over the bottom plot to see exactly how much SWE (in acre-feet) were calculated in each watershed using our method vs. the Reanalysis dataset. The calculated datset will be extended to 2024 soon, to provide current-year April 1 SWE. 
        """,
    margin=(0, 0, 20, 0)
    
)
# titles = pn.pane.Markdown(
#     """
#     <h3 style="font-size:24px; margin-bottom: 10px;">Pick a Basin!</h3>         <h3 text-align = right; style="font-size:24px; margin-bottom: 10px;">Calculated SWE vs. Reanalysis SWE</h3>  

#     """,
#     margin=(0, 0, 10, 0)
    
# )
titles = pn.pane.Markdown(
    """
    <div>
        <h3 style="font-size:24px; margin-bottom: 10px; display: inline-block;">Pick a watershed!</h3>
        <h3 style="font-size:24px; margin-bottom: 10px; float: right;">Calculated SWE vs. Reanalysis SWE</h3>
    </div>
    """,
    margin=(0, 0, 10, 0)
)

template.main.insert(0, subtitle)
template.main.insert(1, titles)


# Add the GridSpec layout to the template
template.main.append(gspec)


# Define the Panel app
def panel_app():
    #pn.state.add_periodic_callback(lambda: None, period=100, count=100)
    #return layout
    #return gspec
    return template

# Start the server
pn.serve({'/': panel_app}, port=5329, show=True)