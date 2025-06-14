import streamlit as st
import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
        port=st.secrets["mysql"]["port"]
    )

def display_ownership_tree(project_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT partner_id, partner_name, share_percentage FROM partners WHERE project_id = %s", (project_id,))
    partners = cursor.fetchall()

    st.subheader("Ownership Tree")
    for partner in partners:
        st.markdown(f"🔵 **{partner['partner_name']}** - {partner['share_percentage']}%")
        cursor.execute("SELECT sub_partner_name, share_percentage FROM sub_partners WHERE partner_id = %s", (partner['partner_id'],))
        sub_partners = cursor.fetchall()
        for sub in sub_partners:
            effective_share = round(partner['share_percentage'] * sub['share_percentage'] / 100, 2)
            st.markdown(f"&emsp;&emsp;🔹 **{sub['sub_partner_name']}** - {effective_share}% (of project)", unsafe_allow_html=True)

    cursor.close()
    conn.close()

def main():
    st.set_page_config(page_title="View Ownership Structure")
    st.title("Project Ownership Viewer")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT project_id, project_name FROM projects")
    projects = cursor.fetchall()
    project_dict = {name: pid for pid, name in projects}
    cursor.close()
    conn.close()

    selected_project = st.selectbox("Select a Project", list(project_dict.keys()))
    if selected_project:
        display_ownership_tree(project_dict[selected_project])

if __name__ == "__main__":
    main()
