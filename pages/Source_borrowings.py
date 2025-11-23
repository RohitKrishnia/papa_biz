# =========================================
# Source Borrowings (Summary Only)
# Shows: Lender (source) name + total amount borrowed
# =========================================

import streamlit as st
import pandas as pd
from io import StringIO
from supabase import create_client, Client

# -------------------------------
# Page & Supabase Setup
# -------------------------------
st.set_page_config(page_title="Source Borrowings (Summary)")

@st.cache_resource
def get_supabase() -> Client:
    url = "https://ogecahtzmpsznesragam.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZWNhaHR6bXBzem5lc3JhZ2FtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5MzE0NDEsImV4cCI6MjA2NTUwNzQ0MX0.SVPUtm2-bhTRjc0XZnUII8pHt2Jc435Mr_fsEkmKpvs"
    return create_client(url, key)

supabase = get_supabase()

# -------------------------------
# Helpers
# -------------------------------
def fetch_projects():
    r = (supabase.table("projects")
         .select("project_id, project_name")
         .order("project_name")
         .execute())
    return r.data or []

def fetch_users_map():
    """Return {id: {'name': str, 'parent_user_id': int|None}}"""
    r = supabase.table("users").select("id, name, parent_user_id").execute()
    users = r.data or []
    return {u["id"]: {"name": u["name"], "parent_user_id": u.get("parent_user_id")} for u in users}

def build_stakeholders_for_project(project_id: int) -> set[int]:
    """
    Stakeholders = partners + sub-partners (ONLY).
    Children are NOT treated as stakeholders for borrowings.
    """
    partners = (supabase.table("partners")
                .select("partner_id, partner_user_id")
                .eq("project_id", project_id)
                .execute().data or [])
    partner_ids = [p["partner_id"] for p in partners]
    partner_user_ids = [p["partner_user_id"] for p in partners if p.get("partner_user_id") is not None]

    sub_ids = []
    if partner_ids:
        subs = (supabase.table("sub_partners")
                .select("sub_partner_user_id, partner_id")
                .in_("partner_id", partner_ids)
                .execute().data or [])
        sub_ids = [s["sub_partner_user_id"] for s in subs if s.get("sub_partner_user_id") is not None]

    return set(partner_user_ids) | set(sub_ids)

def fetch_transactions_for_stakeholder(project_id: int, stakeholder_user_id: int):
    """All transactions in project where paid_by = selected stakeholder."""
    r = (supabase.table("transactions")
         .select("transaction_id")
         .eq("project_id", project_id)
         .eq("paid_by", stakeholder_user_id)
         .execute())
    return r.data or []

def fetch_sources_for_transactions(txn_ids: list[int]):
    """Return list of sources rows for the given transaction_ids."""
    if not txn_ids:
        return []
    r = (supabase.table("transaction_sources")
         .select("transaction_id, source_id, amount")
         .in_("transaction_id", txn_ids)
         .execute())
    return r.data or []

def to_float(x) -> float:
    try:
        return float(x or 0.0)
    except Exception:
        return 0.0

def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buff = StringIO()
    df.to_csv(buff, index=False)
    return buff.getvalue().encode("utf-8")

# -------------------------------
# UI
# -------------------------------
st.title("Source Borrowings (Summary)")

# 1) Select project
projects = fetch_projects()
if not projects:
    st.warning("No projects found.")
    st.stop()

proj_map = {p["project_name"]: p["project_id"] for p in projects}
project_name = st.selectbox("Project", list(proj_map.keys()))
project_id = proj_map[project_name]

# 2) Select stakeholder (partner or sub-partner only)
stakeholder_ids = build_stakeholders_for_project(project_id)
users_map = fetch_users_map()

stakeholder_options = [{"id": uid, "name": users_map.get(uid, {}).get("name", f"User {uid}")} for uid in sorted(stakeholder_ids)]
if not stakeholder_options:
    st.info("No stakeholders (partners/sub-partners) found for this project.")
    st.stop()

stakeholder_label_list = [o["name"] for o in stakeholder_options]
stakeholder_choice = st.selectbox("Stakeholder (Partner / Sub-partner)", stakeholder_label_list)
selected_stakeholder_id = stakeholder_options[stakeholder_label_list.index(stakeholder_choice)]["id"]

st.divider()

# 3) Fetch transactions where paid_by = selected stakeholder
txns = fetch_transactions_for_stakeholder(project_id, selected_stakeholder_id)
txn_ids = [t["transaction_id"] for t in txns]
if not txn_ids:
    st.info("No transactions where this stakeholder is 'Paid By'.")
    st.stop()

# 4) Fetch all sources for these txns and keep only non-stakeholder sources
sources = fetch_sources_for_transactions(txn_ids)

borrow_rows = []
for s in sources:
    src_user_id = s["source_id"]
    if src_user_id in stakeholder_ids:
        continue  # skip internal sources (partners/sub-partners)
    borrow_rows.append({
        "source_name": users_map.get(src_user_id, {}).get("name", f"User {src_user_id}"),
        "amount_borrowed": to_float(s.get("amount")),
    })

if not borrow_rows:
    st.success("No external borrowings found for this stakeholder in the selected project.")
    st.stop()

# 5) Summary by lender (ONLY name + amount)
summary_df = (pd.DataFrame(borrow_rows)
              .groupby("source_name", as_index=False)["amount_borrowed"]
              .sum()
              .sort_values("amount_borrowed", ascending=False))

total_borrowed = summary_df["amount_borrowed"].sum()

st.subheader("Borrowings by Lender")
st.dataframe(summary_df, use_container_width=True)
st.metric("Total Borrowed (from non-stakeholders)", f"₹{total_borrowed:,.2f}")

# 6) Download
st.download_button(
    "⬇️ Download Borrowings Summary (CSV)",
    data=df_to_csv_bytes(summary_df),
    file_name=f"borrowings_summary_{project_id}_{selected_stakeholder_id}.csv",
    mime="text/csv"
)

st.caption(
    "This view aggregates sources where the lender is NOT a partner or sub-partner in the selected project. "
    "Only lender name and total amount borrowed are shown."
)
