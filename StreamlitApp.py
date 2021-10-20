import streamlit as st
import pandas as pd
import pydeck as pdk
import numpy as np
import folium
from branca.colormap import linear

st.set_page_config(page_title="Flight Delay/Cancellation Dashboard",
                   page_icon=":notes:",
                   layout='wide')

def load_data():
    data = pd.read_csv("cleaned.csv")
    data = data[["ORIGIN_LATITUDE", "ORIGIN_LONGITUDE", "FLIGHT_NUMBER", "ARRIVAL_DELAY", "CANCELLED", "AIRLINE", "ORIGIN_AIRPORT"]]
    data.columns = ["lat", "lon", "flight_num", "arr_delay", "cancelled", "airline", "airport"]
    airports = pd.read_csv("rawdata/airports.csv")
    airports = airports[["IATA_CODE", "AIRPORT", "LATITUDE", "LONGITUDE"]]
    airports.columns = ["code", "airport", "lat", "lon"]
    airports = airports.set_index(['code'])
    return data, airports

data, airports = load_data()

def delay_rate(delay_threshold):
    mask = data['arr_delay'] >= delay_threshold
    delayed = data[mask]
    delayed = delayed[["flight_num",'airport']]
    delayed = delayed.groupby(['airport']).count()
    all = data[["flight_num",'airport']]
    all = all.groupby(['airport']).count()
    ratio = pd.merge(all, delayed, how="outer", left_index=True, right_index=True)
    ratio = ratio.fillna(0)
    ratio["ratio"] = ratio["flight_num_y"] / ratio["flight_num_x"]
    ratio = pd.merge(ratio, airports, how="left", left_index=True, right_index=True)
    return ratio[["ratio", "lat", "lon", "airport"]]

def dataset_overview():
    st.title('A tour of dataset')
    '''
    ### Brief Introduction to dataset
    This dataset is retrieved from [Kaggle](https://www.kaggle.com/usdot/flight-delays) about 2015 flight delays and cancellations.
    More specifically, this dataset is based on U.S. Department of Transportation's tracking of on-time performance of domestic flights
    operated by large air carriers. This dataset includes multiple csv files that cover information about individucal flights (and their
    on-time performance), airline inforamtion, and airport information. I used them jointly to provide this visualization dashboard. 
    '''
    '''
    ### Pre-Processing of dataset
    Details of preprocessing can be checked out [here](https://github.com/IDSF21/assignment-2-cynthiadwq/blob/main/PreProcessing.ipynb) in Jupyter notebook form. Here are some highlights I would like to mention:
    - This dataset include 12 month flights data from 14 airlines, which is a huge amount of data. In order to make pre-processing 
    and visualization in my local machine, I chose January flights data from 3 major airlines: American Airline, Delta Airline and 
    United Airline. This sampled dataset contains 146875 flights, which should provide us a reasonable analysis on flight delay 
    and cancellation.
    - I joined flights data with corresponding origin and destination location data to enable visualization and analysis on map.
    '''


def location(delay_threshold):
    # use chicago O'Hare airport as first viewpoint
    main_map = folium.Map(location=(41.97960, -87.90446), zoom_start=4)
    delay_ratio = delay_rate(delay_threshold)
    colormap = linear.YlOrRd_04.scale(0, np.max(delay_ratio["ratio"]))
    colormap.add_to(main_map)
    for _, row in delay_ratio.iterrows():
        icon_color = colormap.rgb_hex_str(row['ratio'])
        #city_graph = city_graphs['for_map'][city.station_id][field_to_color_by]
        folium.CircleMarker(location=[row['lat'], row['lon']],
                    tooltip=f"{row['airport']} delay rate: %.3f" % row["ratio"],
                    fill=True,
                    fill_color=icon_color,
                    color=None,
                    fill_opacity=0.7,
                    radius=5,
                    ).add_to(main_map)
    return main_map

