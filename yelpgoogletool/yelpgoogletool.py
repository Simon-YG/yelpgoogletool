import os
import pandas as pd
import requests
import json
import re
import warnings
import geocoder
import getpass

google_key = os.getenv("POETRY_GOOGLE_KEY")
yelp_key = os.getenv("POETRY_YELP_KEY")
pd.options.display.max_colwidth = 300


if google_key is None:
    google_key = getpass.getpass("Please input your Google API key.\n")

if yelp_key is None:
    yelp_key = getpass.getpass("Please input your Yelp Fusion API key.\n")



def ParsingAddress(raw_location_list):
    """
    Parse the raw location info from Yelp Fusion API to make it more readable.

    Parameters
    ----------
    raw_location_list : pandas.core.series.Series
      Required. A pd.Series of dictionaries containing address information in the JSON output from Fusion API
   
    Returns
    -------
    pandas.core.series.Series
      A list that stores more readable result. A typical element from the output list is a string of format: "<street address>, <City>, <State> <ZIP code>". E.g. "509 Amsterdam Ave, New York, NY 10024".
    """
    
    location_list = []
    for raw_location in raw_location_list:
        temp = [v for k,v in raw_location.items()]
        temp_location = ', '.join(temp[len(temp)-1])
        location_list = location_list + [temp_location]
    return(location_list)


def SearchRestaurant(yelp_key = yelp_key,
                     searching_keywords = "restaurant",
                     location = "Union Square, New York, NY 10003",
                     longitude = None,
                     latitude = None,
                     distance_max = 15000,
                     list_len = 40,
                     price = "1,2,3,4"):
    """
    Perform restaurant searching on Yelp.

    Parameters
    ----------
    yelp_key : str
      Required. The API key for Yelp fusion API.
    searching_keywords : str
      Optional. The keywords for Yelp searching. If not specified, the general term "restaurant" is searched.
    location : str
      Optional. A string describe the address of the location around which the search is conducted.
    longitude : float
      Required if location is not specified. The longitude of the current location.
    latitude : float
      Required if location is not specified. The latitude of the current location.
    distance_max : int
      Optional. A suggested search radius in meters.
    list_len : int
      Optional. The number of restaurants to show in the resulting dataframe.
    price : str
      Optional. Pricing levels to filter the search result with: 1 = $, 2 = $$, 3 = $$$, 4 = $$$$.
      The price filter can be a list of comma delimited pricing levels. For example, "1, 2, 3" will
      filter the results to show the ones that are $, $$, or $$$.
    
    Returns
    -------
    pandas.core.frame.DataFrame
      A dataframe that include essential information about the restaurants in the resarching result.

    Examples
    --------
    
    """
    
    
    # Check whether the parameters are of valid type
    longlat_input_checker = (longitude == None) + (longitude == None)
    assert type(searching_keywords) == str, "The parameter 'searching_keywords' should be a string!"
    assert type(location) == str, "The parameter 'location' should be a string!"
    assert (type(longitude) == type(None) or type(longitude) == float), "The parameter 'longitude' should be a float!"
    assert (type(latitude) == type(None) or type(latitude) == float), "The parameter 'latitude' should be a float!"
    assert type(distance_max) == int, "The parameter 'distance_max' should be an integer!"
    assert type(list_len) == int, "The parameter 'list_len' should be an integer!"
    assert (type(price) == type(None) or type(price) == str), "The parameter 'price' should be a str representing price levels, e.g. '1,2,3'!"
    
    # Check whether longitude and latitude are speciefied or not specified at the same time
    assert longlat_input_checker != 1, "Either both or neither of 'longitude' and 'latitude' should be specified!"
    
    # Check whether some parameters are off limit
    assert distance_max <= 20000, "You do not want to travel more than 20 km for your dinner!"
    assert list_len <= 500, "The length of searching result list should be no more than 500!"
    
     # Set the parameters for API queries
    url = "https://api.yelp.com/v3/businesses/search"
    headers = {"Authorization":yelp_key}
    querystring = {"term":searching_keywords}
    if longlat_input_checker == 0:
        assert (longitude >= -180) & (latitude >= -180) & (longitude <= 180) & (latitude <= 180), "Invalid 'longitude' or 'latitude'"
        if location != "Union Square, New York, NY 10003":
            warnings.warn("The parameter 'location' is not used when longitude and latitude are specified.")
        querystring["longitude"] = longitude
        querystring["latitude"] = latitude
    else:
        querystring["location"] = location
    if type(price) == str:
        querystring["price"] = price
    # Set offset to be the number of records that has already been searched
    offset = 0
    df_restaurant_list = pd.DataFrame()
    while offset < list_len:
        # This is the number of records to search in this batch
        limit = min(list_len - offset, 50)
        querystring["limit"] = limit
        querystring["offset"] = offset
        # request data from Fusion API
        response = requests.request("GET", url, headers = headers, params = querystring)
        rspn_json = response.json()
        #if rspn_json
        # merge the data into df_restaurant_list
        for business in rspn_json['businesses']:
            df_restaurant_list = df_restaurant_list.append(pd.Series(business),ignore_index=True)
        # Update the offset variable
        offset += limit
        
        df_restaurant_list = df_restaurant_list[['name',
                                                 'id',
                                                 'distance',
                                                 'location',
                                                 'price',
                                                 'phone',
                                                 'rating',
                                                 'review_count']].assign(
                                                       location = lambda x: ParsingAddress(x.location),
                                                       review_count = df_restaurant_list['review_count'].astype(int),
                                                       distance = round(df_restaurant_list['distance']/1609,1))
        
    return(df_restaurant_list)



