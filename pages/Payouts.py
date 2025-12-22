import streamlit as st
from datetime import date
from supabase import create_client, Client
import base64

# ---------------------------
# Page config + Supabase setup
# ---------------------------
st.set_page_config(page_title="Record Payout (Project Sale)")

@st.cache_resource
def get_supabase() -> Client:
    url = "https://ogecahtzmpsznesragam.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZWNhaHR6bXBzem5lc3JhZ2FtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5MzE0NDEsImV4cCI6MjA2NTUwNzQ0MX0.SVPUtm2-bhTRjc0XZnUII8pHt2Jc435Mr_fsEkmKpvs"
    return create_client(url, key)

supabase = get_supabase()

# ---------------------------
# Constants
# ---------------------------
BANK_NAME_OPTIONS = [
    "State Bank of India (SBI)", "Punjab National Bank (PNB)", "HDFC Bank", "ICICI Bank",
    "Axis Bank", "Kotak Mahindra Bank", "Bank of Baroda", "Union Bank of India",
    "Canara Bank", "IndusInd Bank", "Yes Bank", "IDFC FIRST Bank",
    "Central Bank of India", "Indian Bank", "Bank of India", "AU Bank"
]
MANUAL_ENTRY = "Other (enter manually)"

# ---------------------------
# Helpers
# ---------------------------
def insert(table: str, data: dict):
    return supabase.table(table).insert(data).execute()

def fetch_projects():
    r = supabase.table("projects").select("project_id, project_name").order("project_name").execute()
    return r.data or []

