# import streamlit as st
# from datetime import date, datetime
# from supabase import create_client, Client
# import base64

# # ---------- CONFIG ----------
# st.set_page_config(page_title="Edit Transaction (Expandable)")

# @st.cache_resource
# def get_supabase() -> Client:
#     url = "https://ogecahtzmpsznesragam.supabase.co"
#     key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZWNhaHR6bXBzem5lc3JhZ2FtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5MzE0NDEsImV4cCI6MjA2NTUwNzQ0MX0.SVPUtm2-bhTRjc0XZnUII8pHt2Jc435Mr_fsEkmKpvs"
#     return create_client(url, key)

# supabase = get_supabase()

# BANK_NAME_OPTIONS = [
#     "State Bank of India (SBI)",
#     "Punjab National Bank (PNB)",
#     "HDFC Bank",
#     "ICICI Bank",
#     "Axis Bank",
#     "Kotak Mahindra Bank",
#     "Bank of Baroda",
#     "Union Bank of India",
#     "Canara Bank",
#     "IndusInd Bank",
#     "Yes Bank",
#     "IDFC FIRST Bank",
#     "Central Bank of India",
#     "Indian Bank",
#     "Bank of India",
#     "AU Bank"
# ]

# # ---------- HELPERS ----------
# def select_all(table: str, cols: str = "*", **filters):
#     q = supabase.table(table).select(cols)
#     for k, v in filters.items():
#         q = q.eq(k, v)
#     return q.execute().data or []

# def single_or_none(table: str, **filters):
#     rows = select_all(table, "*", **filters)
#     return rows[0] if rows else None

# def get_stakeholders(project_id):
#     # Get partners
#     partners = supabase.table("partners").select("partner_user_id, partner_id").eq("project_id", project_id).execute().data or []
#     partner_user_ids = [p["partner_user_id"] for p in partners]
#     partner_ids = [p["partner_id"] for p in partners]

#     # Get sub-partners for those partners
#     subs = supabase.table("sub_partners").select("sub_partner_user_id, partner_id").execute().data or []
#     sub_partner_user_ids = [s["sub_partner_user_id"] for s in subs if s["partner_id"] in partner_ids]

#     stakeholder_ids = partner_user_ids + sub_partner_user_ids

#     if not stakeholder_ids:
#         return {}

#     # ✅ Include children of stakeholders
#     children = supabase.table("users").select("id, parent_user_id").in_("parent_user_id", stakeholder_ids).execute().data or []
#     child_ids = [c["id"] for c in children]

#     all_user_ids = stakeholder_ids + child_ids

#     # Fetch user names
#     users = supabase.table("users").select("id, name").in_("id", all_user_ids).execute().data or []
#     return {u["id"]: u["name"] for u in users}


# def get_users_excluding(ids_to_exclude):
#     all_users = supabase.table("users").select("id, name").execute().data or []
#     return {u["id"]: u["name"] for u in all_users if u["id"] not in ids_to_exclude}

# def get_user_map():
#     users = supabase.table("users").select("id, name").execute().data or []
#     return {u["id"]: u["name"] for u in users}

# def delete_mode_children(transaction_id: int):
#     """Remove any existing mode-specific rows for this transaction."""
#     for table in ("upi_payments", "cheque_payments", "netbanking_payments"):
#         supabase.table(table).delete().eq("transaction_id", transaction_id).execute()

# def load_all_mode_children(transaction_id: int):
#     """Return dicts for each possible child table (if exists)."""
#     upi = single_or_none("upi_payments", transaction_id=transaction_id) or {}
#     cheque = single_or_none("cheque_payments", transaction_id=transaction_id) or {}
#     netb = single_or_none("netbanking_payments", transaction_id=transaction_id) or {}
#     return upi, cheque, netb

# # ---------- PAGE ----------
# def main():
#     st.title("Edit Transactions")

#     # --- Project selection ---
#     projects = supabase.table("projects").select("project_id, project_name").execute().data or []
#     if not projects:
#         st.warning("Create a project first.")
#         return

#     proj_map = {p["project_name"]: p["project_id"] for p in projects}
#     project_name = st.selectbox("Select Project", list(proj_map.keys()))
#     project_id = proj_map[project_name]

