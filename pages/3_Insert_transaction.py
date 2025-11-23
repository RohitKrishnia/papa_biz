

# import streamlit as st
# from datetime import date
# from supabase import create_client, Client
# import base64

# # ===============================
# # CONFIG
# # ===============================
# st.set_page_config(page_title="Insert Transaction")

# @st.cache_resource
# def get_supabase() -> Client:
#     url = "https://ogecahtzmpsznesragam.supabase.co"
#     key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZWNhaHR6bXBzem5lc3JhZ2FtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5MzE0NDEsImV4cCI6MjA2NTUwNzQ0MX0.SVPUtm2-bhTRjc0XZnUII8pHt2Jc435Mr_fsEkmKpvs"
#     return create_client(url, key)

# supabase = get_supabase()

# BANK_NAME_OPTIONS = [
#     "State Bank of India (SBI)", "Punjab National Bank (PNB)", "HDFC Bank", "ICICI Bank",
#     "Axis Bank", "Kotak Mahindra Bank", "Bank of Baroda", "Union Bank of India",
#     "Canara Bank", "IndusInd Bank", "Yes Bank", "IDFC FIRST Bank",
#     "Central Bank of India", "Indian Bank", "Bank of India", "AU Bank"
# ]

# # ===============================
# # HELPERS
# # ===============================
# def insert(table: str, data: dict):
#     return supabase.table(table).insert(data).execute()

# def fetch_bank_accounts_for_user(user_id: int):
#     if user_id is None:
#         return []
#     resp = supabase.table("bank_accounts").select("id, bank_name, account_number").eq("user_id", user_id).execute()
#     return resp.data or []

# def format_account_label(acc: dict):
#     return f"{acc.get('bank_name','')} — {acc.get('account_number','')}"

# def add_bank_account(user_id: int, bank_name: str, account_number: str):
#     resp = insert("bank_accounts", {"user_id": user_id, "bank_name": bank_name, "account_number": account_number})
#     if resp.data:
#         return resp.data[0]
#     else:
#         raise Exception(f"Failed to add bank account: {resp}")

# def get_all_users_list():
#     resp = supabase.table("users").select("id, name, parent_user_id").execute()
#     return resp.data or []

# def build_stakeholder_sets(project_id: int):
#     partners = supabase.table("partners").select("partner_user_id, partner_id").eq("project_id", project_id).execute().data or []
#     partner_user_ids = [p["partner_user_id"] for p in partners if p.get("partner_user_id") is not None]
#     partner_ids = [p["partner_id"] for p in partners]

#     subs = supabase.table("sub_partners").select("sub_partner_user_id, partner_id").in_("partner_id", partner_ids).execute().data or []
#     sub_user_ids = [s["sub_partner_user_id"] for s in subs if s.get("sub_partner_user_id") is not None]

#     stakeholder_ids = set(partner_user_ids) | set(sub_user_ids)

#     children = []
#     if stakeholder_ids:
#         children = supabase.table("users").select("id").in_("parent_user_id", list(stakeholder_ids)).execute().data or []
#     child_ids = set(c["id"] for c in children)

#     all_ids = list(stakeholder_ids | child_ids)
#     stakeholder_name_map = {}
#     if all_ids:
#         users = supabase.table("users").select("id, name").in_("id", all_ids).execute().data or []
#         stakeholder_name_map = {u["id"]: u["name"] for u in users}

#     stakeholder_or_children_ids = stakeholder_ids | child_ids
#     return stakeholder_ids, stakeholder_or_children_ids, stakeholder_name_map

# def idx_of(seq, key, val, default=0):
#     for i, x in enumerate(seq):
#         if x.get(key) == val:
#             return i
#     return default

# # ===============================
# # SESSION STATE for dynamic Sources
# # ===============================
# if "sources" not in st.session_state:
#     st.session_state.sources = []  # each: {"user_id": None, "amount": 0.0, "is_partner": False}

# # ===============================
# # APP
# # ===============================
# def main():
#     st.title("Insert a Transaction")

#     # ---------------------------
#     # Project Selection
#     # ---------------------------
#     projects = supabase.table("projects").select("project_id, project_name").order("project_name").execute().data or []
#     if not projects:
#         st.warning("Create a project first.")
#         return

#     proj_map = {p["project_name"]: p["project_id"] for p in projects}
#     project_name = st.selectbox("Select Project", list(proj_map.keys()))
#     project_id = proj_map[project_name]

