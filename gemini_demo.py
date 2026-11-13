"""
Gemini API Template - Example Usage
Demonstrates basic text generation, streaming, and multi-turn conversations.
"""

import sys
from gemini_client import GeminiClient


def main():
    print("=" * 60)
    print(" Google Gemini API Template")
    print("=" * 60)

    # 1. Initialize Client (reads GEMINI_API_KEY from .env)
    try:
        gemini = GeminiClient()
        print("[✓] Client initialized successfully.")
    except Exception as e:
        print(f"[!] Initialization error: {e}")
        sys.exit(1)

    # 2. Basic Text Generation
    print("\n--- 1. Basic Text Generation ---")
    prompt = "Explain on ukrainian language in 2 sentences what an audio spectrum analyzer does."
    print(f"Prompt: {prompt}")
    print("Response:")
    response = gemini.generate_text(
        prompt=prompt,
        system_instruction="You are an audio engineering expert.",
    )
    print(response.strip())

    # 3. Streaming Response (Tokens streamed in real-time)
    print("\n--- 2. Streaming Response ---")
    stream_prompt = "List 3 key acoustic features used in audio classification."
    print(f"Prompt: {stream_prompt}")
    print("Streaming: ", end="", flush=True)
    for chunk in gemini.generate_stream(stream_prompt):
        print(chunk, end="", flush=True)
    print("\n")

    # 4. Multi-turn Stateful Conversation
    print("--- 3. Multi-turn Conversation ---")
    chat = gemini.create_conversation()

    # Turn 1
    t1 = "My favorite instrument is the acoustic cello."
    print(f"User: {t1}")
    r1 = chat.send_message(t1)
    print(f"Gemini: {r1.strip()}\n")

    # Turn 2 (Model remembers turn 1)
    t2 = "What frequency range does my favorite instrument typically cover?"
    print(f"User: {t2}")
    r2 = chat.send_message(t2)
    print(f"Gemini: {r2.strip()}")

    # 5. Audio Analysis Note
    print("\n--- 4. Audio Analysis ---")
    print("To analyze an audio file (.wav, .mp3, .ogg):")
    print('  result = gemini.analyze_audio("path/to/audio.wav", "Transcribe and analyze rhythm")')
    print("=" * 60)


if __name__ == "__main__":
    main()
