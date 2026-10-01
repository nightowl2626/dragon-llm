"""Workshop API: browser -> Modal/FastAPI -> Qwen or ElevenLabs.

Read top to bottom: configuration, image build, startup, HTTP routes.
Redeploy with `modal deploy backend.py` after changing this file.
"""

import io
import json
import os
import time
from uuid import uuid4

import modal

# TRY IT: another compatible Hugging Face causal model. Larger models need
# more GPU memory and may expect different chat templates.
MODEL_ID = "Qwen/Qwen3-0.6B"
MODEL_DIR = "/models/qwen3-0.6b"

# Workshop previews appear in Modal logs. Disable for private conversations.
LOG_TEXT_PREVIEWS = True


def log(event, **details):
    """Modal captures stdout; JSON escapes newlines into one readable log line."""
    print(f"[Ember] {event} {json.dumps(details, ensure_ascii=True)}", flush=True)


def preview(text):
    """Short teaching previews; do not pass credentials or raw audio here."""
    if not LOG_TEXT_PREVIEWS:
        return "[disabled]"
    return text[:160] + ("..." if len(text) > 160 else "")

# START HERE: change this personality, redeploy, then compare the same question.
# This is prompting, not training: the model weights remain unchanged.
SYSTEM_PROMPT = """
You are Ember, a friendly dragon trainer assistant.

You are playful, warm, and lightly dragon-themed, but you are still a genuinely
useful assistant. Answer clearly and concisely. You can occasionally use a small
dragon metaphor or expression, but do not overdo the roleplay.

You are especially happy to explain technology to beginners.
""".strip()


# Download the open model once while the Modal image is being built.
# At runtime, inference happens on Modal. Hugging Face is not called for each chat.
def download_model():
    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=MODEL_ID,
        local_dir=MODEL_DIR,
    )


# These dependencies and weights live in Modal's image, not on your laptop.
image = (
    modal.Image.debian_slim(python_version="3.11")
    .uv_pip_install(
        "torch",
        "transformers>=4.52.4",
        "accelerate",
        "huggingface_hub",
        "fastapi[standard]",
        "python-multipart",
        "elevenlabs",
    )
    .run_function(download_model)
)

app = modal.App("dragon-trainer")


