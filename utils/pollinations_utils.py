import pollinations
import google.generativeai as genai


def ask_ai_google(prompt):
    genai.configure(api_key="AIzaSyACatPWoKiilMQljY3d5abxoSM6BErP63g")
    model = genai.GenerativeModel("gemini-1.5-flash")

    response = model.generate_content(prompt)

    return response.text


def ask_ai(text):
    txt = pollinations.Text(
        model="openai",
        system="ты — помощник",
        contextual=True,
        temperature=0.7,
    )

    response = txt.Generate(prompt=text)

    return response


def ask_ai_with_fallback(text):
    try:
        response = ask_ai(text)
        return response
    except Exception as e:
        print(e)
        return ask_ai_google(text)
