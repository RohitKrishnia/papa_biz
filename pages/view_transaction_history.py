import streamlit as st
import pandas as pd
from supabase import create_client, Client

# ---------- Supabase Setup ----------
st.set_page_config(page_title="Project Transactions & Settlements")
@st.cache_resource
def get_supabase() -> Client:

    url = "https://ogecahtzmpsznesragam.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZWNhaHR6bXBzem5lc3JhZ2FtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5MzE0NDEsImV4cCI6MjA2NTUwNzQ0MX0.SVPUtm2-bhTRjc0XZnUII8pHt2Jc435Mr_fsEkmKpvs"
    return create_client(url, key)

supabase = get_supabase()
# ---------- Fetch Project List ----------

def get_projects():
    res = supabase.table("projects").select("project_name").execute()
    return [row["project_name"] for row in res.data or []]

# ---------- Fetch Transactions ----------

def get_transactions(project_name):
    res = supabase.table("projects").select("project_id").eq("project_name", project_name).execute()
    if not res.data:
        return [], None
    project_id = res.data[0]["project_id"]

    tx_res = (
        supabase.table("transactions")
        .select("transaction_type, paid_by, amount, mode, purpose, split_type, created_at")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .execute()
    )

    return tx_res.data or [], project_id

# ---------- Fetch Settlements ----------

def get_settlements(project_id):
    res = (
        supabase.table("settlements")
        .select("paid_by, paid_to, amount, created_at")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []

# ---------- Streamlit UI ----------

def main():
    
    st.title("📜 View Transaction History & Settlements")

    projects = get_projects()
    if not projects:
        st.warning("No projects found.")
        return

    selected_project = st.selectbox("Select a Project", projects)

    if selected_project:
        st.subheader("📌 Transactions")
        transactions, project_id = get_transactions(selected_project)

        if transactions:
            df_trans = pd.DataFrame(transactions)
            df_trans.columns = [col.replace("_", " ").title() for col in df_trans.columns]
            st.dataframe(df_trans)
        else:
            st.info("No transactions found for this project.")

        st.subheader("💸 Settlements")
        if project_id is not None:
            settlements = get_settlements(project_id)
            if settlements:
                df_settle = pd.DataFrame(settlements)
                df_settle.columns = [col.replace("_", " ").title() for col in df_settle.columns]
                st.dataframe(df_settle)
            else:
                st.info("No settlements recorded for this project.")

if __name__ == "__main__":
    main()
