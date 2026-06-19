import json

from fastapi import FastAPI, Request, HTTPException

from config.settings import config
from alexa import intents
from alexa.verify import verify, VerificationError

app = FastAPI()


def _supports_apl(body: dict) -> bool:
    """True if the requesting device has a screen that can render APL (Echo Show)."""
    interfaces = (
        body.get("context", {}).get("System", {}).get("device", {}).get("supportedInterfaces", {})
    )
    return "Alexa.Presentation.APL" in (interfaces or {})


@app.post("/alexa")
async def alexa_endpoint(request: Request):
    raw = await request.body()
    try:
        body = json.loads(raw)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON")

    # Reject anything that isn't a genuine, fresh request from Amazon for this skill.
    # Toggle off with ALEXA_VERIFY=false (local dev only — never in production).
    if config.alexa_verify:
        try:
            verify(request.headers, raw, body)
        except VerificationError as e:
            raise HTTPException(status_code=400, detail=f"request verification failed: {e}")

    request_type = body.get("request", {}).get("type")
    session_attributes = body.get("session", {}).get("attributes", {})
    supports_apl = _supports_apl(body)

    if request_type == "LaunchRequest":
        return intents.launch_response(supports_apl)

    elif request_type == "IntentRequest":
        intent = body["request"]["intent"]
        intent_name = intent["name"]
        slots = intent.get("slots", {})
        return intents.handle_intent(intent_name, slots, session_attributes, supports_apl)

    elif request_type == "SessionEndedRequest":
        return {"version": "1.0", "response": {}}

    raise HTTPException(status_code=400, detail="Unknown request type")
