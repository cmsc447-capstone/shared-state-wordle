import requests

# 1. Define the API endpoint
url = "https://random-word-api.herokuapp.com/word?length=5&diff=3" # A free API that looks up zip codes

# 2. Send the request
response = requests.get(url)

# 3. Check if successful and parse the JSON data
if response.status_code == 200:
    data = response.json()
    print(f"Word: {data[0]}")
else:
    print("Failed to retrieve data.")
