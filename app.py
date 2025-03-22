from flask import Flask, render_template, request, jsonify
import pandas as pd
import pickle
import requests
import os

app = Flask(__name__, static_folder='static', template_folder='templates')

# Load API keys from environment variables or set them directly
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', '3fcbb4e945f4372e7b24f6d4b17b9ec4')
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', 'AIzaSyDVe7e401j8dwNr8SdH99rfDdn9-N8NlZU')

# Load dataset
df = pd.read_csv('holidify.csv')

# Load the trained travel model
try:
    with open('travel_model.pkl', 'rb') as f:
        travel_model = pickle.load(f)
    print("Travel model loaded successfully!")
except Exception as e:
    print("Error loading travel model:", e)
    travel_model = None


def get_weather(city):
    """Fetch weather data for a city using the OpenWeather API."""
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {'q': city, 'appid': OPENWEATHER_API_KEY, 'units': 'metric'}
    try:
        response = requests.get(base_url, params=params)
        data = response.json()
        # Simplify weather info
        weather = {
            'description': data['weather'][0]['description'].capitalize(),
            'temp': data['main']['temp'],
            'humidity': data['main']['humidity']
        }
        return weather
    except Exception as e:
        print("Error fetching weather:", e)
        return None


def get_traffic(city):
    """Fetch simulated traffic data using Google Maps API.
       (Note: For real-time traffic, you'd typically use the Directions API with traffic_model parameters.)
    """
    base_url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    # Simulate origin as a central location in India (e.g., New Delhi)
    origin = "New Delhi, India"
    params = {
        'origins': origin,
        'destinations': city + ", India",
        'key': GOOGLE_MAPS_API_KEY,
        'departure_time': 'now'
    }
    try:
        response = requests.get(base_url, params=params)
        data = response.json()
        # Extract duration in traffic if available
        if data['rows'][0]['elements'][0].get('duration_in_traffic'):
            traffic_duration = data['rows'][0]['elements'][0]['duration_in_traffic']['value']
        else:
            traffic_duration = data['rows'][0]['elements'][0]['duration']['value']
        return traffic_duration  # lower value means less traffic
    except Exception as e:
        print("Error fetching traffic data:", e)
        return None


def get_recommendations(user_input):
    """
    Use the pre-trained model to generate recommendations.
    This example assumes the model has a method 'predict' or similar that returns recommendations
    for a given input. Adjust as per your model's API.
    """
    # For demonstration, let's assume the model takes a user input (like preferred region or travel style)
    # and returns a list of city indices (or names) ranked by suitability.
    # In this demo, we'll simply rank all cities based on weather and traffic conditions.
    recommendations = []

    for index, row in df.iterrows():
        city = row['City']
        weather = get_weather(city)
        traffic = get_traffic(city)
        if weather is None or traffic is None:
            continue

        # A simple scoring: lower traffic (normalized) and lower chance of bad weather improve score.
        # For instance, clear weather (e.g., description includes "Clear") and minimal traffic.
        weather_score = 0
        if "Clear" in weather['description']:
            weather_score = 1  # best
        # Normalize traffic (assuming duration in seconds; lower is better)
        traffic_score = 1 / (traffic + 1)  # avoid division by zero

        # Combine scores. You can adjust weights based on your priorities.
        overall_score = 0.6 * weather_score + 0.4 * traffic_score

        recommendations.append({
            'city': city,
            'rating': row.get('Rating', 'N/A'),
            'description': row.get('About the city (long Description)', ''),
            'best_time': row.get('Best Time to visit', ''),
            'weather': weather,
            'traffic': traffic,
            'score': overall_score
        })

    # Sort recommendations by overall_score in descending order
    sorted_recommendations = sorted(recommendations, key=lambda x: x['score'], reverse=True)
    return sorted_recommendations


@app.route('/')
def index():
    return render_template('index.html', google_maps_api_key=GOOGLE_MAPS_API_KEY)


@app.route('/plan', methods=['GET', 'POST'])
def plan_trip():
    if request.method == 'POST':
        # Retrieve user input from form (e.g., travel preferences)
        user_input = request.form.get('preferences')
        # You could also get more inputs such as current location, budget, etc.

        # Get recommendations from the travel model and API data
        recommendations = get_recommendations(user_input)

        return render_template('results.html', recommendations=recommendations)
    return render_template('plan_trip.html')


@app.route('/api/recommend', methods=['POST'])
def api_recommend():
    data = request.get_json()
    user_input = data.get('preferences', '')
    recommendations = get_recommendations(user_input)
    return jsonify(recommendations)


if __name__ == '__main__':
    app.run(debug=True)
