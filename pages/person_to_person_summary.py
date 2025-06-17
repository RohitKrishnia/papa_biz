import streamlit as st
from supabase import create_client, Client
from collections import defaultdict




st.set_page_config(page_title="Person-to-Person Debt Summary")

@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)

supabase = get_supabase_client()

# ---------- Fetch All Unique Names ----------

def get_all_people_names():
    partner_names = supabase.table("partners").select("partner_name").execute().data
    sub_partner_names = supabase.table("sub_partners").select("sub_partner_name").execute().data
    debtors = supabase.table("transaction_splits").select("receiver_name").execute().data
    creditors = supabase.table("transaction_splits").select("payer_name").execute().data
    payers = supabase.table("settlements").select("paid_by").execute().data
    payees = supabase.table("settlements").select("paid_to").execute().data

    names = set()
    for row in partner_names: names.add(row["partner_name"])
    for row in sub_partner_names: names.add(row["sub_partner_name"])
    for row in debtors: names.add(row["receiver_name"])
    for row in creditors: names.add(row["payer_name"])
    for row in payers: names.add(row["paid_by"])
    for row in payees: names.add(row["paid_to"])

    return sorted(list(names))

# ---------- Compute Net Amount Owed ----------

def compute_owed_amount(person1, person2):
    # Debt: person1 owes person2
    debt_result = supabase.table("transaction_splits").select("amount").eq("receiver_name", person1).eq("payer_name", person2).execute().data
    total_debt = sum(float(r["amount"]) for r in debt_result)

    # Settlement: person1 paid person2
    payment_result = supabase.table("settlements").select("amount").eq("paid_by", person1).eq("paid_to", person2).execute().data
    total_paid = sum(float(r["amount"]) for r in payment_result)

    return round(total_debt - total_paid, 2)

# ---------- Streamlit UI ----------

def main():
    st.title("🔍 Person-to-Person Net Owed Amount Across All Projects")

    all_names = get_all_people_names()

    person1 = st.selectbox("Select Debtor (Person 1)", all_names)
    person2 = st.selectbox("Select Creditor (Person 2)", all_names)

    if person1 == person2:
        st.warning("Please select two different people.")
        return

    if st.button("Calculate"):
        amount = compute_owed_amount(person1, person2)
        if amount <= 0:
            st.success(f"✅ {person1} owes nothing to {person2}.")
        else:
            st.error(f"💰 {person1} owes ₹{amount} to {person2} across all projects.")

if __name__ == "__main__":
    main()
