import requests, os, json
from datetime import *
import pandas as pd
import numpy as np
from init.weather_database import add_weather, WeatherDB
from __main__ import db

# API Key for weather_url and weather_forecast_url
weather_api_key = os.environ.get('OpenWeather_API_key')

# Open Weather API - 
weather_forecast_url = 'https://api.openweathermap.org/data/3.0/onecall'
current_weather_url = 'https://api.openweathermap.org/data/2.5/weather'

      

class Weather:
    def __init__(self, location, latitude, longitude, unit='metric'):
        self.location = location
        self.latitude = latitude
        self.longitude = longitude
        self.unit = unit
        self.datetime_within_30mins = datetime.utcnow() - timedelta(minutes=30)
        self.datetime_within_24hrs = datetime.utcnow() - timedelta(hours=24)
        self.datetime_7days_after = (datetime.utcnow() + timedelta(days=7)).strftime('%Y-%m-%d')
        self.datetime_current_date = datetime.utcnow().strftime('%Y-%m-%d')

    
    ###################################
    # Function - Check current weather#
    ####################################
    def check_current_weather(self):

        try:
            # If there is, check the data from DB
            # Condition location + timestamp = within 30 min + date = today + pop is null
            temp_weather = db.session.query(WeatherDB).filter(
                WeatherDB.location==self.location.lower(),
                WeatherDB.created_timestamp >= self.datetime_within_30mins,
                WeatherDB.date == self.datetime_current_date,
                WeatherDB.pop == None
            ).first()

            
            self.cur_weather = temp_weather.desc
            self.cur_temp = temp_weather.cur_temp
            self.cur_humidity = temp_weather.humidity
            self.cur_max_temp = temp_weather.max_temp
            self.cur_min_temp = temp_weather.min_temp
            self.cur_date = temp_weather.date
            self.icon = temp_weather.icon

            return({
                "cur_weather": self.cur_weather, 
                "cur_temp": self.cur_temp, 
                "cur_max_temp": self.cur_max_temp, 
                "cur_min_temp": self.cur_min_temp, 
                "cur_humidity": self.cur_humidity, 
                "cur_date": self.cur_date,
                "icon": self.icon
            })
        
        except:
            # If not, get data using Current weather API
            resp = requests.get(f'{current_weather_url}?lat={self.latitude}&lon={self.longitude}&units={self.unit}&appid={weather_api_key}')
            
            if resp.status_code == 200:
                resp_json = resp.json()

                self.cur_weather = resp_json['weather'][0]['main']
                self.cur_temp = resp_json['main']['temp']
                self.cur_humidity = resp_json['main']['humidity']
                self.cur_max_temp = resp_json['main']['temp_max']
                self.cur_min_temp = resp_json['main']['temp_min']
                self.cur_date = datetime.utcfromtimestamp(resp_json['dt']).strftime('%Y-%m-%d')
                self.icon = resp_json['weather'][0]['icon']

                # Add current weather data in database
                add_weather(location=self.location.lower(), 
                            date=self.cur_date,
                            desc = self.cur_weather,
                            cur_temp=self.cur_temp,
                            min_temp = self.cur_min_temp,
                            max_temp = self.cur_max_temp,
                            humidity = self.cur_humidity,
                            icon = self.icon
                            )

                return({
                    "cur_weather": self.cur_weather, 
                    "cur_temp": self.cur_temp, 
                    "cur_max_temp": self.cur_max_temp, 
                    "cur_min_temp": self.cur_min_temp, 
                    "cur_humidity": self.cur_humidity, 
                    "cur_date": self.cur_date,
                    "icon": self.icon
                })
                
            else:
                raise Exception (f'Filed to retrieve current weather. Please try again. Error:{resp.status_code}')

    #########################################################
    # Function - Check weather for a specific date in a week#
    #########################################################
    def check_weather_date(self, date):

        try:
            # check weather in DB for the location/date
            # Condition location + timestamp = within 24 hours + date = selected date + pop is NOT null
            temp_weather = db.session.query(WeatherDB).filter(
                WeatherDB.location==self.location.lower(),
                WeatherDB.created_timestamp >= self.datetime_within_24hrs,
                WeatherDB.date == date,
                WeatherDB.pop != None
            ).first()

            self.cur_weather = temp_weather.desc
            self.cur_humidity = temp_weather.humidity
            self.cur_max_temp = temp_weather.max_temp
            self.cur_min_temp = temp_weather.min_temp
            self.cur_date = temp_weather.date
            self.icon = temp_weather.icon
            self.pop = temp_weather.pop

            return({
                "cur_weather": self.cur_weather, 
                "cur_max_temp": self.cur_max_temp, 
                "cur_min_temp": self.cur_min_temp, 
                "cur_humidity": self.cur_humidity, 
                "cur_date": self.cur_date,
                "icon": self.icon,
                "pop": self.pop
            })
        
        
        # If not, get data 
        except:
            # If not, get data from API
            resp = requests.get(f'{weather_forecast_url}?lat={self.latitude}&lon={self.longitude}&units={self.unit}&exclude=hourly,minutely,alerts&appid={weather_api_key}')
        
            if resp.status_code == 200:
                resp_json = resp.json()
                weather_forecast = resp_json['daily']

                # Iterate through and extract information for each day
                weather_next_8days = map(lambda x: 
                    {
                        'date': datetime.utcfromtimestamp(x['dt']).strftime('%Y-%m-%d'), 
                        'min_temp': x['temp']['min'],
                        'max_temp': x['temp']['max'],
                        'weather': x['weather'][0]['main'],
                        'humidity': x['humidity'],
                        'pop': x['pop'],
                        'icon': x['weather'][0]['icon']
                    } 
                    ,weather_forecast[0:])

                self.weather_next_8days = list(weather_next_8days)
                temp_weather_for_date = ''
                
                # Store the data in DB - date, description, min/max temp, humidity, icon and pop
                for temp_weather_forecast in self.weather_next_8days:

                    add_weather(
                        location=self.location.lower(), 
                        date=temp_weather_forecast['date'],
                        desc = temp_weather_forecast['weather'],
                        min_temp = temp_weather_forecast['min_temp'],
                        max_temp = temp_weather_forecast['max_temp'],
                        humidity = temp_weather_forecast['humidity'],
                        icon = temp_weather_forecast['icon'],
                        pop = temp_weather_forecast['pop']
                        )

                    if date == temp_weather_forecast['date']:
                        temp_weather_for_date = temp_weather_forecast

                return({
                    "cur_weather": temp_weather_for_date['weather'], 
                    "cur_max_temp": temp_weather_for_date['max_temp'], 
                    "cur_min_temp": temp_weather_for_date['min_temp'], 
                    "cur_humidity": temp_weather_for_date['humidity'], 
                    "cur_date": temp_weather_for_date['date'],
                    "icon": temp_weather_for_date['icon'],
                    "pop": temp_weather_for_date['pop']
                })

            else:
                raise Exception (f'Filed to retrieve current weather. Please try again. Error:{resp.status_code}')

    ##################################
    # Function - Check 8days forecast#
    ##################################
    def check_weather_forecast(self, temp_itinerary=False):

        try:
            # check weather in DB for the location/date
            # Condition location + timestamp = within 24 hours + date is from today to 8 days later + pop is NOT null
            temp_weekly_weather = db.session.query(WeatherDB).filter(
                WeatherDB.location==self.location.lower(),
                WeatherDB.created_timestamp >= self.datetime_within_24hrs,
                WeatherDB.date >= self.datetime_current_date,
                WeatherDB.date <= self.datetime_7days_after,
                WeatherDB.pop != None
            ).all()

            if len(temp_weekly_weather) >= 8:

                self.weather_next_8days = []

                for temp_weather in  temp_weekly_weather:
                    self.weather_next_8days.append(                
                        {
                            'weather': temp_weather.desc,
                            'date': temp_weather.date, 
                            'min_temp': temp_weather.min_temp,
                            'max_temp': temp_weather.max_temp,
                            'humidity': temp_weather.humidity,
                            'icon': temp_weather.icon,
                            'pop': temp_weather.pop,
                            'location': temp_weather.location.capitalize()
                        })


                return self.weather_next_8days
            
            else:
                # If not, get data
                resp = requests.get(f'{weather_forecast_url}?lat={self.latitude}&lon={self.longitude}&units={self.unit}&exclude=hourly,minutely,alerts&appid={weather_api_key}')
                
                if resp.status_code == 200:
                    resp_json = resp.json()
                    weather_forecast = resp_json['daily']

                    # Iterate through and extract information for each day
                    weather_next_8days = map(lambda x: 
                        {
                            'date': datetime.utcfromtimestamp(x['dt']).strftime('%Y-%m-%d'), 
                            'min_temp': x['temp']['min'],
                            'max_temp': x['temp']['max'],
                            'weather': x['weather'][0]['main'],
                            'humidity': x['humidity'],
                            'pop': x['pop'],
                            'icon': x['weather'][0]['icon'],
                            'location': self.location.capitalize()
                        } 
                        ,weather_forecast[0:])

                    self.weather_next_8days = list(weather_next_8days)
                    
                    # Store the data in DB
                    for temp_weather_forecast in self.weather_next_8days:

                        add_weather(
                            location=self.location.lower(), 
                            date=temp_weather_forecast['date'],
                            desc = temp_weather_forecast['weather'],
                            min_temp = temp_weather_forecast['min_temp'],
                            max_temp = temp_weather_forecast['max_temp'],
                            humidity = temp_weather_forecast['humidity'],
                            icon = temp_weather_forecast['icon'],
                            pop = temp_weather_forecast['pop'],
                            itinerary = temp_itinerary
                            )


                    return self.weather_next_8days
                
                else:
                    raise Exception (f'Filed to retrieve current weather. Please try again. Error:{resp.status_code}')

        except:
            raise Exception (f'Filed to retrieve current weather. Please try again. Error:{resp.status_code}')



    #################################################################
    # Function - Check weather depending on the weather_type passeed#
    #################################################################
    def search_weather(self, weather_type, date=None):
        temp_weather_type = int(weather_type)

        if temp_weather_type == 1:
            return self.check_current_weather()

        elif temp_weather_type == 2 and date:
            return self.check_weather_date(date)

        elif temp_weather_type == 3:
            return self.check_weather_forecast()

        elif temp_weather_type == 4:
            return f'Weacher: As you don\'t need to know the weather in {self.location}, let\'s talks something else.'
        
        else:
            return 'Please select the option from 1 to 4'


