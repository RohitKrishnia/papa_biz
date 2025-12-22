"""
Edit Payouts Page
- Select a project -> list payouts
- Choose a payout -> load all payout data (mode-details, distributions, proofs)
- Edit any field: amount, date, received_by (stakeholder), mode-specific details, distributions
- Validations: distributions sum must equal amount_received (tolerance applied)
- On save: update payouts row, replace distributions, update mode-specific tables, update proofs
- On cancel: reload original data
"""

import streamlit as st
from datetime import date
from supabase import create_client, Client
import base64

# ------------------------------
# Config + Supabase client
# ------------------------------
st.set_page_config(page_title="View & Edit Payouts")

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
MANUAL_ENTRY = "Other (enter manually)"
TOLERANCE = 0.005  # acceptable rounding tolerance for rupees

# ------------------------------
# Helpers (DB interactions)
# ------------------------------
def fetch_projects():
    r = supabase.table("projects").select("project_id, project_name").order("project_name").execute()
    return r.data or []

def build_stakeholders(project_id: int):
    """Return list of dicts {id, name} for partners + sub-partners in given project."""
    partners = (supabase.table("partners").select("partner_id, partner_user_id")
                .eq("project_id", project_id).execute().data or [])
    partner_ids = [p["partner_id"] for p in partners]
    partner_user_ids = {p["partner_user_id"] for p in partners if p.get("partner_user_id") is not None}

    sub_user_ids = set()
    if partner_ids:
        subs = (supabase.table("sub_partners").select("sub_partner_user_id, partner_id")
                .in_("partner_id", partner_ids).execute().data or [])
        sub_user_ids = {s["sub_partner_user_id"] for s in subs if s.get("sub_partner_user_id") is not None}

    stakeholder_ids = list(partner_user_ids | sub_user_ids)
    if not stakeholder_ids:
        return []

    users = (supabase.table("users").select("id, name").in_("id", stakeholder_ids).order("name").execute().data or [])
    return users

def fetch_payouts_for_project(project_id: int):
    """Return list of payouts for project (basic fields)."""
    r = (supabase.table("payouts")
         .select("payout_id, amount_received, payout_date, received_by, mode, remarks, created_at")
         .eq("project_id", project_id)
         .order("payout_date", desc=True)
         .execute())
    return r.data or []

def fetch_payout_full(payout_id: int):
    """Fetch payout, distributions, mode-specific details, proofs."""
    # payout row
    p = supabase.table("payouts").select("*").eq("payout_id", payout_id).execute().data or []
    payout = p[0] if p else None

    # distributions
    d = supabase.table("payout_distributions").select("distribution_id, user_id, amount").eq("payout_id", payout_id).order("distribution_id").execute().data or []

    # mode tables
    upi = supabase.table("upi_payouts").select("*").eq("payout_id", payout_id).execute().data or []
    cheque = supabase.table("cheque_payouts").select("*").eq("payout_id", payout_id).execute().data or []
    netbank = supabase.table("netbanking_payouts").select("*").eq("payout_id", payout_id).execute().data or []

    # proofs
    proofs = supabase.table("payout_proofs").select("proof_id, file_name, description, created_at").eq("payout_id", payout_id).order("created_at", desc=True).execute().data or []

    return {
        "payout": payout,
        "distributions": d,
        "upi": upi[0] if upi else None,
        "cheque": cheque[0] if cheque else None,
        "netbank": netbank[0] if netbank else None,
        "proofs": proofs
    }

def fetch_bank_accounts_for_user(user_id: int):
    if not user_id:
        return []
    r = supabase.table("bank_accounts").select("id, bank_name, account_number").eq("user_id", user_id).order("bank_name").execute()
    return r.data or []

def delete_mode_rows_for_payout(payout_id: int):
    # remove any existing mode-details rows
    supabase.table("upi_payouts").delete().eq("payout_id", payout_id).execute()
    supabase.table("cheque_payouts").delete().eq("payout_id", payout_id).execute()
    supabase.table("netbanking_payouts").delete().eq("payout_id", payout_id).execute()

