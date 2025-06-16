import streamlit as st
import psycopg2
from psycopg2 import Error
from datetime import date

# ---------- Database Setup ----------

def get_db_connection():
    return psycopg2.connect(
        host=st.secrets["postgres"]["host"],
        database=st.secrets["postgres"]["database"],
        user=st.secrets["postgres"]["user"],
        password=st.secrets["postgres"]["password"],
        port=st.secrets["postgres"]["port"]
    )

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            project_id SERIAL PRIMARY KEY,
            project_name VARCHAR(255) UNIQUE NOT NULL,
            description TEXT,
            start_date DATE
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS partners (
            partner_id SERIAL PRIMARY KEY,
            project_id INTEGER,
            partner_name VARCHAR(255),
            share_percentage NUMERIC(5,2),
            FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sub_partners (
            sub_partner_id SERIAL PRIMARY KEY,
            partner_id INTEGER,
            sub_partner_name VARCHAR(255),
            share_percentage NUMERIC(5,2),
            FOREIGN KEY (partner_id) REFERENCES partners(partner_id) ON DELETE CASCADE
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attachments (
            attachment_id SERIAL PRIMARY KEY,
            project_id INTEGER,
            file_name VARCHAR(255),
            file_data BYTEA,
            description TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
        );
    """)

    conn.commit()
    cursor.close()
    conn.close()

# ---------- Streamlit UI ----------

def main():
    st.set_page_config(page_title="Create Project")
    st.title("Create a New Project")

    create_tables()

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
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("INSERT INTO projects (project_name, description, start_date) VALUES (%s, %s, %s) RETURNING project_id;",
                           (project_name, description, start_date))
            project_id = cursor.fetchone()[0]

            for partner_name, share, sub_partners in partners_data:
                cursor.execute("INSERT INTO partners (project_id, partner_name, share_percentage) VALUES (%s, %s, %s) RETURNING partner_id;",
                               (project_id, partner_name, share))
                partner_id = cursor.fetchone()[0]

                for sub_name, sub_share in sub_partners:
                    cursor.execute("INSERT INTO sub_partners (partner_id, sub_partner_name, share_percentage) VALUES (%s, %s, %s)",
                                   (partner_id, sub_name, sub_share))

            for fname, (file, desc) in file_descriptions.items():
                file_data = file.read()
                cursor.execute("INSERT INTO attachments (project_id, file_name, file_data, description) VALUES (%s, %s, %s, %s)",
                               (project_id, fname, file_data, desc))

            conn.commit()
            st.success("Project created successfully!")

        except Error as e:
            st.error(f"An error occurred: {e}")

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


if __name__ == "__main__":
    main()