def ExactRestaurantID(restaurant_name, location, yelp_key=yelp_key):
    """
    Search the unique id of a restaurant by its name and location.
    
    Parameters
    ----------
    restaurant_name : str
      Required. The name of the restaurant. Do not need to be exact.
    location : str
      Optional. A string describe the address of the location around which the search is conducted.
    yelp_key : str
      Required. The API key for Yelp fusion API.
      
    Returns
    -------
    str
      A string that serves as the identifier of the restaurant of interest.
    
    Example
    -------
    
    
    """
    # Set the parameters for API queries
    url = "https://api.yelp.com/v3/businesses/search"
    headers = {"Authorization":yelp_key}
    found = "N"
    restaurants_searched = 0
    while found != "Y":
        querystring = {"term":restaurant_name, "limit":5, "location":location,"offset":restaurants_searched}
        response = requests.request("GET", url, headers = headers, params = querystring)
        restaurants_searched += 5
        rspn_json = response.json()
        #if rspn_json
        # merge the data into df_restaurant_list
        df_restaurant_list = pd.DataFrame()
        for business in rspn_json['businesses']:
            df_restaurant_list = df_restaurant_list.append(pd.Series(business),ignore_index=True)
        df_restaurant_list_clean = df_restaurant_list[['name','location']].assign(location = lambda x: ParsingAddress(x.location))
        print(df_restaurant_list_clean)
        found = input("Is the desired restaurant in the list above? (Y/N)\n")
        if found == "Y":
            index = int(input("Please input the index at the beginning of the row corresponding to the desired restaurant.\n"))
            restaurant_id = df_restaurant_list['id'][index]
        else:
            print('\n\n\n\n\n')
        if restaurants_searched % 15 == 0:
            restart = (input("Do you want to exit the current search and refine the searching term? (Y/N)") in ["Y","y"])
            if restart:
                print("Current searching is terminated")
                return(None)
    print("Restaurant found!")
    return(restaurant_id)




