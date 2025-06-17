import streamlit as st
from datetime import date
from supabase import create_client, Client

# ---------- Supabase Setup ----------

st.set_page_config(page_title="Insert Transaction")
@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)

supabase = get_supabase_client()

# ---------- Fetch Projects ----------

def get_projects():
    response = supabase.table("projects").select("project_id, project_name").execute()
    return [
        {"project_id": p["project_id"], "project_name": p["project_name"]}
        for p in response.data or []
    ]

# ---------- Fetch Participants (Partners + Sub-Partners) ----------

def get_all_participants(project_id):
    # Fetch partners
    partners_resp = (
        supabase.table("partners")
        .select("partner_id, partner_name")
        .eq("project_id", project_id)
        .execute()
    )
    partner_ids = {p["partner_id"] for p in partners_resp.data or []}
    partner_names = [p["partner_name"] for p in partners_resp.data or []]

    # Fetch sub-partners (client-side join)
    sub_partners_resp = supabase.table("sub_partners").select("sub_partner_name, partner_id").execute()
    sub_partner_names = [
        sp["sub_partner_name"]
        for sp in sub_partners_resp.data or []
        if sp["partner_id"] in partner_ids
    ]

    return list(set(partner_names + sub_partner_names))

# ---------- Insert Settlement ----------

def record_payment(project_id, payer, payee, amount, mode, note, settlement_date):
    response = supabase.table("settlements").insert({
        "project_id": project_id,
        "paid_by": payer,
        "paid_to": payee,
        "amount": amount,
        "mode": mode,
        "remarks": note,
        "date": settlement_date.isoformat()
    }).execute()

    if response.data is None:
        raise Exception(f"Failed to insert record: {response}")

# ---------- Streamlit UI ----------

def main():
    st.title("💸 Record a Settlement Payment")

    projects = get_projects()
    if not projects:
        st.warning("No projects found.")
        return

    project_map = {p["project_name"]: p["project_id"] for p in projects}
    selected_project = st.selectbox("Select Project", list(project_map.keys()))
    project_id = project_map[selected_project]

    participants = get_all_participants(project_id)
    if len(participants) < 2:
        st.warning("Not enough participants in this project.")
        return

    payer = st.selectbox("Who paid?", participants)
    payee_candidates = [p for p in participants if p != payer]
    payee = st.selectbox("Who received?", payee_candidates)

    amount = st.number_input("Amount Paid", min_value=0.0, step=1.0)
    mode = st.selectbox("Payment Mode", ["cash", "online"])
    settlement_date = st.date_input("Settlement Date", date.today())
    note = st.text_area("Optional Note")

    if st.button("Record Payment"):
        if amount <= 0:
            st.error("Amount must be greater than 0.")
        else:
            try:
                record_payment(project_id, payer, payee, amount, mode, note, settlement_date)
                st.success(f"✅ Recorded payment of ₹{amount} from {payer} to {payee}")
            except Exception as e:
                st.error(f"❌ Failed to record payment: {str(e)}")

if __name__ == "__main__":
    main()