#     # ---------------------------
#     # Stakeholders & Users
#     # ---------------------------
#     all_users = get_all_users_list()  # [{'id','name','parent_user_id'}]
#     all_users_map = {u["id"]: u["name"] for u in all_users}

#     stakeholder_ids, stakeholder_or_children_ids, stakeholder_name_map = build_stakeholder_sets(project_id)

#     # Paid By — stakeholders or their children
#     paid_by_options = [u for u in all_users if u["id"] in stakeholder_or_children_ids]
#     if not paid_by_options:
#         st.error("No eligible 'Paid By' users (stakeholders or their children).")
#         st.stop()
#     paid_by_names = [u["name"] for u in paid_by_options]
#     paid_by_name = st.selectbox("Paid By (Stakeholder or Child)", paid_by_names)
#     paid_by_id = paid_by_options[paid_by_names.index(paid_by_name)]["id"]

#     # Paid To — exclude stakeholders and children of stakeholders
#     paid_to_candidates = [u for u in all_users if (u["id"] not in stakeholder_ids and (u["parent_user_id"] is None or u["parent_user_id"] not in stakeholder_ids))]
#     if not paid_to_candidates:
#         st.warning("No eligible 'Paid To' users (everyone is a stakeholder or their child).")
#     paid_to_names = [u["name"] for u in paid_to_candidates] if paid_to_candidates else ["— none —"]
#     paid_to_name = st.selectbox("Paid To (Non-stakeholder and not a child of stakeholder)", paid_to_names)
#     paid_to_id = None if not paid_to_candidates else paid_to_candidates[paid_to_names.index(paid_to_name)]["id"]

#     # Payment Via — ANY user (OPTIONAL)
#     # Add a "— none —" option to allow leaving this blank (stored as NULL)
#     paid_via_options = ["— none —"] + [u["name"] for u in all_users]
#     paid_via_selection = st.selectbox("Payment Via (account/card/UPI used) — optional", paid_via_options)
#     if paid_via_selection == "— none —":
#         paid_via_id = None
#     else:
#         # map name back to id (first occurrence)
#         idx = paid_via_options.index(paid_via_selection) - 1  # -1 because of the prefixed none option
#         paid_via_id = all_users[idx]["id"]

#     # ---------------------------
#     # Transaction Core Fields
#     # ---------------------------
#     txn_date = st.date_input("Transaction Date", date.today())
#     txn_type = st.selectbox("Transaction Type", ["investment", "expense"])
#     amount = st.number_input("Total Amount", min_value=0.0, format="%.2f")
#     mode = st.selectbox("Mode of Payment", ["cash", "UPI", "cheque", "netbanking"])
#     purpose = st.text_area("Purpose")

#     st.markdown("---")
#     st.subheader("Select / Add Bank Accounts")

#     # ---------------------------
#     # Sender (Paid By) account
#     # ---------------------------
#     st.markdown("**Sender (Paid By) account**")
#     paid_by_accounts = fetch_bank_accounts_for_user(paid_by_id)
#     pb_options = [format_account_label(a) for a in paid_by_accounts]
#     PB_ADD_NEW = "+ Add new account"
#     pb_options_display = pb_options + [PB_ADD_NEW] if pb_options else [PB_ADD_NEW]

#     selected_pb_label = st.selectbox("Choose sender account", pb_options_display, key="pb_account_select")
#     selected_pb_account = None
#     if selected_pb_label == PB_ADD_NEW:
#         with st.expander("➕ Add Sender Bank Account"):
#             new_bank = st.selectbox("Bank", BANK_NAME_OPTIONS, key="pb_new_bank")
#             new_acc_no = st.text_input("Account Number", key="pb_new_acc_no")
#             if st.button("Save & use sender account", key="pb_save"):
#                 if not new_acc_no or not new_bank:
#                     st.warning("Provide bank and account number.")
#                 else:
#                     try:
#                         new_row = add_bank_account(paid_by_id, new_bank, new_acc_no)
#                         st.success("Sender account added.")
#                         selected_pb_account = new_row
#                     except Exception as e:
#                         st.error(f"Could not add account: {e}")
#     else:
#         if pb_options:
#             idx = pb_options_display.index(selected_pb_label)
#             if idx < len(paid_by_accounts):
#                 selected_pb_account = paid_by_accounts[idx]

#     # ---------------------------
#     # Receiver (Paid To) account
#     # ---------------------------
#     st.markdown("**Receiver (Paid To) account**")
#     paid_to_accounts = fetch_bank_accounts_for_user(paid_to_id) if paid_to_id else []
#     pt_options = [format_account_label(a) for a in paid_to_accounts]
#     PT_ADD_NEW = "+ Add new account"
#     pt_options_display = pt_options + [PT_ADD_NEW] if pt_options else [PT_ADD_NEW]

