"""Central Supabase client initialization for the app.

Uses st.secrets for credentials so it works both locally (.streamlit/secrets.toml)
and on Streamlit Community Cloud (via the Secrets UI).
"""

import streamlit as st
from supabase import create_client, Client


@st.cache_resource(show_spinner="Connecting to Supabase...")
def get_supabase_client() -> Client:
    """Initialize and cache the Supabase client."""
    try:
        url: str = st.secrets["SUPABASE_URL"]
        key: str = st.secrets["SUPABASE_KEY"]
        client: Client = create_client(url, key)
        return client
    except KeyError:
        st.error(
            "❌ Supabase credentials not configured.\n\n"
            "Create `.streamlit/secrets.toml` (local) or add Secrets in Streamlit Cloud:\n\n"
            "SUPABASE_URL = \"https://<your-project>.supabase.co\"\n"
            "SUPABASE_KEY = \"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...\""
        )
        raise
    except Exception as e:
        st.error(f"Failed to connect to Supabase: {e}")
        raise
