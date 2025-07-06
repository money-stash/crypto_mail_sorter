import pollinations


def ask_ai(text):
    txt = pollinations.Text(
        model="openai",
        system="ты — помощник",
        contextual=True,
        temperature=0.7,
    )

    response = txt.Generate(prompt=text)

    return response
