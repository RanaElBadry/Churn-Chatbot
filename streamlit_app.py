import streamlit as st
import requests

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="ChurnGuard AI",
    page_icon="logo.png",
    layout="centered"
)

# ---------- CUSTOM CSS ----------
st.markdown("""
<style>
body {
    background-color: #F7F9FC;
}
.main {
    background-color: #F7F9FC;
}
.header-container {
    display: flex;
    align-items: center;
    gap: 15px;
    margin-bottom: 5px;
}
.big-title {
    font-size: 42px;
    font-weight: 700;
    margin: 0;
}
.subtitle {
    font-size: 18px;
    color: #555;
    margin-bottom: 30px;
}
.result-card {
    background-color: white;
    padding: 25px;
    border-radius: 15px;
    margin-top: 30px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}
.risk-low {
    color: #1DB954;
    font-weight: bold;
    font-size: 22px;
}
.risk-high {
    color: #E63946;
    font-weight: bold;
    font-size: 22px;
}
textarea {
    border-radius: 12px !important;
}
</style>
""", unsafe_allow_html=True)

# ---------- HEADER WITH LOGO BESIDE TITLE ----------
col1, col2 = st.columns([1, 6])

with col1:
    st.image("logo.png", width=80)

with col2:
    st.markdown(
        '<div class="big-title">ChurnGuard AI</div>',
        unsafe_allow_html=True
    )

st.markdown(
    '<div class="subtitle">Ask about a customer</div>',
    unsafe_allow_html=True
)

# ---------- SESSION STATE ----------
if "input_text" not in st.session_state:
    st.session_state.input_text = ""

# ---------- DYNAMIC HEIGHT ----------
lines = st.session_state.input_text.count("\n") + 1
height = min(50 + (lines * 24), 300)

# ---------- FORM ----------
with st.form("churn_form", clear_on_submit=True):

    user_input = st.text_area(
        "",
        placeholder="Describe a customer profile...",
        key="input_text",
        height=height
    )

    submitted = st.form_submit_button("Analyze")

# ---------- ANALYSIS ----------
if submitted:

    if user_input.strip() == "":
        st.warning("Please enter a customer description.")
    else:
        with st.spinner("Analyzing customer profile..."):

            try:
                response = requests.post(
                    "http://127.0.0.1:8000/chat",
                    json={"message": user_input}
                )

                if response.status_code != 200:
                    st.error("API error. Make sure FastAPI server is running.")
                else:
                    result = response.json()

                    risk = result["risk_level"]
                    prob = result["churn_probability"]
                    explanation = result["explanation"]
                    structured = result["structured_data"]

                    st.markdown('<div class="result-card">', unsafe_allow_html=True)

                    st.subheader("Prediction Result")

                    if risk == "LOW":
                        st.markdown(
                            f'<div class="risk-low">Risk Level: {risk}</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            f'<div class="risk-high">Risk Level: {risk}</div>',
                            unsafe_allow_html=True
                        )

                    st.write(f"Churn Probability: **{prob*100:.2f}%**")

                    st.markdown("---")
                    st.subheader("Explanation")
                    st.write(explanation)

                    st.markdown("---")
                    with st.expander("Structured Data"):
                        st.json(structured)

                    st.markdown('</div>', unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Connection error: {e}")