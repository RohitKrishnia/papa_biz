import streamlit as st
from collections import defaultdict
from supabase import create_client, Client

# ---------- Supabase Setup ----------

st.set_page_config(page_title="Insert Transaction")
@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)

supabase = get_supabase_client()

# ---------- Fetch Project List ----------

def get_projects():
    res = supabase.table("projects").select("project_id, project_name").execute()
    return [{"project_id": row["project_id"], "project_name": row["project_name"]} for row in res.data or []]

# ---------- Fetch All Debts ----------

def get_all_debts(project_id):
    transactions_res = supabase.table("transactions").select("transaction_id").eq("project_id", project_id).execute()
    transaction_ids = [t["transaction_id"] for t in transactions_res.data]

    if not transaction_ids:
        return []

    splits_res = supabase.table("transaction_splits").select("receiver_name, payer_name, amount").in_("transaction_id", transaction_ids).execute()
    return [
        {"debtor": r["receiver_name"], "creditor": r["payer_name"], "amount": r["amount"]}
        for r in splits_res.data
    ]

# ---------- Fetch Settlements ----------

def get_all_settlements(project_id):
    res = supabase.table("settlements").select("paid_by, paid_to, amount").eq("project_id", project_id).execute()
    return [
        {"debtor": r["paid_to"], "creditor": r["paid_by"], "amount": r["amount"]}
        for r in res.data
    ]

# ---------- Compute Net Summary ----------

def total_settlements(project_id):
    debts = get_all_debts(project_id)
    settlements = get_all_settlements(project_id)

    net_balances = defaultdict(float)

    for row in debts:
        net_balances[row["debtor"]] -= float(row["amount"])  # debtor
        net_balances[row["creditor"]] += float(row["amount"])  # creditor

    for row in settlements:
        net_balances[row["debtor"]] -= float(row["amount"])  # debtor
        net_balances[row["creditor"]] += float(row["amount"])  # creditor

    # Create final settlements
    debtors = [(k, v) for k, v in net_balances.items() if v < 0]
    creditors = [(k, v) for k, v in net_balances.items() if v > 0]

    debtors.sort(key=lambda x: x[1])
    creditors.sort(key=lambda x: x[1], reverse=True)

    i, j = 0, 0
    settlements_summary = []

    while i < len(debtors) and j < len(creditors):
        debtor, d_amt = debtors[i]
        creditor, c_amt = creditors[j]
        transfer = min(-d_amt, c_amt)
        settlements_summary.append((debtor, creditor, round(transfer, 2)))

        debtors[i] = (debtor, d_amt + transfer)
        creditors[j] = (creditor, c_amt - transfer)

        if abs(debtors[i][1]) < 1e-2:
            i += 1
        if abs(creditors[j][1]) < 1e-2:
            j += 1

    return settlements_summary

# ---------- Streamlit UI ----------

def main():
    st.title("💰 Project Settlements Overview")

    projects = get_projects()
    if not projects:
        st.warning("No projects available.")
        return

    project_map = {p["project_name"]: p["project_id"] for p in projects}
    selected_project = st.selectbox("Select a Project", list(project_map.keys()))
    project_id = project_map[selected_project]

    settlements = total_settlements(project_id)

    st.subheader("Net Settlements")
    if settlements:
        for debtor, creditor, amount in settlements:
            st.markdown(f"🔄 **{debtor}** owes **₹{amount}** to **{creditor}**")
    else:
        st.success("✅ All dues are settled!")

if __name__ == "__main__":
    main()
