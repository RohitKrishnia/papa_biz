# =========================================
# Record Settlement Page (Streamlit + Supabase)
# - Stores mode details in settlement-specific tables
# - Bank name dropdown (static list)
# - Netbanking: fetches bank accounts for Paid By / Paid To users
# =========================================

import streamlit as st
from datetime import date
from supabase import create_client, Client

# -------------------------------
# Page & Supabase Setup
# -------------------------------
st.set_page_config(page_title="Record Settlement")

@st.cache_resource
def get_supabase() -> Client:
    url = "https://ogecahtzmpsznesragam.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZWNhaHR6bXBzem5lc3JhZ2FtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5MzE0NDEsImV4cCI6MjA2NTUwNzQ0MX0.SVPUtm2-bhTRjc0XZnUII8pHt2Jc435Mr_fsEkmKpvs"
    return create_client(url, key)

supabase = get_supabase()

# -------------------------------
# Constants
# -------------------------------
BANK_NAME_OPTIONS = [
    "State Bank of India (SBI)", "Punjab National Bank (PNB)", "HDFC Bank", "ICICI Bank",
    "Axis Bank", "Kotak Mahindra Bank", "Bank of Baroda", "Union Bank of India",
    "Canara Bank", "IndusInd Bank", "Yes Bank", "IDFC FIRST Bank",
    "Central Bank of India", "Indian Bank", "Bank of India", "AU Bank"
]
MANUAL_ENTRY = "Other (enter manually)"

# -------------------------------
# Helpers
# -------------------------------
def fetch_projects():
    r = (supabase.table("projects")
         .select("project_id, project_name")
         .order("project_name")
         .execute())
    return r.data or []

def build_stakeholders(project_id: int):
    """
    Return [{'id','name'}] for partners + sub-partners in the project.
    """
    partners = (supabase.table("partners")
                .select("partner_id, partner_user_id")
                .eq("project_id", project_id)
                .execute().data or [])
    partner_ids = [p["partner_id"] for p in partners]
    partner_user_ids = {p["partner_user_id"] for p in partners if p.get("partner_user_id") is not None}

    sub_user_ids = set()
    if partner_ids:
        subs = (supabase.table("sub_partners")
                .select("sub_partner_user_id, partner_id")
                .in_("partner_id", partner_ids)
                .execute().data or [])
        sub_user_ids = {s["sub_partner_user_id"] for s in subs if s.get("sub_partner_user_id") is not None}

    stakeholder_ids = list(partner_user_ids | sub_user_ids)
    if not stakeholder_ids:
        return []

    users = (supabase.table("users")
             .select("id, name")
             .in_("id", stakeholder_ids)
             .order("name")
             .execute().data or [])
    return users

def fetch_bank_accounts_for_user(user_id: int):
    """Return list of dicts: [{'id','bank_name','account_number'}]"""
    if not user_id:
        return []
    r = (supabase.table("bank_accounts")
         .select("id, bank_name, account_number")
         .eq("user_id", user_id)
         .order("bank_name")
         .execute())
    return r.data or []

def format_account(a: dict) -> str:
    return f"{a.get('bank_name','')} — {a.get('account_number','')}"

# -------------------------------
# UI
# -------------------------------
st.title("Record a Settlement")

# 1) Project
projects = fetch_projects()
if not projects:
    st.warning("No projects found.")
    st.stop()

proj_map = {p["project_name"]: p["project_id"] for p in projects}
project_name = st.selectbox("Project", list(proj_map.keys()))
project_id = proj_map[project_name]

# 2) Stakeholders
stakeholders = build_stakeholders(project_id)
if not stakeholders:
    st.info("No partners/sub-partners found for this project.")
    st.stop()

stake_names = [u["name"] for u in stakeholders]
name_to_id = {u["name"]: u["id"] for u in stakeholders}

c1, c2 = st.columns(2)
with c1:
    paid_by_name = st.selectbox("Paid By (Partner/Sub-partner)", stake_names)
with c2:
    # default to a different person if available
    default_idx = 1 if len(stake_names) > 1 and stake_names[0] == paid_by_name else 0
    paid_to_name = st.selectbox("Paid To (Partner/Sub-partner)", stake_names, index=default_idx)

if paid_by_name == paid_to_name:
    st.warning("Paid By and Paid To cannot be the same stakeholder.")

paid_by_id = name_to_id[paid_by_name]
paid_to_id = name_to_id[paid_to_name]

# 3) Amount / Date / Mode
c3, c4 = st.columns(2)
with c3:
    amount = st.number_input("Amount (₹)", min_value=0.0, step=0.01, format="%.2f")
with c4:
    settle_date = st.date_input("Settlement Date", value=date.today())

mode = st.selectbox("Mode of Payment", ["cash", "UPI", "cheque", "netbanking"])
remarks = st.text_area("Remarks (optional)")

# 4) Mode-specific inputs
mode_data = {}

if mode == "UPI":
    st.subheader("UPI Details")
    mode_data["reference_number"] = st.text_input("UPI Reference Number")
    mode_data["app_used"] = st.text_input("UPI App Used")

elif mode == "cheque":
    st.subheader("Cheque Details")
    mode_data["cheque_number"] = st.text_input("Cheque Number")
    # Bank name dropdown from provided list
    mode_data["bank_name"] = st.selectbox("Bank Name", BANK_NAME_OPTIONS)