def replace_proofs(payout_id: int, uploaded_file):
    """
    If uploaded_file provided, delete existing proofs and insert the new one.
    (You can adapt to allow multiple proofs; current logic replaces.)
    """
    supabase.table("payout_proofs").delete().eq("payout_id", payout_id).execute()
    if uploaded_file:
        encoded = base64.b64encode(uploaded_file.read()).decode("utf-8")
        supabase.table("payout_proofs").insert({
            "payout_id": payout_id,
            "file_name": uploaded_file.name,
            "file_data": encoded,
            "description": None
        }).execute()

# ------------------------------
# Page UI: Project selection
# ------------------------------
st.title("View & Edit Payouts")

projects = fetch_projects()
if not projects:
    st.warning("No projects found.")
    st.stop()

proj_map = {p["project_name"]: p["project_id"] for p in projects}
project_name = st.selectbox("Project", list(proj_map.keys()))
project_id = proj_map[project_name]

# build stakeholders list for this project
stakeholders = build_stakeholders(project_id)
if not stakeholders:
    st.info("No partners/sub-partners found for this project.")
    st.stop()

# id -> name map (used for display)
stakeholder_map = {u["id"]: u["name"] for u in stakeholders}
# name -> id map (used for lookups)
stakeholder_id_map = {u["name"]: u["id"] for u in stakeholders}

# ------------------------------
# Show payouts list & choose one to edit
# ------------------------------
payouts = fetch_payouts_for_project(project_id)
if not payouts:
    st.info("No payouts recorded for this project yet.")
    st.stop()

# Present a friendly label: date — amount — received_by
labels = []
for p in payouts:
    rid = p.get("received_by")
    rname = stakeholder_map.get(rid, f"User {rid}") if rid else "Unknown"
    labels.append(f"{p.get('payout_date')} — ₹{float(p.get('amount_received') or 0):,.2f} — {rname} (id:{p.get('payout_id')})")

selected_label = st.selectbox("Select a payout to view / edit", labels)
selected_idx = labels.index(selected_label)
selected_payout = payouts[selected_idx]
selected_payout_id = selected_payout["payout_id"]

# Load full data for selected payout
full = fetch_payout_full(selected_payout_id)
payout_row = full["payout"]
distributions = full["distributions"]  # list of dicts
mode_upi = full["upi"]
mode_cheque = full["cheque"]
mode_netbank = full["netbank"]
existing_proofs = full["proofs"]

# ------------------------------
# Session state initialization for editing form
# ------------------------------
if "edit_state" not in st.session_state or st.session_state.get("edit_state", {}).get("payout_id") != selected_payout_id:
    # initialize edit_state from DB values
    st.session_state.edit_state = {
        "payout_id": selected_payout_id,
        "amount_received": float(payout_row.get("amount_received") or 0.0),
        "payout_date": payout_row.get("payout_date"),
        "received_by": int(payout_row.get("received_by")) if payout_row.get("received_by") is not None else None,
        "mode": payout_row.get("mode") or "cash",
        "remarks": payout_row.get("remarks") or "",
        # distributions as list of dicts
        "distributions": [{"distribution_id": d.get("distribution_id"), "user_id": d.get("user_id"), "amount": float(d.get("amount") or 0.0)} for d in distributions],
        # mode details prefill
        "mode_upi": {"reference_number": mode_upi.get("reference_number") if mode_upi else "", "app_used": mode_upi.get("app_used") if mode_upi else ""},
        "mode_cheque": {"cheque_number": mode_cheque.get("cheque_number") if mode_cheque else "", "bank_name": mode_cheque.get("bank_name") if mode_cheque else ""},
        "mode_netbank": {
            "receiver_bank": mode_netbank.get("receiver_bank") if mode_netbank else "",
            "receiver_bank_ifsc": mode_netbank.get("receiver_bank_ifsc") if mode_netbank else "",
            "receiver_account_number": mode_netbank.get("receiver_account_number") if mode_netbank else "",
            "sender_bank": mode_netbank.get("sender_bank") if mode_netbank else "",
            "sender_account_number": mode_netbank.get("sender_account_number") if mode_netbank else ""
        },
        # proof file placeholder (if user uploads new proof we will replace existing)
        "new_proof": None
    }

