"""
Personal AI Companion - v2 (terminal chat + long-term memory)
Uses Groq's free API + ChromaDB (local, free) for persistent memory.

Run:
    pip install groq chromadb sentence-transformers
    export GROQ_API_KEY="your_key_here"     (Mac/Linux)
    setx GROQ_API_KEY "your_key_here"        (Windows, then restart terminal)
    python chat_memory.py

New in v2:
    - Remembers facts about you across sessions (stored locally in ./memory_db)
    - After each reply, the LLM quietly decides if anything's worth saving
    - Type /remember <fact> to force-save something
    - Type /memories to see everything stored
    - Type /forget <number> to delete a memory
"""

import os
import sys
import json
import uuid
from groq import Groq
import chromadb
from chromadb.utils import embedding_functions

# ---- CONFIG ----
MODEL = "llama-3.3-70b-versatile"
NAME = "Girisha"
DB_PATH = "./memory_db"

SYSTEM_PROMPT_BASE = f"""You are {NAME}, a personal companion to the user. Core traits:

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

# ---- MEMORY SETUP ----
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
chroma_client = chromadb.PersistentClient(path=DB_PATH)
memory_collection = chroma_client.get_or_create_collection(
    name="memories", embedding_function=embedding_fn
)


def save_memory(fact: str):
    memory_collection.add(
        ids=[str(uuid.uuid4())],
        documents=[fact],
    )


def search_memories(query: str, n_results: int = 4):
    count = memory_collection.count()
    if count == 0:
        return []
    results = memory_collection.query(
        query_texts=[query], n_results=min(n_results, count)
    )
    return results["documents"][0] if results["documents"] else []


def is_duplicate(fact: str, threshold: float = 0.15) -> bool:
    """Check if a very similar memory already exists (lower distance = more similar)."""
    count = memory_collection.count()
    if count == 0:
        return False
    results = memory_collection.query(
        query_texts=[fact], n_results=1
    )
    if not results["distances"] or not results["distances"][0]:
        return False
    closest_distance = results["distances"][0][0]
    return closest_distance < threshold


def list_memories():
    all_items = memory_collection.get()
    return list(zip(all_items["ids"], all_items["documents"]))


def delete_memory(index: int):
    items = list_memories()
    if 0 <= index < len(items):
        mem_id, doc = items[index]
        memory_collection.delete(ids=[mem_id])
        return doc
    return None


def maybe_extract_memory(client, user_msg: str, assistant_msg: str):
    """Ask the LLM whether anything in this exchange is worth remembering long-term."""
    extraction_prompt = f"""Below is one exchange from a conversation. Decide if it contains
a durable fact worth remembering long-term about the user (preferences, ongoing situations,
important dates, relationships, goals, things they care about). Small talk, greetings, and
one-off questions are NOT worth remembering.

If there IS something worth remembering, respond with ONLY a short factual sentence
capturing it (max 20 words), nothing else.
If there is NOT, respond with exactly: NONE

User: {user_msg}
Assistant: {assistant_msg}
"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": extraction_prompt}],
            temperature=0,
            max_tokens=50,
        )
        result = response.choices[0].message.content.strip()
        if result and result.upper() != "NONE":
            if is_duplicate(result):
                return None
            save_memory(result)
            return result
    except Exception:
        pass
    return None


def build_system_prompt(user_msg: str) -> str:
    relevant = search_memories(user_msg)
    if not relevant:
        return SYSTEM_PROMPT_BASE
    memory_block = "\n".join(f"- {m}" for m in relevant)
    return (
        SYSTEM_PROMPT_BASE
        + f"\n\nThings you remember about the user from past conversations:\n{memory_block}\n"
        "Use these naturally if relevant. Don't force them in or list them out loud."
    )


def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY environment variable not set.")
        print("Get a free key at https://console.groq.com then set it:")
        print('  export GROQ_API_KEY="your_key_here"')
        sys.exit(1)

    client = Groq(api_key=api_key)
    messages = []  # session-only short-term history (system prompt rebuilt each turn)

    print(f"--- Chatting with {NAME} (memory enabled) ---")
    print("Commands: /remember <fact>, /memories, /forget <number>, quit\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            print(f"{NAME}: Talk soon. Take care of yourself.")
            break
        if not user_input:
            continue

        if user_input.startswith("/remember "):
            fact = user_input[len("/remember "):].strip()
            if fact:
                save_memory(fact)
                print(f"[saved: {fact}]\n")
            continue

        if user_input == "/memories":
            items = list_memories()
            if not items:
                print("[no memories stored yet]\n")
            else:
                for i, (_id, doc) in enumerate(items):
                    print(f"  {i}: {doc}")
                print()
            continue

        if user_input.startswith("/forget "):
            try:
                idx = int(user_input[len("/forget "):].strip())
                removed = delete_memory(idx)
                if removed:
                    print(f"[forgot: {removed}]\n")
                else:
                    print("[no memory at that number - check /memories]\n")
            except ValueError:
                print("[usage: /forget <number>]\n")
            continue

        # Build fresh system prompt with relevant memories pulled in
        system_prompt = build_system_prompt(user_input)
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        full_messages.append({"role": "user", "content": user_input})

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=full_messages,
                temperature=0.8,
                max_tokens=600,
            )
        except Exception as e:
            print(f"[Error talking to Groq: {e}]")
            continue

        reply = response.choices[0].message.content
        messages.append({"role": "user", "content": user_input})
        messages.append({"role": "assistant", "content": reply})

        print(f"\n{NAME}: {reply}\n")

        # Trim short-term history so it doesn't grow unbounded
        if len(messages) > 20:
            messages = messages[-20:]

        # Quietly check if this exchange contains something worth remembering long-term
        maybe_extract_memory(client, user_input, reply)


if __name__ == "__main__":
    main()