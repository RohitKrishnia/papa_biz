import streamlit as st
from datetime import date
from supabase import create_client, Client
import base64

# ---------- Supabase Setup ----------
st.set_page_config(page_title="Create Project")
@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)

supabase = get_supabase_client()

# ---------- Streamlit UI ----------

def main():
    
    st.title("Create a New Project")

    # st.info("⚠️ Make sure all required tables are already created in Supabase schema.")

    project_name = st.text_input("Project Name")
    description = st.text_area("Project Description")
    start_date = st.date_input("Start Date", date.today())

    num_partners = st.number_input("Number of Partners", min_value=1, step=1, key="num_partners")

    partners_data = []
    for i in range(int(num_partners)):
        st.subheader(f"Partner {i+1}")
        partner_name = st.text_input(f"Partner {i+1} Name", key=f"partner_name_{i}")
        partner_share = st.number_input(f"Partner {i+1} Share (%)", key=f"partner_share_{i}", min_value=0.0)
        num_sub_partners = st.number_input(f"Number of Sub-partners for Partner {i+1}", min_value=0, step=1, key=f"num_sub_{i}")

        sub_partners = []
        for j in range(int(num_sub_partners)):
            sub_name = st.text_input(f"Sub-Partner {j+1} Name (of Partner {i+1})", key=f"sub_name_{i}_{j}")
            sub_share = st.number_input(f"Sub-Partner {j+1} Share (%)", key=f"sub_share_{i}_{j}", min_value=0.0)
            sub_partners.append((sub_name, sub_share))

        partners_data.append((partner_name, partner_share, sub_partners))

    st.markdown("---")
    uploaded_files = st.file_uploader("Attach Files (PDF/JPEG)", type=["pdf", "jpg", "jpeg"], accept_multiple_files=True)
    file_descriptions = {}
    for uploaded_file in uploaded_files:
        desc = st.text_input(f"Description for {uploaded_file.name}", key=f"desc_{uploaded_file.name}")
        file_descriptions[uploaded_file.name] = (uploaded_file, desc)

    if st.button("Create Project"):
        try:
            
            # Insert into projects table
            project_res = supabase.table("projects").insert({
                "project_name": project_name,
                "description": description,
                "start_date": start_date.isoformat()
            }).execute()

            if project_res.data is None:
                raise Exception(f"Insert failed. Response: {project_res}")


            project_id = project_res.data[0]["project_id"]

            # Insert partners and sub-partners
            for partner_name, share, sub_partners in partners_data:
                partner_res = supabase.table("partners").insert({
                    "project_id": project_id,
                    "partner_name": partner_name,
                    "share_percentage": share
                }).execute()


                if partner_res.data is None:
                    raise Exception(f"Failed to create partner: {partner_res}")

                partner_id = partner_res.data[0]["partner_id"]

                for sub_name, sub_share in sub_partners:
                    supabase.table("sub_partners").insert({
                        "partner_id": partner_id,
                        "sub_partner_name": sub_name,
                        "share_percentage": sub_share
                    }).execute()

            # Insert attachments (note: Supabase REST API can't directly store binary data in BYTEA)
            for fname, (file, desc) in file_descriptions.items():
                encoded_data = base64.b64encode(file.read()).decode("utf-8")  # Convert bytes to base64 string
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