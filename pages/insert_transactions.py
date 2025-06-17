import streamlit as st
from datetime import date
from supabase import create_client, Client


st.set_page_config(page_title="Insert Transaction")
@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)

supabase = get_supabase_client()

# -------- Split Calculation Logic --------

def calculate_auto_split(project_id, total_amount, paid_by):
    data = supabase.table("partners").select("*").eq("project_id", project_id).execute().data or []
    effective_shares = {}
    for p in data:
        pid, pname, pshare = p["partner_id"], p["partner_name"], float(p["share_percentage"])
        subs = supabase.table("sub_partners").select("*").eq("partner_id", pid).execute().data or []
        if not subs:
            effective_shares[pname] = round(pshare, 2)
        else:
            sub_total = sum(float(s["share_percentage"]) for s in subs)
            for s in subs:
                effective_shares[s["sub_partner_name"]] = round(pshare * float(s["share_percentage"]) / 100, 2)
            effective_shares[pname] = round((100 - sub_total) * pshare / 100, 2)

    owed = {n: round(sh * total_amount / 100, 2) for n, sh in effective_shares.items()}
    payments = [{"payer": n, "receiver": paid_by, "amount": amt} for n, amt in owed.items()]
    return payments, effective_shares, owed

# -------- CRUD Utility --------

def insert(table: str, data: dict):
    return supabase.table(table).insert(data).execute()

def get_stakeholders(project_id):
    # Step 1: Get partners for the project
    partners_resp = supabase.table("partners").select("partner_id, partner_name").eq("project_id", project_id).execute()
    partners = partners_resp.data or []
    
    partner_ids = [p["partner_id"] for p in partners]
    partner_names = [p["partner_name"] for p in partners]

    # Step 2: Get sub-partners for those partner_ids
    subs_resp = supabase.table("sub_partners").select("sub_partner_name, partner_id").execute()
    subs_all = subs_resp.data or []

    sub_names = [s["sub_partner_name"] for s in subs_all if s["partner_id"] in partner_ids]

    return partner_names + sub_names

# -------- Streamlit App --------

def main():
    
    st.title("Insert a Transaction")

    projs = supabase.table("projects").select("project_id,project_name").execute().data or []
    if not projs:
        st.warning("Create a project first.")
        return

    pmap = {p["project_name"]: p["project_id"] for p in projs}
    sel = st.selectbox("Select Project", list(pmap.keys()))
    pid = pmap[sel]

    stakeholders = get_stakeholders(pid)
    txn_date = st.date_input("Transaction Date", date.today())
    txn_type = st.selectbox("Transaction Type", ["investment", "expense"])
    paid_by = st.selectbox("Paid By", stakeholders)
    amount = st.number_input("Amount", 0.0, format="%.2f")
    mode = st.selectbox("Mode", ["cash", "online"])
    purpose = st.text_area("Purpose")
    split_type = st.radio("Split Type", ["share as per ownership", "custom"])

    splits = []
    if split_type == "custom":
        st.markdown("### Custom Split")
        total = 0
        for s in stakeholders:
            owe = st.number_input(f"{s} owes", 0.0, format="%.2f", key=s)
            if owe > 0:
                splits.append((paid_by, s, owe))
                total += owe
        if round(total, 2) != round(amount, 2):
            st.warning("Total owes doesn't match paid amount.")
    else:
        payments, shares, owed = calculate_auto_split(pid, amount, paid_by)
        st.subheader("Auto-Calculated Split:")
        for pay in payments:
            st.markdown(f"**{pay['payer']}** → ₹{pay['amount']} → **{pay['receiver']}**")
        for n, amt in owed.items():
            splits.append((paid_by, n, amt))

    att = st.file_uploader("Attach Files", ["pdf","jpg","jpeg"], accept_multiple_files=True)
    file_desc = {f.name: st.text_input(f"Desc for {f.name}", key=f.name) for f in att}

    if st.button("Submit Transaction"):
        tx = insert("transactions", {
            "project_id": pid, "transaction_type": txn_type, "paid_by": paid_by,
            "amount": amount, "transaction_date": txn_date.isoformat(),
            "mode": mode, "purpose": purpose,
            "split_type": "auto" if split_type=="share as per ownership" else "custom"
        })
        tid = tx.data[0]["transaction_id"]
        for payer, recv, amt in splits:
            insert("transaction_splits", {
                "transaction_id": tid, "payer_name": payer, "receiver_name": recv, "amount": amt
            })
        for f in att:
            data_enc = f.read().decode("utf-8")
            insert("transaction_attachments", {
                "transaction_id": tid, "file_name": f.name, "file_data": data_enc,
                "description": file_desc[f.name]
            })
        st.success("Transaction recorded!")

if __name__ == "__main__":
    main()
