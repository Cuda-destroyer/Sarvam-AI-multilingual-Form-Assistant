"""
Sarvam AI-Powered Multilingual Form & Document Assistant.
Main Streamlit application entry point and screen router.
"""

from pathlib import Path
import sys
import uuid
import streamlit as st

# Ensure repository root is on Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.components.ui import apply_custom_styles, render_header, render_stepper
from app.i18n.strings import get_str
from core.config import get_config
from core.generation.docx_writer import DocxDocumentWriter
from core.generation.pdf_acroform_writer import PdfAcroFormWriter
from core.generation.pdf_overlay_writer import PdfOverlayWriter
from core.generation.verifier import RoundTripVerifier
from core.ingestion.file_gate import FileGateError
from core.ingestion.schema_builder import SchemaBuilder
from core.interview.controller import InterviewController
from core.models import FieldState, SessionStateModel
from core.privacy.logger import get_logger
from core.services.sarvam.fakes import FakeSarvamClient
from core.services.sarvam.llm import LLMService
from core.services.sarvam.speech_lang import SpeechLanguageService
from core.services.sarvam.stt import SpeechToTextService

logger = get_logger("streamlit_app")

# Page configuration
st.set_page_config(
    page_title="Sarvam Multilingual Form Assistant",
    page_icon="🇮🇳",
    layout="centered",
    initial_sidebar_state="collapsed",
)


def init_session() -> SessionStateModel:
    """Initialize or restore typed session state."""
    if "app_session" not in st.session_state or st.session_state.app_session is None:
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        st.session_state.app_session = SessionStateModel(session_id=session_id)
        logger.info("Initialized new user session: %s", session_id)
    return st.session_state.app_session


def get_services():
    """Retrieve services, using live Sarvam client if configured or mock client for offline safety."""
    config = get_config()
    if config.is_sarvam_configured():
        stt = SpeechToTextService()
        llm = LLMService()
        speech_lang = SpeechLanguageService()
    else:
        # Transparent fallback to test fakes when running without live key
        fake_client = FakeSarvamClient()
        stt = SpeechToTextService(client=fake_client)
        llm = LLMService(client=fake_client)
        speech_lang = SpeechLanguageService(client=fake_client)
    return stt, llm, speech_lang


def wipe_session():
    """Securely clear all session state and temporary files."""
    session = st.session_state.get("app_session")
    if session:
        # Clean up files if created
        for p in [session.uploaded_file_path, session.generated_file_path]:
            if p and Path(p).exists():
                try:
                    Path(p).unlink()
                except Exception:
                    pass
    st.session_state.app_session = None
    st.session_state.clear()
    st.rerun()