#     stakeholder_map = get_stakeholders(project_id)             # {id: name} for partners/subpartners
#     external_users_map = get_users_excluding(stakeholder_map)  # {id: name} excluding stakeholders
#     user_map_all = get_user_map()

#     # --- Transactions in this project ---
#     # FIX #1: Stable ordering with secondary sort by transaction_id DESC
#     txns = (
#         supabase.table("transactions")
#         .select("transaction_id, transaction_date, transaction_type, amount, paid_by, paid_to, mode, purpose")
#         .eq("project_id", project_id)
#         .order("transaction_date", desc=True)
#         .order("transaction_id", desc=True)
#         .execute()
#         .data
#         or []
#     )

#     if not txns:
#         st.info("No transactions in this project yet.")
#         return

#     st.caption("Click a row to expand and edit.")
#     for txn in txns:
#         txn_id = txn["transaction_id"]
#         amount = txn.get("amount", 0) or 0
#         paid_by_name_hdr = user_map_all.get(txn.get("paid_by"), f"User {txn.get('paid_by')}")
#         header = f"₹{float(amount):.2f} — Paid by {paid_by_name_hdr}"

#         with st.expander(header, expanded=False):
#             # Prefetch child rows
#             upi_row, cheque_row, netb_row = load_all_mode_children(txn_id)

#             # ----------------- FIX #2: Live mode switching -----------------
#             mode_list = ["cash", "UPI", "cheque", "netbanking"]
#             state_key = f"mode_{txn_id}"
#             if state_key not in st.session_state:
#                 # default to the txn's saved mode
#                 st.session_state[state_key] = txn.get("mode", "cash") if txn.get("mode") in mode_list else "cash"

#             st.markdown("#### Mode of Payment")
#             # place mode selector OUTSIDE the form to allow immediate reruns
#             st.selectbox(
#                 "Mode",
#                 mode_list,
#                 index=mode_list.index(st.session_state[state_key]),
#                 key=state_key,
#                 help="Changing this updates the fields below immediately."
#             )
#             current_mode = st.session_state[state_key]
#             st.divider()

#             # ----------------- EDIT FORM -----------------
#             with st.form(f"edit_txn_form_{txn_id}", clear_on_submit=False):
#                 st.subheader(f"Transaction #{txn_id}")

#                 # Date
#                 try:
#                     existing_date = datetime.fromisoformat(str(txn["transaction_date"])).date()
#                 except Exception:
#                     existing_date = date.today()
#                 txn_date = st.date_input("Transaction Date", existing_date, key=f"date_{txn_id}")

#                 # Type
#                 txn_type = st.selectbox(
#                     "Transaction Type",
#                     ["investment", "expense", "withdrawal"],
#                     index=["investment", "expense", "withdrawal"].index(txn["transaction_type"]),
#                     key=f"type_{txn_id}"
#                 )

#                 # Paid By (stakeholders only)
#                 paid_by_options = list(stakeholder_map.values()) or ["(no stakeholders)"]
#                 paid_by_default_name = stakeholder_map.get(txn["paid_by"], paid_by_options[0])
#                 paid_by_name = st.selectbox(
#                     "Paid By (Partner/Sub-Partner)",
#                     paid_by_options,
#                     index=paid_by_options.index(paid_by_default_name) if paid_by_default_name in paid_by_options else 0,
#                     key=f"paidby_{txn_id}"
#                 )
#                 paid_by_id = next((uid for uid, nm in stakeholder_map.items() if nm == paid_by_name), txn.get("paid_by"))

#                 # Paid To (external users only)
#                 paid_to_options = list(external_users_map.values()) or ["(no external users)"]
#                 paid_to_default_name = external_users_map.get(txn["paid_to"], paid_to_options[0])
#                 paid_to_name = st.selectbox(
#                     "Paid To (External User)",
#                     paid_to_options,
#                     index=paid_to_options.index(paid_to_default_name) if paid_to_default_name in paid_to_options else 0,
#                     key=f"paidto_{txn_id}"
#                 )
#                 paid_to_id = next((uid for uid, nm in external_users_map.items() if nm == paid_to_name), txn.get("paid_to"))

#                 amount_val = st.number_input(
#                     "Total Amount", value=float(amount), min_value=0.0, format="%.2f", key=f"amt_{txn_id}"
#                 )