def airline_comp(delay_threshold):
    mask = data["cancelled"] == True
    cancelled = data[mask][["airline", "flight_num"]].reset_index(drop=True).groupby("airline").count()
    cancelled.columns = ["cancelled_count"]

    mask = data['arr_delay'] >= delay_threshold
    delayed = data[mask][["airline", "flight_num"]].reset_index(drop=True).groupby("airline").count()
    delayed.columns = ["delayed_count"]

    total = data[["airline", "flight_num"]].groupby("airline").count()
    total.columns = ["normal_count"]

    airline_comp = pd.merge(cancelled, delayed, left_index=True, right_index=True)
    airline_comp = pd.merge(airline_comp, total, left_index=True, right_index=True)
    airline_comp["delayed_rate"] = airline_comp["delayed_count"] / airline_comp["normal_count"]
    airline_comp["cancelled_rate"] = airline_comp["cancelled_count"] / airline_comp["normal_count"]
    airline_comp["normal_count"] = airline_comp["normal_count"] - airline_comp["delayed_count"] - airline_comp["cancelled_count"]
    airline_comp = airline_comp.rename(index={"AA": "American Airline", "UA": "United Airline", "DL": "Delta Airline"})
    return airline_comp


def table(delay_threshold):
    chart_data = airline_comp(delay_threshold)
    st.dataframe(chart_data.style.highlight_max(axis=0))


# Create a page dropdown 
st.sidebar.subheader("Please check out dropdown menu to explore questions you are interested in.")
page = st.sidebar.selectbox("What are you interested in?", [
    'Overview of dataset', 
    'Delay vs Origin Airport',
    'Delay/Cancel vs Airline',
])
if page == 'Overview of dataset':
    dataset_overview()
if page == "Delay vs Origin Airport":
    st.title("Delay vs Origin Airport")
    st.sidebar.write(
    "In this page, you can check out the relationship between origin airport and flight delay."
    )
    """
    You may notice that there are some airports have higher delay rates. In other words, flights take off from those 
    airports are more likely to encounter a delay. In order to explore if this thought is just bias or it's actually a fact 
    that can be proved by data, I visualize the origin airport delay rate over US map. With this visualization, we may also discover 
    the possible reasons that some origin airports are famous for delay flights. 
    """
    """
    **To begin with, please choose a threshold below to indicate how many minutes late do you consider as a delay?**
    """
    col1, col2 = st.columns(2)
    with col1:
        delay_threshload = st.slider('How many minutes do you considered a delay', min_value=0, max_value=120, value=30)

    st.write("""
    You can zoom into or out of the map. You can also get an airport's name and delay rate by hovering over it. The color bar indicates 
    the delay rate (number of delayed flights over number of all flights). The color more close to dark red indicates **high delay rate** while
    the color more close to light yellow indicates **low delay rate**. 
    """)
    main_map = location(delay_threshload)
    folium_static(main_map)
    """
    We can see from the map that there are definitely some airports which have significant higher delay rate than others (e.g. Montrose Regional Airport).
    By looking closely in the map, we can see that airports in Colorado region have high delay rate in general. It might be caused by geographical reason?
    Airports in New York area also have higher delay rate, which might be caused by the fact that three international airports too close to each other and 
    making the area too crowded.  
    """
if page == "Delay/Cancel vs Airline":
    st.title("Delay/Cancel vs Airline")
    st.sidebar.write(
    "In this page, you can check out the relationship between flight delay and its corresponding operating airline."
    )
    """
    You may notice that there are some airlines that have bad reputation, and people complain that their flights are often
    delayed or cancelled. I visualize a dataframe that shows the number of cancelled and delayed flights for each major 
    airline. Delayed rate and cancelled rate are also shown in table. For each column, the maximum number is highlighted
    in yellow.
    """
    """
    **To begin with, please choose a threshold below to indicate how many minutes late do you consider as a delay?**
    """
    col1, col2 = st.columns(2)
    with col1:
        delay_threshload = st.slider('How many minutes do you considered a delay', min_value=0, max_value=120, value=30)
    table(delay_threshload)
    """
    We can see that among three of them, United Airline has worst delay rate and cancell rate. In addition, Delta Airline 
    performs the best.
    """