elif mode == "netbanking":
    st.subheader("Netbanking Details")

    # Fetch accounts for Paid By / Paid To
    paid_by_accounts = fetch_bank_accounts_for_user(paid_by_id)
    paid_to_accounts = fetch_bank_accounts_for_user(paid_to_id)

    # Sender (Paid By)
    st.markdown("**Sender (Paid By) Account**")
    sender_choices = [format_account(a) for a in paid_by_accounts] + [MANUAL_ENTRY] if paid_by_accounts else [MANUAL_ENTRY]
    sender_choice = st.selectbox("Choose sender account", sender_choices, key="sender_choice_nb")

    if sender_choice != MANUAL_ENTRY and paid_by_accounts:
        idx = sender_choices.index(sender_choice)
        if idx < len(paid_by_accounts):
            sel = paid_by_accounts[idx]
            mode_data["sender_bank"] = st.selectbox("Sender Bank", BANK_NAME_OPTIONS,
                                                    index=(BANK_NAME_OPTIONS.index(sel["bank_name"]) if sel["bank_name"] in BANK_NAME_OPTIONS else 0))
            mode_data["sender_account_number"] = st.text_input("Sender Account Number", value=sel["account_number"])
        else:
            # fallback to manual (shouldn't happen)
            mode_data["sender_bank"] = st.selectbox("Sender Bank", BANK_NAME_OPTIONS)
            mode_data["sender_account_number"] = st.text_input("Sender Account Number")
    else:
        mode_data["sender_bank"] = st.selectbox("Sender Bank", BANK_NAME_OPTIONS)
        mode_data["sender_account_number"] = st.text_input("Sender Account Number")

    # Receiver (Paid To)
    st.markdown("**Receiver (Paid To) Account**")
    receiver_choices = [format_account(a) for a in paid_to_accounts] + [MANUAL_ENTRY] if paid_to_accounts else [MANUAL_ENTRY]
    receiver_choice = st.selectbox("Choose receiver account", receiver_choices, key="receiver_choice_nb")

    if receiver_choice != MANUAL_ENTRY and paid_to_accounts:
        idx = receiver_choices.index(receiver_choice)
        if idx < len(paid_to_accounts):
            sel = paid_to_accounts[idx]
            mode_data["receiver_bank"] = st.selectbox("Receiver Bank", BANK_NAME_OPTIONS,
                                                      index=(BANK_NAME_OPTIONS.index(sel["bank_name"]) if sel["bank_name"] in BANK_NAME_OPTIONS else 0))
            mode_data["receiver_account_number"] = st.text_input("Receiver Account Number", value=sel["account_number"])
        else:
            mode_data["receiver_bank"] = st.selectbox("Receiver Bank", BANK_NAME_OPTIONS)
            mode_data["receiver_account_number"] = st.text_input("Receiver Account Number")
    else:
        mode_data["receiver_bank"] = st.selectbox("Receiver Bank", BANK_NAME_OPTIONS)
        mode_data["receiver_account_number"] = st.text_input("Receiver Account Number")

    mode_data["receiver_bank_ifsc"] = st.text_input("Receiver Bank IFSC (optional)")

# 5) Submit → insert into settlements + settlement-mode table
if st.button("Record Settlement"):
    errors = []
    if paid_by_name == paid_to_name:
        errors.append("Paid By and Paid To must be different stakeholders.")
    if amount <= 0:
        errors.append("Amount must be greater than 0.")

    # Mode validations
    if mode == "UPI":
        if not (mode_data.get("reference_number") or "").strip():
            errors.append("UPI reference number is required.")
    if mode == "cheque":
        if not (mode_data.get("cheque_number") or "").strip():
            errors.append("Cheque number is required.")
        if not (mode_data.get("bank_name") or "").strip():
            errors.append("Bank name is required.")
    if mode == "netbanking":
        if not (mode_data.get("sender_bank") or "").strip():
            errors.append("Sender bank is required.")
        if not (mode_data.get("sender_account_number") or "").strip():
            errors.append("Sender account number is required.")
        if not (mode_data.get("receiver_bank") or "").strip():
            errors.append("Receiver bank is required.")
        if not (mode_data.get("receiver_account_number") or "").strip():
            errors.append("Receiver account number is required.")
        # IFSC optional per your schema

    if errors:
        st.error("Please fix the following:\n\n- " + "\n- ".join(errors))
        st.stop()

    try:
        # 1) Insert into settlements (schema stores stakeholder names as text)
        ins = (supabase.table("settlements").insert({
            "project_id": project_id,
            "paid_by": paid_by_name,
            "paid_to": paid_to_name,
            "amount": float(amount),
            "mode": mode,
            "remarks": (remarks or None),
            "date": settle_date.isoformat()
        }).execute())

        if not ins.data:
            raise Exception(f"Settlement insert failed: {ins}")
        settlement_id = ins.data[0]["settlement_id"]

        # 2) Insert mode details into settlement-specific tables
        if mode == "UPI":
            supabase.table("upi_settlements").insert({
                "settlement_id": settlement_id,
                "reference_number": mode_data["reference_number"],
                "app_used": mode_data.get("app_used") or None
            }).execute()

        elif mode == "cheque":
            supabase.table("cheque_settlements").insert({
                "settlement_id": settlement_id,
                "cheque_number": mode_data["cheque_number"],
                "bank_name": mode_data["bank_name"]
            }).execute()

        elif mode == "netbanking":
            supabase.table("netbanking_settlements").insert({
                "settlement_id": settlement_id,
                "receiver_bank": mode_data.get("receiver_bank") or None,
                "receiver_bank_ifsc": mode_data.get("receiver_bank_ifsc") or None,
                "receiver_account_number": mode_data.get("receiver_account_number") or None,
                "sender_bank": mode_data.get("sender_bank") or None,
                "sender_account_number": mode_data.get("sender_account_number") or None
            }).execute()
        # cash → no detail row

        st.success("✅ Settlement recorded with mode details.")
        st.toast("Saved!", icon="✅")

    except Exception as e:
        st.error(f"❌ Failed to record settlement: {e}")
