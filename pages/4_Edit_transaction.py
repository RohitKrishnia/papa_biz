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

def fetch_payment_proofs(transaction_id: int):
    """Fetch all payment proofs for a transaction."""
    r = supabase.table("payment_proofs").select("proof_id, file_name, description").eq("transaction_id", transaction_id).execute()
    return r.data or []

def get_proof_file_data(proof_id: int):
    """Fetch and decode payment proof file data."""
    r = supabase.table("payment_proofs").select("file_data, file_name").eq("proof_id", proof_id).single().execute()
    if r.data and r.data.get("file_data"):
        return base64.b64decode(r.data["file_data"]), r.data["file_name"]
    return None, None

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
if "sources_to_remove" not in st.session_state:
    st.session_state.sources_to_remove = []  # Indices of sources marked for removal

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
# Always fetch fresh from DB when transaction changes, ignoring any unsaved removals
if st.session_state.get("loaded_txn_id") != transaction_id:
    existing_sources = fetch_sources(transaction_id)
    st.session_state.edit_sources = [
        {"source_id": s["source_id"], "amount": money(s["amount"]),
         "is_partner": bool(s.get("is_partner", False))}
        for s in existing_sources
    ]
    st.session_state.sources_to_remove = []  # Reset removal list when loading new transaction
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
    st.markdown(f"💰 Amount in Lakhs: **₹{amount / 1_00_000:.2f} Lakhs**")
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

# Filter out sources marked for removal for display (they disappear from UI)
active_sources_display = [(i, row) for i, row in enumerate(st.session_state.edit_sources) if i not in st.session_state.sources_to_remove]

for display_idx, (i, row) in enumerate(active_sources_display, start=1):
    with st.expander(f"Source {display_idx}", expanded=True):
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
            # Mark for removal - source disappears from UI immediately
            if i not in st.session_state.sources_to_remove:
                st.session_state.sources_to_remove.append(i)
            st.rerun()

# Calculate total excluding sources marked for removal
active_sources_for_total = [r for i, r in enumerate(st.session_state.edit_sources) if i not in st.session_state.sources_to_remove]
sources_total = sum(money(r.get("amount")) for r in active_sources_for_total)
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
# Payment Proof Section
# -------------------------------
st.subheader("Proof of Payment")

# Display existing proofs
existing_proofs = fetch_payment_proofs(transaction_id)
if existing_proofs:
    st.markdown("**Existing Proofs:**")
    proofs_to_delete = []
    for proof in existing_proofs:
        col1, col2, col3 = st.columns([2.5, 1, 1])
        with col1:
            desc = proof.get("description", "") or "No description"
            st.markdown(f"📄 **{proof['file_name']}** - {desc}")
        with col2:
            # Download proof
            try:
                doc_data, file_name = get_proof_file_data(proof["proof_id"])
                if doc_data and file_name:
                    # Determine MIME type from file extension
                    if file_name.lower().endswith('.pdf'):
                        mime_type = "application/pdf"
                    elif file_name.lower().endswith(('.jpg', '.jpeg')):
                        mime_type = "image/jpeg"
                    else:
                        mime_type = "application/octet-stream"
                    st.download_button(
                        "📥 Download",
                        data=doc_data,
                        file_name=file_name,
                        mime=mime_type,
                        key=f"download_proof_{proof['proof_id']}"
                    )
            except Exception as e:
                st.error(f"Could not load proof: {e}")
        with col3:
            if st.button("🗑️ Remove", key=f"del_proof_{proof['proof_id']}"):
                proofs_to_delete.append(proof["proof_id"])
    
    # Delete selected proofs
    if proofs_to_delete:
        try:
            for proof_id in proofs_to_delete:
                supabase.table("payment_proofs").delete().eq("proof_id", proof_id).execute()
            st.success(f"✅ Removed {len(proofs_to_delete)} proof(s)")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Failed to remove proof: {e}")

# Upload new proof
st.markdown("**Upload New Proof:**")
new_proof_file = st.file_uploader("Upload proof (PDF/JPEG)", type=["pdf", "jpg", "jpeg"], key="new_proof")
new_proof_name = st.text_input("Proof File Name", key="new_proof_name")
new_proof_desc = st.text_area("Proof Description", key="new_proof_desc")

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

        # 3) Sources → replace all rows for this transaction (excluding those marked for removal)
        # Filter out sources marked for removal
        active_sources = [r for i, r in enumerate(st.session_state.edit_sources) if i not in st.session_state.sources_to_remove]
        payload = [{
            "transaction_id": transaction_id,
            "source_id": r["source_id"],
            "is_partner": bool(r["is_partner"]),
            "amount": money(r["amount"]),
        } for r in active_sources if r.get("source_id") is not None and money(r.get("amount")) > 0.0]
        replace_sources(transaction_id, payload)
        
        # Update session state to reflect what's actually in the database
        # Remove sources that were marked for removal from the session state
        st.session_state.edit_sources = [r for i, r in enumerate(st.session_state.edit_sources) if i not in st.session_state.sources_to_remove]
        
        # Clear the removal list after successful save
        st.session_state.sources_to_remove = []
        
        # Force reload from database on next render by invalidating loaded_txn_id
        # This ensures we always show what's actually in the database
        if "loaded_txn_id" in st.session_state:
            del st.session_state.loaded_txn_id

        # 4) Insert new proof if uploaded
        if new_proof_file:
            new_proof_file.seek(0)  # Reset file pointer
            encoded_data = base64.b64encode(new_proof_file.read()).decode("utf-8")
            supabase.table("payment_proofs").insert({
                "transaction_id": transaction_id,
                "file_name": (new_proof_name or new_proof_file.name),
                "file_data": encoded_data,
                "description": (new_proof_desc or None)
            }).execute()

        st.success("✅ Transaction updated successfully.")
        st.toast("Saved!", icon="✅")

    except Exception as e:
        st.error(f"❌ Failed to update transaction: {e}")