es = st.session_state.edit_state

# ------------------------------
# Editable form (left) + Details (right)
# ------------------------------
st.subheader("Edit Payout")

# Basic fields
c1, c2 = st.columns(2)
with c1:
    es["amount_received"] = st.number_input("Total Amount Received (₹)", min_value=0.0, format="%.2f", value=float(es["amount_received"]), key="edit_amount")
    st.markdown(f"💰 Entered Investment: **₹{es["amount_received"] / 1_00_000:.2f} Lakhs**")
with c2:
    # if payout_date stored as string, convert to date object for date_input
    try:
        default_date = date.fromisoformat(es["payout_date"]) if isinstance(es["payout_date"], str) else es["payout_date"]
    except Exception:
        default_date = date.today()
    new_date = st.date_input("Payout Date", value=default_date, key="edit_date")
    es["payout_date"] = new_date.isoformat()

# Received by (stakeholder dropdown)
received_by_name = stakeholder_map.get(es["received_by"]) if es.get("received_by") else None
received_by_name = st.selectbox("Received By (Partner / Sub-partner)", [u["name"] for u in stakeholders], index=[u["id"] for u in stakeholders].index(es["received_by"]) if es.get("received_by") else 0)
es["received_by"] = stakeholder_id_map[received_by_name] if (received_by_name := received_by_name) else es["received_by"]

# Mode and remarks
es["mode"] = st.selectbox("Mode", ["cash", "UPI", "cheque", "netbanking"], index=["cash", "UPI", "cheque", "netbanking"].index(es.get("mode") or "cash"))
es["remarks"] = st.text_area("Remarks", value=es.get("remarks") or "")

st.markdown("---")
st.subheader("Mode-specific details")

# UPI
if es["mode"] == "UPI":
    es["mode_upi"]["reference_number"] = st.text_input("UPI Reference Number", value=es["mode_upi"].get("reference_number",""))
    es["mode_upi"]["app_used"] = st.text_input("UPI App Used (optional)", value=es["mode_upi"].get("app_used",""))

# Cheque
elif es["mode"] == "cheque":
    es["mode_cheque"]["cheque_number"] = st.text_input("Cheque Number", value=es["mode_cheque"].get("cheque_number",""))
    # attempt to default bank_index if existing bank present
    bank_default_idx = 0
    if es["mode_cheque"].get("bank_name") in BANK_NAME_OPTIONS:
        bank_default_idx = BANK_NAME_OPTIONS.index(es["mode_cheque"].get("bank_name"))
    es["mode_cheque"]["bank_name"] = st.selectbox("Bank Name", BANK_NAME_OPTIONS, index=bank_default_idx)

