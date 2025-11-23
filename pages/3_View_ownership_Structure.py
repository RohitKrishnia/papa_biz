import streamlit as st
from supabase import create_client, Client

# ---------- Supabase Setup ----------

st.set_page_config(page_title="Insert Transaction")
@st.cache_resource
def get_supabase() -> Client:

    url = "https://ogecahtzmpsznesragam.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZWNhaHR6bXBzem5lc3JhZ2FtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5MzE0NDEsImV4cCI6MjA2NTUwNzQ0MX0.SVPUtm2-bhTRjc0XZnUII8pHt2Jc435Mr_fsEkmKpvs"
    return create_client(url, key)

supabase = get_supabase()
# ---------- Ownership Tree Viewer ----------


def get_user_name_by_id(user_id, supabase):
    """
    Fetch the user name from the 'users' table given the user_id using Supabase.
    """
    try:
        response = (
            supabase.table("users")
            .select("name")
            .eq("id", user_id)
            .execute()
        )
        
        if response.data and len(response.data) > 0:
            return response.data[0]["name"]
        else:
            return None
    except Exception as e:
        print(f"Error fetching user name: {e}")
        return None



def display_ownership_tree(project_id):
    partners_resp = supabase.table("partners") \
        .select("partner_id, partner_user_id, share_percentage") \
        .eq("project_id", project_id) \
        .execute()

    st.subheader("Ownership Tree")

    if not partners_resp.data:
        st.info("No partners found for this project.")
        return

    for partner in partners_resp.data:
        partner_id = partner["partner_id"]
        partner_name = get_user_name_by_id(partner["partner_user_id"],supabase)
        partner_share = partner["share_percentage"]
        st.markdown(f"🔵 **{partner_name}** - {partner_share}%")

        sub_resp = supabase.table("sub_partners") \
            .select("sub_partner_user_id, share_percentage") \
            .eq("partner_id", partner_id) \
            .execute()

        for sub in sub_resp.data or []:

            effective_share = round(partner_share * sub["share_percentage"] / 100, 2)
            sub_partner_name = get_user_name_by_id(sub["sub_partner_user_id"], supabase)
            st.markdown(f"&emsp;&emsp;🔹 **{sub_partner_name}** - {effective_share}% (of project)",unsafe_allow_html=True)

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
