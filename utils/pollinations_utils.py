import pollinations

txt = pollinations.Text(
    model="openai",
    system="you — помощник",
    contextual=True,
    temperature=0.7,
)

response = txt.Generate(prompt="что такое биткоин?")
print(response)
