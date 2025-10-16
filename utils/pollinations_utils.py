import requests


def ask_ai_google(prompt: str) -> str:
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    params = {"key": "AIzaSyACatPWoKiilMQljY3d5abxoSM6BErP63g"}

    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    resp = requests.post(url, params=params, json=payload)
    resp.raise_for_status()
    data = resp.json()

    return data["candidates"][0]["content"]["parts"][0]["text"]


def ask_ai(text: str) -> str:
    url = "https://text.pollinations.ai/"
    payload = {
        "model": "openai",
        "system": "ты — помощник",
        "contextual": True,
        "temperature": 0.7,
        "prompt": text,
    }

    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    return resp.text


def ask_ai_with_fallback(text: str) -> str:
    try:
        return ask_ai(text)
    except Exception as e:
        print("Ошибка:", e)
        return ask_ai_google(text)


if __name__ == "__main__":
    print(ask_ai_with_fallback("Привет, как дела?"))
