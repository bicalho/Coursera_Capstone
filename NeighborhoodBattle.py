#%% [markdown]
#  # Neighborhood Recommendation System
#  In this project, we will create a recommendation system for neighborhoods based on the venues located in them and the users interests.
#%% [markdown]
#  ## Import the librarys nedded

#%%
import numpy as np # library to handle data in a vectorized manner

import pandas as pd # library for data analsysis
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

import json # library to handle JSON files

import geocoder
from geopy.geocoders import Nominatim # convert an address into latitude and longitude values

import requests # library to handle requests
from pandas.io.json import json_normalize # tranform JSON file into a pandas dataframe

# Matplotlib and associated plotting modules
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors


import folium # map rendering library

from bs4 import BeautifulSoup
import csv

import random


print('Libraries imported.')

#%% [markdown]
#  ## Get the html from the wikipedia page with the postal codes of Canada

#%%
source = requests.get('https://en.wikipedia.org/wiki/List_of_postal_codes_of_Canada:_M').text

soup = BeautifulSoup(source, 'lxml')

#%% [markdown]
# Now that we have the html, we need to find the table in it.
# 

#%%
table = soup.find('table')

#%% [markdown]
# Also, we need to create the csv file in which we will save the necessary data

#%%
csv_file = open('csv_toronto_neighborhood.csv', 'w')
csv_writer = csv.writer(csv_file)

#%% [markdown]
# ## Write the header in the csv file

#%%
row = []

for th in table.find_all('th'):
    row_value = th.text.rstrip()
    
    row.append(row_value)
print(row)
csv_writer.writerow(row)

#%% [markdown]
# ## Write all the data on the csv file
#%% [markdown]
# It's important to remove the data with no Borough assigned and write the Borough name as neighborhood if no neighborhood is assigned

#%%
for tr in table.find_all('tr'):
    i=0
    row=[]
    discard = False
    postalCode = None
    borough = None
    neighborhood = None
    for td in tr.find_all('td'):
        if i==0:
            postalCode = td.text.rstrip()
        elif i==1:
            if (td.text.rstrip() == 'Not assigned'):
                discard = True
            else:
                borough = td.text.rstrip()
        else:
            i=0
            if (td.text.rstrip() == 'Not assigned'):
                neighborhood = borough
            else:
                neighborhood = td.text.rstrip()
        i=i+1
    if (discard == False):
        row.append(postalCode)
        row.append(borough)
        row.append(neighborhood)
        csv_writer.writerow(row)
        #print(row)

#%% [markdown]
# Close the csv file to save the modifications

#%%
csv_file.close()

#%% [markdown]
# ## Open the new csv file

#%%
df = pd.read_csv('csv_toronto_neighborhood.csv')
df.head()


#%%
df.shape

#%% [markdown]
# ## Group Neighbourhoods with the same Postcode

#%%
df_mod = df.groupby(['Postcode', 'Borough'])['Neighbourhood'].apply(lambda x: "%s" % ', '.join(x))
df_mod = df_mod.reset_index()
#Rename to fix the name Neighbourhood to Neighborhood
df_mod = df_mod.rename(columns={'Neighbourhood': 'Neighborhood'})
df_mod.head()


#%%
df_mod.shape

#%% [markdown]
# ## Get the latitue and longitude of each Postal code
#%% [markdown]
# we can download the CSV from http://cocl.us/Geospatial_data

#%%
url = 'http://cocl.us/Geospatial_data'
df_geo=pd.read_csv(url)


#%%
df_geo.head()

#%% [markdown]
# Now we can merge both datas to create a full Toronto dataset with Postal code, boroughs, neighborhoods and geospatial data

#%%
df_toronto = df_mod.join(df_geo.set_index('Postal Code'), on='Postcode')
df_toronto.head()

#%% [markdown]
# ## Using the Foursquare API
#%% [markdown]
# We can use the Foursquare API to get the venues of each neighborhood. But first, let's get the latitude longitude of Toronto.

#%%
address = 'Toronto, Ontario'

geolocator = Nominatim(user_agent="toronto_explorer")
location = geolocator.geocode(address)
latitude = location.latitude
longitude = location.longitude
print('The geograpical coordinate of Toronto are {}, {}.'.format(latitude, longitude))

