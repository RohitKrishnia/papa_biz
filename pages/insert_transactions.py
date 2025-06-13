import streamlit as st
import mysql.connector
from datetime import date


# ---------- DB Setup ----------

def calculate_auto_split(conn, project_id, total_amount, paid_by):
    cursor = conn.cursor(dictionary=True)

    # Fetch all partners and their shares
    cursor.execute("SELECT partner_id, partner_name, share_percentage FROM partners WHERE project_id = %s", (project_id,))
    partners = cursor.fetchall()
   
    effective_shares = {}

    for partner in partners:
        partner_id = partner["partner_id"]
        pname = partner["partner_name"]
        pshare = float(partner["share_percentage"])

        # Check sub-partners under each partner
        cursor.execute("SELECT sub_partner_name, share_percentage FROM sub_partners WHERE partner_id = %s", (partner_id,))
        sub_partners = cursor.fetchall()

        if not sub_partners:
            effective_shares[pname] = round(pshare, 2)
        else:
            
            sub_partners_share_total = 0
            for sub in sub_partners:
                sname = sub["sub_partner_name"]
                sshare = float(sub["share_percentage"])
                sub_partners_share_total = sub_partners_share_total + sshare
                effective_shares[sname] = round(pshare * sshare / 100, 2)
            effective_shares[pname] = (100-sub_partners_share_total)*(round(pshare, 2))/100


            # after each sub partner 

    # Calculate what each member owes
   
    
    owed_amounts = {name: round(share * total_amount / 100, 2) for name, share in effective_shares.items()}

    # Remove the payer
    # if paid_by in owed_amounts:
    #     del owed_amounts[paid_by]

  

    # Final payments: Who pays the payer and how much
    payments = [{"payer": name, "receiver": paid_by, "amount": amount} for name, amount in owed_amounts.items()]




    cursor.close()
    return payments, effective_shares, owed_amounts


def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="scooter4230",
        database="real_estate_db"
    )
    
def create_transaction_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Transactions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INT AUTO_INCREMENT PRIMARY KEY,
            project_id INT,
            transaction_type ENUM('investment', 'expense'),
            paid_by VARCHAR(255),
            amount DECIMAL(10,2),
            transaction_date DATE,
            mode ENUM('cash', 'online'),
            purpose TEXT,
            split_type ENUM('auto', 'custom'),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
        );
    """)

    # Splits Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transaction_splits (
            split_id INT AUTO_INCREMENT PRIMARY KEY,
            transaction_id INT,
            payer_name VARCHAR(255),
            receiver_name VARCHAR(255),
            amount DECIMAL(10,2),
            FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id) ON DELETE CASCADE
        );
    """)

    # Attachments Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transaction_attachments (
            attachment_id INT AUTO_INCREMENT PRIMARY KEY,
            transaction_id INT,
            file_name VARCHAR(255),
            file_data LONGBLOB,
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
        for key,value in owed_amounts.items():
            splits.append((paid_by, key, value))

    
    
        # st.info("Automatic split based on ownership structure will be added in the next version.")
        # To be implemented next

    uploaded_files = st.file_uploader("Attach Files", type=["pdf", "jpg", "jpeg"], accept_multiple_files=True)
    file_descriptions = {}
    for file in uploaded_files:
        desc = st.text_input(f"Description for {file.name}", key=f"desc_{file.name}")
        file_descriptions[file.name] = (file, desc)

    if st.button("Submit Transaction"):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Insert transaction
            cursor.execute("""
                           INSERT INTO transactions (project_id, transaction_type, paid_by, amount, transaction_date,
                                                     mode, purpose, split_type)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                           """, (
                               project_id, transaction_type, paid_by, amount, transaction_date, mode, purpose,
                               'auto'
                           ))
            transaction_id = cursor.lastrowid

            # Insert splits (example for auto-split logic - assume `splits` is a list of tuples)
            # splits = [(payer_name, receiver_name, amount), ...]
            for payer, receiver, split_amt in splits:
                cursor.execute("""
                               INSERT INTO transaction_splits (transaction_id, payer_name, receiver_name, amount)
                               VALUES (%s, %s, %s, %s)
                               """, (transaction_id, payer, receiver, split_amt))

            # Insert attachments
            for file in uploaded_files:
                file_data = file.read()
                desc = st.text_input(f"Description for {file.name}", key=f"desc_{file.name}")
                cursor.execute("""
                               INSERT INTO transaction_attachments (transaction_id, file_name, file_data, description)
                               VALUES (%s, %s, %s, %s)
                               """, (transaction_id, file.name, file_data, desc))

            conn.commit()
            st.success("✅ Transaction recorded successfully!")

        except mysql.connector.Error as e:
            st.error(f"❌ Database error: {e}")

        finally:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    main()
