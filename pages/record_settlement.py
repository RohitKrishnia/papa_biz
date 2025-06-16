import streamlit as st
from datetime import date
import psycopg2

# ---------- DB Connection ----------

def get_db_connection():
    conn = psycopg2.connect(
        host=st.secrets["postgres"]["host"],
        database=st.secrets["postgres"]["database"],
        user=st.secrets["postgres"]["user"],
        password=st.secrets["postgres"]["password"],
        port=st.secrets["postgres"]["port"]
    )
    return conn

# ---------- Create Table If Not Exists ----------

def create_settlement_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settlements (
            settlement_id SERIAL PRIMARY KEY,
            project_id INT,
            paid_by VARCHAR(255),
            paid_to VARCHAR(255),
            amount DECIMAL(10, 2),
            mode VARCHAR(20) CHECK (mode IN ('cash', 'online')),
            remarks TEXT,
            date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
        );
    """)

    conn.commit()
    cursor.close()
    conn.close()

# ---------- Fetch Helpers ----------

def get_projects():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT project_id, project_name FROM projects")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"project_id": row[0], "project_name": row[1]} for row in data]

def get_all_participants(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT partner_name FROM partners WHERE project_id = %s
        UNION
        SELECT sp.sub_partner_name
        FROM sub_partners sp
        JOIN partners p ON p.partner_id = sp.partner_id
        WHERE p.project_id = %s
    """
    cursor.execute(query, (project_id, project_id))
    names = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return names

# ---------- Insert Payment ----------

def record_payment(project_id, payer, payee, amount, mode, note, settlement_date):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO settlements (project_id, paid_by, paid_to, amount, mode, remarks, date)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (project_id, payer, payee, amount, mode, note, settlement_date))

    conn.commit()
    cursor.close()
    conn.close()

# ---------- Streamlit UI ----------

def main():
    st.set_page_config(page_title="Record Settlement")
    st.title("💸 Record a Settlement Payment")

    create_settlement_table()

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
        if amount == 0:
            st.error("Amount must be greater than 0.")
        else:
            record_payment(project_id, payer, payee, amount, mode, note, settlement_date)
            st.success(f"Recorded payment of ₹{amount} from {payer} to {payee}")

if __name__ == "__main__":
    main()