#     selected_pt_label = st.selectbox("Choose receiver account", pt_options_display, key="pt_account_select")
#     selected_pt_account = None
#     if selected_pt_label == PT_ADD_NEW:
#         with st.expander("➕ Add Receiver Bank Account"):
#             new_bank = st.selectbox("Bank", BANK_NAME_OPTIONS, key="pt_new_bank")
#             new_acc_no = st.text_input("Account Number", key="pt_new_acc_no")
#             if st.button("Save & use receiver account", key="pt_save"):
#                 if not new_acc_no or not new_bank or not paid_to_id:
#                     st.warning("Provide bank, account number, and select a valid receiver.")
#                 else:
#                     try:
#                         new_row = add_bank_account(paid_to_id, new_bank, new_acc_no)
#                         st.success("Receiver account added.")
#                         selected_pt_account = new_row
#                     except Exception as e:
#                         st.error(f"Could not add account: {e}")
#     else:
#         if pt_options:
#             idx = pt_options_display.index(selected_pt_label)
#             if idx < len(paid_to_accounts):
#                 selected_pt_account = paid_to_accounts[idx]

#     st.markdown("---")
#     st.subheader("Mode-specific details")

#     # ---------------------------
#     # Mode-specific Fields
#     # ---------------------------
#     mode_data = {}
#     if mode == "UPI":
#         mode_data["reference_number"] = st.text_input("UPI Reference Number")
#         mode_data["app_used"] = st.text_input("UPI App Used")
#     elif mode == "cheque":
#         pre_bank = selected_pb_account.get("bank_name") if selected_pb_account else None
#         mode_data["cheque_number"] = st.text_input("Cheque Number")
#         mode_data["bank_name"] = st.selectbox(
#             "Bank Name", BANK_NAME_OPTIONS,
#             index=BANK_NAME_OPTIONS.index(pre_bank) if pre_bank in BANK_NAME_OPTIONS else 0
#         )
#     elif mode == "netbanking":
#         pre_receiver_bank = selected_pt_account.get("bank_name") if selected_pt_account else None
#         pre_receiver_acc = selected_pt_account.get("account_number") if selected_pt_account else ""
#         pre_sender_bank = selected_pb_account.get("bank_name") if selected_pb_account else None
#         pre_sender_acc = selected_pb_account.get("account_number") if selected_pb_account else ""
#         mode_data["receiver_bank"] = st.selectbox(
#             "Receiver Bank Name", BANK_NAME_OPTIONS,
#             index=BANK_NAME_OPTIONS.index(pre_receiver_bank) if pre_receiver_bank in BANK_NAME_OPTIONS else 0
#         )
#         mode_data["receiver_bank_ifsc"] = st.text_input("Receiver Bank IFSC Code", value="")
#         mode_data["receiver_account_number"] = st.text_input("Receiver Account Number", value=pre_receiver_acc)
#         mode_data["sender_bank"] = st.selectbox(
#             "Sender Bank Name", BANK_NAME_OPTIONS,
#             index=BANK_NAME_OPTIONS.index(pre_sender_bank) if pre_sender_bank in BANK_NAME_OPTIONS else 0
#         )
#         mode_data["sender_account_number"] = st.text_input("Sender Account Number", value=pre_sender_acc)

#     # ---------------------------
#     # Sources of Funds (no hard equality)
#     # ---------------------------
#     st.markdown("---")
#     st.subheader("Sources of Funds")

#     if st.button("➕ Add Source"):
#         st.session_state.sources.append({"user_id": None, "amount": 0.0, "is_partner": False})

#     remove_idxs = []
#     for i, row in enumerate(st.session_state.sources):
#         with st.expander(f"Source {i+1}", expanded=True):
#             c1, c2, c3 = st.columns([1.2, 0.8, 0.5])
#             with c1:
#                 names = [u["name"] for u in all_users]
#                 # default to first user if not set yet, to avoid index errors
#                 current_idx = 0
#                 if row.get("user_id") is not None:
#                     for ix, u in enumerate(all_users):
#                         if u["id"] == row["user_id"]:
#                             current_idx = ix
#                             break
#                 name_choice = st.selectbox("User", names, index=current_idx, key=f"src_user_{i}")
#                 row["user_id"] = all_users[names.index(name_choice)]["id"]
#             with c2:
#                 row["amount"] = st.number_input("Amount", min_value=0.0, step=0.01, format="%.2f",
#                                                 value=float(row.get("amount", 0.0)), key=f"src_amt_{i}")
#             with c3:
#                 row["is_partner"] = (row["user_id"] in stakeholder_or_children_ids)
#                 st.checkbox("Is Partner?", value=row["is_partner"], key=f"src_is_partner_{i}", disabled=True)
#             if st.button("Remove", key=f"rm_src_{i}"):
#                 remove_idxs.append(i)
#     for idx in reversed(remove_idxs):
#         st.session_state.sources.pop(idx)

