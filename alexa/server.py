from fastapi import FastAPI, Request, HTTPException
from alexa.intents import handle_intent

app = FastAPI()


@app.post("/alexa")
async def alexa_endpoint(request: Request):
    body = await request.json()

    request_type = body.get("request", {}).get("type")

    if request_type == "LaunchRequest":
        return {
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "SSML",
                    "ssml": "<speak>Welcome to your planner. You can ask me what's planned for today.</speak>",
                },
                "shouldEndSession": False,
            },
        }

    elif request_type == "IntentRequest":
        intent_name = body["request"]["intent"]["name"]
        return handle_intent(intent_name)

    elif request_type == "SessionEndedRequest":
        return {"version": "1.0", "response": {}}

    raise HTTPException(status_code=400, detail="Unknown request type")