# Netbanking
elif es["mode"] == "netbanking":
    # For receiver (prefill from received_by's bank accounts)
    receiver_accounts = fetch_bank_accounts_for_user(es["received_by"])
    receiver_choices = [format_account_label(a) for a in receiver_accounts] + [MANUAL_ENTRY] if receiver_accounts else [MANUAL_ENTRY]
    # try to set default to existing receiver_bank/account if present
    default_receiver_idx = 0
    if es["mode_netbank"].get("receiver_bank") and es["mode_netbank"].get("receiver_account_number"):
        # if matches one of accounts, choose it
        for i,a in enumerate(receiver_accounts):
            if a.get("bank_name") == es["mode_netbank"].get("receiver_bank") and a.get("account_number") == es["mode_netbank"].get("receiver_account_number"):
                default_receiver_idx = i
                break
    receiver_choice = st.selectbox("Choose Receiver Account", receiver_choices, index=default_receiver_idx, key="edit_payout_receiver_choice")
    if receiver_choice != MANUAL_ENTRY and receiver_accounts:
        idx = receiver_choices.index(receiver_choice)
        if idx < len(receiver_accounts):
            sel = receiver_accounts[idx]
            es["mode_netbank"]["receiver_bank"] = st.selectbox("Receiver Bank", BANK_NAME_OPTIONS, index=(BANK_NAME_OPTIONS.index(sel["bank_name"]) if sel["bank_name"] in BANK_NAME_OPTIONS else 0))
            es["mode_netbank"]["receiver_account_number"] = st.text_input("Receiver Account Number", value=sel["account_number"])
        else:
            es["mode_netbank"]["receiver_bank"] = st.selectbox("Receiver Bank", BANK_NAME_OPTIONS)
            es["mode_netbank"]["receiver_account_number"] = st.text_input("Receiver Account Number")
    else:
        es["mode_netbank"]["receiver_bank"] = st.selectbox("Receiver Bank", BANK_NAME_OPTIONS, index=(BANK_NAME_OPTIONS.index(es["mode_netbank"].get("receiver_bank")) if es["mode_netbank"].get("receiver_bank") in BANK_NAME_OPTIONS else 0))
        es["mode_netbank"]["receiver_account_number"] = st.text_input("Receiver Account Number", value=es["mode_netbank"].get("receiver_account_number",""))
    es["mode_netbank"]["receiver_bank_ifsc"] = st.text_input("Receiver Bank IFSC (optional)", value=es["mode_netbank"].get("receiver_bank_ifsc",""))

    # Sender info manual
    es["mode_netbank"]["sender_bank"] = st.selectbox("Sender Bank (optional)", [""] + BANK_NAME_OPTIONS, index=(BANK_NAME_OPTIONS.index(es["mode_netbank"].get("sender_bank"))+1 if es["mode_netbank"].get("sender_bank") in BANK_NAME_OPTIONS else 0))
    es["mode_netbank"]["sender_account_number"] = st.text_input("Sender Account Number (optional)", value=es["mode_netbank"].get("sender_account_number",""))

st.markdown("---")
st.subheader("Distributions (how payout was split)")

# Ensure distributions in session from edit state
if "edit_distributions" not in st.session_state or st.session_state.get("edit_state", {}).get("payout_id") != selected_payout_id:
    st.session_state.edit_distributions = list(es["distributions"])

# Buttons: add row / auto-fill by ownership %
if st.button("➕ Add Distribution Row", key="add_dist_edit"):
    st.session_state.edit_distributions.append({"distribution_id": None, "user_id": None, "amount": 0.0})

if st.button("Auto-fill by ownership %", key="auto_fill_edit"):
    # compute ownership_pct similarly to other pages and fill distributions
    partners = supabase.table("partners").select("partner_id, partner_user_id, share_percentage").eq("project_id", project_id).execute().data or []
    partner_ids = [p["partner_id"] for p in partners]
    partner_meta = {p["partner_id"]: {"user_id": p["partner_user_id"], "share": float(p["share_percentage"] or 0)} for p in partners}
    subs = []
    if partner_ids:
        subs = supabase.table("sub_partners").select("partner_id, sub_partner_user_id, share_percentage").in_("partner_id", partner_ids).execute().data or []

    ownership_pct = {}
    for pid, meta in partner_meta.items():
        uid = meta["user_id"]
        if uid:
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

    st.session_state.edit_distributions = []
    for uid,pct in ownership_pct.items():
        if pct <= 0:
            continue
        amt = round((pct/100.0)*float(es["amount_received"] or 0.0), 2)
        st.session_state.edit_distributions.append({"distribution_id": None, "user_id": uid, "amount": amt})

# Render dynamic distribution rows
remove_idxs = []
for i, row in enumerate(st.session_state.edit_distributions):
    with st.expander(f"Recipient {i+1}", expanded=True):
        c1, c2, c3 = st.columns([2,1,0.6])
        # recipient dropdown
        names = [u["name"] for u in stakeholders]
        default_idx = 0
        if row.get("user_id") is not None:
            for ix,u in enumerate(stakeholders):
                if u["id"] == row["user_id"]:
                    default_idx = ix
                    break
        sel_name = st.selectbox("Stakeholder", names, index=default_idx, key=f"edit_dist_user_{i}")
        row["user_id"] = stakeholder_id_map[sel_name]
        # amount
        row["amount"] = st.number_input("Amount (₹)", min_value=0.0, step=0.01, format="%.2f", value=float(row.get("amount") or 0.0), key=f"edit_dist_amt_{i}")
        # remove button
        if st.button("Remove", key=f"edit_rm_dist_{i}"):
            remove_idxs.append(i)
