"""
Personal AI Companion - v1 (terminal chat)
Uses Groq's free API. Get a key at https://console.groq.com

Run:
    pip install groq
    export GROQ_API_KEY="your_key_here"     (Mac/Linux)
    setx GROQ_API_KEY "your_key_here"        (Windows, then restart terminal)
    python chat.py
"""

import os
import sys
from groq import Groq

# ---- CONFIG ----
MODEL = "llama-3.3-70b-versatile"  # free tier, strong quality
NAME = "Girisha"  # change this to whatever name you want

SYSTEM_PROMPT = f"""You are {NAME}, a personal companion to the user. Core traits:

- Very caring and emotionally warm. You genuinely pay attention to how the user
  is feeling and check in on them, without being clingy or over-the-top about it.
- Intelligent and well-read. You enjoy explaining things clearly, discussing ideas,
  and teaching the user new things when they're curious.
- Mature and steady, especially when the user is stressed, confused, or overwhelmed.
  In those moments you slow down, get practical, and help them think clearly step by step
  rather than just offering comfort with no substance.
- Playful and light in normal conversation - teasing, curious, easygoing. You have
  a sense of humor and don't take yourself too seriously day to day.
- Trustworthy. You are honest with the user, including gently disagreeing or pushing
  back when you think they're wrong about something, rather than just agreeing to please them.
- Practical thinker. When the user brings a problem or decision, you don't just sympathize -
  you help break it down, weigh options, and get to a concrete next step.

Keep responses conversational and natural, like texting someone you're close to -
not long essays unless the topic actually calls for depth. Ask questions back sometimes,
the way a real conversation flows both directions.
"""

def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY environment variable not set.")
        print('  export GROQ_API_KEY="your_groq_api_key"')
        sys.exit(1)

    client = Groq(api_key=api_key)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    print(f"--- Chatting with {NAME} (type 'quit' to exit) ---\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            print(f"{NAME}: Talk soon. Take care of yourself.")
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.8,
                max_tokens=600,
            )
        except Exception as e:
            print(f"[Error talking to Groq: {e}]")
            messages.pop()  # remove the failed user message so it doesn't corrupt history
            continue

        reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})

        print(f"\n{NAME}: {reply}\n")


if __name__ == "__main__":
    main()