#                 purpose = st.text_area("Purpose", value=txn.get("purpose") or "", key=f"purpose_{txn_id}")

#                 st.markdown("##### Mode details")
#                 mode_payload = {}

#                 # Render fields based on *current_mode* (live)
#                 if current_mode == "UPI":
#                     mode_payload["reference_number"] = st.text_input(
#                         "UPI Reference Number", value=upi_row.get("reference_number", ""), key=f"upi_ref_{txn_id}"
#                     )
#                     mode_payload["app_used"] = st.text_input(
#                         "UPI App Used", value=upi_row.get("app_used", ""), key=f"upi_app_{txn_id}"
#                     )

#                 elif current_mode == "cheque":
#                     bank_prefill = cheque_row.get("bank_name", BANK_NAME_OPTIONS[0]) if cheque_row else BANK_NAME_OPTIONS[0]
#                     if bank_prefill not in BANK_NAME_OPTIONS:
#                         bank_prefill = BANK_NAME_OPTIONS[0]
#                     mode_payload["cheque_number"] = st.text_input(
#                         "Cheque Number", value=cheque_row.get("cheque_number", ""), key=f"chq_no_{txn_id}"
#                     )
#                     mode_payload["bank_name"] = st.selectbox(
#                         "Bank Name", BANK_NAME_OPTIONS, index=BANK_NAME_OPTIONS.index(bank_prefill), key=f"chq_bank_{txn_id}"
#                     )

#                 elif current_mode == "netbanking":
#                     rb = netb_row.get("receiver_bank", BANK_NAME_OPTIONS[0]) if netb_row else BANK_NAME_OPTIONS[0]
#                     sb = netb_row.get("sender_bank", BANK_NAME_OPTIONS[0]) if netb_row else BANK_NAME_OPTIONS[0]
#                     if rb not in BANK_NAME_OPTIONS: rb = BANK_NAME_OPTIONS[0]
#                     if sb not in BANK_NAME_OPTIONS: sb = BANK_NAME_OPTIONS[0]
#                     mode_payload["receiver_bank"] = st.selectbox(
#                         "Receiver Bank Name", BANK_NAME_OPTIONS, index=BANK_NAME_OPTIONS.index(rb), key=f"nb_rbank_{txn_id}"
#                     )
#                     mode_payload["receiver_bank_ifsc"] = st.text_input(
#                         "Receiver Bank IFSC Code", value=netb_row.get("receiver_bank_ifsc", ""), key=f"nb_rifsc_{txn_id}"
#                     )
#                     mode_payload["receiver_account_number"] = st.text_input(
#                         "Receiver Account Number", value=netb_row.get("receiver_account_number", ""), key=f"nb_racc_{txn_id}"
#                     )
#                     mode_payload["sender_bank"] = st.selectbox(
#                         "Sender Bank Name", BANK_NAME_OPTIONS, index=BANK_NAME_OPTIONS.index(sb), key=f"nb_sbank_{txn_id}"
#                     )
#                     mode_payload["sender_account_number"] = st.text_input(
#                         "Sender Account Number", value=netb_row.get("sender_account_number", ""), key=f"nb_sacc_{txn_id}"
#                     )

#                 st.markdown("---")
#                 st.subheader("Payment Proofs")
#                 proofs = select_all("payment_proofs", "*", transaction_id=txn_id)
#                 del_flags = {}
#                 if proofs:
#                     st.caption("Select proofs to delete:")
#                     for pr in proofs:
#                         label = f"{pr['proof_id']} • {pr.get('file_name','(no name)')} – {pr.get('description','')}"
#                         del_flags[pr["proof_id"]] = st.checkbox(label, key=f"del_proof_{txn_id}_{pr['proof_id']}")
#                 else:
#                     st.caption("No proofs attached.")

#                 new_proof = st.file_uploader("Upload additional proof (PDF/JPEG)", type=["pdf", "jpg", "jpeg"], key=f"u_{txn_id}")
#                 new_proof_name = st.text_input("New Proof File Name", key=f"un_{txn_id}")
#                 new_proof_desc = st.text_area("New Proof Description", key=f"ud_{txn_id}")

#                 submitted = st.form_submit_button("💾 Save Changes", type="primary")