def FindBestRestaurants(list_of_restaurants, by = "rating and review count", result_len = 5):
    """
    Sort a list of restaurants and return the top choices.
    
    Parameters
    ----------
    list_of_restaurants: pandas.core.frame.DataFrame
      Required. A dataframe of restaurants from which the best ones are looked for. A typical choice is the output from `SearchingRestaurant()` function.
    by : str
      Optional. A string represent the criterion of sorting. The details are as follows:
        - "rating and review counts": sort by the Yelp rating. In the case that ratings are tied, use the number of reviews as the second criterion;
        - "rating and distance": sort by the Yelp rating. In the case that ratings are tied, use the distance to current location as the second criterion;
        - "review count": sort by the number of reviews;
        - "distance": sort by the distance to the current location.
      The default choice is "rating and review counts".
    result_len : int
      Optional. The number of the top-ranked restaurants to return. The default value is 5.
    
    Returns
    -------
    pandas.core.frame.DataFrame
      A sub-dataframe of the original input consisting the top restaurants from the searching results.
    
    Example
    -------
    
    """
    # Check the validity of the input
    assert type(list_of_restaurants) == type(pd.DataFrame()), "'list_of_restaurants' should be a pandas Dataframe!"
    assert type(by) == str, "'by' should be a string!"
    assert (type(result_len) == int) & (result_len <= 20), "'result_len' should not exceed 20!"

    # In these two cases, there are not likely to have tied records
    if by == "review count":
        sorted_list = list_of_restaurants.sort_values(by = "review_count", ascending = False)
        return(sorted_list[0:result_len])
    if by == "distance":
        sorted_list = list_of_restaurants.sort_values(by = "distance", ascending = True)
        return(sorted_list[0:result_len])
    
    # If the primary variable for sorting is rating, a secondary criterion is need to deal with the tie-rank situation
    # Sort the list by rating
    if by in ["rating and review count","rating and distance"]:
        sorted_list = list_of_restaurants.sort_values(by = "rating", ascending = False)

        # Get all the unique rating in the data
        rating_list = list(set(list_of_restaurants['rating']))
        rating_list.sort(reverse = True)

        # Get the best restaurants
        count_rating = 0
        result_list = pd.DataFrame()
        while len(result_list.index) < result_len:
            temp_rating = rating_list[count_rating]
            temp_list = list_of_restaurants[list_of_restaurants['rating'] == temp_rating]
            # When sorting by review_count, sort in descending order; when sorting by distance, sort in ascending order
            if by == "rating and review count":
                temp_list = temp_list.sort_values(by = "review_count", ascending = False)
            else:
                temp_list = temp_list.sort_values(by = "distance", ascending = True)
            if len(result_list.index) + len(temp_list.index) > result_len:
                # Take only the top (result_len - len(result_df.index)) records
                temp_list = temp_list[0:(result_len - len(result_list.index))]
            result_list = result_list.append(temp_list)
            count_rating += 1
        return(result_list.reset_index())


