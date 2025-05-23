import json
import sys
import traceback

import requests


def fetch_llm_response(prompt, print_usage=True) -> str:
    url = "http://localhost:10501/prompt"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "test",
    }
    # Set the data to be sent

    # This is expected to be a list of turns, ending with the user

    data = {"message": prompt}

    # Send the request and get the response
    response = requests.post(url, headers=headers, json=data, stream=True)
    if response.status_code != 200:
        print(
            f"Error: Failed to fetch response from server. Status code: {response.status_code}"
        )
        return

    output = ""
    for chunk in response.iter_content(chunk_size=None):
        try:
            responses = [
                ('{"choices": ' + f"{x}")
                for x in str(chunk.decode("utf-8")).split('{"choices":')[1:]
            ]
            for response in responses:
                response_json = json.loads(response.strip())
                print(
                    response_json["choices"][0]["message"]["content"],
                    flush=True,
                    end="",
                )
                output += response_json["choices"][0]["message"]["content"]
                if print_usage:
                    if "usage" in response_json:
                        if response_json["usage"] != {}:
                            print(f"\n\n{response_json['usage']}")
        except json.JSONDecodeError:
            print(traceback.format_exc())
            print("Invalid JSON:", chunk.decode("utf-8"))

    print("\n")
    return output

chat_history = [
    {
        "role": "system",
        "content": "You are a helpful assistant. Please help the user with their questions and answer as truthfully as you can. If you are unsure of an answer please state that you are not sure.",
    },
]


if __name__ == "__main__":
    while True:
        if len(sys.argv) > 1:
            # If command-line arguments are provided, join them into a single promptc
            prompt = " ".join(sys.argv[1:])
        else:
            # If no arguments are provided, ask for input interactively
            prompt = input("Enter your LLM prompt: ")
            if prompt == "exit":
                break
            if prompt.strip() == "":
                continue

        chat_history.append({"role": "user", "content": prompt})

        msg = fetch_llm_response(chat_history, True)
        chat_history.append(
            {
                "role": "assistant",
                "content": msg,
            }
        )