#     sources_total = sum(float(r.get("amount") or 0.0) for r in st.session_state.sources)
#     st.caption(f"Sources total: **₹{sources_total:,.2f}** / Transaction amount: **₹{amount:,.2f}**")

#     # If there is a gap, require a note
#     funding_note = ""
#     gap = float(amount or 0.0) - float(sources_total or 0.0)
#     if gap > 1e-6:
#         funding_note = st.text_area(
#             f"Explain the remaining ₹{gap:,.2f} (e.g., self-funded, prior savings, credit, etc.)",
#             placeholder="Add a brief note about how the remaining amount was covered"
#         )

#     # ---------------------------
#     # Proof Upload
#     # ---------------------------
#     st.subheader("Proof of Payment")
#     proof_file = st.file_uploader("Upload proof (PDF/JPEG)", type=["pdf", "jpg", "jpeg"])
#     proof_name = st.text_input("Proof File Name")
#     proof_desc = st.text_area("Proof Description")

#     # ---------------------------
#     # Submit
#     # ---------------------------
#     if st.button("Submit Transaction"):
#         errs = []
#         if amount <= 0:
#             errs.append("Amount must be greater than 0.")
#         if not paid_by_id:
#             errs.append("Select a valid 'Paid By' user.")

#         # Mode-specific required fields
#         if mode == "UPI" and not mode_data.get("reference_number"):
#             errs.append("UPI reference number is required.")
#         if mode == "cheque" and (not mode_data.get("cheque_number") or not mode_data.get("bank_name")):
#             errs.append("Cheque number and bank name are required.")

#         # Sources rules:
#         #  - allow empty or partial coverage
#         #  - do NOT allow sources to exceed amount
#         if sources_total - float(amount) > 1e-6:
#             errs.append(f"Sources total (₹{sources_total:,.2f}) cannot exceed transaction amount (₹{amount:,.2f}).")
#         #  - if partial, require a note
#         if float(amount) - sources_total > 1e-6 and not funding_note.strip():
#             errs.append("Please add a note explaining how the remaining amount was covered.")

#         if errs:
#             st.error("Please fix the following:\n\n- " + "\n- ".join(errs))
#             st.stop()

#         try:
#             # 1) Insert into transactions (paid_via may be None)
#             tx = insert("transactions", {
#                 "project_id": project_id,
#                 "transaction_type": txn_type,
#                 "paid_by": paid_by_id,
#                 "paid_to": paid_to_id,            # may be None
#                 "paid_via": paid_via_id,          # can be None (NULL in DB)
#                 "amount": float(amount),
#                 "transaction_date": txn_date.isoformat(),
#                 "mode": mode,
#                 "purpose": purpose or None,
#                 "funding_note": funding_note or None
#             })

#             if not tx.data:
#                 raise Exception(f"Transaction insert failed: {tx}")
#             transaction_id = tx.data[0]["transaction_id"]

#             # 2) Mode-specific detail
#             if mode == "UPI":
#                 insert("upi_payments", {"transaction_id": transaction_id, **mode_data})
#             elif mode == "cheque":
#                 insert("cheque_payments", {"transaction_id": transaction_id, **mode_data})
#             elif mode == "netbanking":
#                 insert("netbanking_payments", {"transaction_id": transaction_id, **mode_data})

#             # 3) Insert sources (if any rows present)
#             if st.session_state.sources:
#                 sources_payload = [{
#                     "transaction_id": transaction_id,
#                     "source_id": r["user_id"],
#                     "is_partner": bool(r["is_partner"]),
#                     "amount": float(r["amount"]),
#                 } for r in st.session_state.sources if r.get("user_id") is not None and float(r.get("amount") or 0) > 0]
#                 if sources_payload:
#                     supabase.table("transaction_sources").insert(sources_payload).execute()

