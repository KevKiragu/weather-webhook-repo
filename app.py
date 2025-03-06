from flask import Flask, request, jsonify
import requests
import os  # For environment variables

app = Flask(__name__)

# Set your OpenWeatherMap API key as an environment variable in Heroku ***
WEATHER_API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY')
if not WEATHER_API_KEY:
    WEATHER_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"  # Fallback for local testing (replace with your key for local runs too)
    print("Warning: OPENWEATHERMAP_API_KEY environment variable not set. Using fallback. For Heroku deployment, set it in Heroku Config Vars.")


WEATHER_API_BASE_URL = "https://api.openweathermap.org/data/2.5/weather?lat=44.34&lon=10.99&appid=ea802647cb6017af642b9d424646fa32"

def kelvin_to_fahrenheit(kelvin):
    fahrenheit = (kelvin - 273.15) * (9/5) + 32
    return fahrenheit

def get_weather_forecast(city):
    """Calls OpenWeatherMap API and gets weather forecast for a city."""
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

        forecast_response = (f"The weather in {city_name} is: {description}. "
                             f"Temperature: {temperature_celsius:.2f}°C ({temperature_fahrenheit:.2f}°F). "
                             f"Humidity: {humidity}%. Wind speed: {wind_speed} m/s.")
        return forecast_response

    except requests.exceptions.RequestException as e:
        print(f"API Request Error: {e}")
        return f"Sorry, I couldn't get weather for {city} right now. Please try again later."
    except KeyError as e:
        print(f"Data Parsing Error: {e} - API response format might have changed.")
        return f"Oops, something went wrong with the weather data. Please try again."

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint for Dialogflow fulfillment."""
    req_json = request.get_json(force=True)
    intent_name = req_json['queryResult']['intent']['displayName']
    parameters = req_json['queryResult']['parameters']

    if intent_name == 'GetWeather':
        city = parameters.get('city')
        if city:
            forecast_response = get_weather_forecast(city)
            fulfillment_text = forecast_response
        else:
            fulfillment_text = "Which city are you asking about?" # Should not happen if city is required in Dialogflow
    elif intent_name == 'GetDetails':
        # Placeholder for GetDetails fulfillment (will implement later)
        fulfillment_text = "Fulfillment for GetDetails is not yet implemented via Heroku."
    else:
        fulfillment_text = "Sorry, I didn't understand what you meant. Could you rephrase?"

    return jsonify({
        "fulfillmentText": fulfillment_text
    })

if __name__ == '__main__':
    app.run(debug=True) # Run Flask app in debug mode for local testing