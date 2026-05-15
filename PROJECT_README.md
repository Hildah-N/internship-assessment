# GenAI — Sunbird AI Pipeline

A web application that takes text or audio as input and runs it through a full AI pipeline powered entirely by [Sunbird AI](https://sunbird.ai): transcription, summarisation, translation into a Ugandan local language, and text-to-speech playback.

---

## Project description

GenAI lets a user paste text or upload an audio file (MP3, WAV, OGG, M4A, AAC — up to 5 minutes), then automatically:

1. Transcribes the audio to text (audio mode only) using Sunbird's Speech-to-Text API.
2. Summarises the text using the Sunflower LLM.
3. Translates the summary into a chosen Ugandan local language (Luganda, Runyankole, Ateso, Lugbara, or Acholi) using the Sunflower LLM.
4. Synthesises an audio clip of the translated summary using Sunbird's Text-to-Speech API.

Every intermediate result — transcript, summary, translated summary, and the generated audio player — is shown in the UI.

---

## Architecture overview

```
User input (text or audio)
        │
        ▼
┌───────────────────┐
│  app.py (Gradio)  │  ← UI, input validation, error display
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│   pipeline.py     │  ← orchestrates the 4-step pipeline
└────────┬──────────┘
         │
         ▼
┌────────────────────────┐
│   sunbird_client.py    │  ← thin HTTP wrapper around Sunbird AI APIs
└────────────────────────┘
         │
         ├── Step 1 (audio only): POST /tasks/stt          → transcript
         ├── Step 2:              POST /tasks/summarise     → English summary
         ├── Step 3:              POST /tasks/sunflower_inference → translated summary
         └── Step 4:              POST /tasks/tts           → audio bytes
```

All AI capabilities come from **Sunbird AI** — no OpenAI, Anthropic, or other providers are used.

---

## Local setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd <repo-folder>
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your Sunbird AI API token:

```
SUNBIRD_API_TOKEN=your_token_here
```

Get a token by signing up at the [Sunbird AI API portal](https://sunbird.ai).

### 5. Run the app

```bash
python app.py
```

Then open [http://127.0.0.1:7860](http://127.0.0.1:7860) in your browser.

---

## Environment variables

| Variable            | Required | Description                                                                   |
| ------------------- | -------- | ----------------------------------------------------------------------------- |
| `SUNBIRD_API_TOKEN` | ✅ Yes   | Bearer token for all Sunbird AI API calls. Obtain from the Sunbird AI portal. |

Never commit your `.env` file. It is already listed in `.gitignore`.

---

## Usage walkthrough

## Start Screen

![Start Screen](screenshots/start.png)

## Text Input

![Text Input](screenshots/text.png)

## Audio Input

![Audio Input](screenshots/audio.png)

### Text input mode

1. Select **Text Input** (default).
2. Paste or type your text in the text box.
3. Choose a target language from the dropdown (e.g. _Luganda_).
4. Click **Generate**.
5. The results panel fills in left-to-right: source text → English summary → translated summary → audio player.

### Audio upload mode

1. Select **Audio Upload**.
2. Click the upload area and choose an audio file (MP3, WAV, OGG, M4A, or AAC). Files longer than 5 minutes are rejected before any API call is made.
3. Choose a target language.
4. Click **Generate**.
5. The results panel shows the transcript (from STT), English summary, translated summary, and a playable audio clip.

### Error handling

- If no input is provided, a prompt appears before any API call is made.
- If the audio exceeds 5 minutes, the file is rejected immediately with the exact duration shown.
- API errors (timeouts, HTTP errors, auth failures) surface in a red error box at the bottom of the results panel. The box is hidden when there is no error.

---

## Deployed link

🔗 **[Live on Hugging Face Spaces]**
https://huggingface.co/spaces/Hildah-N/GenAI

---

## Known limitations

- **5-minute audio cap** — files longer than 5 minutes are rejected. This is a deliberate constraint to keep API response times reasonable.
- **Supported languages** — Luganda, Runyankole, Ateso, Lugbara, Acholi. English is supported as a source language for STT but not as a TTS output target.
- **Sunbird API latency** — the Sunbird STT and TTS endpoints can be slow when the server is under load. The app waits up to 5 minutes before showing a timeout error. If you hit a timeout, wait 30 seconds and try again.
- **No streaming** — all four pipeline steps complete before any result is shown. Progress is not streamed step-by-step.
- **Text input transcript** — when text input mode is used, "Step 1 — Transcript" simply echoes the text you typed; no STT is performed.
