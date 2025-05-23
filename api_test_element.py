import asyncio
import json
import os
from functools import wraps
from uuid import UUID

from element_framework import Context, Element
from element_framework.comms.messages import ColorFormat, Frame, Preview
from element_framework.element.settings import (
    ElementSettings,
    NumberSetting,
    TextSetting,
)
from element_framework.element.variables import (
    ElementInputs,
    ElementOutputs,
    Input,
    Output,
)
from quart import Quart, Response, jsonify, request
from quart_cors import cors, route_cors


class Inputs(ElementInputs):
    in1 = Input[Frame]()


class Outputs(ElementOutputs):
    preview = Output[Preview]()
    out1 = Output[Frame]()


class Settings(ElementSettings):
    api_key = TextSetting(
        name="api_key",
        display_name="API key",
        default="",
        sensitive=True,
    )

    timeout = NumberSetting[float](
        name="timeout",
        display_name="Endpoint Timeout Seconds",
        description="Timeout for SSE endpoint, default is 0 or no timeout",
        default=0.0,
        min_value=0.0,
        hints=["advanced"],
    )


element = Element(
    id=UUID("68f81646-53de-4952-b171-6ee7cdbd9fb0"),
    name="api",
    display_name="API",
    description="Facilitates communication with a Large Language Model. It sends a user-defined prompt (instruction or question) to the model, receives the model's generated response, and returns the response.",
    version="0.0.23",
    inputs=Inputs(),
    outputs=Outputs(),
    settings=Settings(),
    init_run=True,
)


class ElementPreviewServer(Quart):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.startup_event = asyncio.Event()

    async def startup(self):
        await super().startup()
        self.startup_event.set()


app = ElementPreviewServer(__name__)
app = cors(app, allow_origin="*")


class PromptRequest:
    def __init__(self, prompt):
        self.prompt = prompt
        self.queue = asyncio.Queue()


requests = asyncio.Queue()
curr_request = None

api_key_list = []
initialFrame = True

prev_token_count = 0
api_tokens = []
endpoint_timeout = 0.0


def token_required(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        global api_tokens
        token = request.headers.get("X-API-Key")

        if not token:
            return jsonify({"message": "API key is missing"}), 401
        if token not in api_tokens:
            return jsonify({"message": "Invalid API key"}), 401
        return await f(*args, **kwargs)

    return decorated


def set_api_token(secret_value: str):
    global api_tokens
    api_tokens = secret_value.split(",")


@element.startup
async def startup(ctx: Context[Inputs, Outputs, Settings]):

    global api_tokens, endpoint_timeout
    user_api_key = ctx.settings.api_key.value
    endpoint_timeout = ctx.settings.timeout.value
    api_tokens = [t.strip() for t in user_api_key.split(",")]
    port = ctx.preview_port
    print(f"Serving on {port}")

    asyncio.create_task(app.run_task(host="0.0.0.0", port=port, debug=False))


@element.executor
async def run(ctx: Context[Inputs, Outputs, Settings]):
    """
    OpenAI Response Structure
    {
    "choices": [
        {
        "finish_reason": "stop",
        "index": 0,
        "message": {
            "content": "The 2020 World Series was played in Texas at Globe Life Field in Arlington.",
            "role": "assistant"
        },
        "logprobs": null
        }
    ],
    "created": 1677664795,
    "id": "chatcmpl-7QyqpwdfhqwajicIEznoc6Q47XAyW",
    "model": "gpt-4o-mini",
    "object": "chat.completion",
    # we can add these later if they need them
    "usage": {
        "completion_tokens": 17,
        "prompt_tokens": 57,
        "total_tokens": 74
    }
    }
    """
    global initialFrame, prev_token_count, curr_request

    # Initialize the LLM element
    if initialFrame:
        initialFrame = False
        yield ctx.outputs.out1(Frame(ndframe=None, other_data={"init": True}))

    while True:
        if not curr_request:
            # Note that these are some of the arguments normally passed to create a chat completion with gpt
            """
            gpt.chat.completions.create(
                        model=self._model_name,
                        messages=messages,
                        max_tokens=self._config.max_tokens,
                        temperature=self._config.temp,
                        stream=self._config.stream,
                    )
            """
            request = await requests.get()
            curr_request = request

            yield ctx.outputs.out1(
                Frame(
                    ndframe=None,
                    other_data={"api": request.prompt},
                )
            )
        else:
            frame = ctx.inputs.in1.value  # TODO: make sure we don't propogate old data
            if (
                frame is None
                or curr_request is None
                or "init" in frame.other_data
                or "message" not in frame.other_data
                or (frame.other_data["token_number"] == prev_token_count)
            ):
                return

            prev_token_count = frame.other_data["token_number"]
            output = {
                "choices": [
                    {
                        "finish_reason": (
                            None if not frame.other_data["done"] else "length"
                        ),
                        "index": 0,
                        "message": {
                            "content": frame.other_data["message"],
                            "role": "assistant",
                        },
                        "logprobs": None,
                    }
                ],
                "created": 1677664795,
                "id": "webaichat-6ee7cdbd9fb0",
                "model": "nav",
                "object": "chat.completion",
                "usage": frame.other_data.get("usage", {"token_number": frame.other_data.get("token_number")}),
            }

            await curr_request.queue.put(output)

            if frame.other_data["done"] == True:
                curr_request = None
                continue
            else:
                return


@app.route("/")
async def index():
    return "Please use the API endpoint /prompt"


@app.route(
    "/prompt", methods=["POST", "OPTIONS"]
)  # TODO: Construct the address similar to OpenAI?
@route_cors(
    allow_headers=["Content-Type", "X-API-Key"],
    allow_methods=["POST"],
)
async def prompt():
    if request.method == "OPTIONS":
        response = Response("", status=200)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-API-Key"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        return response

    @token_required
    async def handle_prompt():
        global endpoint_timeout

        # TODO: Check the key in the header and make sure it's in the setting's list
        # api_key = request.headers.get("x-api-key")
        # if api_key != user_api_key:
        #   abort(401, description="Invalid API key")

        data = await request.get_json()
        if "message" not in data:
            return jsonify({"error": 'Missing "message" field in JSON'}), 400

        # Pass the prompt
        # should come in as a list in the openAI style
        promptRequest = PromptRequest(data["message"])
        queue = promptRequest.queue
        await requests.put(promptRequest)

        # Wait for responses and stream them out as they are received
        # TODO: Are these the correct headers?
        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }

        async def event_stream(queue: asyncio.Queue):
            while True:
                try:
                    response = await queue.get()

                    if "choices" not in response or not isinstance(
                        response["choices"], list
                    ):
                        print("Invalid response format")
                        continue

                    # TODO: Structure response as OpenAPI chunk messages before sending back
                    yield json.dumps(response)
                    if response["choices"][-1].get("finish_reason") is not None:
                        break
                except Exception as e:
                    print(f"API: Error: {e}")
                    continue

        resp = Response(event_stream(queue), headers=headers)
        resp.timeout = endpoint_timeout if endpoint_timeout > 0 else None
        return resp

    return await handle_prompt()