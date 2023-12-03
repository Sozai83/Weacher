import requests, os, json
from datetime import *
import pandas as pd
import numpy as np
from init.weather_database import add_weather, db, WeatherDB


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

    def generate_map(self):
        self.map = f'{map_url}?key={map_api_key}&q={self.latitude},{self.longitude}&zoom=7'
        return self.map
    
    # Get current weather for the location
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

            return(
                self.cur_weather, 
                self.cur_temp, 
                self.cur_max_temp, 
                self.cur_min_temp, 
                self.cur_humidity, 
                self.cur_date,
                self.icon
            )
        
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

                return(
                    self.cur_weather, 
                    self.cur_temp, 
                    self.cur_max_temp, 
                    self.cur_min_temp, 
                    self.cur_humidity, 
                    self.cur_date,
                    self.icon
                )
                
            else:
                raise Exception (f'Filed to retrieve current weather. Please try again. Error:{resp.status_code}')

    # Get weather for the location on a specific date
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

            return(
                self.cur_weather, 
                self.cur_temp, 
                self.cur_max_temp, 
                self.cur_min_temp, 
                self.cur_humidity, 
                self.cur_date,
                self.icon
            )
        
        
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


                return(
                    temp_weather_for_date['date'], 
                    temp_weather_for_date['max_temp'], 
                    temp_weather_for_date['min_temp'], 
                    temp_weather_for_date['humidity'], 
                    temp_weather_for_date['date'],
                    temp_weather_for_date['icon']
                )

            else:
                raise Exception (f'Filed to retrieve current weather. Please try again. Error:{resp.status_code}')

    # Get 8 days weather forecast for the location
    def check_weather_forecast(self):

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
                            'temp_min': temp_weather.min_temp,
                            'temp_max': temp_weather.max_temp,
                            'humidity': temp_weather.humidity,
                            'icon': temp_weather.icon,
                            'pop': temp_weather.pop
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
                            'icon': x['weather'][0]['icon']
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
                            pop = temp_weather_forecast['pop']
                            )

                    return self.weather_next_8days
                
                else:
                    raise Exception (f'Filed to retrieve current weather. Please try again. Error:{resp.status_code}')

        except:
            raise Exception (f'Filed to retrieve current weather. Please try again. Error:{resp.status_code}')




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