#%% [markdown]
# We can also print the map of toronto with all neighborhoods marked on it to help visualize

#%%
# create map of Toronto using latitude and longitude values
map_Toronto = folium.Map(location=[latitude, longitude], zoom_start=10)

# add markers to map
for lat, lng, borough, neighborhood in zip(df_toronto['Latitude'], df_toronto['Longitude'], df_toronto['Borough'], df_toronto['Neighborhood']):
    label = '{}, {}'.format(neighborhood, borough)
    label = folium.Popup(label, parse_html=True)
    folium.CircleMarker(
        [lat, lng],
        radius=5,
        popup=label,
        color='blue',
        fill=True,
        fill_color='#3186cc',
        fill_opacity=0.7,
        ).add_to(map_Toronto)  
    
map_Toronto

#%% [markdown]
# Those are the possible recommendations spots for our recommendation system.
#%% [markdown]
# Before using the Foursquare API, we need to enter the client credentials and secret.

#%%
# @hidden_cell
CLIENT_ID = 'OKNYTCECCAN5OE4SE0BRVL2YJBPDX3J2KFMPZQE4C5XOI4H4' # your Foursquare ID
CLIENT_SECRET = 'WHNEDNAGZHBZEPC0ZXDF4NNGZDWD053IRNDKLPA5WKO54EFT' # your Foursquare Secret
VERSION = '20180605' # Foursquare API version

#%% [markdown]
# We define a maximum of 100 venues and a 500 meters radius from the center of the neighborhood

#%%
LIMIT = 100
radius = 500

#%% [markdown]
# Define a fundction to extract the nearby venues from the json that returns from the API request

#%%
def getNearbyVenues(names, latitudes, longitudes, radius=500):
    
    venues_list=[]
    for name, lat, lng in zip(names, latitudes, longitudes):
        print(name)
            
        # create the API request URL
        url = 'https://api.foursquare.com/v2/venues/explore?&client_id={}&client_secret={}&v={}&ll={},{}&radius={}&limit={}'.format(
            CLIENT_ID, 
            CLIENT_SECRET, 
            VERSION, 
            lat, 
            lng, 
            radius, 
            LIMIT)
            
        # make the GET request
        results = requests.get(url).json()["response"]['groups'][0]['items']
        
        # return only relevant information for each nearby venue
        venues_list.append([(
            name, 
            lat, 
            lng, 
            v['venue']['name'], 
            v['venue']['location']['lat'], 
            v['venue']['location']['lng'],  
            v['venue']['categories'][0]['name']) for v in results])

    nearby_venues = pd.DataFrame([item for venue_list in venues_list for item in venue_list])
    nearby_venues.columns = ['Neighborhood', 
                  'Neighborhood Latitude', 
                  'Neighborhood Longitude', 
                  'Venue', 
                  'Venue Latitude', 
                  'Venue Longitude', 
                  'Venue Category']
    
    return(nearby_venues)

#%% [markdown]
# And now we can get the nearby venues for all neighborhoods

#%%
toronto_venues = getNearbyVenues(names=df_toronto['Neighborhood'],
                                   latitudes=df_toronto['Latitude'],
                                   longitudes=df_toronto['Longitude']
                                  )

#%% [markdown]
# Now, lets check how many venues we have in our database

#%%
print(toronto_venues.shape)
toronto_venues.head()

#%% [markdown]
# 2237 venues should be good enough for our protype
#%% [markdown]
# Now, let's check how many venues for each neighborhood

#%%
toronto_venues.groupby('Neighborhood').count()

#%% [markdown]
# We can see that some of the neighborhoods reached the 100 venue limit we established. But that shouldn't affect so much the prototype
#%% [markdown]
# How many categorys can we find in Toronto?

#%%
print('There are {} uniques categories.'.format(len(toronto_venues['Venue Category'].unique())))

#%% [markdown]
# Now we can onehot encode to prepare the dataset for our recommendation system

#%%
# one hot encoding
toronto_onehot = pd.get_dummies(toronto_venues[['Venue Category']], prefix="", prefix_sep="")

# add neighborhood column back to dataframe
toronto_onehot['Neighborhood'] = toronto_venues['Neighborhood'] 

