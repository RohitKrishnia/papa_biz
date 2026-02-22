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
        .select("transaction_type, paid_by, amount, mode, purpose, created_at")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .execute()
    )

    transactions = tx_res.data or []
    
    # Get all unique paid_by user IDs
    paid_by_ids = [txn.get("paid_by") for txn in transactions if txn.get("paid_by") is not None]
    unique_user_ids = list(set(paid_by_ids))
    
    # Batch fetch user names
    user_name_map = {}
    if unique_user_ids:
        users_res = (
            supabase.table("users")
            .select("id, name")
            .in_("id", unique_user_ids)
            .execute()
        )
        user_name_map = {u["id"]: u["name"] for u in (users_res.data or [])}
    
    # Replace paid_by IDs with user names
    for txn in transactions:
        paid_by_id = txn.get("paid_by")
        if paid_by_id is not None:
            txn["paid_by"] = user_name_map.get(paid_by_id, f"User {paid_by_id}")
        else:
            txn["paid_by"] = "—"  # Display dash for None values

    return transactions, project_id

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
            # df_trans["Amount"] = round(df_trans["Amount"]/1e5,2)
            # df_trans = df_trans.rename(columns={"Amount": "Amount (Lakhs)"})
            st.dataframe(df_trans)
        else:
            st.info("No transactions found for this project.")

        st.subheader("💸 Settlements")
        if project_id is not None:
            settlements = get_settlements(project_id)
            if settlements:
                df_settle = pd.DataFrame(settlements)
                df_settle.columns = [col.replace("_", " ").title() for col in df_settle.columns]
                # df_settle["Amount"] = round(df["Amount"]/1e5,2)
                # df_settle = df_settle.rename(columns={"Amount": "Amount (Lakhs)"})

                st.dataframe(df_settle)
            else:
                st.info("No settlements recorded for this project.")



if __name__ == "__main__":
    main()
