""" 
Gets models from local webFrame instance and prints them to the console
Also saves the models to a file called models.txt
"""

def get_model_ids():
    import requests
    import json

    # Send POST request to get models list with empty search phrase and static flag
    response = requests.post('http://localhost:8004/v1/models_list', 
                           json={'search_phrase': '', 'static': True})
    
    # Parse JSON response
    models_data = response.json()
    
    # Extract model IDs
    model_ids = [model['id'] for model in models_data['data']]
    
    return model_ids

if __name__ == '__main__':
    model_ids = get_model_ids()
    
    # Print to console
    print("\nAvailable Models:")
    print("------------------")
    for model_id in model_ids:
        print(f"- {model_id}")
    
    # Save to file
    with open('models.txt', 'w') as f:
        f.write("Available Models:\n")
        f.write("------------------\n")
        for model_id in model_ids:
            f.write(f"- {model_id}\n")
    
    print("\nResults have been saved to models.txt")
