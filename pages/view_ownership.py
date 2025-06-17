import streamlit as st
from supabase import create_client, Client

# ---------- Supabase Setup ----------

st.set_page_config(page_title="Insert Transaction")
@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)

supabase = get_supabase_client()
# ---------- Ownership Tree Viewer ----------

def display_ownership_tree(project_id):
    partners_resp = supabase.table("partners") \
        .select("partner_id, partner_name, share_percentage") \
        .eq("project_id", project_id) \
        .execute()

    st.subheader("Ownership Tree")

    if not partners_resp.data:
        st.info("No partners found for this project.")
        return

    for partner in partners_resp.data:
        partner_id = partner["partner_id"]
        partner_name = partner["partner_name"]
        partner_share = partner["share_percentage"]
        st.markdown(f"🔵 **{partner_name}** - {partner_share}%")

        sub_resp = supabase.table("sub_partners") \
            .select("sub_partner_name, share_percentage") \
            .eq("partner_id", partner_id) \
            .execute()

        for sub in sub_resp.data or []:
            effective_share = round(partner_share * sub["share_percentage"] / 100, 2)
            st.markdown(f"&emsp;&emsp;🔹 **{sub['sub_partner_name']}** - {effective_share}% (of project)", unsafe_allow_html=True)

# ---------- Streamlit UI ----------

def main():
    st.title("📊 Project Ownership Viewer")

    project_resp = supabase.table("projects").select("project_id, project_name").execute()
    if not project_resp.data:
        st.warning("No projects found.")
        return

    project_dict = {proj["project_name"]: proj["project_id"] for proj in project_resp.data}
    selected_project = st.selectbox("Select a Project", list(project_dict.keys()))

    if selected_project:
        display_ownership_tree(project_dict[selected_project])

if __name__ == "__main__":
    main()
