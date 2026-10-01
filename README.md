# 🐉 Ember — Dragon Trainer

A deliberately tiny workshop demo showing how an open model becomes an application.

[Try the live demo](https://nightowl2626.github.io/dragon-llm/)

**Make it yours:** copy or fork this repository, get the original running, then
change one thing at a time. Start with Ember's personality in `backend.py`.
No frontend build tools or local GPU are required.

- **Qwen3-0.6B** model weights come from Hugging Face.
- The model itself runs on a **Modal A10 GPU**.
- **ElevenLabs Scribe v2** turns microphone recordings into text.
- **ElevenLabs TTS** speaks Ember's responses.
- `index.html` is a mobile-first static frontend that can live on **GitHub Pages**.
- `dragon.js` adds an optional animated **Three.js** welcome dragon. It is built
  from editable shapes, with no 3D model files or extra backend services.

## Architecture

```text
                     build time
Hugging Face ─────────────────────────► Modal image
                Qwen model weights


                     runtime
            ┌──────────────────────────────┐
phone ─────►│ Modal backend                │
browser     │                              │
            │ /chat       → Qwen/GPU       │
            │ /transcribe → ElevenLabs     │
            │ /speak      → ElevenLabs     │
            └──────────────────────────────┘
                    │
                    ▼
               phone browser
```

The important workshop point: **Hugging Face stores the model; Modal serves it.**

## Files

```text
backend.py   # Modal + Qwen + ElevenLabs endpoints
index.html   # mobile-first chat + microphone UI
dragon.js    # optional 3D decoration; chat works without it
README.md
```

## 1. Install and authenticate Modal

You need Python 3.11 or newer, a Modal account with GPU usage available, and an
ElevenLabs account/API key with speech access. Cloud GPU and voice calls can
incur charges. A GitHub account is only needed if you want to publish with Pages.

Open a terminal in this folder. A virtual environment is recommended:

```bash
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` in Windows PowerShell, or
`source .venv/bin/activate` on macOS/Linux. Then:

```bash
pip install modal
modal setup
```

## 2. Create the ElevenLabs secret

Pick any ElevenLabs voice you like and copy its voice ID.

```bash
modal secret create elevenlabs \
  ELEVENLABS_API_KEY=YOUR_API_KEY \
  ELEVENLABS_VOICE_ID=YOUR_VOICE_ID
```

In PowerShell, use this single-line equivalent (the backslash above is a Bash
line continuation):

```powershell
modal secret create elevenlabs ELEVENLABS_API_KEY=YOUR_API_KEY ELEVENLABS_VOICE_ID=YOUR_VOICE_ID
```

`ELEVENLABS_VOICE_ID` is optional. If omitted, the demo uses ElevenLabs' public
George example voice ID.

**Do not put the ElevenLabs API key in `index.html`.**
GitHub Pages is public, so all ElevenLabs requests go through the Modal backend.

The current backend initializes ElevenLabs at startup, so this secret is needed
even if you only use text chat. Turning off the frontend Voice button does not
remove that backend dependency.

Alternatively, store `ELEVENLABS_API_KEY` and optionally `ELEVENLABS_VOICE_ID`
in a local `.env` file, then upload them without putting values in your command:

```bash
python -m modal secret create elevenlabs --from-dotenv .env
```

The `.env` file is ignored by Git. Only put the ElevenLabs variables in this file
when using this command. Modal does not automatically read your local `.env`
inside the deployed container; it uses the named secret created above.

## 3. Deploy

```bash
modal deploy backend.py
```

Modal will print a public URL similar to:

```text
https://YOUR-WORKSPACE--dragon-trainer-web.modal.run
```

Copy it.

## 4. Connect the frontend

Open `index.html` and set `API_BASE` to your own deployment URL:

```js
const API_BASE = "PASTE_YOUR_MODAL_URL_HERE";
```

with the Modal URL.

This repository currently points to the workshop host's deployment. When you
use this template, replace that existing URL with your own Modal URL.

For local development, serve this folder:

```bash
python -m http.server 8000
```

Open **http://localhost:8000**. This gives modules and microphone permissions a
consistent origin. Microphone access needs localhost or HTTPS; an HTTP address
on your local network is not enough for phone testing. Use Pages for that.

The dragon loads Three.js from a pinned CDN URL and needs internet/WebGL support.
If it cannot load, the welcome screen keeps its emoji and chat remains usable.

## 5. GitHub Pages

Push the repo to GitHub and enable:

**Settings → Pages → Deploy from branch → `main` / root**

The static frontend will be available from your GitHub Pages URL.

Publish `dragon.js` alongside `index.html` if you want the avatar.

## Follow one request

1. `sendMessage()` in `index.html` adds your text to the tab's `conversation`
   array and POSTs it to `/chat` as JSON.
2. `chat()` in `backend.py` keeps up to 10 recent messages, truncates each to
   2,000 characters, and prepends your `SYSTEM_PROMPT`.
3. The tokenizer formats model-specific role separators and converts text to
   token IDs. Qwen generates up to 180 new tokens on Modal's GPU.
4. The backend removes the prompt tokens, decodes the reply, and returns
   `{"response": "..."}`. The frontend displays it as text.
5. With Voice enabled, a separate `/speak` call returns MP3 audio. The frontend
   downloads and decodes the audio before playing it.

There is no database or model training in this demo. Refreshing the page clears
the conversation. Prompt changes steer generation without changing weights.

| Route | Input | Output |
| --- | --- | --- |
| `GET /health` | None | `ok` and model ID |
| `POST /chat` | JSON `messages` array of role/content objects | JSON `response` |
| `POST /transcribe` | Multipart file field `audio` | JSON `text` |
| `POST /speak` | JSON `text` | MP3 audio |

Visit your backend URL plus `/docs` to explore FastAPI's interactive API docs.
Its requests use the live services and may incur charges.

## Workshop experiments

Try each change separately and compare the result with the original:

| Experiment | Where to edit | What to notice |
| --- | --- | --- |
| Turn Ember into a language tutor or cooking coach | `SYSTEM_PROMPT` in `backend.py` | How instructions affect the same question |
| Ask for shorter or more varied answers | `max_new_tokens`, `temperature`, `top_p` in `model.generate()` | Length, variety, and response time; keep temperature above zero while sampling |
| Rebrand the app | Title, welcome text, suggestion buttons and CSS variables in `index.html` | The UI and model personality are independent |
| Change the voice | `ELEVENLABS_VOICE_ID` in the Modal secret | Speech changes without changing the language model |
| Repaint the dragon | `COLORS` in `dragon.js` | Geometry, materials, lights and animation are separate pieces |
| Try a different open model | `MODEL_ID` and `MODEL_DIR` in `backend.py` | Compatibility, download size, GPU memory and chat-template differences |

Redeploy after backend changes. For frontend changes, refresh your local page or
publish the updated static files. After changing a secret, redeploy so new
containers use it. `MODEL_DIR` is the path inside the container, not your laptop.

## Disable or remove the dragon

Set `ENABLE_DRAGON = false` at the top of `dragon.js`. This keeps the emoji and
skips downloading Three.js entirely.

To remove it from your version, delete the `<script src="dragon.js" defer></script>`
tag in `index.html`, then delete `dragon.js`. The optional `.dragon-ready` and
`.big-dragon canvas` CSS rules can also be removed. No backend changes are needed.

The dragon appears on the welcome screen and is removed on the first message.
It releases its GPU resources at that point, pauses animation in hidden tabs,
and stays still when the browser requests reduced motion.

For further experiments, see the official
[Three.js renderer documentation](https://threejs.org/docs/pages/WebGLRenderer.html).

## Watch the backend work in Modal

Open your deployed `dragon-trainer` app in the Modal dashboard and view its
`web` function logs. You can also read logs from your terminal:

```bash
python -m modal app logs dragon-trainer
```

Send a chat or record a voice message while watching the logs. Lines prefixed
with `[Ember]` explain each step:

- `startup.loading_model` / `startup.ready`: model loading, device and startup time.
- `request.received`: route, method and a short request ID.
- `chat.prompt` / `chat.generating` / `chat.complete`: recent message count,
  input/output token counts, a text preview and elapsed seconds.
- `transcription.started` / `transcription.complete`: upload size, elapsed time
  and a preview of what ElevenLabs heard.
- `speech.started` / `speech.complete`: text preview, MP3 byte count and elapsed time.
- `request.failed` / `speech.failed`: exception type when something goes wrong.
  Validation rejections show their HTTP status in `response.headers`.

Match the `request_id` across lines to follow one request. Chat, transcription
and speech are separate HTTP calls and have separate IDs. `response.headers`
means the response started; for audio, wait for `speech.complete` to confirm
that all audio chunks were generated (this does not confirm browser playback).

**Learning mode logs conversation text.** Previews are enabled by default and
limited to 160 characters. Set `LOG_TEXT_PREVIEWS = False` in `backend.py` and
redeploy to hide prompts, replies, transcriptions and speech text in future
custom log lines. Existing logs are not erased. Timing and size logs remain.
The custom logs never include API keys, headers or raw audio; avoid using real
private conversations in the workshop.

## Troubleshooting

- **Cannot reach Ember:** check `API_BASE`, deploy again if needed, and visit
  `/health`. The first request after inactivity can be slower because the GPU
  container must start and load the model. Inspect Modal logs for startup errors.
- **Secret/startup error:** confirm the secret is named `elevenlabs` and contains
  `ELEVENLABS_API_KEY`. Check your ElevenLabs access and usage allowance.
- **Microphone unavailable:** use localhost or HTTPS, allow microphone access,
  and check your browser's recording support.
- **Voice playback fails:** try the Voice toggle or a reply's speaker button;
  mobile browsers may require a user gesture to enable audio. Also check the
  selected voice ID and backend logs.
- **Only an emoji appears:** check that `dragon.js` is served beside the HTML,
  the switch is enabled, and the CDN/WebGL is available. This fallback is expected.
- **Model download or memory error after a swap:** return to the original small
  Qwen model first. Other models may need authentication, more memory, or code changes.

## Voice mode

On mobile:

1. Tap the microphone.
2. Speak.
3. Tap it again.
4. The browser uploads the recording to `/transcribe`.
5. ElevenLabs Scribe v2 returns text.
6. The text is sent to Qwen on the Modal GPU.
7. If **Voice** is enabled, the reply is sent to ElevenLabs TTS and played aloud.

Chrome/Android commonly records WebM/Opus. Safari/iPhone commonly uses MP4 audio.
ElevenLabs Scribe supports both formats.

## Workshop caveat

This demo intentionally has an open public backend and permissive CORS so the
static GitHub Pages frontend works with minimal setup.

That is useful for a 10-minute workshop demo, but it is **not production auth**.
After the workshop, undeploy it or add proper authentication/rate limiting before
sharing it widely.

Stop the deployed app from the Modal dashboard when finished. An idle container
scaling down does not remove the public endpoint; a later request can start it
again. The demo's message/audio limits and single-container setting do not cap
total spending. Keep API keys, virtual environments, and local secret files out
of your published repository.
