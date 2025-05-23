import json
import time
import os
import argparse
import traceback
import pandas as pd

import requests


def fetch_llm_response(prompt, print_usage=False) -> dict:
    url = "http://localhost:10501/prompt"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "test",
    }
    # Set the data to be sent

    # This is expected to be a list of turns, ending with the user
    data = {"message": [{"role": "user", "content": prompt}]}

    # Send the request and get the response
    start = time.time()
    try:
        response = requests.post(url, headers=headers, json=data, stream=True)
        if response.status_code != 200:
            print(
                f"Error: Failed to fetch response from server. Status code: {response.status_code}"
            )
            return {
                "error": True,
                "status_code": response.status_code,
                "ttft": None,
                "tok/s": None,
                "tokens": 0,
                "init_tokens": 0
            }
    except requests.exceptions.RequestException as e:
        print(f"Error: Failed to connect to server. {str(e)}")
        return {
            "error": True,
            "status_code": None,
            "ttft": None,
            "tok/s": None,
            "tokens": 0,
            "init_tokens": 0
        }

    tok = 0
    init_tokens = 0
    ttft = None
    end = None
    for chunk in response.iter_content(chunk_size=None):
        try:
            responses = [
                ('{"choices": ' + f"{x}")
                for x in str(chunk.decode("utf-8")).split('{"choices":')[1:]
            ]
            for response in responses:
                response_json = json.loads(response.strip())
                # Handle different token count field names
                if "usage" in response_json:
                    usage = response_json["usage"]
                    # Try different common token count field names
                    token_count = None
                    if "token_number" in usage:
                        token_count = usage["token_number"]
                    elif "completion_tokens" in usage:
                        token_count = usage["completion_tokens"]
                    elif "total_tokens" in usage:
                        token_count = usage["total_tokens"]
                    elif "tokens" in usage:
                        token_count = usage["tokens"]
                    
                    if token_count is not None and token_count > 0:
                        tok = token_count
                
                if tok >= 1 and ttft is None:
                    init_tokens = tok
                    tmp = time.time()
                    ttft = time.time() - start
                    start = tmp
                
                if "choices" in response_json and len(response_json["choices"]) > 0:
                    if "message" in response_json["choices"][0] and "content" in response_json["choices"][0]["message"]:
                        print(
                            response_json["choices"][0]["message"]["content"],
                            flush=True,
                            end="",
                        )
        except json.JSONDecodeError:
            print(traceback.format_exc())
            print("Invalid JSON:", chunk.decode("utf-8"))
            return {
                "error": True,
                "status_code": None,
                "ttft": None,
                "tok/s": None,
                "tokens": 0,
                "init_tokens": 0
            }
        except KeyError as e:
            print(f"Warning: Missing expected key in response: {str(e)}")
            continue

    end = time.time() - start
    print("\n")

    return {
        "error": False,
        "status_code": 200,
        "ttft": ttft,
        "tok/s": (tok - init_tokens) / end if end > 0 else 0,
        "tokens": tok,
        "init_tokens": init_tokens,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="webAI Platform Test Utility")

    # Test fixture only
    parser.add_argument(
        "-m", "--model", type=str, default="llama-3.1-8b", help="Hugging Face Model ID"
    )
    parser.add_argument(
        "-p", "--prompt", type=str, default="Once upon a time,", help="Prompt"
    )
    parser.add_argument(
        "-i", "--iterations", type=int, default=1, help="Test Iterations"
    )
    parser.add_argument(
        "-s", "--save", type=bool, default=False, help="Save results in CSV"
    )

    args = parser.parse_args()

    df = None
    if args.save:
        try:
            os.mkdir("artifacts")
        except BaseException as _:
            pass
        try:
            df = pd.read_csv(os.path.expanduser("artifacts/platform-results.csv"))
        except BaseException as _:
            pass

    for _ in range(args.iterations):
        test_data = fetch_llm_response(args.prompt, True)
        
        if test_data["error"]:
            print(f"Test failed with status code: {test_data['status_code']}")
            continue

        if df is None:
            df = pd.DataFrame(
                {
                    "model": [args.model],
                    "ttft": [test_data["ttft"]],
                    "tok/s": [test_data["tok/s"]],
                    "tokens": [test_data["tokens"]],
                    "init_tokens": [test_data["init_tokens"]],
                }
            )
        else:
            df = pd.concat(
                [
                    df,
                    pd.DataFrame(
                        {
                            "model": [args.model],
                            "ttft": [test_data["ttft"]],
                            "tok/s": [test_data["tok/s"]],
                            "tokens": [test_data["tokens"]],
                            "init_tokens": [test_data["init_tokens"]],
                        }
                    ),
                ],
                ignore_index=True,
            )
        print(df)
        if args.save:
            df.to_csv(os.path.expanduser("artifacts/platform-results.csv"), index=False)
