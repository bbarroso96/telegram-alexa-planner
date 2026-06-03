from datetime import date
from bot import sheets


def _get_today_speech() -> str:
    today_str = date.today().isoformat()
    all_tasks = sheets.get_all_tasks()

    tasks = [
        t for t in all_tasks
        if t.get("Done", "FALSE").upper() == "FALSE"
        and t.get("Type", "") != "Major"
        and (not t.get("Date") or t.get("Date") <= today_str)
    ]

    if not tasks:
        return "You have no tasks planned for today. Enjoy your day!"

    titles = [t["Title"] for t in tasks]

    if len(titles) == 1:
        return f"You have 1 task for today: {titles[0]}."

    task_list = ", ".join(titles[:-1]) + f", and {titles[-1]}"
    return f"You have {len(titles)} tasks for today: {task_list}."


def handle_intent(intent_name: str) -> dict:
    if intent_name == "GetTodayTasksIntent":
        speech = _get_today_speech()
    elif intent_name in ("AMAZON.HelpIntent",):
        speech = "You can ask me what's planned for today."
    elif intent_name in ("AMAZON.StopIntent", "AMAZON.CancelIntent"):
        speech = "Goodbye!"
    else:
        speech = "Sorry, I didn't understand that."

    return {
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "SSML",
                "ssml": f"<speak>{speech}</speak>",
            },
            "shouldEndSession": True,
        },
    }