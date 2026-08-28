"""
Personal AI Companion - v3 (voice in, voice out, + memory)
Groq (brain) + ChromaDB (memory) + faster-whisper (ears) + edge-tts (voice)

Install:
    python -m pip install groq chromadb sentence-transformers faster-whisper edge-tts sounddevice soundfile pygame

Setup:
    export GROQ_API_KEY="your_key_here"     (Mac/Linux)
    setx GROQ_API_KEY "your_key_here"        (Windows, then restart terminal)

Run:
    python voice_chat.py

How it works:
    - Press ENTER to start talking, speak, press ENTER again to stop
    - It transcribes what you said, sends it to the brain (with memory context),
      then speaks the reply back out loud
    - Type instead of speaking any time by just typing text + Enter at the prompt
    - Commands still work: /remember <fact>, /memories, /forget <number>, quit
"""

import os
import sys
import uuid
import asyncio
import tempfile

import numpy as np
import sounddevice as sd
import soundfile as sf
from groq import Groq
import chromadb
from chromadb.utils import embedding_functions
from faster_whisper import WhisperModel
import edge_tts
import pygame

# ---- CONFIG ----
MODEL = "llama-3.3-70b-versatile"
NAME = "Girisha"
DB_PATH = "./memory_db"
WHISPER_MODEL_SIZE = "base"       # tiny/base/small - base is a good speed/accuracy balance on CPU
TTS_VOICE = "en-US-AriaNeural"    # natural-sounding edge-tts voice; try en-US-JennyNeural too
SAMPLE_RATE = 16000

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

Keep responses SHORT and conversational - you're being heard out loud, not read.
Avoid long lists or lots of punctuation-heavy structure. Talk the way people actually talk.
Ask questions back sometimes, the way a real conversation flows both directions.
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
    memory_collection.add(ids=[str(uuid.uuid4())], documents=[fact])


def search_memories(query: str, n_results: int = 4):
    count = memory_collection.count()
    if count == 0:
        return []
    results = memory_collection.query(query_texts=[query], n_results=min(n_results, count))
    return results["documents"][0] if results["documents"] else []


def is_duplicate(fact: str, threshold: float = 0.15) -> bool:
    count = memory_collection.count()
    if count == 0:
        return False
    results = memory_collection.query(query_texts=[fact], n_results=1)
    if not results["distances"] or not results["distances"][0]:
        return False
    return results["distances"][0][0] < threshold


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


# ---- VOICE: SPEECH-TO-TEXT ----
print("Loading speech recognition model (first run downloads it, be patient)...")
whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")


def record_until_enter() -> str:
    """Records mic audio until the user presses Enter again. Returns path to a temp wav file."""
    print("[recording... press ENTER to stop]")
    frames = []

    def callback(indata, frame_count, time_info, status):
        frames.append(indata.copy())

    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=callback)
    with stream:
        input()  # blocks until Enter pressed again

    if not frames:
        return None

    audio = np.concatenate(frames, axis=0)
    tmp_path = os.path.join(tempfile.gettempdir(), f"rec_{uuid.uuid4().hex}.wav")
    sf.write(tmp_path, audio, SAMPLE_RATE)
    return tmp_path


def transcribe(wav_path: str) -> str:
    segments, _ = whisper_model.transcribe(wav_path, language="en")
    text = " ".join(seg.text.strip() for seg in segments)
    try:
        os.remove(wav_path)
    except OSError:
        pass
    return text.strip()


# ---- VOICE: TEXT-TO-SPEECH ----
pygame.mixer.init()


async def _speak_async(text: str):
    tmp_path = os.path.join(tempfile.gettempdir(), f"tts_{uuid.uuid4().hex}.mp3")
    communicate = edge_tts.Communicate(text, TTS_VOICE)
    await communicate.save(tmp_path)
    pygame.mixer.music.load(tmp_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)
    pygame.mixer.music.unload()
    try:
        os.remove(tmp_path)
    except OSError:
        pass


def speak(text: str):
    asyncio.run(_speak_async(text))


# ---- MAIN LOOP ----
def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY environment variable not set.")
        sys.exit(1)

    client = Groq(api_key=api_key)
    messages = []

    print(f"\n--- Talking with {NAME} (voice mode) ---")
    print("Press ENTER to start speaking, ENTER again to stop.")
    print("Or just type a message instead. Commands: /remember, /memories, /forget <n>, quit\n")

    while True:
        print("You: ", end="", flush=True)
        first = input()  # empty Enter = start voice recording; non-empty = typed message

        if first.lower() in ("quit", "exit"):
            print(f"{NAME}: Talk soon. Take care of yourself.")
            speak("Talk soon. Take care of yourself.")
            break

        if first == "":
            wav_path = record_until_enter()
            if wav_path is None:
                continue
            user_input = transcribe(wav_path)
            if not user_input:
                print("[didn't catch that, try again]\n")
                continue
            print(f"(heard: {user_input})")
        else:
            user_input = first.strip()
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
                print(f"[forgot: {removed}]\n" if removed else "[no memory at that number]\n")
            except ValueError:
                print("[usage: /forget <number>]\n")
            continue

        system_prompt = build_system_prompt(user_input)
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        full_messages.append({"role": "user", "content": user_input})

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=full_messages,
                temperature=0.8,
                max_tokens=300,
            )
        except Exception as e:
            print(f"[Error talking to Groq: {e}]")
            continue

        reply = response.choices[0].message.content
        messages.append({"role": "user", "content": user_input})
        messages.append({"role": "assistant", "content": reply})

        print(f"\n{NAME}: {reply}\n")
        speak(reply)

        if len(messages) > 20:
            messages = messages[-20:]

        maybe_extract_memory(client, user_input, reply)


if __name__ == "__main__":
    main()