#             # ---------- SUBMIT HANDLER ----------
#             if submitted:
#                 try:
#                     # 1) Update base transaction
#                     supabase.table("transactions").update({
#                         "transaction_date": txn_date.isoformat(),
#                         "transaction_type": txn_type,
#                         "paid_by": paid_by_id,
#                         "paid_to": paid_to_id,
#                         "amount": amount_val,
#                         "mode": current_mode,   # use the live mode
#                         "purpose": purpose
#                     }).eq("transaction_id", txn_id).execute()

#                     # 2) Mode-specific rows: delete all others, then insert selected mode child
#                     delete_mode_children(txn_id)
#                     if current_mode == "UPI":
#                         supabase.table("upi_payments").insert({"transaction_id": txn_id, **mode_payload}).execute()
#                     elif current_mode == "cheque":
#                         supabase.table("cheque_payments").insert({"transaction_id": txn_id, **mode_payload}).execute()
#                     elif current_mode == "netbanking":
#                         supabase.table("netbanking_payments").insert({"transaction_id": txn_id, **mode_payload}).execute()
#                     # cash → no child row

#                     # 3) Delete selected proofs
#                     if del_flags:
#                         to_delete = [pid for pid, flagged in del_flags.items() if flagged]
#                         for pid in to_delete:
#                             supabase.table("payment_proofs").delete().eq("proof_id", pid).execute()

#                     # 4) Insert new proof if provided
#                     if new_proof:
#                         encoded = base64.b64encode(new_proof.read()).decode("utf-8")
#                         supabase.table("payment_proofs").insert({
#                             "transaction_id": txn_id,
#                             "file_name": new_proof_name or new_proof.name,
#                             "file_data": encoded,
#                             "description": new_proof_desc
#                         }).execute()

#                     st.success("✅ Transaction updated.")
#                     st.rerun()

#                 except Exception as e:
#                     st.error(f"❌ Error updating transaction #{txn_id}: {e}")

# if __name__ == "__main__":
#     main()



# ========================================
# Edit Transaction Page (Streamlit + Supabase)
# ========================================

import streamlit as st
from datetime import date
from supabase import create_client, Client
import base64

# -------------------------------
# Page & Supabase Setup
# -------------------------------
st.set_page_config(page_title="Edit Transaction")

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
    r = supabase.table("projects").select("project_id, project_name").order("project_name").execute()
    return r.data or []

def fetch_users_full():
    r = supabase.table("users").select("id, name, parent_user_id").order("name").execute()
    return r.data or []

def build_stakeholder_sets(project_id: int):
    """Return (stakeholder_ids, stakeholder_or_children_ids) based on partners/sub-partners of project."""
    partners = supabase.table("partners").select("partner_user_id, partner_id").eq("project_id", project_id).execute().data or []
    partner_user_ids = [p["partner_user_id"] for p in partners if p.get("partner_user_id") is not None]
    partner_ids = [p["partner_id"] for p in partners]

    subs = []
    if partner_ids:
        subs = supabase.table("sub_partners").select("sub_partner_user_id, partner_id").in_("partner_id", partner_ids).execute().data or []
    sub_user_ids = [s["sub_partner_user_id"] for s in subs if s.get("sub_partner_user_id") is not None]

    stakeholder_ids = set(partner_user_ids) | set(sub_user_ids)

    children = []
    if stakeholder_ids:
        children = supabase.table("users").select("id").in_("parent_user_id", list(stakeholder_ids)).execute().data or []
    child_ids = set(c["id"] for c in children)

    return stakeholder_ids, (stakeholder_ids | child_ids)

def fetch_transactions_for_project(project_id: int):
    """List transactions for chooser."""
    r = (supabase.table("transactions")
         .select("transaction_id, transaction_date, amount, mode, transaction_type, purpose, paid_by, paid_to, paid_via, funding_note")
         .eq("project_id", project_id)
         .order("transaction_date", desc=True)
         .order("transaction_id", desc=True)
         .execute())
    return r.data or []

