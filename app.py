"""
Sunbird AI Pipeline — Gradio frontend
Entry point: app.py
"""
import os
import tempfile
import traceback

import gradio as gr
from dotenv import load_dotenv

load_dotenv()

from backend.pipeline import run_pipeline
from backend.sunbird_client import TTS_SPEAKER_IDS

LANGUAGES = list(TTS_SPEAKER_IDS.keys())  # ["Acholi", "Ateso", "Runyankole", "Lugbara", "Luganda"]

# ── CSS theming ──────────────────────────────────────────────────────────────
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=Sora:wght@600;700&display=swap');
* { box-sizing: border-box; }
body, .gradio-container {
    font-family: 'DM Sans', sans-serif !important;
    background: #f5f0eb !important;
}
#header-box {
    background: linear-gradient(135deg, #DC7828 0%, #b85e1a 100%);
    border-radius: 14px;
    padding: 28px 32px;
    margin-bottom: 20px;
    color: white;
    box-shadow: 0 4px 24px rgba(220, 120, 40, 0.25);
}
#header-box h1 {
    margin: 0 0 6px 0;
    font-family: 'Sora', sans-serif;
    font-size: 1.9rem;
    letter-spacing: -0.02em;
    text-align: center;
}
#header-box p {
    margin: 0;
    opacity: 0.88;
    font-size: 0.95rem;
    font-weight: 400;
}
.section-heading {
    font-family: 'Sora', sans-serif;
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #8a6a50;
    margin-bottom: 10px;
    padding-bottom: 6px;
    border-bottom: 1.5px solid #e0d4c8;
}
label.svelte-1b6s6s, .gradio-container label {
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    color: #5c4030 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
textarea, input[type="text"] {
    background: #fffaf6 !important;
    border: 1.5px solid #e0d0c0 !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.93rem !important;
    color: #2d1a0a !important;
    transition: border-color 0.15s ease;
}
textarea:focus, input[type="text"]:focus {
    border-color: #DC7828 !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(220, 120, 40, 0.12) !important;
}
#run-btn {
    background: #DC7828 !important;
    color: white !important;
    font-family: 'Sora', sans-serif !important;
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.04em !important;
    border-radius: 8px !important;
    border: none !important;
    padding: 12px 24px !important;
    transition: background 0.15s ease, transform 0.1s ease, box-shadow 0.15s ease !important;
    box-shadow: 0 2px 12px rgba(220, 120, 40, 0.3) !important;
}
#run-btn:hover {
    background: #b85e1a !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 18px rgba(220, 120, 40, 0.4) !important;
}
#run-btn:active {
    transform: translateY(0) !important;
}
.gr-panel, .gr-box, .gr-form, [class*="block"] {
    background: #fffaf6 !important;
    border: 1.5px solid #e8ddd4 !important;
    border-radius: 12px !important;
}
select, .gr-dropdown {
    background: #fffaf6 !important;
    border: 1.5px solid #e0d0c0 !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    color: #2d1a0a !important;
}
#error-box {
    color: #c0392b;
    background: #fff5f5;
    border: 1.5px solid #c0392b;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.9rem;
    font-family: 'DM Sans', sans-serif;
    margin-top: 8px;
}
.step-badge {
    display: inline-block;
    background: #DC7828;
    color: white;
    font-family: 'Sora', sans-serif;
    font-size: 0.65rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 20px;
    letter-spacing: 0.08em;
    margin-right: 6px;
    vertical-align: middle;
}
.gr-examples {
    background: transparent !important;
    border: none !important;
}
.divider {
    border: none;
    border-top: 1.5px solid #e0d4c8;
    margin: 16px 0;
}
"""


# ── Friendly error messages ─────────────────────────────────────────────────

def _friendly_error(e: Exception) -> str:
    """Convert raw technical exceptions into user-friendly messages."""
    import requests as req

    msg = str(e)

    if isinstance(e, (req.exceptions.ConnectionError, ConnectionError, OSError)):
        if "NameResolutionError" in msg or "getaddrinfo" in msg or "Failed to resolve" in msg:
            return "Could not reach the server — please check your internet connection and try again."
        return "A network error occurred. Please check your connection and try again."

    if isinstance(e, req.exceptions.Timeout):
        return "The request timed out. The server may be busy — please try again in a moment."

    if isinstance(e, req.exceptions.HTTPError):
        if "401" in msg or "403" in msg:
            return "Authentication failed. Please check that your API token is correct."
        if "429" in msg:
            return "Too many requests — please wait a moment and try again."
        if "5" in msg[:3]:
            return "The Sunbird server returned an error. Please try again later."
        return "The server returned an unexpected error. Please try again."

    if isinstance(e, (ValueError, RuntimeError)):
        return msg

    return "Something went wrong. Please try again or contact support if the issue persists."


# ── Pipeline runner (called by Gradio) ──────────────────────────────────────

def process(input_mode, text_input, audio_input, target_language):
    """
    Called when the user clicks Generate.
    Validation raises gr.Error immediately (shows as toast, no generator quirk).
    Pipeline errors are also raised as gr.Error from within the generator.
    """
    print("TOKEN SET:", bool(os.environ.get("SUNBIRD_API_TOKEN")))
    print(f"\n=== PROCESS CALLED ===")
    print(f"Input mode: {input_mode}")
    print(f"Text input: {text_input[:50] if text_input else 'None'}")
    print(f"Audio input: {audio_input}")
    print(f"Target language: {target_language}")

    use_audio = (input_mode == "Audio Upload")

    # ── Validation: raise gr.Error immediately, before any yield ──────────
    if use_audio and not audio_input:
        raise gr.Error("Please upload an audio file before running the pipeline.")

    if not use_audio and not (text_input and text_input.strip()):
        raise gr.Error("Please enter some text before running the pipeline.")

    # ── Clear previous results ─────────────────────────────────────────────
    yield ("", "", "", None, gr.update(value="", visible=False))

    try:
        audio_path = audio_input if use_audio else None
        user_text = None if use_audio else text_input

        print("Calling run_pipeline...")
        transcript, summary, translation, audio_bytes = run_pipeline(
            input_text=user_text,
            audio_path=audio_path,
            target_language=target_language,
        )
        print("Pipeline completed successfully")

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp.write(audio_bytes)
        tmp.flush()
        tmp.close()
        print(f"Audio saved to: {tmp.name}")

        yield (
            transcript,
            summary,
            translation,
            tmp.name,
            gr.update(value="", visible=False),
        )

    except gr.Error:
        raise  # let Gradio handle its own errors

    except Exception as e:
        print(f"\n=== EXCEPTION CAUGHT ===")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {str(e)}")
        traceback.print_exc()

        raise gr.Error(_friendly_error(e))


# ── Build Gradio UI ──────────────────────────────────────────────────────────

def build_ui():
    with gr.Blocks(title="GenAI", css=CUSTOM_CSS) as demo:

        # Header
        gr.HTML("""
        <div id="header-box">
          <h1>GenAI</h1>
        </div>
        """)

        with gr.Row():
            # ── Left column: inputs ──────────────────────────────────────────
            with gr.Column(scale=1):
                gr.HTML('<p class="section-heading">Input</p>')

                input_mode = gr.Radio(
                    choices=["Text Input", "Audio Upload"],
                    value="Text Input",
                    label="Input type",
                    interactive=True,
                )

                text_input = gr.Textbox(
                    label="Text (ENG OR LUG)",
                    placeholder="Type or paste your text here…",
                    lines=6,
                    visible=True,
                )

                audio_input = gr.Audio(
                    label="Audio file  (MP3, WAV, OGG, M4A, AAC — max 5 min)",
                    type="filepath",
                    sources=["upload"],
                    visible=False,
                )

                target_language = gr.Dropdown(
                    choices=LANGUAGES,
                    value="Luganda",
                    label="Target language for translation and speech",
                )

                run_btn = gr.Button("Generate", elem_id="run-btn", variant="primary")

            # ── Right column: outputs ────────────────────────────────────────
            with gr.Column(scale=1):
                gr.HTML('<p class="section-heading">Results</p>')

                transcript_out = gr.Textbox(
                    label="Transcript / Source text",
                    lines=4,
                    interactive=False,
                )
                summary_out = gr.Textbox(
                    label="English summary",
                    lines=4,
                    interactive=False,
                )
                translation_out = gr.Textbox(
                    label="Translated summary",
                    lines=4,
                    interactive=False,
                )
                audio_out = gr.Audio(
                    label="Synthesised speech",
                    type="filepath",
                    interactive=False,
                )


        # ── Toggle text / audio visibility ────────────────────────────────
        def toggle_inputs(mode):
            return (
                gr.update(visible=(mode == "Text Input"), value=""),
                gr.update(visible=(mode == "Audio Upload"), value=None),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=None),
                
            )

        input_mode.change(
            fn=toggle_inputs,
            inputs=[input_mode],
            outputs=[text_input, audio_input, transcript_out, summary_out, translation_out, audio_out],
            show_progress="hidden",
        )

        # ── Wire the Run button ────────────────────────────────────────────
        run_btn.click(
            fn=process,
            inputs=[input_mode, text_input, audio_input, target_language],
            outputs=[transcript_out, summary_out, translation_out, audio_out],
            show_progress="full",
        )

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.queue()
    demo.launch(server_name="0.0.0.0", server_port=7860, ssr_mode=False)