#             # 4) Proof
#             if proof_file:
#                 encoded_data = base64.b64encode(proof_file.read()).decode("utf-8")
#                 insert("payment_proofs", {
#                     "transaction_id": transaction_id,
#                     "file_name": (proof_name or proof_file.name),
#                     "file_data": encoded_data,
#                     "description": proof_desc or None
#                 })

#             st.success("✅ Transaction recorded successfully (with sources, payment via, and funding note if applicable).")
#             st.toast("Saved!", icon="✅")
#             st.session_state.sources = []

#         except Exception as e:
#             st.error(f"❌ Error saving transaction: {e}")

# if __name__ == "__main__":
#     main()




import streamlit as st
from datetime import date
from supabase import create_client, Client
import base64

# ===============================
# CONFIG
# ===============================
st.set_page_config(page_title="Insert Transaction")

@st.cache_resource
def get_supabase() -> Client:
    url = "https://ogecahtzmpsznesragam.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZWNhaHR6bXBzem5lc3JhZ2FtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5MzE0NDEsImV4cCI6MjA2NTUwNzQ0MX0.SVPUtm2-bhTRjc0XZnUII8pHt2Jc435Mr_fsEkmKpvs"
    return create_client(url, key)

supabase = get_supabase()


BANK_NAME_OPTIONS = [
    "State Bank of India (SBI)", "Punjab National Bank (PNB)", "HDFC Bank", "ICICI Bank",
    "Axis Bank", "Kotak Mahindra Bank", "Bank of Baroda", "Union Bank of India",
    "Canara Bank", "IndusInd Bank", "Yes Bank", "IDFC FIRST Bank",
    "Central Bank of India", "Indian Bank", "Bank of India", "AU Bank"
]

# ===============================
# HELPERS
# ===============================
def insert(table: str, data: dict):
    return supabase.table(table).insert(data).execute()

def fetch_bank_accounts_for_user(user_id: int):
    if user_id is None:
        return []
    resp = supabase.table("bank_accounts").select("id, bank_name, account_number").eq("user_id", user_id).execute()
    return resp.data or []

def format_account_label(acc: dict):
    return f"{acc.get('bank_name','')} — {acc.get('account_number','')}"

def add_bank_account(user_id: int, bank_name: str, account_number: str):
    resp = insert("bank_accounts", {"user_id": user_id, "bank_name": bank_name, "account_number": account_number})
    if resp.data:
        return resp.data[0]
    else:
        raise Exception(f"Failed to add bank account: {resp}")

def get_all_users_list():
    resp = supabase.table("users").select("id, name, parent_user_id").execute()
    return resp.data or []

def build_stakeholder_sets(project_id: int):
    partners = supabase.table("partners").select("partner_user_id, partner_id").eq("project_id", project_id).execute().data or []
    partner_user_ids = [p["partner_user_id"] for p in partners if p.get("partner_user_id") is not None]
    partner_ids = [p["partner_id"] for p in partners]

    subs = supabase.table("sub_partners").select("sub_partner_user_id, partner_id").in_("partner_id", partner_ids).execute().data or []
    sub_user_ids = [s["sub_partner_user_id"] for s in subs if s.get("sub_partner_user_id") is not None]

    stakeholder_ids = set(partner_user_ids) | set(sub_user_ids)

    children = []
    if stakeholder_ids:
        children = supabase.table("users").select("id").in_("parent_user_id", list(stakeholder_ids)).execute().data or []
    child_ids = set(c["id"] for c in children)

    all_ids = list(stakeholder_ids | child_ids)
    stakeholder_name_map = {}
    if all_ids:
        users = supabase.table("users").select("id, name").in_("id", all_ids).execute().data or []
        stakeholder_name_map = {u["id"]: u["name"] for u in users}

    stakeholder_or_children_ids = stakeholder_ids | child_ids
    return stakeholder_ids, stakeholder_or_children_ids, stakeholder_name_map

def idx_of(seq, key, val, default=0):
    for i, x in enumerate(seq):
        if x.get(key) == val:
            return i
    return default

# ===============================
# SESSION STATE for dynamic Sources
# ===============================
if "sources" not in st.session_state:
    st.session_state.sources = []  # each: {"user_id": None, "amount": 0.0, "is_partner": False}

