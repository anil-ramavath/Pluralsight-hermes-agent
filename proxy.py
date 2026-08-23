from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
import os
import uuid
import json

app = FastAPI()

PLURALSIGHT_API_KEY = os.environ.get("PLURALSIGHT_API_KEY")

PLURALSIGHT_URL = (
    "https://labs.pluralsight.com/"
    "labs-ai-proxy/rest/openai/chatgpt-4o/v1/chat/completions"
)


def extract_answer(data):
    print("\n=== RAW PLURALSIGHT JSON ===")
    print(json.dumps(data, indent=2))

    # Documented Pluralsight response
    if isinstance(data.get("message"), dict):
        if isinstance(data["message"].get("content"), str):
            return data["message"]["content"]

    # OpenAI-style response
    choices = data.get("choices")

    if isinstance(choices, list) and choices:
        choice = choices[0]

        if isinstance(choice, dict):

            message = choice.get("message")

            if isinstance(message, dict):
                content = message.get("content")

                if isinstance(content, str):
                    return content

            text = choice.get("text")

            if isinstance(text, str):
                return text

    # Other common response fields
    for key in ["content", "response", "text", "output"]:

        value = data.get(key)

        if isinstance(value, str):
            return value

    raise RuntimeError(
        "Could not find assistant text in Pluralsight response"
    )


@app.post("/v1/chat/completions")
async def chat(request: Request):

    try:

        if not PLURALSIGHT_API_KEY:
            raise RuntimeError(
                "PLURALSIGHT_API_KEY is not set"
            )

        body = await request.json()

        print("\n=== HERMES REQUEST ===")
        print(json.dumps(body, indent=2))

        messages = body.get("messages", [])

        prompt_parts = []

        for message in messages:

            role = message.get("role", "user")
            content = message.get("content", "")

            if isinstance(content, list):

                content = " ".join(
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict)
                )

            prompt_parts.append(
                f"{role}: {content}"
            )

        prompt_parts.append("assistant:")

        prompt = "\n".join(prompt_parts)

        print("\n=== PROMPT SENT TO PLURALSIGHT ===")
        print(prompt)

        response = requests.post(

            PLURALSIGHT_URL,

            headers={
                "Authorization":
                    f"Bearer {PLURALSIGHT_API_KEY}",

                "Content-Type":
                    "application/json",

                "Accept":
                    "application/json",
            },

            json={
                "prompt": prompt
            },

            timeout=120,
        )

        print("\n=== PLURALSIGHT HTTP STATUS ===")
        print(response.status_code)

        print("\n=== PLURALSIGHT RAW RESPONSE ===")
        print(response.text)

        if not response.ok:

            return JSONResponse(

                status_code=response.status_code,

                content={
                    "error": response.text
                }
            )

        data = response.json()

        answer = extract_answer(data)

        print("\n=== FINAL ANSWER ===")
        print(answer)

        return {

            "id":
                f"pluralsight-{uuid.uuid4()}",

            "object":
                "chat.completion",

            "choices": [

                {

                    "index": 0,

                    "message": {

                        "role":
                            "assistant",

                        "content":
                            answer
                    },

                    "finish_reason":
                        "stop"
                }
            ]
        }

    except Exception as e:

        import traceback

        traceback.print_exc()

        return JSONResponse(

            status_code=500,

            content={
                "error": str(e)
            }
        )
