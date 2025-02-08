import requests


def call_update_model_tos():
    # Define the URL of the Django API endpoint
    url = "http://127.0.0.1:8000/api/update_model_tos"

    # Prepare the POST data as a dictionary
    post_data = {
        "desc": "Example model description",
        "name": "test",
        "version": "1.0",
        "brand": "Example Brand",
        "model": "智己LS6",
        "hardware_config_version": "",
        "md5_value": "c5fdf4a8e66286fd5693f3bcebd40ae1"
    }

    # Send the POST request
    try:
        response = requests.post(url, data=post_data)

        # Check response status code
        if response.status_code == 200:
            print("Success:", response.json())
        else:
            print("Error:", response.status_code, response.json())
    except requests.exceptions.RequestException as e:
        print("HTTP Request failed:", e)


def search_tos():
    # Define the URL of the Django API endpoint
    url = "http://127.0.0.1:8000/api/search_model_tos"

    # Prepare the POST data as a dictionary
    post_data = {
        "model": "智己LS6",
        # "hardware_config_version": "v1.2.3",
    }

    # Send the POST request
    try:
        response = requests.post(url, data=post_data)

        # Check response status code
        if response.status_code == 200:
            print("Success:", response.json())
        else:
            print("Error:", response.status_code, response.json())
    except requests.exceptions.RequestException as e:
        print("HTTP Request failed:", e)
# Execute the function

# call_update_model_tos()
search_tos()