def build_stakeholders(project_id: int):
    """
    Return list of stakeholder users (partners + sub-partners) as dicts: {id, name}
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
    """Return list of bank-account dicts for a user (id, bank_name, account_number)."""
    if not user_id:
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
    resp = supabase.table("users").select("id, name, parent_user_id").order("name").execute()
    return resp.data or []

def build_stakeholder_sets(project_id: int):
    """
    Returns:
      stakeholder_ids (set of partner/sub ids),
      stakeholder_or_children_ids (stakeholders + their children),
      stakeholder_name_map {id: name}
    """
    partners = supabase.table("partners").select("partner_user_id, partner_id").eq("project_id", project_id).execute().data or []
    partner_user_ids = [p["partner_user_id"] for p in partners if p.get("partner_user_id") is not None]
    partner_ids = [p["partner_id"] for p in partners]

    subs = supabase.table("sub_partners").select("sub_partner_user_id, partner_id").in_("partner_id", partner_ids).execute().data or []
    sub_user_ids = [s["sub_partner_user_id"] for s in subs if s.get("sub_partner_user_id") is not None]

    stakeholder_ids = set(partner_user_ids) | set(sub_user_ids)

    # children of stakeholders
    child_ids = set()
    if stakeholder_ids:
        children = supabase.table("users").select("id, name").in_("parent_user_id", list(stakeholder_ids)).execute().data or []
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

# ---------------------------
# Session state for dynamic distributions
# ---------------------------
if "payout_distributions" not in st.session_state:
    st.session_state.payout_distributions = []  # each: {"user_id": None, "amount": 0.0}

# ---------------------------
# Page UI
# ---------------------------
st.title("Record a Payout / Project Sale Installment")

# --- Project selection
projects = fetch_projects()
if not projects:
    st.warning("No projects found. Create a project first.")
    st.stop()

proj_map = {p["project_name"]: p["project_id"] for p in projects}
project_name = st.selectbox("Select Project", list(proj_map.keys()))
project_id = proj_map[project_name]

# --- Stakeholders & user lists
stakeholders = build_stakeholders(project_id)  # partners + sub-partners
if not stakeholders:
    st.info("No partners/sub-partners found for this project.")
    st.stop()

stakeholder_names = [u["name"] for u in stakeholders]
stakeholder_id_map = {u["name"]: u["id"] for u in stakeholders}

all_users = get_all_users_list()
all_user_names = [u["name"] for u in all_users]
all_user_id_map = {u["name"]: u["id"] for u in all_users}

# --- Payout core fields
col1, col2 = st.columns(2)
with col1:
    amount_received = st.number_input("Total Amount Received (₹)", min_value=0.0, format="%.2f", step=0.01)
    if amount_received:
        st.markdown(f"💰 Entered Investment: **₹{amount_received / 1_00_000:.2f} Lakhs**")
with col2:
    payout_date = st.date_input("Payout Date", value=date.today())

received_by_name = st.selectbox("Received By (Partner / Sub-partner)", stakeholder_names)
received_by_id = stakeholder_id_map[received_by_name]

mode = st.selectbox("Mode of Receipt", ["cash", "UPI", "cheque", "netbanking"])
remarks = st.text_area("Remarks (optional)")

# --- Mode-specific sections
mode_data = {}

if mode == "UPI":
    st.subheader("UPI Details")
    mode_data["reference_number"] = st.text_input("UPI Reference Number")
    mode_data["app_used"] = st.text_input("UPI App Used")

elif mode == "cheque":
    st.subheader("Cheque Details")
    mode_data["cheque_number"] = st.text_input("Cheque Number")
    mode_data["bank_name"] = st.selectbox("Bank Name", BANK_NAME_OPTIONS)

elif mode == "netbanking":
    st.subheader("Netbanking Details")
    # For payout netbanking we pre-fill receiver account from received_by user's bank accounts (like your insert txn code)
    receiver_accounts = fetch_bank_accounts_for_user(received_by_id)
    receiver_choices = [format_account_label(a) for a in receiver_accounts] + [MANUAL_ENTRY] if receiver_accounts else [MANUAL_ENTRY]
    receiver_choice = st.selectbox("Choose Receiver Account (pre-filled from received_by)", receiver_choices, key="payout_receiver_choice")

    if receiver_choice != MANUAL_ENTRY and receiver_accounts:
        idx = receiver_choices.index(receiver_choice)
        if idx < len(receiver_accounts):
            sel = receiver_accounts[idx]
            # prefill and let user edit (as in your insert txn code)
            mode_data["receiver_bank"] = st.selectbox("Receiver Bank", BANK_NAME_OPTIONS, index=(BANK_NAME_OPTIONS.index(sel["bank_name"]) if sel["bank_name"] in BANK_NAME_OPTIONS else 0))
            mode_data["receiver_account_number"] = st.text_input("Receiver Account Number", value=sel["account_number"])
        else:
            mode_data["receiver_bank"] = st.selectbox("Receiver Bank", BANK_NAME_OPTIONS)
            mode_data["receiver_account_number"] = st.text_input("Receiver Account Number")
    else:
        mode_data["receiver_bank"] = st.selectbox("Receiver Bank", BANK_NAME_OPTIONS)
        mode_data["receiver_account_number"] = st.text_input("Receiver Account Number")
    mode_data["receiver_bank_ifsc"] = st.text_input("Receiver Bank IFSC (optional)")

    # Sender: external payer — allow manual entry
    st.markdown("**Sender (Payer) details** — usually the buyer / external account")
    mode_data["sender_bank"] = st.selectbox("Sender Bank (if known)", [""] + BANK_NAME_OPTIONS)
    mode_data["sender_account_number"] = st.text_input("Sender Account Number (optional)")

# --- Optional proof upload
proof_file = st.file_uploader("Upload proof (PDF/JPEG)", type=["pdf", "jpg", "jpeg"])
proof_name = st.text_input("Proof File Name (optional)")
proof_desc = st.text_area("Proof Description (optional)")

st.markdown("---")
st.subheader("Distributions: who receives what part of this payout")

# --- Convenience: auto-fill by ownership % (optional) ---
if st.button("Auto-fill by ownership %"):
    # fetch ownership distribution logic from DB (partners + sub -> absolute %)
    # This code will attempt to compute ownership % same as earlier pages
    partners = supabase.table("partners").select("partner_id, partner_user_id, share_percentage").eq("project_id", project_id).execute().data or []
    partner_ids = [p["partner_id"] for p in partners]
    partner_meta = {p["partner_id"]: {"user_id": p["partner_user_id"], "share": float(p["share_percentage"] or 0)} for p in partners}
    subs = []
    if partner_ids:
        subs = supabase.table("sub_partners").select("partner_id, sub_partner_user_id, share_percentage").in_("partner_id", partner_ids).execute().data or []

    ownership_pct = {}
    for pid, meta in partner_meta.items():
        uid = meta["user_id"]
        if uid is not None:
            ownership_pct[uid] = ownership_pct.get(uid, 0.0) + meta["share"]

    for sp in subs:
        pid = sp["partner_id"]
        sub_uid = sp.get("sub_partner_user_id")
        rel = float(sp.get("share_percentage") or 0)
        if pid not in partner_meta or sub_uid is None:
            continue
        partner_uid = partner_meta[pid]["user_id"]
        p_share = partner_meta[pid]["share"]
        sub_abs = p_share * rel / 100.0
        ownership_pct[sub_uid] = ownership_pct.get(sub_uid, 0.0) + sub_abs
        if partner_uid is not None:
            ownership_pct[partner_uid] = ownership_pct.get(partner_uid, 0.0) - sub_abs

    # build distributions from ownership_pct — only include stakeholders with >0
    st.session_state.payout_distributions = []
    for uid, pct in ownership_pct.items():
        if pct <= 0:
            continue
        amt = round((pct / 100.0) * float(amount_received or 0.0), 2)
        st.session_state.payout_distributions.append({"user_id": uid, "amount": amt})

# --- Add distribution row
if st.button("➕ Add Distribution Row"):
    st.session_state.payout_distributions.append({"user_id": None, "amount": 0.0})

# Show dynamic list of distribution rows
remove_idxs = []
for i, row in enumerate(st.session_state.payout_distributions):
    with st.expander(f"Recipient {i+1}", expanded=True):
        c1, c2, c3 = st.columns([2, 1, 0.6])
        # Recipients dropdown: restrict to stakeholders (so money only assigned to partners/subs)
        with c1:
            names = [u["name"] for u in stakeholders]
            current_idx = 0
            if row.get("user_id") is not None:
                for ix, u in enumerate(stakeholders):
                    if u["id"] == row["user_id"]:
                        current_idx = ix
                        break
            name_choice = st.selectbox("Stakeholder", names, index=current_idx, key=f"dist_user_{i}")
            row["user_id"] = stakeholders[names.index(name_choice)]["id"]
        with c2:
            row["amount"] = st.number_input("Amount (₹)", min_value=0.0, step=0.01, format="%.2f", value=float(row.get("amount", 0.0)), key=f"dist_amt_{i}")
            st.markdown(f"💰 Entered Amount: **₹{row["amount"] / 1_00_000:.2f} Lakhs**")
        with c3:
            if st.button("Remove", key=f"rm_dist_{i}"):
                remove_idxs.append(i)
for idx in reversed(remove_idxs):
    st.session_state.payout_distributions.pop(idx)

# Validate distribution totals
dist_total = sum(float(d.get("amount") or 0.0) for d in st.session_state.payout_distributions)
st.caption(f"Distributions total: **₹{dist_total:,.2f}** / Amount received: **₹{amount_received:,.2f}**")

# show a clear badge about equality
tolerance = 0.005  # accept up to 0.5 paise difference
if abs(dist_total - float(amount_received or 0.0)) <= tolerance:
    st.success("Distributions sum ✅ matches the total amount received.")
else:
    st.error("Distributions sum does NOT match the total amount received. Fix before submitting.")

st.markdown("---")

# --- Submit payout
if st.button("Record Payout"):
    errors = []
    if amount_received <= 0:
        errors.append("Amount received must be greater than 0.")
    if not received_by_id:
        errors.append("Choose a valid 'Received By' stakeholder.")
    if len(st.session_state.payout_distributions) == 0:
        errors.append("Add at least one distribution row.")
    # distributions must sum exactly to amount_received
    if abs(dist_total - float(amount_received or 0.0)) > tolerance:
        errors.append("Sum of distribution amounts must equal the total amount received (fix distributions).")

    # mode-specific validations
    if mode == "UPI":
        if not (mode_data.get("reference_number") or "").strip():
            errors.append("UPI reference number is required.")
    if mode == "cheque":
        if not (mode_data.get("cheque_number") or "").strip():
            errors.append("Cheque number is required.")
        if not (mode_data.get("bank_name") or "").strip():
            errors.append("Cheque bank is required.")
    if mode == "netbanking":
        if not (mode_data.get("receiver_bank") or "").strip():
            errors.append("Receiver bank is required for netbanking.")
        if not (mode_data.get("receiver_account_number") or "").strip():
            errors.append("Receiver account number is required for netbanking.")

    if errors:
        st.error("Please fix the following before submit:\n\n- " + "\n- ".join(errors))
        st.stop()

    try:
        # 1) Insert into payouts
        ins = supabase.table("payouts").insert({
            "project_id": project_id,
            "received_by": int(received_by_id),
            "amount_received": float(amount_received),
            "payout_date": payout_date.isoformat(),
            "mode": mode,
            "remarks": (remarks or None)
        }).execute()

        if not ins.data:
            raise Exception(f"Payout insert failed: {ins}")
        payout_id = ins.data[0]["payout_id"]

        # 2) Insert distributions
        dist_payload = []
        for d in st.session_state.payout_distributions:
            uid = int(d.get("user_id"))
            amt = float(d.get("amount") or 0.0)
            if amt <= 0:
                continue
            dist_payload.append({"payout_id": payout_id, "user_id": uid, "amount": amt})
        if dist_payload:
            supabase.table("payout_distributions").insert(dist_payload).execute()

        # 3) Mode-specific table insert
        if mode == "UPI":
            supabase.table("upi_payouts").insert({
                "payout_id": payout_id,
                "reference_number": mode_data.get("reference_number"),
                "app_used": mode_data.get("app_used") or None
            }).execute()
        elif mode == "cheque":
            supabase.table("cheque_payouts").insert({
                "payout_id": payout_id,
                "cheque_number": mode_data.get("cheque_number"),
                "bank_name": mode_data.get("bank_name")
            }).execute()
        elif mode == "netbanking":
            supabase.table("netbanking_payouts").insert({
                "payout_id": payout_id,
                "receiver_bank": mode_data.get("receiver_bank") or None,
                "receiver_bank_ifsc": mode_data.get("receiver_bank_ifsc") or None,
                "receiver_account_number": mode_data.get("receiver_account_number") or None,
                "sender_bank": mode_data.get("sender_bank") or None,
                "sender_account_number": mode_data.get("sender_account_number") or None
            }).execute()
        # cash -> nothing to insert in mode tables

        # 4) Proof file (if any)
        if proof_file:
            encoded = base64.b64encode(proof_file.read()).decode("utf-8")
            supabase.table("payout_proofs").insert({
                "payout_id": payout_id,
                "file_name": (proof_name or proof_file.name),
                "file_data": encoded,
                "description": (proof_desc or None)
            }).execute()

        st.success("✅ Payout recorded successfully and distributions saved.")
        st.toast("Payout saved!", icon="✅")
        # clear distributions session state
        st.session_state.payout_distributions = []

    except Exception as e:
        st.error(f"❌ Failed to record payout: {e}")