def GetDirection(restaurant_id,
                 google_key = google_key,
                 yelp_key = yelp_key,
                 verbose = True,
                 mode = "transit",
                 start_location = "Union Square, New York, NY 10003",
                 start_latitude = None,
                 start_longitude = None):
    """
    Print out the navigation from the current location a specific restaurant.
    
    Parameters
    ----------
    restaurant_id : str
      Required. The unique identifier of the restaurant.
    google_key : str
      Required. The API key for Google Direction API.
    yelp_key : str
      Required. The API key for Yelp fusion API.
    verbose : bool
      Required. The name of the restaurant. Do not need to be exact.
    mode : str
      Optional. The mode of transportation. Should be one of "driving" (default), "walking" and "transit".
    start_location : str
      Optional. A string describe the address of the location as the origin.
    start_latitude : str
      Required if `start_location` is not specified. The latitude of the origin.
    start_longitude : str
      Required if `start_location` is not specified. The longitude of the origin.

    

    Returns
    -------
    str
      A string that stores the detailed instruction to get to the restaurant.
    
    Example
    -------
    
    
    """
     # Check the validity of input
    assert mode in ["driving","walking","transit"], "Invalid 'mode'!"
    assert type(restaurant_id) == str, "The parameter 'restaurant_id' should be a string!"
    assert type(verbose) == bool, "The parameter 'verbose' should be a boolean variable!"
    # Check whether longitude and latitude are speciefied or not specified at the same time
    longlat_input_checker = (start_longitude == None) + (start_longitude == None)
    assert longlat_input_checker != 1, "Either both or neither of 'stlongitude' and 'latitude' should be specified!"
    
    # Get the start location if start_latitude and start_longitude are specified
    if longlat_input_checker == 0:
        if start_location != "Union Square, New York, NY 10003":
            warnings.warn("The parameter 'start_location' is ignored when longitude and latitude are specified.")
        start_location = str(start_latitude) + "," + str(start_longitude)
    
    if mode == "driving" and verbose:
        warnings.warn("The parameter 'verbose' is ignored when 'mode' is 'driving'.")
    # Get the destination location
    url = "https://api.yelp.com/v3/businesses/" + restaurant_id
    headers = {"Authorization":yelp_key}
    rspn_json = requests.request("GET", url = url, headers = headers).json()
    restaurant_location = ", ".join(rspn_json["location"]["display_address"])
    
    # Get the direction
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {"origin":start_location,"destination":restaurant_location,"mode":mode,"key":google_key}
    direction_json = requests.request("GET", url = url, params=params).json()
    
    # Initialize a string for store detailed instruction
    direction_str = "*" * 100 + "\n"
    
    # start address
    direction_str += "Starting location:".ljust(30) + direction_json['routes'][0]['legs'][0]['start_address']
    direction_str += "\n"
    
    # destination address
    direction_str += "Destination location:".ljust(30) + direction_json['routes'][0]['legs'][0]['end_address']
    direction_str += "\n"
    
    # distance
    direction_str += "Total distance:".ljust(30) + direction_json['routes'][0]['legs'][0]['distance']['text']
    direction_str += "\n"
    direction_str += "*" * 100
    direction_str += "\n"
    
    # transportation mode
    direction_str += "Transportation mode:".ljust(30) + mode
    direction_str += "\n"
    
    ############
    # duration
    direction_str += "Total duration:".ljust(30) + direction_json['routes'][0]['legs'][0]['duration']['text']
    direction_str += "\n"
    
    # store steps, travel_steps is a list of steps
    travel_steps = direction_json['routes'][0]['legs'][0]['steps']
    
    direction_str += "*" * 100
    direction_str += "\n"
    
    direction_str += "Detailed direction to the restaurant: \n"
    direction_str += "\n"
    
    # Print instructions
    step_count = 0
    for step in travel_steps:
        step_count += 1
        instruction = re.sub(r'<div[^>]*>','. ',step['html_instructions'])
        instruction = re.sub(r'<[^>]*>','',instruction)
        instruction = re.sub('&nbsp;','',instruction)
        direction_str += "Step " + str(step_count) + ": " + instruction +" (" + step['distance']['text'] + ', ' + step['duration']["text"]+")"
        direction_str += "\n"
        if step['travel_mode'] == "WALKING" and verbose  and ('steps' in step.keys()):
            substep_list = step['steps']
            for substep in substep_list:
                if 'html_instructions' in substep.keys():
                    sub_instruction = re.sub(r'<div[^>]*>','. ',substep['html_instructions'])
                    sub_instruction = re.sub(r'<[^>]*>','',sub_instruction)
                    sub_instruction = re.sub('&nbsp;','',sub_instruction)
                    direction_str += '      - ' + sub_instruction +" (" + substep['distance']['text'] + ', ' + substep['duration']["text"]+")"
                    direction_str += "\n"
            print("\n")
        if step['travel_mode'] == "TRANSIT" and verbose:
            direction_str += "      - Vehicle:".ljust(35) + step['transit_details']['line']['vehicle']['name'] + " " + step['transit_details']['line']['short_name']
            direction_str += "\n"
            direction_str += "      - Departure stop:".ljust(35) + step['transit_details']['departure_stop']['name']
            direction_str += "\n"
            direction_str += "      - Arrival stop:".ljust(35) + step['transit_details']['arrival_stop']['name']
            direction_str += "\n"
            direction_str += "      - Number of stops:".ljust(35) + str(step['transit_details']['num_stops'])
            direction_str += "\n\n"
    return(direction_str)

def GetReviews(restaurant_id, yelp_key = yelp_key):
    """
    Get three most recent review for a specific restaurant.
    
    Parameters
    ----------
    restaurant_id : str
      Required. The unique identifier of the restaurant.
    yelp_key : str
      Required. The API key for Yelp fusion API.
      
    Returns
    -------
    pandas.core.frame.DataFrame
      A pandas dataframe that stores basic information about reviews on the restaurant.
      
    Example
    -------
    
    
    """
    # set parameters for searching
    url = "https://api.yelp.com/v3/businesses/" + restaurant_id + "/reviews"
    headers = {"Authorization":yelp_key}
    rspn_json = requests.request("GET", url = url, headers = headers).json()
    # parse json response from Fusion API
    review_df = pd.DataFrame()
    for review in rspn_json['reviews']:
        review_series = pd.Series([review['user']['name'],
                                   review['time_created'],
                                   review['rating'],
                                   review['text'].replace("\n",""),
                                   review['url']])
        review_df = review_df.append(review_series,ignore_index=True)
    # rename the dataframe for easier reference
    review_df.columns = ["Name","Date","Rating","Review","Url"]
    return(review_df)

