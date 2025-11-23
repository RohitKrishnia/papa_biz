# -------------------------

import streamlit as st
from datetime import date
from supabase import create_client, Client
import base64

# ---------- Supabase Setup ----------
st.set_page_config(page_title="Create Project")
@st.cache_resource
def get_supabase_client() -> Client:
    url = "https://ogecahtzmpsznesragam.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZWNhaHR6bXBzem5lc3JhZ2FtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5MzE0NDEsImV4cCI6MjA2NTUwNzQ0MX0.SVPUtm2-bhTRjc0XZnUII8pHt2Jc435Mr_fsEkmKpvs"
    return create_client(url, key)

supabase = get_supabase_client()

def get_users():
    """Fetch users with IDs and names for selection."""
    resp = supabase.table("users").select("id, name").execute()
    return resp.data or []


def main():
    st.title("Create a New Project")

    project_name = st.text_input("Project Name")
    description = st.text_area("Project Description")
    start_date = st.date_input("Start Date", date.today())
    expected_cost = st.number_input("Expected Total Investment (₹)", min_value=0.0, step=1000.0)

    if expected_cost:
        st.markdown(f"💰 Entered Investment: **₹{expected_cost / 1_00_000:.2f} Lakhs**")

    num_partners = st.number_input("Number of Partners", min_value=1, step=1, key="num_partners")

    all_users = get_users()
    used_ids = set()

    partners_data = []

    for i in range(int(num_partners)):
        st.subheader(f"Partner {i+1}")

        available_for_partner = [u for u in all_users if u["id"] not in used_ids]
        partner_selection = st.selectbox(
            f"Partner {i+1} Name",
            options=available_for_partner,
            format_func=lambda x: x["name"],
            key=f"partner_name_{i}"
        )
        used_ids.add(partner_selection["id"])

        partner_share = st.number_input(f"Partner {i+1} Share (%)", key=f"partner_share_{i}", min_value=0.0)
        num_sub_partners = st.number_input(f"Number of Sub-partners for Partner {i+1}", min_value=0, step=1, key=f"num_sub_{i}")

        sub_partners = []
        for j in range(int(num_sub_partners)):
            available_for_sub = [u for u in all_users if u["id"] not in used_ids]
            sub_selection = st.selectbox(
                f"Sub-Partner {j+1} Name (of Partner {i+1})",
                options=available_for_sub,
                format_func=lambda x: x["name"],
                key=f"sub_name_{i}_{j}"
            )
            used_ids.add(sub_selection["id"])
            sub_share = st.number_input(f"Sub-Partner {j+1} Share (%)", key=f"sub_share_{i}_{j}", min_value=0.0)
            sub_partners.append((sub_selection["id"], sub_share))

        partners_data.append((partner_selection["id"], partner_share, sub_partners))

    # --- Attachments ---
    uploaded_files = st.file_uploader("Attach Files (PDF/JPEG)", type=["pdf", "jpg", "jpeg"], accept_multiple_files=True)
    file_descriptions = {}
    for uploaded_file in uploaded_files:
        desc = st.text_input(f"Description for {uploaded_file.name}", key=f"desc_{uploaded_file.name}")
        file_descriptions[uploaded_file.name] = (uploaded_file, desc)

    if st.button("Create Project"):
        try:
            project_res = supabase.table("projects").insert({
                "project_name": project_name,
                "description": description,
                "start_date": start_date.isoformat(),
                "expected_cost": expected_cost
            }).execute()

            if not project_res.data:
                raise Exception(f"Insert failed: {project_res}")

            project_id = project_res.data[0]["project_id"]

            # Insert partners and sub-partners with user_id
            for partner_id, share, sub_partners in partners_data:
                partner_res = supabase.table("partners").insert({
                    "project_id": project_id,
                    "partner_user_id": partner_id,  # store the user ID now
                    "share_percentage": share
                }).execute()

                if not partner_res.data:
                    raise Exception(f"Failed to create partner: {partner_res}")

                partner_db_id = partner_res.data[0]["partner_id"]

                for sub_user_id, sub_share in sub_partners:
                    supabase.table("sub_partners").insert({
                        "partner_id": partner_db_id,
                        "sub_partner_user_id": sub_user_id,  # store the sub-partner's user ID
                        "share_percentage": sub_share
                    }).execute()

            # Insert attachments
            for fname, (file, desc) in file_descriptions.items():
                encoded_data = base64.b64encode(file.read()).decode("utf-8")
                supabase.table("attachments").insert({
                    "project_id": project_id,
                    "file_name": fname,
                    "file_data": encoded_data,
                    "description": desc
                }).execute()

            st.success("✅ Project created successfully!")

        except Exception as e:
            st.error(f"❌ An error occurred: {e}")



if __name__ == "__main__":
    main()