def fetch_mode_detail(transaction_id: int, mode: str):
    """Return current mode detail row (if any) for the transaction."""
    if mode == "UPI":
        r = supabase.table("upi_payments").select("*").eq("transaction_id", transaction_id).execute()
        return (r.data or [None])[0]
    if mode == "cheque":
        r = supabase.table("cheque_payments").select("*").eq("transaction_id", transaction_id).execute()
        return (r.data or [None])[0]
    if mode == "netbanking":
        r = supabase.table("netbanking_payments").select("*").eq("transaction_id", transaction_id).execute()
        return (r.data or [None])[0]
    return None  # cash has no detail table

def delete_all_mode_details(transaction_id: int):
    """Remove any existing mode detail rows for this transaction (safe when changing mode)."""
    supabase.table("upi_payments").delete().eq("transaction_id", transaction_id).execute()
    supabase.table("cheque_payments").delete().eq("transaction_id", transaction_id).execute()
    supabase.table("netbanking_payments").delete().eq("transaction_id", transaction_id).execute()

def upsert_mode_detail(transaction_id: int, mode: str, mode_data: dict):
    """Create or update the mode detail appropriate to the chosen mode."""
    delete_all_mode_details(transaction_id)  # simplest & safe
    if mode == "UPI":
        supabase.table("upi_payments").insert({"transaction_id": transaction_id, **mode_data}).execute()
    elif mode == "cheque":
        supabase.table("cheque_payments").insert({"transaction_id": transaction_id, **mode_data}).execute()
    elif mode == "netbanking":
        supabase.table("netbanking_payments").insert({"transaction_id": transaction_id, **mode_data}).execute()
    # cash → no table

def fetch_sources(transaction_id: int):
    r = supabase.table("transaction_sources").select("id, source_id, is_partner, amount").eq("transaction_id", transaction_id).execute()
    return r.data or []

def replace_sources(transaction_id: int, rows: list[dict]):
    """Delete all existing sources for txn and insert fresh payload."""
    supabase.table("transaction_sources").delete().eq("transaction_id", transaction_id).execute()
    if rows:
        supabase.table("transaction_sources").insert(rows).execute()

def money(x) -> float:
    try:
        return float(x or 0.0)
    except Exception:
        return 0.0

def idx_for_user(users, user_id):
    if user_id is None:
        return 0
    for i, u in enumerate(users):
        if u["id"] == user_id:
            return i
    return 0

# -------------------------------
# Session State for editable arrays
# -------------------------------
if "edit_sources" not in st.session_state:
    st.session_state.edit_sources = []  # [{source_id, amount, is_partner}]

# -------------------------------
# UI: Project → Transaction selector
# -------------------------------
st.title("Edit a Transaction")

projects = fetch_projects()
if not projects:
    st.warning("No projects found. Please create a project first.")
    st.stop()

proj_map = {p["project_name"]: p["project_id"] for p in projects}
project_name = st.selectbox("Project", list(proj_map.keys()))
project_id = proj_map[project_name]

# Build stakeholder sets for filters/flags
stakeholder_ids, stakeholder_or_children_ids = build_stakeholder_sets(project_id)

# Pull transactions for this project
txns = fetch_transactions_for_project(project_id)
users = fetch_users_full()
users_map = {u["id"]: u["name"] for u in users}

if not txns:
    st.info("No transactions in this project yet.")
    st.stop()

# Build labels and select a transaction
labels = []
for t in txns:
    d = t.get("transaction_date") or ""
    amt = money(t.get("amount"))
    labels.append(f"#{t['transaction_id']} • {d} • ₹{amt:,.2f} • {t.get('mode','')} • {t.get('purpose','') or ''}")

selected_label = st.selectbox("Select Transaction", labels)
txn = txns[labels.index(selected_label)]
transaction_id = txn["transaction_id"]

# Load sources for this transaction into session state (only when txn changes)
if st.session_state.get("loaded_txn_id") != transaction_id:
    existing_sources = fetch_sources(transaction_id)
    st.session_state.edit_sources = [
        {"source_id": s["source_id"], "amount": money(s["amount"]),
         "is_partner": bool(s.get("is_partner", False))}
        for s in existing_sources
    ]
    st.session_state.loaded_txn_id = transaction_id

# -------------------------------
# Editor: Core fields (left/right)
# -------------------------------
c1, c2 = st.columns(2)

