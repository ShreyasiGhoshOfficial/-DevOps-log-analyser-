import os
os.environ["HTTPX_SSL_VERIFY"] = "0"
os.environ["GROQ_BASE_URL"] = "https://api.groq.com"

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import streamlit as st
from pydantic import BaseModel, Field
from typing import List
from langchain_groq import ChatGroq
import datetime

st.set_page_config(
    page_title="DevOps Log Analyser",
    page_icon="🔍",
    layout="wide"
)

# ── Pydantic schema ────────────────────────────────────────────
class LogAnalysis(BaseModel):
    severity: str = Field(description="One of: critical, high, medium, low")
    log_type: str = Field(description="One of: Jenkins, Kubernetes, Docker, GitHub Actions, other")
    affected_component: str = Field(description="Pod name, stage name, or service affected")
    root_cause: str = Field(description="Root cause in one clear actionable sentence")
    immediate_action: str = Field(description="Exact shell command or step to fix right now")
    prevention: str = Field(description="One concrete step to prevent recurrence")
    related_errors: List[str] = Field(description="Up to 3 other error patterns in the log")

# ── LLM setup (cached) ────────────────────────────────────────
@st.cache_resource
def get_llm():
    return ChatGroq(
        model="llama-3.1-70b-versatile",
        api_key=st.secrets["GROQ_API_KEY"],
        temperature=0
    ).with_structured_output(LogAnalysis)

# ── Severity colour config ────────────────────────────────────
SEV = {
    "critical": {"bg": "#FAECE7", "border": "#F0997B", "text": "#712B13"},
    "high":     {"bg": "#FAEEDA", "border": "#EF9F27", "text": "#633806"},
    "medium":   {"bg": "#E6F1FB", "border": "#85B7EB", "text": "#0C447C"},
    "low":      {"bg": "#E1F5EE", "border": "#5DCAA5", "text": "#085041"},
}

# ── Sample logs ───────────────────────────────────────────────
SAMPLES = {
    "Kubernetes — ImagePullBackOff": 'Back-off pulling image "registry.example.com/frontend:v2.1"\nFailed to pull image: unexpected status code 401 Unauthorized\nWarning  BackOff  2m  kubelet  Back-off restarting failed container',
    "Jenkins — Stage failure": '[Pipeline] stage (Deploy)\nERROR: script returned exit code 1\nhudson.AbortException: kubectl apply returned exit code 1\nerror: error validating manifest: unknown field "specc"\nFinished: FAILURE',
    "Kubernetes — CrashLoopBackOff": "Warning BackOff 5m (x12 over 10m) kubelet Back-off restarting failed container\nState: Waiting  Reason: CrashLoopBackOff\nLast State: Terminated  Reason: OOMKilled  Exit Code: 137",
    "Paste your own log": ""
}

# ── UI ────────────────────────────────────────────────────────
st.title("DevOps Log Analyser")
st.caption("Paste Jenkins, Kubernetes, or Docker logs — instant root cause analysis via LangChain + Groq (LLaMA 3.1 70B)")

left, right = st.columns([1, 1], gap="large")

with left:
    st.subheader("Input")
    choice = st.selectbox("Load sample or paste your own", list(SAMPLES.keys()))
    log_input = st.text_area("Log output", value=SAMPLES[choice], height=280, placeholder="Paste log here...")
    go = st.button("Analyse log", type="primary", use_container_width=True, disabled=not log_input.strip())

with right:
    st.subheader("Analysis")
    if go and log_input.strip():
        with st.spinner("Analysing with LLaMA 3.1 70B..."):
            try:
                result = get_llm().invoke(f"Analyse this DevOps log:\n\n{log_input}")
                cfg = SEV.get(result.severity.lower(), SEV["medium"])

                st.markdown(
                    f'<div style="background:{cfg["bg"]};border:0.5px solid {cfg["border"]};'
                    f'border-radius:8px;padding:10px 16px;margin-bottom:12px;">'
                    f'<span style="font-size:11px;font-weight:500;color:{cfg["text"]};'
                    f'text-transform:uppercase;letter-spacing:.06em;">{result.severity.upper()}</span>'
                    f'<span style="font-size:13px;color:{cfg["text"]};margin-left:12px;">'
                    f'{result.log_type} · {result.affected_component}</span></div>',
                    unsafe_allow_html=True
                )

                st.markdown("**Root cause**")
                st.error(result.root_cause)
                st.markdown("**Immediate fix**")
                st.code(result.immediate_action, language="bash")
                st.markdown("**Prevention**")
                st.info(result.prevention)

                if result.related_errors:
                    with st.expander(f"Related errors ({len(result.related_errors)})"):
                        for e in result.related_errors:
                            st.warning(e)

                st.caption(f"Analysed at {datetime.datetime.now().strftime('%H:%M:%S')}")

            except Exception as e:
                st.error(f"Analysis failed: {e}")
    elif not log_input.strip():
        st.info("Paste a log on the left and click Analyse.")
    else:
        st.info("Click Analyse to get the breakdown.")

st.divider()
st.caption("Built with LangChain · Groq · Streamlit · Pydantic structured output · LLaMA 3.1 70B")