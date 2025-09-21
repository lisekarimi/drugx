"""DrugX - Drug Interaction Analysis Frontend."""

import asyncio
import json
import os
import re
import sys

import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from constants import VERSION
from src.clients.ddinter import check_drug_interactions_consolidated
from src.clients.llm import analyze_drug_interactions_safe
from src.clients.openfda import get_adverse_event_context_safe
from src.clients.rxnorm import normalize_and_deduplicate_drugs
from src.utils.logging import logger, set_log_level

# Set debug level to see API details
set_log_level("DEBUG")


def load_css():
    """Load custom CSS styles from external file."""
    css_file = os.path.join(os.path.dirname(__file__), "styles.css")

    try:
        with open(css_file) as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("CSS file not found. Using default styling.")


def initialize_session_state():
    """Initialize session state variables."""
    if "drug_inputs" not in st.session_state:
        st.session_state.drug_inputs = ["", ""]
    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = None
    if "is_analyzing" not in st.session_state:
        st.session_state.is_analyzing = False
    if "error_message" not in st.session_state:  # Add this
        st.session_state.error_message = None


# Page configuration
st.set_page_config(
    page_title="DrugX – AI Drug Interaction Checker",
    page_icon="💊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Load custom styles and initialize state
load_css()
initialize_session_state()


def extract_risk_level(analysis_text: str) -> str:
    """Extract risk level from LLM analysis using precise regex matching."""
    # First try to extract from "Risk Level: X RISK" pattern
    match = re.search(r"Risk Level.*?:\s*(\w+)\s+RISK", analysis_text, re.IGNORECASE)
    if match:
        risk_word = match.group(1).upper()
        if risk_word in ["LOW", "HIGH", "MODERATE"]:
            return risk_word
        elif risk_word == "NO":
            return "SAFE"

    # Fallback to text scanning with more precise patterns
    analysis_upper = analysis_text.upper()

    # Check for specific risk patterns (order matters - most specific first)
    if "HIGH RISK" in analysis_upper or "SEVERE" in analysis_upper:
        return "HIGH"
    elif "MODERATE RISK" in analysis_upper:
        return "MODERATE"
    elif "LOW RISK" in analysis_upper or "MINOR" in analysis_upper:
        return "LOW"
    elif "SAFE" in analysis_upper or "NO INTERACTION" in analysis_upper:
        return "SAFE"
    else:
        return "UNKNOWN"


def get_risk_css_class(risk_level: str) -> str:
    """Get CSS class for risk level."""
    risk_classes = {
        "HIGH": "risk-high",
        "MODERATE": "risk-moderate",
        "LOW": "risk-low",
        "SAFE": "risk-safe",
        "UNKNOWN": "risk-low",
    }
    return risk_classes.get(risk_level, "risk-low")


def get_risk_icon(risk_level: str) -> str:
    """Get appropriate icon for risk level."""
    risk_icons = {
        "HIGH": "🚨",
        "MODERATE": "⚠️",
        "LOW": "ℹ️",
        "SAFE": "✅",
        "UNKNOWN": "❓",
    }
    return risk_icons.get(risk_level, "❓")


def render_header():
    """Render the application header."""
    st.markdown('<h1 class="main-header">💊 DrugX</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">AI-Powered Tool to Prevent Dangerous Drug Mixes</p>',
        unsafe_allow_html=True,
    )

    # About section
    st.markdown(
        """
        DrugX checks drug interactions using trusted medical databases and AI summaries
        to help prevent dangerous side effects and keep patients safe.
        """
    )
    st.caption(
        "⚠️ Medical Disclaimer: For information only - not a substitute for medical advice."
    )

    # How it works (collapsible for mobile)
    with st.expander("🔍 How it works"):
        st.markdown(
            """
            1. Normalize drug names with RxNorm (PubChem fallback)
            2. Check interactions in DDInter (PostgreSQL)
            3. Fetch real-world adverse events from OpenFDA (FAERS)
            4. Summarize findings with AI into clear risk levels and safety notes
            """
        )


def render_drug_inputs():
    """Render drug input section."""
    st.markdown("### 💊 Add at least 2 medications you want to check for interactions:")

    # Create a container for better spacing
    with st.container():
        # Render existing drug inputs
        drugs_to_remove = []

        # Sample placeholders for better UX
        placeholders = [
            "e.g., Aspirin",
            "e.g., Warfarin",
            "e.g., Lisinopril",
            "e.g., Metformin",
            "e.g., Atorvastatin",
        ]

        for i, drug_value in enumerate(st.session_state.drug_inputs):
            # Use columns for better alignment
            input_col, remove_col = st.columns([6, 1])

            with input_col:
                placeholder_text = (
                    placeholders[i]
                    if i < len(placeholders)
                    else "e.g., Medication name"
                )
                new_value = st.text_input(
                    f"Medication {i + 1}",
                    value=drug_value,
                    placeholder=placeholder_text,
                    key=f"drug_input_{i}",
                    help="Enter one medication per field",
                    label_visibility="collapsed",
                    disabled=st.session_state.is_analyzing,
                )
                st.session_state.drug_inputs[i] = new_value

            with remove_col:
                # Only show remove button if more than 2 inputs
                if len(st.session_state.drug_inputs) > 2:
                    # Add some spacing to align with input
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button(
                        "🗑️",
                        key=f"remove_{i}",
                        help="Remove this medication",
                        disabled=st.session_state.is_analyzing,
                    ):
                        drugs_to_remove.append(i)

        # Remove drugs that were marked for removal
        for i in reversed(drugs_to_remove):
            st.session_state.drug_inputs.pop(i)
            st.rerun()

        # Action buttons
        st.markdown("<br>", unsafe_allow_html=True)
        button_col1, button_col2 = st.columns(2)

        with button_col1:
            # Disable add button if already at max limit or analyzing
            if len(st.session_state.drug_inputs) >= 5:
                st.button(
                    "➕ Add Medication",
                    use_container_width=True,
                    disabled=True,
                    help="Maximum 5 medications allowed",
                )
            else:
                if st.button(
                    "➕ Add Medication",
                    use_container_width=True,
                    disabled=st.session_state.is_analyzing,
                ):
                    st.session_state.drug_inputs.append("")
                    st.rerun()

        with button_col2:
            if st.button(
                "🧹 Clear All",
                use_container_width=True,
                disabled=st.session_state.is_analyzing,
            ):
                st.session_state.drug_inputs = ["", ""]
                st.session_state.analysis_results = None
                st.rerun()

        # Analysis button - centered below the other buttons
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_col1, analyze_col2, analyze_col3 = st.columns([1, 2, 1])
        with analyze_col2:
            analyze_button = st.button(
                "🔬 Analyze Drug Interactions",
                type="primary",
                use_container_width=True,
                disabled=st.session_state.is_analyzing,
            )

    # Get non-empty drugs
    drugs = [drug.strip() for drug in st.session_state.drug_inputs if drug.strip()]
    return drugs, analyze_button


async def analyze_medications(medications: list[str]):
    """Run the complete drug analysis pipeline."""
    # Create containers for progress and messages
    progress_container = st.empty()
    message_container = st.empty()

    try:
        # Step 1: Normalize drugs
        with progress_container.container():
            st.progress(20)
        message_container.info("🔍 Normalizing medication names (RxNorm)...")

        logger.info(f"Starting drug normalization for medications: {medications}")
        rxnorm_result = await normalize_and_deduplicate_drugs(medications)
        normalized_drugs = rxnorm_result["normalized_drugs"]

        logger.info("=== RxNorm Result JSON ===")
        logger.info(f"Final RXNORM JSON result:\n{json.dumps(rxnorm_result, indent=2)}")
        logger.info("=" * 50)

        if len(normalized_drugs) < 2:
            error_msg = f"We could only find {len(normalized_drugs)} valid medication in our database. Please check your spelling or try different medication names."
            logger.error(error_msg)
            progress_container.empty()
            message_container.empty()
            st.session_state.error_message = f"⚠️ {error_msg}"
            return None

        # Step 2: Check interactions
        with progress_container.container():
            st.progress(40)
        message_container.info("🔬 Checking for drug interactions (DDinter)...")

        ingredient_names = [drug["in"] for drug in normalized_drugs]
        logger.info(f"Checking interactions for ingredients: {ingredient_names}")
        interactions_result = await check_drug_interactions_consolidated(
            ingredient_names
        )

        logger.info("=== Drug Interactions Result JSON ===")
        logger.info(
            f"DDInter JSON result:\n{json.dumps(interactions_result, indent=2)}"
        )
        logger.info("=" * 50)

        # Step 3: Get adverse events
        with progress_container.container():
            st.progress(60)
        message_container.info("📊 Analyzing adverse event data (OpenFDA)...")

        logger.info("Fetching adverse events data from OpenFDA")
        adverse_events_result = await get_adverse_event_context_safe(ingredient_names)

        logger.info("=== Adverse Events Result JSON ===")
        logger.info(
            f"OpenFDA JSON result:\n{json.dumps(adverse_events_result, indent=2)}"
        )
        logger.info("=" * 50)

        # Step 4: LLM Analysis
        with progress_container.container():
            st.progress(80)
        message_container.info("🧠 Generating comprehensive analysis with LLM...")

        logger.info("Starting LLM analysis of combined data")
        llm_result = await analyze_drug_interactions_safe(
            rxnorm_result, interactions_result, adverse_events_result
        )

        logger.info("=== LLM Analysis Result JSON ===")
        logger.info(f"LLM Analysis result:\n{json.dumps(llm_result, indent=2)}")
        logger.info("=" * 50)

        # Complete
        with progress_container.container():
            st.progress(100)
        message_container.success("✅ Analysis complete!")
        logger.info("Drug interaction analysis completed successfully")

        # Clear indicators after short delay
        await asyncio.sleep(2)
        progress_container.empty()
        message_container.empty()

        return {
            "rxnorm": rxnorm_result,
            "interactions": interactions_result,
            "adverse_events": adverse_events_result,
            "llm_analysis": llm_result,
        }

    except Exception as e:
        error_msg = f"Analysis failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        message_container.empty()
        st.session_state.error_message = f"❌ {error_msg}"
        return None


def render_analysis_results(result):
    """Render analysis results."""
    if not result:
        return

    analysis_text = result["llm_analysis"]["analysis"]
    risk_level = extract_risk_level(analysis_text)
    risk_class = get_risk_css_class(risk_level)
    risk_icon = get_risk_icon(risk_level)

    # Split analysis into sections
    if (
        "## 🚨 BOTTOM LINE" in analysis_text
        and "## 📋 DETAILED ANALYSIS" in analysis_text
    ):
        parts = analysis_text.split("## 📋 DETAILED ANALYSIS")
        summary_text = parts[0].replace("## 🚨 BOTTOM LINE", "").strip()
        detailed_text = parts[1] if len(parts) > 1 else ""
    else:
        summary_text = analysis_text
        detailed_text = ""

    # Main summary card
    with st.container():
        st.markdown(
            f"""
        <div class="{risk_class}">
            <h3>{risk_icon} Interaction Summary - {risk_level.title()} Risk</h3>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown(summary_text)

    # Detailed analysis and raw data sections
    if detailed_text:
        with st.expander("📋 Detailed Technical Analysis", expanded=False):
            st.markdown(detailed_text)

    with st.expander("🔬 View Raw Data Sources", expanded=False):
        tab1, tab2, tab3 = st.tabs(["RxNorm", "Interactions", "Adverse Events"])

        with tab1:
            st.json(result["rxnorm"])

        with tab2:
            st.json(result["interactions"])

        with tab3:
            st.json(result["adverse_events"])


def render_footer():
    """Render application footer."""
    st.markdown("---")

    st.markdown(
        f"""
    <div class="footer-content">
        <p class="footer-disclaimer">
            ⚠️ Always consult your healthcare provider for medical decisions.
        </p>
        <p class="footer-links">
            <a href="https://github.com/lisekarimi/drugx" target="_blank">🔗 GitHub</a> |
            <a href="https://github.com/lisekarimi/drugx/wiki" target="_blank">📄 Documentation</a> |
            <a href="https://github.com/lisekarimi/drugx/blob/main/CHANGELOG.md" target="_blank">📰 Changelog</a> |
            <a href="https://www.linkedin.com/in/lisekarimi/" target="_blank">💼 LinkedIn</a>
        </p>
        <p class="footer-version">
            v{VERSION}
         </p>
    </div>
    """,
        unsafe_allow_html=True,
    )


def main():
    """Streamlit application."""
    # Header section
    render_header()

    # Add error display
    if st.session_state.error_message:
        st.error(st.session_state.error_message)

    medications, analyze_button = render_drug_inputs()

    if analyze_button:
        st.session_state.error_message = None  # Clear on new analysis

        if len(medications) < 2:
            st.warning(
                "⚠️ Please enter at least 2 medications for interaction analysis."
            )
        else:
            # Clear previous results and set analyzing state
            st.session_state.analysis_results = None
            st.session_state.is_analyzing = True
            st.rerun()  # Force UI update to disable buttons

    # Run analysis if analyzing state is set
    if st.session_state.is_analyzing:
        with st.spinner("Analyzing medications..."):
            medications = [
                drug.strip() for drug in st.session_state.drug_inputs if drug.strip()
            ]
            result = asyncio.run(analyze_medications(medications))
            st.session_state.analysis_results = result
            st.session_state.is_analyzing = False
            st.rerun()

    # Display results if available
    if st.session_state.analysis_results:
        st.markdown("---")
        render_analysis_results(st.session_state.analysis_results)

    # Footer
    render_footer()


if __name__ == "__main__":
    main()