with c1:
    # Paid By (stakeholder or their child)
    paid_by_opts = [u for u in users if u["id"] in stakeholder_or_children_ids]
    paid_by_name_list = [u["name"] for u in paid_by_opts] or ["— none —"]
    paid_by_idx = idx_for_user(paid_by_opts, txn.get("paid_by"))
    paid_by_choice = st.selectbox("Paid By (Stakeholder/Child)", paid_by_name_list, index=min(paid_by_idx, len(paid_by_name_list)-1))
    paid_by_id = None if not paid_by_opts else paid_by_opts[paid_by_name_list.index(paid_by_choice)]["id"]

    # Paid To (exclude stakeholders and their children)
    paid_to_candidates = [u for u in users if (u["id"] not in stakeholder_ids and (u["parent_user_id"] is None or u["parent_user_id"] not in stakeholder_ids))]
    paid_to_name_list = [u["name"] for u in paid_to_candidates] or ["— none —"]
    paid_to_idx = idx_for_user(paid_to_candidates, txn.get("paid_to"))
    paid_to_choice = st.selectbox("Paid To (Non-stakeholder / not child)", paid_to_name_list, index=min(paid_to_idx, len(paid_to_name_list)-1))
    paid_to_id = None if not paid_to_candidates else paid_to_candidates[paid_to_name_list.index(paid_to_choice)]["id"]

    # Payment Via (any user)
    paid_via_name_list = [u["name"] for u in users]
    paid_via_idx = idx_for_user(users, txn.get("paid_via"))
    paid_via_choice = st.selectbox("Payment Via (account/UPI used)", paid_via_name_list, index=min(paid_via_idx, len(paid_via_name_list)-1))
    paid_via_id = users[paid_via_name_list.index(paid_via_choice)]["id"]

with c2:
    txn_date = st.date_input("Transaction Date", value=date.fromisoformat(txn["transaction_date"]) if txn.get("transaction_date") else date.today())
    txn_type = st.selectbox("Transaction Type", ["investment", "expense"], index=(["investment","expense"].index(txn.get("transaction_type")) if txn.get("transaction_type") in ["investment","expense"] else 0))
    amount = st.number_input("Total Amount", min_value=0.0, value=money(txn.get("amount")), step=0.01, format="%.2f")
    mode = st.selectbox("Mode", ["cash", "UPI", "cheque", "netbanking"], index=(["cash","UPI","cheque","netbanking"].index(txn.get("mode")) if txn.get("mode") in ["cash","UPI","cheque","netbanking"] else 0))

purpose = st.text_area("Purpose", value=txn.get("purpose") or "")
funding_note_existing = txn.get("funding_note") or ""

# -------------------------------
# Mode-specific details
# -------------------------------
st.subheader("Mode-specific details")

current_detail = fetch_mode_detail(transaction_id, txn.get("mode") or "cash")  # detail row for CURRENT stored mode
mode_data = {}

if mode == "UPI":
    mode_data["reference_number"] = st.text_input("UPI Reference Number", value=(current_detail or {}).get("reference_number", ""))
    mode_data["app_used"] = st.text_input("UPI App Used", value=(current_detail or {}).get("app_used", ""))

elif mode == "cheque":
    mode_data["cheque_number"] = st.text_input("Cheque Number", value=(current_detail or {}).get("cheque_number", ""))
    mode_data["bank_name"] = st.text_input("Bank Name", value=(current_detail or {}).get("bank_name", ""))

elif mode == "netbanking":
    mode_data["receiver_bank"] = st.text_input("Receiver Bank", value=(current_detail or {}).get("receiver_bank", ""))
    mode_data["receiver_bank_ifsc"] = st.text_input("Receiver Bank IFSC", value=(current_detail or {}).get("receiver_bank_ifsc", ""))
    mode_data["receiver_account_number"] = st.text_input("Receiver Account Number", value=(current_detail or {}).get("receiver_account_number", ""))
    mode_data["sender_bank"] = st.text_input("Sender Bank", value=(current_detail or {}).get("sender_bank", ""))
    mode_data["sender_account_number"] = st.text_input("Sender Account Number", value=(current_detail or {}).get("sender_account_number", ""))

# -------------------------------
# Sources of Funds (editable)
# -------------------------------
st.subheader("Sources of Funds")
if st.button("➕ Add Source"):
    st.session_state.edit_sources.append({"source_id": users[0]["id"] if users else None, "amount": 0.0, "is_partner": False})

