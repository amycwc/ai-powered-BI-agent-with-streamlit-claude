"""
Business Intelligence Agent — Streamlit frontend.

Start with:
    streamlit run frontend/app.py
"""
import streamlit as st

st.set_page_config(
    page_title="e-Commerce BI Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar — branding + LLM settings
# ---------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/bar-chart.png", width=60)
    st.title("e-Commerce BI")
    st.markdown("---")

    with st.expander("⚙️ LLM Settings", expanded=False):
        # Lazy import here to avoid circular issues at module load
        import requests as _req

        _current: dict = {}
        try:
            _r = _req.get("http://localhost:8000/api/config", timeout=5)
            if _r.ok:
                _current = _r.json()
        except Exception:
            pass

        _mode_index = 1 if _current.get("mode") == "gateway" else 0
        mode = st.radio(
            "Connection mode",
            ["Direct Anthropic API", "Custom LLM Gateway"],
            index=_mode_index,
            key="llm_mode_radio",
            horizontal=True,
        )

        model = st.text_input(
            "Model name",
            value=_current.get("model", "claude-3-5-sonnet-20241022"),
            key="llm_model",
        )

        if mode == "Direct Anthropic API":
            api_key = st.text_input(
                "Anthropic API key",
                type="password",
                placeholder="sk-ant-…",
                key="llm_api_key",
            )
            gateway_fields: dict = {}
        else:
            api_key = st.text_input(
                "Gateway API key (LLM_API_KEY)",
                type="password",
                placeholder="Optional — leave blank to keep current",
                key="llm_api_key_gw",
            )
            gateway_fields = {
                "base_url": st.text_input(
                    "Gateway base URL",
                    value=_current.get("base_url", ""),
                    placeholder="https://llm-gw.corp.com",
                    key="llm_base_url",
                ),
                "keycloak_url": st.text_input(
                    "Keycloak token URL",
                    value=_current.get("keycloak_url", ""),
                    placeholder="https://auth.corp.com/realms/X/protocol/openid-connect/token",
                    key="llm_keycloak_url",
                ),
                "client_id": st.text_input(
                    "Client ID",
                    value=_current.get("client_id", ""),
                    key="llm_client_id",
                ),
                "client_secret": st.text_input(
                    "Client secret",
                    type="password",
                    placeholder="Leave blank to keep current",
                    key="llm_client_secret",
                ),
                "llm_username": st.text_input(
                    "LLM username",
                    value=_current.get("llm_username", ""),
                    key="llm_username",
                ),
                "llm_password": st.text_input(
                    "LLM password",
                    type="password",
                    placeholder="Leave blank to keep current",
                    key="llm_password",
                ),
            }

        if st.button("💾 Apply", use_container_width=True, key="llm_save_btn"):
            payload: dict = {
                "mode": "direct" if mode == "Direct Anthropic API" else "gateway",
                "model": model,
                "api_key": api_key,
                **gateway_fields,
            }
            try:
                resp = _req.post(
                    "http://localhost:8000/api/config",
                    json=payload,
                    timeout=10,
                )
                resp.raise_for_status()
                st.success("Settings applied ✓")
            except Exception as exc:
                st.error(f"Failed to apply settings: {exc}")

    st.markdown("---")
    st.caption("Powered by Claude · FastAPI · SQLite")

# Multi-page navigation — st.navigation renders links in the sidebar automatically
pg = st.navigation([
    st.Page("pages/1_ai_chat_page.py",       title="💬 AI Chat"),
    st.Page("pages/2_dashboard_page.py",      title="📊 Dashboard"),
    st.Page("pages/3_analytics_page.py",      title="🔍 Analytics")
])
pg.run()

