"""
Custom UI Components, Styling, and Accessibility helpers for Streamlit.
Provides responsive layout, modern typography, glassmorphic cards, and visual progress.
"""

import streamlit as st


def apply_custom_styles():
    """Apply modern CSS design system tokens and styling."""
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Main container max width & padding */
    .block-container {
        max-width: 900px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    /* Premium card container */
    .sarvam-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    }

    .sarvam-card-highlight {
        background: linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 100%);
        border: 1.5px solid #BFDBFE;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }

    /* Step indicator badge */
    .step-badge {
        display: inline-block;
        background-color: #2563EB;
        color: #FFFFFF;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }

    /* Verification Badge */
    .verify-badge {
        display: inline-flex;
        align-items: center;
        background-color: #ECFDF5;
        color: #065F46;
        border: 1px solid #A7F3D0;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.95rem;
    }

    /* Large question prompt */
    .question-prompt {
        font-size: 1.35rem;
        font-weight: 600;
        color: #1E293B;
        line-height: 1.5;
        margin-bottom: 1rem;
    }

    /* Button enhancements */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15);
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_header(lang: str = "en-IN"):
    """Render top application brand banner."""
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 2rem;">
            <div style="display: inline-flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;">
                <span style="font-size: 2rem;">🇮🇳</span>
                <span style="font-size: 1.75rem; font-weight: 700; color: #1E293B; letter-spacing: -0.02em;">
                    Sarvam Form Assistant
                </span>
            </div>
            <p style="color: #64748B; font-size: 1.05rem; margin: 0;">
                AI-Powered Multilingual Form & Document Filling
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stepper(current_step: str):
    """Render a visual breadcrumb progress bar showing current stage."""
    steps = [
        ("welcome", "1. Welcome"),
        ("upload", "2. Upload"),
        ("summary", "3. Analysis"),
        ("language", "4. Language"),
        ("interview", "5. Questions"),
        ("review", "6. Review"),
        ("download", "7. Download"),
    ]

    cols = st.columns(len(steps))
    step_keys = [s[0] for s in steps]
    current_idx = step_keys.index(current_step) if current_step in step_keys else 0

    for i, (key, label) in enumerate(steps):
        with cols[i]:
            if i < current_idx:
                st.markdown(f"<div style='text-align: center; color: #10B981; font-weight: 600; font-size: 0.8rem;'>✓ {label}</div>", unsafe_allow_html=True)
            elif i == current_idx:
                st.markdown(f"<div style='text-align: center; color: #2563EB; font-weight: 700; font-size: 0.8rem; border-bottom: 2px solid #2563EB; padding-bottom: 4px;'>▶ {label}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='text-align: center; color: #94A3B8; font-size: 0.8rem;'>{label}</div>", unsafe_allow_html=True)
    st.markdown("<hr style='margin-top: 0.5rem; margin-bottom: 1.5rem; border: none; border-top: 1px solid #E2E8F0;'/>", unsafe_allow_html=True)
