import streamlit as st
from supabase import create_client, Client

# ---------- PAGE & DB ----------
st.set_page_config(page_title="⚠️ Clear All Data")

@st.cache_resource
def get_supabase_client() -> Client:
    url = "https://ogecahtzmpsznesragam.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZWNhaHR6bXBzem5lc3JhZ2FtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5MzE0NDEsImV4cCI6MjA2NTUwNzQ0MX0.SVPUtm2-bhTRjc0XZnUII8pHt2Jc435Mr_fsEkmKpvs"
    return create_client(url, key)

supabase = get_supabase_client()

# ---------- TABLES & PRIMARY KEYS ----------
# We will NOT touch: users, bank_accounts
# Delete order respects foreign keys: children first, parents later
TABLE_PK = {
    "transaction_attachments": "attachment_id",
    "payment_proofs":          "proof_id",
    "upi_payments":            "upi_payment_id",
    "cheque_payments":         "cheque_payment_id",
    "netbanking_payments":     "netbanking_payment_id",
    "transaction_sources":     "id",
    "transactions":            "transaction_id",
    "attachments":             "attachment_id",
    "sub_partners":            "sub_partner_id",
    "partners":                "partner_id",
    "settlements":             "settlement_id",
    "projects":                "project_id",
    # excluded:
    # "users": "id",
    # "bank_accounts": "id",
}

DELETE_ORDER = [
    # --- transactions and children ---
    "transaction_attachments",
    "payment_proofs",
    "upi_payments",
    "cheque_payments",
    "netbanking_payments",
    "transaction_sources",
    "transactions",
    # --- project attachments & partner graph ---
    "attachments",
    "sub_partners",
    "partners",
    # --- settlements tied to projects ---
    "settlements",
    # --- parent last ---
    "projects",
]

def delete_all_except_users_and_bank_accounts():
    """
    Deletes all rows from configured tables using a 'neq(pk, -1)' filter,
    which effectively deletes every row (since your PKs are always positive).
    """
    for table in DELETE_ORDER:
        pk = TABLE_PK[table]
        # Perform delete; PostgREST requires a filter to allow bulk delete
        resp = supabase.table(table).delete().neq(pk, -1).execute()

        # Basic error visibility
        if getattr(resp, "data", None) is None and getattr(resp, "error", None):
            raise RuntimeError(f"{table}: {getattr(resp, 'error', None)}")

def show_counts():
    st.subheader("Current row counts (before deletion)")
    cols = st.columns(3)
    idx = 0
    for table, pk in TABLE_PK.items():
        # count by selecting a minimal column with exact count; fall back silently if blocked by RLS
        try:
            r = supabase.table(table).select(pk, count="exact", head=True).execute()
            count = r.count if hasattr(r, "count") else "?"
        except Exception:
            count = "?"
        with cols[idx % 3]:
            st.write(f"**{table}**: {count}")
        idx += 1
    # Also show the excluded tables for clarity
    for table in ["users", "bank_accounts"]:
        try:
            r = supabase.table(table).select("id", count="exact", head=True).execute()
            count = r.count if hasattr(r, "count") else "?"
        except Exception:
            count = "?"
        with cols[idx % 3]:
            st.write(f"**{table} (kept)**: {count}")
        idx += 1

def main():
    st.title("⚠️ Danger Zone: Clear All Project Data")
    st.warning("This will permanently delete all projects, partners, settlements, transactions, and attachments.\n\n"
               "It will **NOT** delete users or bank accounts.")

    with st.expander("See current row counts"):
        show_counts()

    st.divider()
    st.checkbox("I understand this action is irreversible.", key="confirm_checkbox")
    confirm_text = st.text_input("Type DELETE to confirm", placeholder="DELETE")

    col1, col2 = st.columns([1, 2])
    with col1:
        delete_btn = st.button("🧨 Delete Everything", type="primary", use_container_width=True)

    if delete_btn:
        if not st.session_state.get("confirm_checkbox") or confirm_text.strip() != "DELETE":
            st.error("You must check the confirmation box and type **DELETE** to proceed.")
            return

        try:
            delete_all_except_users_and_bank_accounts()
            st.success("✅ All selected tables cleared successfully (users & bank_accounts untouched).")
            with st.expander("Row counts after deletion"):
                show_counts()
        except Exception as e:
            st.error(f"❌ Error during cleanup: {e}")

if __name__ == "__main__":
    main()