for idx in reversed(remove_idxs):
    st.session_state.edit_distributions.pop(idx)

# distribution total & validation badge
dist_total = sum(float(d.get("amount") or 0.0) for d in st.session_state.edit_distributions)
st.caption(f"Distributions total: **₹{dist_total:,.2f}** / Amount received: **₹{float(es['amount_received']):,.2f}**")
if abs(dist_total - float(es["amount_received"] or 0.0)) <= TOLERANCE:
    st.success("Distributions sum ✅ matches the total amount received.")
else:
    st.error("Distributions sum does NOT match the total amount received. Fix before saving.")

st.markdown("---")
st.subheader("Proofs")
# show existing proofs (metadata)
if existing_proofs:
    st.write("Existing proof files (will be replaced if you upload a new one):")
    for pf in existing_proofs:
        st.write(f"- {pf.get('file_name')} — {pf.get('created_at')} — {pf.get('description') or ''}")
else:
    st.info("No proof files stored for this payout.")

# allow uploading a new proof to replace existing
new_proof = st.file_uploader("Upload new proof to replace existing (optional)", type=["pdf","jpg","jpeg"], key="edit_payout_proof")
es["new_proof"] = new_proof

# ------------------------------
# Action buttons: Save, Reload original
# ------------------------------
col_save, col_reload, col_delete = st.columns([1,1,1])
with col_save:
    if st.button("Save Changes"):
        # validate before saving
        errors = []
        if float(es["amount_received"] or 0.0) <= 0:
            errors.append("Amount received must be > 0.")
        if not es.get("received_by"):
            errors.append("Received by must be a stakeholder.")
        if len(st.session_state.edit_distributions) == 0:
            errors.append("Add at least one distribution row.")
        if abs(dist_total - float(es["amount_received"] or 0.0)) > TOLERANCE:
            errors.append("Distributions sum must equal amount_received before saving.")
        # mode-specific checks
        if es["mode"] == "UPI" and not (es["mode_upi"].get("reference_number") or "").strip():
            errors.append("UPI reference number required.")
        if es["mode"] == "cheque":
            if not (es["mode_cheque"].get("cheque_number") or "").strip():
                errors.append("Cheque number required.")
            if not (es["mode_cheque"].get("bank_name") or "").strip():
                errors.append("Cheque bank required.")
        if es["mode"] == "netbanking":
            if not (es["mode_netbank"].get("receiver_bank") or "").strip():
                errors.append("Receiver bank required for netbanking.")
            if not (es["mode_netbank"].get("receiver_account_number") or "").strip():
                errors.append("Receiver account number required for netbanking.")

        if errors:
            st.error("Please fix before saving:\n\n- " + "\n- ".join(errors))
        else:
            try:
                # 1) Update payouts row
                upd = supabase.table("payouts").update({
                    "amount_received": float(es["amount_received"]),
                    "payout_date": es["payout_date"],
                    "received_by": int(es["received_by"]),
                    "mode": es["mode"],
                    "remarks": es["remarks"] or None
                }).eq("payout_id", es["payout_id"]).execute()

                # check update success
                if not getattr(upd, "data", None):
                    raise Exception(f"Payout update failed: {getattr(upd, 'error', upd)}")

                # 2) Replace distributions: delete old, insert new
                del_resp = supabase.table("payout_distributions").delete().eq("payout_id", es["payout_id"]).execute()
                if getattr(del_resp, "error", None):
                    # deletion could be fine even if no rows existed; still flag unexpected errors
                    raise Exception(f"Failed to delete existing distributions: {getattr(del_resp, 'error', del_resp)}")

                dist_payload = [{"payout_id": es["payout_id"], "user_id": int(d["user_id"]), "amount": float(d["amount"])} for d in st.session_state.edit_distributions if d.get("user_id") and float(d.get("amount") or 0) > 0]
                if dist_payload:
                    ins_dist = supabase.table("payout_distributions").insert(dist_payload).execute()
                    if not getattr(ins_dist, "data", None):
                        raise Exception(f"Inserting distributions failed: {getattr(ins_dist, 'error', ins_dist)}")

                # 3) Replace mode-specific rows
                delete_mode_rows_for_payout(es["payout_id"])  # helper deletes all mode rows

                if es["mode"] == "UPI":
                    upi_resp = supabase.table("upi_payouts").insert({
                        "payout_id": es["payout_id"],
                        "reference_number": es["mode_upi"].get("reference_number"),
                        "app_used": es["mode_upi"].get("app_used") or None
                    }).execute()
                    if not getattr(upi_resp, "data", None):
                        raise Exception(f"Inserting UPI details failed: {getattr(upi_resp, 'error', upi_resp)}")

                elif es["mode"] == "cheque":
                    ch_resp = supabase.table("cheque_payouts").insert({
                        "payout_id": es["payout_id"],
                        "cheque_number": es["mode_cheque"].get("cheque_number"),
                        "bank_name": es["mode_cheque"].get("bank_name")
                    }).execute()
                    if not getattr(ch_resp, "data", None):
                        raise Exception(f"Inserting cheque details failed: {getattr(ch_resp, 'error', ch_resp)}")

                elif es["mode"] == "netbanking":
                    nb_resp = supabase.table("netbanking_payouts").insert({
                        "payout_id": es["payout_id"],
                        "receiver_bank": es["mode_netbank"].get("receiver_bank") or None,
                        "receiver_bank_ifsc": es["mode_netbank"].get("receiver_bank_ifsc") or None,
                        "receiver_account_number": es["mode_netbank"].get("receiver_account_number") or None,
                        "sender_bank": es["mode_netbank"].get("sender_bank") or None,
                        "sender_account_number": es["mode_netbank"].get("sender_account_number") or None
                    }).execute()
                    if not getattr(nb_resp, "data", None):
                        raise Exception(f"Inserting netbanking details failed: {getattr(nb_resp, 'error', nb_resp)}")

                # 4) Replace proofs if new file uploaded
                if es.get("new_proof"):
                    # delete existing proofs and insert new (replace behavior)
                    supabase.table("payout_proofs").delete().eq("payout_id", es["payout_id"]).execute()
                    encoded = base64.b64encode(es["new_proof"].read()).decode("utf-8")
                    proof_resp = supabase.table("payout_proofs").insert({
                        "payout_id": es["payout_id"],
                        "file_name": es["new_proof"].name,
                        "file_data": encoded,
                        "description": None
                    }).execute()
                    if not getattr(proof_resp, "data", None):
                        raise Exception(f"Inserting proof failed: {getattr(proof_resp, 'error', proof_resp)}")

                st.success("✅ Payout updated successfully.")
                st.rerun()  # reload page to reflect changes

            except Exception as e:
                st.error(f"Failed to save changes: {e}")


with col_reload:
    if st.button("Reload Original"):
        # discard edits and reload page state
        st.session_state.pop("edit_state", None)
        st.session_state.pop("edit_distributions", None)
        st.rerun()

with col_delete:
    if st.button("Delete Payout"):
        confirm = st.confirm("Are you sure? This will delete payout, its distributions, mode rows and proofs.")
        if confirm:
            try:
                supabase.table("payouts").delete().eq("payout_id", es["payout_id"]).execute()
                st.success("Payout deleted.")
                st.rerun()

            except Exception as e:
                st.error(f"Failed to delete payout: {e}")

# ------------------------------
# End of page
# ------------------------------
st.caption(
    "Notes:\n"
    "- Distributions must sum exactly to amount_received (small tolerance allowed).\n"
    "- Editing mode will replace the previous mode-detail rows for this payout.\n"
    "- Proof replacement: uploading a new proof file will replace existing proofs for this payout.\n"
    "- If you want to keep multiple proofs, remove the replace logic and append new proof rows instead."
)