# move neighborhood column to the first column
fixed_columns = [toronto_onehot.columns[-1]] + list(toronto_onehot.columns[:-1])
toronto_onehot = toronto_onehot[fixed_columns]

toronto_onehot.head()


#%%
toronto_onehot.shape


#%%
toronto_grouped = toronto_onehot.groupby('Neighborhood').mean().reset_index()
toronto_grouped.head()


#%%
toronto_grouped.shape

#%% [markdown]
# Now the dataset is ready for our recommendation system
#%% [markdown]
# ## Random user
#%% [markdown]
# We need to create a list of all avaible categorys

#%%
category_list = list(toronto_grouped)
del category_list[0]

#%% [markdown]
# How many categorys will our user have?

#%%
category_amount = random.randint(1,11)


#%%
user_categories = random.sample(category_list, category_amount)


#%%
aux_list = []
aux_list2 = []
for i in range(len(category_list)):
    aux_list2.append(1)
    if category_list[i] in user_categories:
        aux_list.append(1)
    else:
        aux_list.append(0)
user_categories

#%% [markdown]
# Create a dataframe for the user where the columns will have the categories name and the values will be alway 1

#%%
user_df = pd.DataFrame.from_records([aux_list], columns=category_list)
user_df.head()


#%%
aux_df = pd.DataFrame(aux_list2)


#%%
user_profile = user_df.transpose().dot(aux_df.transpose()[0])
#user_profile = user_profile.set_index('index')
#user_profile.rename(columns={'index': 'Categories', '0': 'value'}, inplace = True)
#user_profile = user_profile.set_index('Categories')
user_profile

#%% [markdown]
# Now we have the user favorite categories. All we have to do, is get the categories table for all neighborhoods and compare them to see which neighborhood is the best fit for the user.

#%%
categories_table = toronto_grouped.set_index(toronto_grouped['Neighborhood'])
categories_table = categories_table.drop('Neighborhood', 1)
categories_table.head()

#%% [markdown]
# Now we multipy the matriz cateregories_table and user_profile to obtain the score for each neighborhood

#%%
recommendationTable_df = ((categories_table*user_profile).sum(axis=1))
recommendationTable_df.head()

#%% [markdown]
# With the score, we can sort the recommendation table, to obtain the neighborhoods with the highest score

#%%
recommendationTable_df = pd.DataFrame(recommendationTable_df.sort_values(ascending=False))


#%%
recommendationTable_df.columns = ['Score']
recommendationTableFinal_df = recommendationTable_df.reset_index()
recommendationTableFinal_df.head()

#%% [markdown]
# Now that we have the score for the top neighborhoods, we can join the table with the scores with the table with the location

#%%
df_neighborhood_score = df_toronto.join(recommendationTableFinal_df.set_index('Neighborhood'), on ='Neighborhood')
df_neighborhood_score.head()


#%%
df_neighborhood_score.sort_values(by='Score', ascending=False, inplace = True)
df_neighborhood_score.reset_index(drop=True, inplace = True)
df_neighborhood_score.head()

#%% [markdown]
# And with that we can finally print on the map the 5 best neighborhoods for our user

#%%
recommendation_map = folium.Map(location=[latitude, longitude], zoom_start=11)

# set color scheme for the clusters
x = 5
ys = [i + x + (i*x)**2 for i in range(5)]
colors_array = cm.rainbow(np.linspace(0, 1, len(ys)))
rainbow = [colors.rgb2hex(i) for i in colors_array]

markers_colors = []
for lat, lon, poi, score, index in zip(df_neighborhood_score['Latitude'], df_neighborhood_score['Longitude'], df_neighborhood_score['Neighborhood'], df_neighborhood_score['Score'], range(5)):
    label = folium.Popup(str(poi) + ' Score ' + str(score), parse_html=True)
    folium.CircleMarker(
        [lat, lon],
        radius=5,
        popup=label,
        color=rainbow[int(index)],
        fill=True,
        fill_color=rainbow[int(index)],
        fill_opacity=0.7).add_to(recommendation_map)
       
recommendation_map

#%% [markdown]
# From this example, we can see which neighborhoods are the best for our random user, and by clicking on the printed neighborhoods we can see the scores of each one of them. And with that our user can select the one that best fit his interests

