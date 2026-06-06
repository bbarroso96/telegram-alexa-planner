from fastapi import FastAPI, Request, HTTPException
from alexa.intents import handle_intent

app = FastAPI()


@app.post("/alexa")
async def alexa_endpoint(request: Request):
    body = await request.json()

    request_type = body.get("request", {}).get("type")
    session_attributes = body.get("session", {}).get("attributes", {})

    if request_type == "LaunchRequest":
        return {
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "SSML",
                    "ssml": "<speak>Welcome to your planner. You can ask me what's planned for today, mark tasks as done, or add a quick task.</speak>",
                },
                "shouldEndSession": False,
            },
        }

    elif request_type == "IntentRequest":
        intent = body["request"]["intent"]
        intent_name = intent["name"]
        slots = intent.get("slots", {})
        return handle_intent(intent_name, slots, session_attributes)

    elif request_type == "SessionEndedRequest":
        return {"version": "1.0", "response": {}}

    raise HTTPException(status_code=400, detail="Unknown request type")