# ===============================
# APP
# ===============================
def main():
    st.title("Insert a Transaction")

    # ---------------------------
    # Project Selection
    # ---------------------------
    projects = supabase.table("projects").select("project_id, project_name").order("project_name").execute().data or []
    if not projects:
        st.warning("Create a project first.")
        return

    proj_map = {p["project_name"]: p["project_id"] for p in projects}
    project_name = st.selectbox("Select Project", list(proj_map.keys()))
    project_id = proj_map[project_name]

    # ---------------------------
    # Stakeholders & Users
    # ---------------------------
    all_users = get_all_users_list()  # [{'id','name','parent_user_id'}]
    all_users_map = {u["id"]: u["name"] for u in all_users}

    stakeholder_ids, stakeholder_or_children_ids, stakeholder_name_map = build_stakeholder_sets(project_id)

    # Paid By — stakeholders or their children
    paid_by_options = [u for u in all_users if u["id"] in stakeholder_or_children_ids]
    if not paid_by_options:
        st.error("No eligible 'Paid By' users (stakeholders or their children).")
        st.stop()
    paid_by_names = [u["name"] for u in paid_by_options]
    paid_by_name = st.selectbox("Paid By (Stakeholder or Child)", paid_by_names)
    paid_by_id = paid_by_options[paid_by_names.index(paid_by_name)]["id"]

    # Paid To — exclude stakeholders and children of stakeholders
    paid_to_candidates = [u for u in all_users if (u["id"] not in stakeholder_ids and (u["parent_user_id"] is None or u["parent_user_id"] not in stakeholder_ids))]
    if not paid_to_candidates:
        st.warning("No eligible 'Paid To' users (everyone is a stakeholder or their child).")
    paid_to_names = [u["name"] for u in paid_to_candidates] if paid_to_candidates else ["— none —"]
    paid_to_name = st.selectbox("Paid To (Non-stakeholder and not a child of stakeholder)", paid_to_names)
    paid_to_id = None if not paid_to_candidates else paid_to_candidates[paid_to_names.index(paid_to_name)]["id"]

    # Payment Via — ANY user (OPTIONAL)
    paid_via_options = ["— none —"] + [u["name"] for u in all_users]
    paid_via_selection = st.selectbox("Payment Via (account/card/UPI used) — optional", paid_via_options)
    if paid_via_selection == "— none —":
        paid_via_id = None
    else:
        idx = paid_via_options.index(paid_via_selection) - 1  # -1 because of the prefixed none option
        paid_via_id = all_users[idx]["id"]

    # ---------------------------
    # Transaction Core Fields
    # ---------------------------
    txn_date = st.date_input("Transaction Date", date.today())
    txn_type = st.selectbox("Transaction Type", ["investment", "expense"])
    amount = st.number_input("Total Amount", min_value=0.0, format="%.2f")
    mode = st.selectbox("Mode of Payment", ["cash", "UPI", "cheque", "netbanking"])
    purpose = st.text_area("Purpose")

    # initialize these so branch code can safely use them
    selected_pb_account = None
    selected_pt_account = None

    st.markdown("---")
    st.subheader("Mode-specific details")

    # ---------------------------
    # Mode-specific Fields
    # ---------------------------
    mode_data = {}
    if mode == "UPI":
        mode_data["reference_number"] = st.text_input("UPI Reference Number")
        mode_data["app_used"] = st.text_input("UPI App Used")

    elif mode == "cheque":
        # Without showing bank-account selection UI, we cannot prefill from selected accounts.
        # Leave prefill empty so user selects cheque bank manually.
        mode_data["cheque_number"] = st.text_input("Cheque Number")
        mode_data["bank_name"] = st.selectbox(
            "Bank Name", BANK_NAME_OPTIONS,
            index=0
        )