# -------------------------------------------------------------
# SCREEN 1: WELCOME & CONSENT
# -------------------------------------------------------------
def screen_welcome(session: SessionStateModel):
    lang = session.chosen_language
    render_stepper("welcome")

    st.markdown(f"### {get_str('welcome_header', lang)}")
    st.write(get_str("welcome_desc", lang))

    st.markdown(
        f"""
        <div class="sarvam-card-highlight">
            <h4 style="margin-top: 0; color: #1E3A8A;">🔒 {get_str('privacy_header', lang)}</h4>
            <ul style="color: #334155; margin-bottom: 0;">
                <li>{get_str('privacy_bullet_1', lang)}</li>
                <li>{get_str('privacy_bullet_2', lang)}</li>
                <li>{get_str('privacy_bullet_3', lang)}</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    consent = st.checkbox(get_str("consent_checkbox", lang), value=False)

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button(get_str("start_button", lang), type="primary", disabled=not consent):
            session.current_step = "upload"
            st.rerun()


# -------------------------------------------------------------
# SCREEN 2: UPLOAD & FILE GATE
# -------------------------------------------------------------
def screen_upload(session: SessionStateModel):
    lang = session.chosen_language
    render_stepper("upload")

    st.markdown(f"### {get_str('upload_header', lang)}")
    st.write(get_str("upload_desc", lang))

    # Supported samples shortcut
    st.markdown("💡 *Need a sample form to test?*")
    col_s1, col_s2, col_s3 = st.columns(3)
    fixtures_dir = Path("tests/fixtures/forms")
    with col_s1:
        if st.button("📄 Load Sample DOCX"):
            sample = fixtures_dir / "college_admission_form.docx"
            _load_sample_file(session, sample)
    with col_s2:
        if st.button("📑 Load Sample AcroForm PDF"):
            sample = fixtures_dir / "scholarship_application_form.pdf"
            _load_sample_file(session, sample)
    with col_s3:
        if st.button("📝 Load Sample Flat PDF"):
            sample = fixtures_dir / "bank_account_opening.pdf"
            _load_sample_file(session, sample)

    st.write("---")
    uploaded_file = st.file_uploader(
        get_str("upload_browse_label", lang),
        type=["pdf", "docx"],
        accept_multiple_files=False,
    )

    if uploaded_file is not None:
        try:
            with st.spinner("Validating document and extracting form fields..."):
                file_bytes = uploaded_file.read()
                builder = SchemaBuilder()
                schema = builder.build_schema(file_bytes, uploaded_file.name)

                # Save temporary upload
                config = get_config()
                temp_upload_path = config.temp_dir / f"{session.session_id}_{builder.file_gate.sanitize_filename(uploaded_file.name)}"
                with open(temp_upload_path, "wb") as f:
                    f.write(file_bytes)

                session.schema_model = schema
                session.uploaded_file_path = str(temp_upload_path)
                session.current_step = "summary"
                st.success("Document analyzed successfully!")
                st.rerun()

        except FileGateError as e:
            st.error(f"Upload rejected: {str(e)}")
        except Exception as e:
            st.error(f"Error analyzing document: {str(e)}")


def _load_sample_file(session: SessionStateModel, sample_path: Path):
    if sample_path.exists():
        builder = SchemaBuilder()
        with open(sample_path, "rb") as f:
            file_bytes = f.read()
        schema = builder.build_schema(file_bytes, sample_path.name)
        session.schema_model = schema
        session.uploaded_file_path = str(sample_path)
        session.current_step = "summary"
        st.rerun()
    else:
        st.error(f"Sample file not found at {sample_path}")


# -------------------------------------------------------------
# SCREEN 3: FORM SUMMARY
# -------------------------------------------------------------
def screen_summary(session: SessionStateModel):
    lang = session.chosen_language
    render_stepper("summary")

    schema = session.schema_model
    if not schema:
        session.current_step = "upload"
        st.rerun()
        return

    st.markdown(f"### {get_str('form_summary_header', lang)}")
    st.markdown(f"**Document Title:** {schema.title}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(get_str("detected_type", lang), schema.source_type.upper())
    with col2:
        st.metric(get_str("total_fields", lang), len(schema.fields))
    with col3:
        st.metric(get_str("pages", lang), schema.page_count)

    st.write("#### Detected Form Fields:")
    fields_data = [
        {"#": idx + 1, "Field Label": f.label, "Field Type": f.field_type.value.upper(), "Required": "Yes" if f.required else "Optional"}
        for idx, f in enumerate(schema.fields)
    ]
    st.table(fields_data)

    col_back, col_next = st.columns([1, 2])
    with col_back:
        if st.button("<- Change File"):
            session.current_step = "upload"
            st.rerun()
    with col_next:
        if st.button(get_str("confirm_form_button", lang), type="primary"):
            session.current_step = "language"
            st.rerun()


# -------------------------------------------------------------
# SCREEN 4: LANGUAGE SELECTION
# -------------------------------------------------------------
def screen_language(session: SessionStateModel):
    render_stepper("language")
    st.markdown(f"### {get_str('lang_selection_header', session.chosen_language)}")
    st.write(get_str("lang_selection_desc", session.chosen_language))

    languages = [
        ("Hindi (हिन्दी)", "hi-IN"),
        ("Marathi (मराठी)", "mr-IN"),
        ("Tamil (தமிழ்)", "ta-IN"),
        ("English (Indian)", "en-IN"),
        ("Bengali (বাংলা)", "bn-IN"),
        ("Telugu (తెలుగు)", "te-IN"),
        ("Kannada (ಕನ್ನಡ)", "kn-IN"),
        ("Gujarati (ગુજરાતી)", "gu-IN"),
        ("Punjabi (ਪੰਜਾਬੀ)", "pa-IN"),
    ]

    lang_labels = [l[0] for l in languages]
    current_idx = next((i for i, l in enumerate(languages) if l[1] == session.chosen_language), 0)

    selected_label = st.radio("Choose Spoken Language:", lang_labels, index=current_idx)
    selected_code = next(l[1] for l in languages if l[0] == selected_label)
    session.chosen_language = selected_code

    st.info(f"💡 You will speak or type in **{selected_label}**. Your completed document will be filled in official English as required by the form.")

    col_back, col_next = st.columns([1, 2])
    with col_back:
        if st.button("<- Previous"):
            session.current_step = "summary"
            st.rerun()
    with col_next:
        if st.button(get_str("start_interview_button", session.chosen_language), type="primary"):
            session.current_step = "interview"
            st.rerun()


# -------------------------------------------------------------
# SCREEN 5: GUIDED INTERVIEW
# -------------------------------------------------------------
def screen_interview(session: SessionStateModel):
    render_stepper("interview")
    lang = session.chosen_language
    stt_svc, llm_svc, speech_lang_svc = get_services()
    controller = InterviewController(session, llm_service=llm_svc, speech_lang_service=speech_lang_svc)

    current_field = controller.get_current_field()
    current_val = controller.get_current_value()

    if not current_field or controller.is_interview_complete():
        session.current_step = "review"
        st.rerun()
        return

    completed, total = controller.get_progress()
    progress_val = min(1.0, completed / max(1, total))
    st.progress(progress_val)
    st.caption(get_str("question_counter", lang).format(current=completed + 1, total=total))

    # Question explanation
    prompt_text = controller.get_question_prompt(current_field)
    st.markdown(
        f"""
        <div class="sarvam-card">
            <span class="step-badge">{current_field.label}</span>
            <div class="question-prompt">{prompt_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Optional TTS Audio Playback
    if st.button("🔊 Play Question Audio (Bulbul v3)", key="btn_play_tts"):
        with st.spinner("Generating audio..."):
            audio_bytes = speech_lang_svc.text_to_speech(prompt_text, target_language_code=lang)
            if audio_bytes:
                st.audio(audio_bytes, format="audio/wav")
            else:
                st.info("Audio generation not available in offline demo mode.")

    st.write("---")

    # State: AWAITING_CONFIRMATION
    if current_val and current_val.state == FieldState.AWAITING_CONFIRMATION:
        st.markdown(
            f"""
            <div class="sarvam-card-highlight">
                <h4 style="margin-top:0; color:#1E3A8A;">✅ {get_str('confirm_card_header', lang)}</h4>
                <p style="font-size: 1.15rem; font-weight: 600; color: #0F172A;">
                    {current_val.candidate_value}
                </p>
                <small style="color: #64748B;">Input Method: {current_val.provenance.input_method if current_val.provenance else 'text'}</small>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button(get_str("confirm_and_next", lang), type="primary"):
                controller.confirm_current_answer()
                st.rerun()
        with col_c2:
            if st.button(get_str("edit_answer", lang)):
                current_val.state = FieldState.ASKED
                st.rerun()
        return

    # Error / Clarification notification if invalid
    if current_val and current_val.state == FieldState.INVALID and current_val.validation_error:
        st.error(f"⚠️ {current_val.clarification_question or current_val.validation_error}")

    # Spoken or Text input
    st.write(f"**{get_str('voice_input_label', lang)}**")
    audio_val = None
    try:
        # Streamlit 1.40+ st.audio_input
        audio_val = st.audio_input("Speak your response", key=f"audio_input_{current_field.id}")
    except Exception:
        pass

    if audio_val is not None:
        if st.button("Submit Recorded Voice", key=f"btn_sub_voice_{current_field.id}"):
            with st.spinner("Transcribing speech with Sarvam Saaras v3..."):
                raw_audio = audio_val.read()
                stt_res = stt_svc.transcribe_audio(raw_audio, language_code=lang)
                transcript = stt_res.get("transcript", "")
                if transcript:
                    controller.submit_answer(transcript, input_method="speech")
                    st.rerun()
                else:
                    st.warning("Could not clearly transcribe audio. Please try speaking again or use text below.")

    st.write(f"**{get_str('text_input_label', lang)}**")
    text_input_val = st.text_input(
        f"Enter value for {current_field.label}",
        value=current_val.candidate_value or "",
        key=f"text_in_{current_field.id}",
        label_visibility="collapsed",
    )

    col_sub, col_skip, col_prev = st.columns([2, 1, 1])
    with col_sub:
        if st.button(get_str("submit_answer_button", lang), type="primary"):
            if text_input_val.strip():
                controller.submit_answer(text_input_val, input_method="text")
                st.rerun()
            else:
                st.warning("Please enter or record an answer.")

    with col_skip:
        if not current_field.required:
            if st.button(get_str("skip_button", lang)):
                controller.skip_optional_field()
                st.rerun()

    with col_prev:
        if st.button(get_str("prev_button", lang)):
            # Find previous field index
            fields = session.schema_model.fields
            curr_idx = next((i for i, f in enumerate(fields) if f.id == current_field.id), 0)
            if curr_idx > 0:
                controller.go_to_field(fields[curr_idx - 1].id)
                st.rerun()


# -------------------------------------------------------------
# SCREEN 6: REVIEW & IN-PLACE CORRECTION
# -------------------------------------------------------------
def screen_review(session: SessionStateModel):
    lang = session.chosen_language
    render_stepper("review")

    st.markdown(f"### {get_str('review_header', lang)}")
    st.write(get_str("review_desc", lang))

    schema = session.schema_model
    if not schema:
        session.current_step = "upload"
        st.rerun()
        return

    # Review table with edit capability
    for field in schema.fields:
        val = session.field_values.get(field.id)
        confirmed_text = val.confirmed_value if val and val.state == FieldState.CONFIRMED else "(Not provided)"
        input_method = val.provenance.input_method if val and val.provenance else "none"

        col_f1, col_f2, col_f3 = st.columns([3, 4, 1])
        with col_f1:
            st.markdown(f"**{field.label}**")
        with col_f2:
            st.write(confirmed_text)
            st.caption(f"Method: {input_method} | Required: {'Yes' if field.required else 'No'}")
        with col_f3:
            if st.button("✏️ Edit", key=f"edit_btn_{field.id}"):
                controller = InterviewController(session)
                controller.go_to_field(field.id)
                session.current_step = "interview"
                st.rerun()
        st.markdown("<hr style='margin: 0.25rem 0; border: none; border-top: 1px dashed #E2E8F0;'/>", unsafe_allow_html=True)

    st.write("")
    col_back, col_gen = st.columns([1, 2])
    with col_back:
        if st.button("<- Back to Interview"):
            session.current_step = "interview"
            st.rerun()
    with col_gen:
        if st.button(get_str("generate_button", lang), type="primary"):
            session.current_step = "download"
            st.rerun()


# -------------------------------------------------------------
# SCREEN 7: GENERATION & DOWNLOAD
# -------------------------------------------------------------
def screen_download(session: SessionStateModel):
    lang = session.chosen_language
    render_stepper("download")

    st.markdown(f"### {get_str('download_header', lang)}")
    schema = session.schema_model
    config = get_config()

    if not schema or not session.uploaded_file_path:
        st.error("No active form session.")
        return

    # Perform Generation
    if not session.generated_file_path or not Path(session.generated_file_path).exists():
        with st.spinner("Populating form and verifying layout integrity..."):
            template_path = Path(session.uploaded_file_path)
            ext = template_path.suffix.lower()

            out_filename = f"completed_{schema.original_filename}"
            output_path = config.storage_dir / f"{session.session_id}_{out_filename}"

            if schema.source_type == "docx":
                writer = DocxDocumentWriter()
                writer.populate_form(template_path, schema, session.field_values, output_path)
            elif schema.source_type == "pdf_acroform":
                writer = PdfAcroFormWriter()
                writer.populate_form(template_path, schema, session.field_values, output_path)
            else:
                writer = PdfOverlayWriter()
                writer.populate_form(template_path, schema, session.field_values, output_path)

            session.generated_file_path = str(output_path)

    out_path = Path(session.generated_file_path)

    # Perform Round-Trip Verification
    verifier = RoundTripVerifier()
    report = verifier.verify_output(out_path, schema, session.field_values)

    if report.is_verified:
        st.markdown(
            f"""
            <div class="verify-badge">
                ✓ {get_str('verification_badge', lang)} ({report.verified_fields_count}/{report.total_confirmed_fields} fields verified)
            </div>
            <p style="color: #059669; font-size: 0.95rem; margin-top: 0.5rem;">
                {report.summary_message}
            </p>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.warning(f"⚠️ {report.summary_message}")

    # Download button
    with open(out_path, "rb") as f:
        doc_bytes = f.read()

    mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if out_path.suffix == ".docx" else "application/pdf"
    st.download_button(
        label=f"⬇️ {get_str('download_button', lang)} ({out_path.name})",
        data=doc_bytes,
        file_name=out_path.name,
        mime=mime_type,
        type="primary",
    )

    st.write("---")
    st.markdown("🔒 *Done with your session? Wipe your data cleanly:*")
    if st.button(get_str("restart_button", lang)):
        wipe_session()


# -------------------------------------------------------------
# MAIN APPLICATION ROUTER
# -------------------------------------------------------------
def main():
    apply_custom_styles()
    session = init_session()
    render_header(session.chosen_language)

    step = session.current_step

    if step == "welcome":
        screen_welcome(session)
    elif step == "upload":
        screen_upload(session)
    elif step == "summary":
        screen_summary(session)
    elif step == "language":
        screen_language(session)
    elif step == "interview":
        screen_interview(session)
    elif step == "review":
        screen_review(session)
    elif step == "download":
        screen_download(session)
    else:
        session.current_step = "welcome"
        st.rerun()


if __name__ == "__main__":
    main()
