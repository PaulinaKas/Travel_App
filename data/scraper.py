import requests
import warnings
import pandas as pd
import numpy as np
from datetime import date, timedelta
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlencode, quote_plus
from reader import *

warnings.simplefilter(action='ignore', category=FutureWarning)

options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

columns = ['departure_date', 'departure_weekday', 'departure_time', 'departure_city', 'departure_airport',
           'arrival_date', 'arrival_weekday', 'arrival_time', 'arrival_city', 'arrival_airport',
           'price']

def get_route_data(src_city_code: str,  # City [IATA]
                   dep_date: str, arr_date: str, # rrrr-mm-dd
                   min_days: int, max_days: int) -> pd.DataFrame:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; hobby_travel_app/1.0; +https://example.com)"
    }

    url = build_url(src_city_code, dep_date, arr_date, min_days, max_days)
    driver.get(url)

    with requests.Session() as session:
        session.headers.update(headers)
        response = session.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        df = pd.Series(index=columns)
        result = soup.select(".result")
        if len(result) == 0:
            return df

        for row in result:
            try:
                df_route = pd.Series(index=columns)
                from_raw = row.select_one(".from").text.strip()  # np. '08:10 Warsaw WAW'
                from_parts = from_raw.split(" ")
                departure_time = from_parts[0]
                departure_weekday, departure_date = get_weekday(row, departure_time)
                departure_city = " ".join(from_parts[1:-1])
                departure_airport = from_parts[-1]

                to_raw = row.select_one(".to").text.strip()  # np. '08:10 Warsaw WAW'
                to_parts = to_raw.split(" ")
                arrival_time = to_parts[0]
                arrival_weekday, arrival_date = get_weekday(row, arrival_time)
                arrival_city = " ".join(to_parts[1:-1])
                arrival_airport = to_parts[-1]

                price = row.select_one(".subPrice") or row.select_one(".price") or row.select_one(".priceTotal")
                if price:
                    price = int(price.text.strip().split(' ')[0])
                else:
                    price = None

                df_route['departure_date'] = departure_date
                df_route['departure_weekday'] = departure_weekday
                df_route['departure_time'] = departure_time
                df_route['departure_city'] = departure_city
                df_route['departure_airport'] = departure_airport
                df_route['arrival_date'] = arrival_date
                df_route['arrival_weekday'] = arrival_weekday
                df_route['arrival_time'] = arrival_time
                df_route['arrival_city'] = arrival_city
                df_route['arrival_airport'] = arrival_airport
                df_route['price'] = price
                df = pd.concat([df, df_route], ignore_index=True, axis=1)

            except Exception as e:
                print(2)
                continue

    df = df.T.reset_index()
    if df.iloc[0].unique()[0] == 0 and isinstance(df.iloc[0].unique()[1], float):  # remove empty row
        df = df.iloc[1:]

    df.drop(columns=['index'], inplace=True)
    return df

def build_url(
    src_city_code: str = "", # City [IATA]
    dep_date: str = "", # rr-mm-dd
    arr_date: str = "", # rr-mm-dd
    min_days: int = 1,
    max_days: int = 7,
    adults: int = 2,
    currency: str = "PLN") -> str:

    base_url = "https://www.azair.eu/azfin.php"
    params = {
        "searchtype": "flexi",
        "tp": "0",
        "isOneway": "return",
        "srcAirport": src_city_code,
        "dstAirport": "Anywhere [XXX]",
        "anywhere": "true",
        "depdate": dep_date,
        "arrdate": arr_date,
        "minDaysStay": str(min_days),
        "maxDaysStay": str(max_days),
        "adults": str(adults),
        "currency": currency,
        "resultSubmit": "Search"
    }

    url = f"{base_url}?{urlencode(params, quote_via=quote_plus)}"
    return url

def get_days() -> [str | int]:
    today = date.today()
    start_date = today.isoformat()
    end_date = (today + timedelta(days=7)).isoformat()
    min_days = 1
    max_days = 7

    return [start_date, end_date, min_days, max_days]


def get_weekday(row, departure_time) -> (str, str):
    date_start = row.text.find('There ')
    date_start += len('There ')
    date_end = row.text.find(departure_time)
    date = row.text[date_start:date_end]
    weekday = date.split(' ')[0]
    date = date.split(' ')[1]

    return weekday, date

polish_airports = get_polish_airports()
all_data = pd.DataFrame(columns=columns)
for airport in polish_airports:
    input = [airport]
    input.extend(get_days())
    data = get_route_data(*input)
    if pd.isna(data.nunique()).all():
        continue
    all_data = pd.concat([all_data, data], ignore_index=True)
    iata = data.departure_airport.unique()[0]
    flights_number = data.shape[0]
    data.to_csv(f"output/polish_airports_{iata}.csv", index=False)

    print(f"{str(flights_number)} flights for {iata} saved")

all_data.to_csv("output/polish_airports.csv", index=False)

