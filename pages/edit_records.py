import streamlit as st
from supabase import create_client, Client
from collections import defaultdict
from datetime import datetime

    
st.set_page_config(page_title="Edit Transactions & Settlements")
# --- Setup Supabase Client ---
@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)

supabase = get_supabase_client()

# --- Fetch combined entries ---
def fetch_combined_entries(project_id, page_size, offset):
    # Fetch transactions
    tx_res = supabase.table("transactions") \
        .select("*") \
        .eq("project_id", project_id) \
        .order("created_at", desc=False) \
        .range(offset, offset + page_size - 1) \
        .execute()
    transactions = [{"type":"transaction", **row} for row in (tx_res.data or [])]

    # Fetch settlements
    st_res = supabase.table("settlements") \
        .select("*") \
        .eq("project_id", project_id) \
        .order("created_at", desc=False) \
        .range(offset, offset + page_size - 1) \
        .execute()
    settlements = [{"type":"settlement", **row} for row in (st_res.data or [])]

    combined = transactions + settlements
    combined.sort(key=lambda x: x["created_at"], reverse=True)
    return combined

# --- Update a record dynamically ---
def update_record(table, key_column, key_value, updates):
    resp = supabase.table(table).update(updates).eq(key_column, key_value).execute()
    if resp.data is None:
    	return False
    else:
    	return True
    
    #return resp.status_code == 200

# --- Main Streamlit ---
def main():
    
    st.title("Edit Transactions & Settlements")

    # Fetch project list
    proj_res = supabase.table("projects").select("project_id,project_name").execute()
    projects = proj_res.data or []
    project_map = {p["project_name"]: p["project_id"] for p in projects}

    if len(project_map) == 0:
        st.warning("Create a project first.")
    else: 

        selected = st.selectbox("Select Project", list(project_map.keys()))
        project_id = project_map[selected]

        page_size = 10
        page_no = st.number_input("Page Number", min_value=1, value=1)
        offset = (page_no - 1) * page_size

        entries = fetch_combined_entries(project_id, page_size, offset)

        for entry in entries:
            if entry["type"] == "transaction":
                header = f"Paid by: {entry['paid_by']} | ₹{entry['amount']} | {entry['created_at'][:10]}"
            else:
                header = f"{entry['paid_by']} paid {entry['paid_to']} ₹{entry['amount']} on {entry['created_at'][:10]}"

            with st.expander(header):
                if entry["type"] == "transaction":
                    # Editable fields
                    upd = {
                        "paid_by": st.text_input("Paid By", entry["paid_by"], key=f"paid_by_t{entry['transaction_id']}"),
                        "amount": st.number_input(label = "Amount", value = float(entry["amount"]), min_value = 0.0, key=f"amt_t{entry['transaction_id']}"),
                        "mode": st.selectbox("Mode", ["cash", "online"], index=["cash", "online"].index(entry["mode"]), key=f"mode_t{entry['transaction_id']}"),
                        "purpose": st.text_area("Purpose", entry["purpose"], key=f"purp_t{entry['transaction_id']}"),
                        "split_type": st.selectbox("Split Type", ["auto", "custom"], index=["auto","custom"].index(entry["split_type"]), key=f"split_t{entry['transaction_id']}"),
                        "created_at": st.date_input("Date", datetime.fromisoformat(entry["created_at"]).date(), key=f"date_t{entry['transaction_id']}").isoformat()
                    }
                    if st.button("Update", key=f"btn_t{entry['transaction_id']}"):
                        if update_record("transactions", "transaction_id", entry["transaction_id"], upd):
                            st.success("✅ Updated successfully")
                            st.rerun()
                        else:
                            st.error("❌ Update failed")
                else:
                    upd = {
                        "paid_by": st.text_input("Payer", entry["paid_by"], key=f"payr_s{entry['settlement_id']}"),
                        "paid_to": st.text_input("Payee", entry["paid_to"], key=f"pyee_s{entry['settlement_id']}"),
                        "amount": st.number_input(label = "Amount", value = float(entry["amount"]),  min_value = 0.0, key=f"amt_s{entry['settlement_id']}"),
                        "created_at": st.date_input("Date", datetime.fromisoformat(entry["created_at"]).date(), key=f"date_s{entry['settlement_id']}").isoformat()
                    }
                    if st.button("Update", key=f"btn_s{entry['settlement_id']}"):
                        if update_record("settlements", "settlement_id", entry["settlement_id"], upd):
                            st.success("✅ Updated successfully")
                            st.rerun()
                        else:
                            st.error("❌ Update failed")

if __name__ == "__main__":
    main()
