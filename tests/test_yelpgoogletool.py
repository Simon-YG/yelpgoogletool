from yelpgoogletool import __version__
from yelpgoogletool import yelpgoogletool
import pandas as pd

def test_version():
    assert __version__ == '1.0.0'

def test_SearchRestaurant():
    list_len = 30
    search_result = yelpgoogletool.SearchRestaurant(list_len = list_len)
    assert isinstance(search_result,pd.core.frame.DataFrame) & (search_result.shape[0]<=list_len)


def test_FindBestRestaurant():
    # create a testing dataframe `test_df`
    name = pd.Series(['a','b','c','d','e','f','g','h'])
    distance = pd.Series([1,2,3,4,5,6,7,8])
    rating = pd.Series([2.0,5.0,4.5,4.0,4.5,3.0,3.5,4.0])
    review_count = pd.Series([40,60,30,20,70,80,15,9])
    test_df = pd.DataFrame({"name":name,"distance":distance,"rating":rating,"review_count":review_count})
    # try different modes of sorting
    assert list(yelpgoogletool.FindBestRestaurants(test_df,"rating and review count",2)['name']) == ['b','e']
    assert list(yelpgoogletool.FindBestRestaurants(test_df,"rating and distance",2)['name']) == ['b','c']
    assert list(yelpgoogletool.FindBestRestaurants(test_df,"distance",2)['name']) == ['a','b']
    assert list(yelpgoogletool.FindBestRestaurants(test_df,"review count",2)['name']) == ['f','e']


def test_GetDirection():
    result = yelpgoogletool.GetDirection(start_location = "Columbia University, NYC", restaurant_id = "4yPqqJDJOQX69gC66YUDkA")
    assert isinstance(result,str)
    assert result[:100] == 100 * "*"

def test_GetReviews():
    result = yelpgoogletool.GetReviews("4yPqqJDJOQX69gC66YUDkA")
    assert isinstance(result,pd.core.frame.DataFrame)
    assert list(result.columns) == ['Name', 'Date', 'Rating', 'Review', 'Url']