def review_report(df_reviews):
    """
    Print the reviews in a more reader-friendly format.
    
    Parameters
    ----------
    df_reviews : pandas.core.frame.DataFrame
      Required. A pandas dataframe stores basic information about reviews on the restaurant. It is typically the output from `GetReviews()` function
   
    Returns
    -------
    None
      
    Example
    -------
    
    
    """
    for i in range(df_reviews.shape[0]):
        print("*" * 100 + "\n")
        print("On " + df_reviews['Date'][i] + " " + df_reviews['Name'][i] + " gave a rating of " + str(df_reviews['Rating'][i])  + " and said:\n" )
        print(df_reviews['Review'][i] + "\n")
        print("See more: " + df_reviews['Url'][i] + "\n")


def Where2Eat(yelp_key = yelp_key, google_key = google_key):
    """
    An interactive function that assist the user to decide where to have dinner. The function wraps up almost all the functionalities of the package. It can
     - Search restaurants according to various criteria including searching keywords, location, ditance from current location, etc.
     - Sort a list of restaurants and find the best ones
     - Print recent reviews on Yelp
     - Generate a navigation instruction to a restaurant of user's selection
    
    Parameters
    ----------
    yelp_key : str
      Required. The API key for Yelp fusion API.
    google_key : str
      Required. The API key for Google Direction API.
    
    Returns
    -------
    None
    
    
    """
    currentloc = geocoder.ip('me')
    location_check = input("The geographic coordinate of your current location is " +
                           str(tuple(currentloc.latlng)) +
                           ". Do you want to search restaurants near this location? (Y/N)\n")
    assert location_check in ['Y','N'], "invalid input!"
    if location_check == "N":
        print("\nPlease input a new location for the restaurant searching. \n")
        coord_or_name = input("Which of the following you would you like to provide: \n"\
                              "1. Georeference coordinate \n2. The address of the current location \n"
                              "Please type (1/2)\n")
        assert coord_or_name in ['1','2'], "invalid input!"
        # Input the location manually
        if coord_or_name == '1':
            try:
                latitude = float(input("\nPlease provide the latitude:"))
            except:
                print("Invalid input. The latitude should be a number.")
            assert (latitude>=-180) & (latitude<=180), "Invalid input. The latitude should be between -180 and 180"
            try:
                longitude = float(input("Please provide the longitude:"))
            except:
                print("Invalid input. The longitude should be a number.")
            assert (longitude>=-180) & (longitude<=180), "Invalid input. The longitude should be between -180 and 180"
        else:
            location = input("Please provide the current address:\n")

    # Input parameters for the restaurant searching
    searching_keywords =  input("\nPlease input some keyword(s) for restaurant searching.\n")
    try:
        distance_max = int(input("\nWhat is the maximum distance in miles that you would accept?"\
                         " Please input a positive integer smaller or equal to 10.\n")) * 1609
    except:
        print("Invalid input. Please input an integer smaller or equal to 10.\n")
    assert (distance_max > 0) and (distance_max <= 20000), "Invalid input. Please input a positive integer smaller or equal to 10.\n"

    price = input("\nPlease indicate the pricing levels of the restaurant you want to consider."\
                  " In particular, the number 1 represents the lowest level and number 4 represents the highest level."\
                  " Multiple levels are allowed by a list of comma delimited pricing levels, e.g. '1,2,3' will"\
                  " include restaurants with pricing levels 1, 2 and 3.\n")

    # Input parameters for the restaurant ranking
    sorting_criterion = input("\nThe searching result will be sorted and only the best restaurants will be reported."\
                              "Please choose one of the following criteria for sorting:\n"\
                              "1. Sort by the Yelp rating. In the case that ratings are tied, use the number of reviews as"\
                              " the second criterion\n"\
                              "2. Sort by the Yelp rating. In the case that ratings are tied, use the distance to current"\
                              " location as the second criterion\n"\
                              "3. Sort by the number of reviews\n"\
                              "4. Sort by the distance to the current location \n (1/2/3/4) \n"\
                             )
    assert sorting_criterion in ['1','2','3','4'], "Invalid input!"

    if sorting_criterion == "1":
        by = "rating and review count"
    if sorting_criterion == "2":
        by = "rating and distance"
    if sorting_criterion == "3":
        by = "review count"
    if sorting_criterion == "4":
        by = "distance"

    try:
        result_len = int(input("\nHow many of the top-ranked restaurants do you want to have a look? Please input"\
                          " an integer smaller or equal to 20. \n"))
    except:
        print("Invalid input. Please input an integer smaller or equal to 20.")
    assert (result_len <= 20) and (result_len >= 1), "Invalid input. Please input an integer smaller or equal to 20."

    print("\n Searching in process...\n")

    # Perform the restaurant searching
    if (coord_or_name == '1') or (location_check == "Y"):
        list_of_restaurants = SearchRestaurant(yelp_key=yelp_key,
                                               searching_keywords = searching_keywords,
                                               latitude = latitude,
                                               longitude = longitude,
                                               distance_max = distance_max,
                                               price = price)
    else:
        list_of_restaurants = SearchRestaurant(yelp_key=yelp_key,
                                               searching_keywords = searching_keywords,
                                               location = location,
                                               distance_max = distance_max,
                                               price = price)



    # Find the best restaurants
    df_BestRestaurant = FindBestRestaurants(list_of_restaurants = list_of_restaurants,
                                            by = by,
                                            result_len = result_len).reset_index()

    print("The top " + str(result_len) + " restaurants from the searching results:\n")

    # print the best restaurants
    df_BestRestaurant_to_Show = df_BestRestaurant[['name','rating','review_count','distance','price']]
    df_BestRestaurant_to_Show.columns = ["Name","Rating","Review count","Distance (in miles)","Price"]
    df_BestRestaurant_to_Show = df_BestRestaurant_to_Show
    print(df_BestRestaurant_to_Show)

    # print reviews
    review_request = input("\nWould you like to read some recent reviews of these restaurants? (Y/N)\n")
    assert review_request in ['Y','N'], "Invalid input!"
    while review_request == "Y":
        restaurant_index = int(input("Please type the index at the begining of the row of"\
                                     " the restaurant whose reviews you are interested.\n"))
        df_review = GetReviews(yelp_key = yelp_key,
                               restaurant_id = df_BestRestaurant['id'][restaurant_index])
        review_report(df_review)
        review_request = input("\nWould you like to read more recent reviews of other restaurants? (Y/N)\n")
        assert review_request in ['Y','N'], "Invalid input!"
    
    # user input the choice of restaurant
    try:
        restaurant_index = int(input("Which restaurant from the list do you prefer?"\
                                " Please type the index at the begining of the corresponding row.\n"))
    except:
        print("Invalid input. Please input the integer-valued index!")
    assert restaurant_index < result_len, "Index out of range!"
    
    mode = input("\nNow, let's see how we can get there... Please input your preferred method of transportation.\n"\
         "(driving/walking/transit)\n")
         
    if mode != "driving":
        verbose = input("Do you want a detailed version of navigation to the restaurant of choice?"\
                        " Type 'Y' for a detailed version, 'N' for a concise one.  \n")
        verbose = (verbose == "Y")
    else:
        verbose = False

    restaurant_id = df_BestRestaurant['id'][restaurant_index]
    print("\nThe direction to the restaurant is as follows:\n")
    if (coord_or_name == '1') or (location_check == "Y"):
        print(GetDirection(yelp_key = yelp_key,
                     google_key = google_key,
                     restaurant_id=restaurant_id,
                     verbose=verbose,
                     mode = mode,
                     start_latitude = latitude,
                     start_longitude = longitude))
    else:
        print(GetDirection(yelp_key = yelp_key,
                     google_key = google_key,
                     restaurant_id = restaurant_id,
                     verbose = verbose,
                     mode = mode,
                     start_location = location))

