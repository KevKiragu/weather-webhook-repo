from flask import Flask, request, jsonify
import requests
import os  # For environment variables

app = Flask(__name__)

# Set your OpenWeatherMap API key as an environment variable in Heroku ***
WEATHER_API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY')
if not WEATHER_API_KEY:
    WEATHER_API_KEY = "0cff8841701acf82d6c36ba9dfa762b8"  # Fallback for local testing - USING USER'S API KEY
    print("Warning: OPENWEATHERMAP_API_KEY environment variable not set. Using fallback. For Heroku deployment, set it in Heroku Config Vars.")

# Corrected WEATHER_API_BASE_URL - just the base URL, no parameters here
WEATHER_API_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

def kelvin_to_fahrenheit(kelvin):
    fahrenheit = (kelvin - 273.15) * (9/5) + 32
    return fahrenheit

def get_weather_forecast(city):
    """Calls OpenWeatherMap API and gets weather forecast for a city and details."""
    params = {
        'q': city,
        'appid': WEATHER_API_KEY,
        'units': 'metric' # or 'imperial' for Fahrenheit
    }
    try:
        response = requests.get(WEATHER_API_BASE_URL, params=params)
        response.raise_for_status()
        weather_data = response.json()

        temperature_kelvin = weather_data['main']['temp']
        temperature_celsius = temperature_kelvin
        temperature_fahrenheit = kelvin_to_fahrenheit(temperature_kelvin)
        humidity = weather_data['main']['humidity']
        wind_speed = weather_data['wind']['speed']
        description = weather_data['weather'][0]['description']
        city_name = weather_data['name']

        # Return all weather data in a dictionary for easier access in webhook()
        return {
            "city_name": city_name,
            "description": description,
            "temperature_celsius": f"{temperature_celsius:.2f}°C",
            "temperature_fahrenheit": f"{temperature_fahrenheit:.2f}°F",
            "humidity": f"{humidity}%",
            "wind_speed": f"{wind_speed} m/s"
        }

    except requests.exceptions.RequestException as e:
        print(f"API Request Error: {e}")
        return {"error": f"Sorry, I couldn't get weather for {city} right now. Please try again later."}
    except KeyError as e:
        print(f"Data Parsing Error: {e} - API response format might have changed.")
        return {"error": "Oops, something went wrong with the weather data. Please try again."}

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint for Dialogflow fulfillment."""
    req_json = request.get_json(force=True)
    intent_name = req_json['queryResult']['intent']['displayName']
    parameters = req_json['queryResult']['parameters']  

    if intent_name == 'GetWeather':
        city = parameters.get('geo-city') # Utilizes'geo-city' for purposes of matching Dialogflow in the parameter name
        if city:
            weather_data = get_weather_forecast(city) # The get_weather_forecast resquest returns a workable dictionary
            if "error" in weather_data: # This step checks for errors after retreiving the from get_weather_forecast
                fulfillment_text = weather_data["error"]
            else:
                fulfillment_text = (f"The weather in {weather_data['city_name']} is: {weather_data['description']}. "
                                    f"Temperature: {weather_data['temperature_celsius']} ({weather_data['temperature_fahrenheit']}). "
                                    f"Humidity: {weather_data['humidity']}. Wind speed: {weather_data['wind_speed']}.")
        else:
            fulfillment_text = "Which city are you asking about?" # Should not happen if city is required in Dialogflow

    elif intent_name == 'GetDetails':
        city = parameters.get('geo-city') # Get city - assuming context is maintained from previous GetWeather intent.
        detail_request = parameters.get('request') # Use 'request' now (corrected parameter name)

        if city and detail_request:
            weather_data = get_weather_forecast(city) # Get weather data again for the city
            if "error" in weather_data:
                fulfillment_text = weather_data["error"]
            else:
                details_info = [] # List to build details response
                if "humidity" in detail_request:
                    details_info.append(f"Humidity is {weather_data['humidity']}")
                if "wind" in detail_request: # Assuming "wind" can also be in detail_request (check Dialogflow entity)
                    details_info.append(f"Wind speed is {weather_data['wind_speed']}")

                if details_info: # If we have details to provide
                    fulfillment_text = ", ".join(details_info) # Join humidity and/or wind details with comma
                else:
                    fulfillment_text = "Sorry, I couldn't retrieve the requested weather details." # Should not usually happen

        else:
            fulfillment_text = "Could you please specify both the city and the weather details you are interested in (like humidity or wind)?" # More informative error.  Might need to refine this based on Dialogflow setup.


    else:
        fulfillment_text = "Sorry, I didn't understand what you meant. Could you rephrase?"

    return jsonify({
        "fulfillmentText": fulfillment_text
    })

if __name__ == '__main__':
    app.run(debug=True) # Run Flask app in debug mode for local testing