import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date

# ---------- DB Setup ----------

def get_db_connection():
    return psycopg2.connect(
        host=st.secrets["postgres"]["host"],
        database=st.secrets["postgres"]["database"],
        user=st.secrets["postgres"]["user"],
        password=st.secrets["postgres"]["password"],
        port=st.secrets["postgres"]["port"]
    )

def calculate_auto_split(conn, project_id, total_amount, paid_by):
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT partner_id, partner_name, share_percentage FROM partners WHERE project_id = %s", (project_id,))
    partners = cursor.fetchall()

    effective_shares = {}

    for partner in partners:
        partner_id = partner["partner_id"]
        pname = partner["partner_name"]
        pshare = float(partner["share_percentage"])

        cursor.execute("SELECT sub_partner_name, share_percentage FROM sub_partners WHERE partner_id = %s", (partner_id,))
        sub_partners = cursor.fetchall()

        if not sub_partners:
            effective_shares[pname] = round(pshare, 2)
        else:
            sub_partners_share_total = 0
            for sub in sub_partners:
                sname = sub["sub_partner_name"]
                sshare = float(sub["share_percentage"])
                sub_partners_share_total += sshare
                effective_shares[sname] = round(pshare * sshare / 100, 2)
            effective_shares[pname] = round((100 - sub_partners_share_total) * pshare / 100, 2)

    owed_amounts = {name: round(share * total_amount / 100, 2) for name, share in effective_shares.items()}
    payments = [{"payer": name, "receiver": paid_by, "amount": amount} for name, amount in owed_amounts.items()]
    
    cursor.close()
    return payments, effective_shares, owed_amounts

def create_transaction_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id SERIAL PRIMARY KEY,
            project_id INTEGER,
            transaction_type VARCHAR(20) CHECK (transaction_type IN ('investment', 'expense')),
            paid_by VARCHAR(255),
            amount NUMERIC(10,2),
            transaction_date DATE,
            mode VARCHAR(20) CHECK (mode IN ('cash', 'online')),
            purpose TEXT,
            split_type VARCHAR(20) CHECK (split_type IN ('auto', 'custom')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transaction_splits (
            split_id SERIAL PRIMARY KEY,
            transaction_id INTEGER,
            payer_name VARCHAR(255),
            receiver_name VARCHAR(255),
            amount NUMERIC(10,2),
            FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id) ON DELETE CASCADE
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transaction_attachments (
            attachment_id SERIAL PRIMARY KEY,
            transaction_id INTEGER,
            file_name VARCHAR(255),
            file_data BYTEA,
            description TEXT,
            FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id) ON DELETE CASCADE
        );
    """)

    conn.commit()
    cursor.close()
    conn.close()

# ---------- Data Fetch Helpers ----------

def fetch_projects():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT project_id, project_name FROM projects")
    projects = cursor.fetchall()
    cursor.close()
    conn.close()
    return projects

def fetch_all_stakeholders(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT partner_name FROM partners WHERE project_id = %s", (project_id,))
    partners = [row[0] for row in cursor.fetchall()]

    cursor.execute("""
        SELECT sp.sub_partner_name FROM sub_partners sp
        JOIN partners p ON sp.partner_id = p.partner_id
        WHERE p.project_id = %s
    """, (project_id,))
    subpartners = [row[0] for row in cursor.fetchall()]

    cursor.close()
    conn.close()
    return partners + subpartners

# ---------- Main Streamlit App ----------

def main():
    st.set_page_config(page_title="Insert Transaction")
    st.title("Insert a Transaction")
    create_transaction_tables()

    projects = fetch_projects()
    if not projects:
        st.warning("No projects found. Please create a project first.")
        return

    project_name_to_id = {name: pid for pid, name in projects}
    selected_project = st.selectbox("Select Project", list(project_name_to_id.keys()))
    if not selected_project:
        st.stop()

    project_id = project_name_to_id[selected_project]
    stakeholders = fetch_all_stakeholders(project_id)
    transaction_date = st.date_input("Transaction Date", date.today())
    transaction_type = st.selectbox("Transaction Type", ["investment", "expense"])
    paid_by = st.selectbox("Paid By", stakeholders)
    amount = st.number_input("Amount", min_value=0.0, step=0.01)
    mode = st.selectbox("Mode of Payment", ["cash", "online"])
    purpose = st.text_area("Purpose of Transaction")
    split_type = st.radio("How to split?", ["share as per ownership", "custom"])
    created_at = date.today()

    splits = []

    if split_type == "custom":
        st.markdown("### Custom Split")
        owed_amount_total = 0
        for name in stakeholders:
            owed = st.number_input(f"{name} owes", min_value=0.0, step=0.01, key=f"custom_{name}")
            if owed > 0:
                splits.append((paid_by, name, owed))
                owed_amount_total += owed

        if round(owed_amount_total, 2) != round(amount, 2):
            st.warning("⚠️ Total owed doesn't match the amount paid!")

    elif split_type == "share as per ownership":
        payments, shares, owed_amounts = calculate_auto_split(get_db_connection(), project_id, amount, paid_by)
        st.subheader("Auto-calculated splits:")
        for payment in payments:
            st.markdown(f"**{payment['payer']}** will pay **₹{payment['amount']}** to **{payment['receiver']}**")
        for key, value in owed_amounts.items():
            splits.append((paid_by, key, value))

    uploaded_files = st.file_uploader("Attach Files", type=["pdf", "jpg", "jpeg"], accept_multiple_files=True)
    file_descriptions = {}
    for file in uploaded_files:
        desc = st.text_input(f"Description for {file.name}", key=f"desc_{file.name}")
        file_descriptions[file.name] = (file, desc)

    if st.button("Submit Transaction"):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Insert transaction and get its ID
            cursor.execute("""
                INSERT INTO transactions (project_id, transaction_type, paid_by, amount, transaction_date,
                                          mode, purpose, split_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING transaction_id
            """, (
                project_id, transaction_type, paid_by, amount, transaction_date, mode, purpose,
                'auto' if split_type == "share as per ownership" else 'custom'
            ))
            transaction_id = cursor.fetchone()[0]

            for payer, receiver, split_amt in splits:
                cursor.execute("""
                    INSERT INTO transaction_splits (transaction_id, payer_name, receiver_name, amount)
                    VALUES (%s, %s, %s, %s)
                """, (transaction_id, payer, receiver, split_amt))

            for file in uploaded_files:
                file_data = file.read()
                desc = file_descriptions[file.name][1]
                cursor.execute("""
                    INSERT INTO transaction_attachments (transaction_id, file_name, file_data, description)
                    VALUES (%s, %s, %s, %s)
                """, (transaction_id, file.name, file_data, desc))

            conn.commit()
            st.success("✅ Transaction recorded successfully!")

        except Exception as e:
            st.error(f"❌ Database error: {e}")

        finally:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    main()