remove_src_idx = []
for i, row in enumerate(st.session_state.edit_sources):
    with st.expander(f"Source {i+1}", expanded=True):
        c1, c2, c3 = st.columns([1.2, 0.8, 0.6])
        with c1:
            names = [u["name"] for u in users]
            # set index to current user if present
            idx = idx_for_user(users, row.get("source_id"))
            chosen = st.selectbox("User", names, index=min(idx, len(names)-1), key=f"src_user_{i}")
            row["source_id"] = users[names.index(chosen)]["id"]
        with c2:
            row["amount"] = st.number_input("Amount", min_value=0.0, step=0.01, format="%.2f", value=float(row.get("amount", 0.0)), key=f"src_amt_{i}")
        with c3:
            # auto-compute is_partner (stakeholder or their child)
            row["is_partner"] = (row["source_id"] in stakeholder_or_children_ids)
            st.checkbox("Is Partner?", value=row["is_partner"], disabled=True, key=f"src_is_partner_{i}")
        if st.button("Remove", key=f"rm_src_{i}"):
            remove_src_idx.append(i)

for idx in reversed(remove_src_idx):
    st.session_state.edit_sources.pop(idx)

sources_total = sum(money(r.get("amount")) for r in st.session_state.edit_sources)
st.caption(f"Sources total: **₹{sources_total:,.2f}** / Transaction amount: **₹{amount:,.2f}**")

gap = money(amount) - sources_total
if gap > 1e-6:
    funding_note = st.text_area(
        f"Explain remaining ₹{gap:,.2f}",
        value=funding_note_existing,
        placeholder="Example: self-funded from savings / borrowed temporarily / credit, etc."
    )
else:
    funding_note = st.text_area("Funding Note (optional)", value=funding_note_existing)

# -------------------------------
# Save changes
# -------------------------------
if st.button("💾 Save Changes"):
    # Validation
    errors = []
    if amount <= 0:
        errors.append("Amount must be greater than 0.")
    if not paid_by_id:
        errors.append("Please choose a valid 'Paid By' user.")
    # Mode-specific requirements
    if mode == "UPI" and not (mode_data.get("reference_number") or "").strip():
        errors.append("UPI: reference number is required.")
    if mode == "cheque":
        if not (mode_data.get("cheque_number") or "").strip():
            errors.append("Cheque: cheque number is required.")
        if not (mode_data.get("bank_name") or "").strip():
            errors.append("Cheque: bank name is required.")
    # Sources must not exceed amount
    if sources_total - amount > 1e-6:
        errors.append(f"Sources total (₹{sources_total:,.2f}) cannot exceed transaction amount (₹{amount:,.2f}).")
    # If there is a gap, require note
    if amount - sources_total > 1e-6 and not (funding_note or "").strip():
        errors.append("Please add a funding note explaining how the remaining amount was covered.")

    if errors:
        st.error("Please fix the following:\n\n- " + "\n- ".join(errors))
        st.stop()

    try:
        # 1) Update core transaction row
        supabase.table("transactions").update({
            "transaction_date": txn_date.isoformat(),
            "transaction_type": txn_type,
            "amount": amount,
            "mode": mode,
            "purpose": (purpose or None),
            "paid_by": paid_by_id,
            "paid_to": paid_to_id,       # can be None
            "paid_via": paid_via_id,     # may be same as paid_by or different
            "funding_note": (funding_note or None),
        }).eq("transaction_id", transaction_id).execute()

        # 2) Mode detail → delete old & insert current
        upsert_mode_detail(transaction_id, mode, mode_data)

        # 3) Sources → replace all rows for this transaction
        payload = [{
            "transaction_id": transaction_id,
            "source_id": r["source_id"],
            "is_partner": bool(r["is_partner"]),
            "amount": money(r["amount"]),
        } for r in st.session_state.edit_sources if r.get("source_id") is not None and money(r.get("amount")) > 0.0]
        replace_sources(transaction_id, payload)

        st.success("✅ Transaction updated successfully.")
        st.toast("Saved!", icon="✅")

    except Exception as e:
        st.error(f"❌ Failed to update transaction: {e}")