# Containers start on demand and can stop after 300 idle seconds. The next
# request may wait for model loading. One container is not a spending cap.
@app.function(
    image=image,
    gpu="A10",
    timeout=300,
    scaledown_window=300,
    max_containers=1,
    secrets=[modal.Secret.from_name("elevenlabs")],
)
@modal.asgi_app()
def web():
    # Runs remotely at startup; the model and clients are reused by the routes.
    from elevenlabs.client import ElevenLabs
    from fastapi import FastAPI, File, HTTPException, UploadFile, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch

    api = FastAPI(title="Dragon Trainer API")

    # Workshop/demo setting. For a real product, restrict this to your frontend origin.
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    startup = time.perf_counter()
    log("startup.loading_model", model=MODEL_ID)

    # Tokenizers map text to IDs; the model predicts subsequent token IDs.
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_DIR,
        torch_dtype="auto",
        device_map="auto",
    )
    model.eval()

    # Modal injects the secret into the environment. Never put keys in HTML.
    elevenlabs = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
    # A missing or blank optional setting uses the public George example voice.
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "").strip() or "JBFqnCBsd6RMkjVDRZzb"
    log("startup.ready", device=str(model.device), seconds=round(time.perf_counter() - startup, 2), text_previews=LOG_TEXT_PREVIEWS)

    @api.middleware("http")
    async def request_logs(request, call_next):
        # IDs connect lines when multiple workshop participants send requests.
        request.state.log_id = uuid4().hex[:8]
        started = time.perf_counter()
        log("request.received", request_id=request.state.log_id, method=request.method, path=request.url.path)
        try:
            response = await call_next(request)
        except Exception as error:
            log("request.failed", request_id=request.state.log_id, error_type=type(error).__name__)
            raise
        # Streaming headers arrive before the audio finishes; see speech.complete.
        log("response.headers", request_id=request.state.log_id, status=response.status_code, seconds=round(time.perf_counter() - started, 2))
        return response

    @api.get("/health")
    def health():
        return {"ok": True, "model": MODEL_ID}

    @api.post("/chat")
    def chat(data: dict, request: Request):
        started = time.perf_counter()
        # No database: the browser keeps history and resends it on every request.
        # Input: {"messages": [{"role": "user", "content": "Hello"}]}.
        incoming = data.get("messages", [])

        # Bound context and ignore client system roles. These demo checks are
        # not complete input validation or prompt-injection protection.
        clean_messages = []
        for message in incoming[-10:]:
            role = message.get("role")
            content = str(message.get("content", "")).strip()

            if role not in {"user", "assistant"} or not content:
                continue

            clean_messages.append(
                {"role": role, "content": content[:2000]}
            )

        if not clean_messages or clean_messages[-1]["role"] != "user":
            raise HTTPException(status_code=400, detail="A user message is required.")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *clean_messages,
        ]

        log("chat.prompt", request_id=request.state.log_id, messages=len(clean_messages), text=preview(clean_messages[-1]["content"]))

        # Each model expects particular role separators. Its template adds
        # those and the assistant start marker. Thinking=False is for Qwen3.
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )

        # Encode text as PyTorch tensors and move them to the model's device.
        inputs = tokenizer(text, return_tensors="pt").to(model.device)
        log("chat.generating", request_id=request.state.log_id, input_tokens=inputs.input_ids.shape[1], max_new_tokens=180)

        # No gradients needed: we generate text rather than train weights.
        with torch.inference_mode():
            outputs = model.generate(
                **inputs,
                max_new_tokens=180,  # TRY IT: reply budget in tokens, not words.
                temperature=0.7,  # Higher = more varied; keep > 0 when sampling.
                top_p=0.9,  # Sample tokens covering 90% of probability mass.
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )

        # Output includes prompt + reply. Slice off the prompt before decoding.
        generated = outputs[0][inputs.input_ids.shape[1]:]
        answer = tokenizer.decode(generated, skip_special_tokens=True).strip()
        log("chat.complete", request_id=request.state.log_id, output_tokens=len(generated), seconds=round(time.perf_counter() - started, 2), text=preview(answer))

        return {"response": answer}

    @api.post("/transcribe")
    async def transcribe(request: Request, audio: UploadFile = File(...)):
        started = time.perf_counter()
        # Multipart form with an `audio` file. Recognition runs at ElevenLabs.
        # Browser MediaRecorder commonly produces WebM/Opus on Chrome and MP4 on Safari.
        # ElevenLabs Scribe accepts both.
        raw = await audio.read()

        if not raw:
            raise HTTPException(status_code=400, detail="Empty audio file.")

        if len(raw) > 15 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Audio is too large.")

        # Wrap bytes as a file-like object for the SDK, without writing to disk.
        audio_file = io.BytesIO(raw)
        audio_file.name = audio.filename or "voice.webm"
        log("transcription.started", request_id=request.state.log_id, audio_bytes=len(raw), model="scribe_v2")

        result = elevenlabs.speech_to_text.convert(
            file=audio_file,
            model_id="scribe_v2",
            tag_audio_events=False,
            diarize=False,
        )

        transcript = result.text.strip()
        log("transcription.complete", request_id=request.state.log_id, seconds=round(time.perf_counter() - started, 2), characters=len(transcript), text=preview(transcript))
        return {"text": transcript}

    @api.post("/speak")
    def speak(data: dict, request: Request):
        started = time.perf_counter()
        text = str(data.get("text", "")).strip()

        if not text:
            raise HTTPException(status_code=400, detail="Text is required.")

        # Keep workshop requests short and predictable.
        text = text[:2500]
        log("speech.started", request_id=request.state.log_id, characters=len(text), text=preview(text))

        audio_stream = elevenlabs.text_to_speech.stream(
            voice_id=voice_id,
            output_format="mp3_22050_32",
            text=text,
            model_id="eleven_multilingual_v2",
        )

        # Forward MP3 chunks. Our browser waits for all bytes before playback.
        def logged_audio():
            # Streaming runs after the route returns. Count bytes here, not above,
            # so a provider failure cannot be mistaken for successful speech.
            total = 0
            try:
                for chunk in audio_stream:
                    total += len(chunk)
                    yield chunk
            except Exception as error:
                log("speech.failed", request_id=request.state.log_id, error_type=type(error).__name__, audio_bytes=total)
                raise
            else:
                log("speech.complete", request_id=request.state.log_id, audio_bytes=total, seconds=round(time.perf_counter() - started, 2))
            finally:
                audio_stream.close()

        return StreamingResponse(logged_audio(), media_type="audio/mpeg")

    return api