# ---------------------------
# NETBANKING: show only Select / Add Bank Accounts UI
# Replace your current `elif mode == "netbanking":` section with this block
# ---------------------------

    elif mode == "netbanking":
        st.markdown("**Netbanking — select or add bank accounts**")

        # --- Sender (Paid By) account selection / add ---
        st.markdown("**Sender (Paid By) account**")
        paid_by_accounts = fetch_bank_accounts_for_user(paid_by_id)
        pb_options = [format_account_label(a) for a in paid_by_accounts]
        PB_ADD_NEW = "+ Add new account"
        pb_display_options = pb_options + [PB_ADD_NEW] if pb_options else [PB_ADD_NEW]

        selected_pb_label = st.selectbox("Choose sender account", pb_display_options, key="pb_account_select")
        selected_pb_account = None

        # If user chose to add new account, show bank dropdown (from BANK_NAME_OPTIONS) + acc no + save button
        if selected_pb_label == PB_ADD_NEW:
            new_pb_bank = st.selectbox("Bank (sender)", BANK_NAME_OPTIONS, key="pb_new_bank")
            new_pb_acc_no = st.text_input("Account number (sender)", key="pb_new_acc_no")
            if st.button("Save & use sender account", key="pb_save"):
                if not new_pb_bank.strip() or not new_pb_acc_no.strip():
                    st.warning("Provide both bank name and account number to add.")
                else:
                    try:
                        new_row = add_bank_account(paid_by_id, new_pb_bank.strip(), new_pb_acc_no.strip())
                        st.success("Sender account added and selected.")
                        selected_pb_account = new_row
                        # update the label variable so downstream code can pick values from selected_pb_account
                        selected_pb_label = format_account_label(new_row)
                    except Exception as e:
                        st.error(f"Could not add sender account: {e}")
        else:
            # user picked an existing saved account label => find the account dict
            if pb_options:
                idx = pb_display_options.index(selected_pb_label)
                if idx < len(paid_by_accounts):
                    selected_pb_account = paid_by_accounts[idx]

        # --- Receiver (Paid To) account selection / add ---
        st.markdown("**Receiver (Paid To) account**")
        paid_to_accounts = fetch_bank_accounts_for_user(paid_to_id) if paid_to_id else []
        pt_options = [format_account_label(a) for a in paid_to_accounts]
        PT_ADD_NEW = "+ Add new account"
        pt_display_options = pt_options + [PT_ADD_NEW] if pt_options else [PT_ADD_NEW]

        selected_pt_label = st.selectbox("Choose receiver account", pt_display_options, key="pt_account_select")
        selected_pt_account = None

        if selected_pt_label == PT_ADD_NEW:
            new_pt_bank = st.selectbox("Bank (receiver)", BANK_NAME_OPTIONS, key="pt_new_bank")
            new_pt_acc_no = st.text_input("Account number (receiver)", key="pt_new_acc_no")
            if st.button("Save & use receiver account", key="pt_save"):
                if not new_pt_bank.strip() or not new_pt_acc_no.strip() or not paid_to_id:
                    st.warning("Provide bank, account number, and select a valid receiver.")
                else:
                    try:
                        new_row = add_bank_account(paid_to_id, new_pt_bank.strip(), new_pt_acc_no.strip())
                        st.success("Receiver account added and selected.")
                        selected_pt_account = new_row
                        selected_pt_label = format_account_label(new_row)
                    except Exception as e:
                        st.error(f"Could not add receiver account: {e}")
        else:
            if pt_options:
                idx = pt_display_options.index(selected_pt_label)
                if idx < len(paid_to_accounts):
                    selected_pt_account = paid_to_accounts[idx]

        # --- Now populate mode_data from selected accounts (keeps later DB inserts same) ---
        mode_data["sender_bank"] = selected_pb_account.get("bank_name") if selected_pb_account else None
        mode_data["sender_account_number"] = selected_pb_account.get("account_number") if selected_pb_account else None
        mode_data["receiver_bank"] = selected_pt_account.get("bank_name") if selected_pt_account else None
        mode_data["receiver_account_number"] = selected_pt_account.get("account_number") if selected_pt_account else None

        # Optional: show a small hint if receiver is missing
        if paid_to_id is None:
            st.warning("No 'Paid To' (receiver) selected. Please select a receiver in the Paid To field above to pick/add bank accounts.")

    st.markdown("---")
    st.subheader("Sources of Funds")

    if st.button("➕ Add Source"):
        st.session_state.sources.append({"user_id": None, "amount": 0.0, "is_partner": False})

    remove_idxs = []
    for i, row in enumerate(st.session_state.sources):
        with st.expander(f"Source {i+1}", expanded=True):
            c1, c2, c3 = st.columns([1.2, 0.8, 0.5])
            with c1:
                names = [u["name"] for u in all_users]
                # default to first user if not set yet, to avoid index errors
                current_idx = 0
                if row.get("user_id") is not None:
                    for ix, u in enumerate(all_users):
                        if u["id"] == row["user_id"]:
                            current_idx = ix
                            break
                name_choice = st.selectbox("User", names, index=current_idx, key=f"src_user_{i}")
                row["user_id"] = all_users[names.index(name_choice)]["id"]
            with c2:
                row["amount"] = st.number_input("Amount", min_value=0.0, step=0.01, format="%.2f",
                                                value=float(row.get("amount", 0.0)), key=f"src_amt_{i}")
            with c3:
                row["is_partner"] = (row["user_id"] in stakeholder_or_children_ids)
                st.checkbox("Is Partner?", value=row["is_partner"], key=f"src_is_partner_{i}", disabled=True)
            if st.button("Remove", key=f"rm_src_{i}"):
                remove_idxs.append(i)
    for idx in reversed(remove_idxs):
        st.session_state.sources.pop(idx)

    sources_total = sum(float(r.get("amount") or 0.0) for r in st.session_state.sources)
    st.caption(f"Sources total: **₹{sources_total:,.2f}** / Transaction amount: **₹{amount:,.2f}**")

    # If there is a gap, require a note
    funding_note = ""
    gap = float(amount or 0.0) - float(sources_total or 0.0)
    if gap > 1e-6:
        funding_note = st.text_area(
            f"Explain the remaining ₹{gap:,.2f} (e.g., self-funded, prior savings, credit, etc.)",
            placeholder="Add a brief note about how the remaining amount was covered"
        )

    # ---------------------------
    # Proof Upload
    # ---------------------------
    st.subheader("Proof of Payment")
    proof_file = st.file_uploader("Upload proof (PDF/JPEG)", type=["pdf", "jpg", "jpeg"])
    proof_name = st.text_input("Proof File Name")
    proof_desc = st.text_area("Proof Description")

    # ---------------------------
    # Submit
    # ---------------------------
    if st.button("Submit Transaction"):
        errs = []
        if amount <= 0:
            errs.append("Amount must be greater than 0.")
        if not paid_by_id:
            errs.append("Select a valid 'Paid By' user.")

        # Mode-specific required fields
        if mode == "UPI" and not mode_data.get("reference_number"):
            errs.append("UPI reference number is required.")
        if mode == "cheque" and (not mode_data.get("cheque_number") or not mode_data.get("bank_name")):
            errs.append("Cheque number and bank name are required.")
        if mode == "netbanking":
            # simple checks for netbanking required fields
            if not mode_data.get("receiver_account_number"):
                errs.append("Receiver account number is required for netbanking.")
            if not mode_data.get("sender_account_number"):
                errs.append("Sender account number is required for netbanking.")

        # Sources rules:
        #  - allow empty or partial coverage
        #  - do NOT allow sources to exceed amount
        if sources_total - float(amount) > 1e-6:
            errs.append(f"Sources total (₹{sources_total:,.2f}) cannot exceed transaction amount (₹{amount:,.2f}).")
        #  - if partial, require a note
        if float(amount) - sources_total > 1e-6 and not funding_note.strip():
            errs.append("Please add a note explaining how the remaining amount was covered.")

        if errs:
            st.error("Please fix the following:\n\n- " + "\n- ".join(errs))
            st.stop()

        try:
            # 1) Insert into transactions (paid_via may be None)
            tx = insert("transactions", {
                "project_id": project_id,
                "transaction_type": txn_type,
                "paid_by": paid_by_id,
                "paid_to": paid_to_id,            # may be None
                "paid_via": paid_via_id,          # can be None (NULL in DB)
                "amount": float(amount),
                "transaction_date": txn_date.isoformat(),
                "mode": mode,
                "purpose": purpose or None,
                "funding_note": funding_note or None
            })

            if not tx.data:
                raise Exception(f"Transaction insert failed: {tx}")
            transaction_id = tx.data[0]["transaction_id"]

            # 2) Mode-specific detail
            if mode == "UPI":
                insert("upi_payments", {"transaction_id": transaction_id, **mode_data})
            elif mode == "cheque":
                insert("cheque_payments", {"transaction_id": transaction_id, **mode_data})
            elif mode == "netbanking":
                insert("netbanking_payments", {"transaction_id": transaction_id, **mode_data})

            # 3) Insert sources (if any rows present)
            if st.session_state.sources:
                sources_payload = [{
                    "transaction_id": transaction_id,
                    "source_id": r["user_id"],
                    "is_partner": bool(r["is_partner"]),
                    "amount": float(r["amount"]),
                } for r in st.session_state.sources if r.get("user_id") is not None and float(r.get("amount") or 0) > 0]
                if sources_payload:
                    supabase.table("transaction_sources").insert(sources_payload).execute()

            # 4) Proof
            if proof_file:
                encoded_data = base64.b64encode(proof_file.read()).decode("utf-8")
                insert("payment_proofs", {
                    "transaction_id": transaction_id,
                    "file_name": (proof_name or proof_file.name),
                    "file_data": encoded_data,
                    "description": proof_desc or None
                })

            st.success("✅ Transaction recorded successfully (with sources, payment via, and funding note if applicable).")
            st.toast("Saved!", icon="✅")
            st.session_state.sources = []

        except Exception as e:
            st.error(f"❌ Error saving transaction: {e}")

if __name__ == "__main__":
    main()
