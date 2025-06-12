import streamlit as st
import mysql.connector
from mysql.connector import Error

# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="scooter4230",
        database="real_estate_db"
    )

# Get all projects
def get_projects():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT project_id, project_name FROM projects")
    projects = cursor.fetchall()
    cursor.close()
    conn.close()
    return projects

# Get transactions for a project
def get_transactions(project_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT transaction_id, transaction_type, paid_by, amount, mode, purpose, split_type, created_at
        FROM transactions
        WHERE project_id = %s
        ORDER BY created_at DESC
    """, (project_id,))
    transactions = cursor.fetchall()
    cursor.close()
    conn.close()
    return transactions

# Streamlit page
def main():
    st.set_page_config(page_title="View Transaction History")
    st.title("📜 View Transaction History")

    projects = get_projects()
    if not projects:
        st.warning("No projects found.")
        return

    project_names = {p["project_name"]: p["project_id"] for p in projects}
    selected_project = st.selectbox("Select a Project", list(project_names.keys()))

    if selected_project:
        project_id = project_names[selected_project]
        transactions = get_transactions(project_id)

        if not transactions:
            st.info("No transactions found for this project.")
        else:
            st.subheader(f"Transaction History for '{selected_project}'")

            for txn in transactions:
                with st.expander(f"{txn['transaction_type'].capitalize()} | ₹{txn['amount']} | {txn['created_at'].strftime('%Y-%m-%d')}"):
                    st.markdown(f"**Paid By:** {txn['paid_by']}")
                    st.markdown(f"**Payment Mode:** {txn['mode']}")
                    st.markdown(f"**Purpose:** {txn['purpose']}")
                    st.markdown(f"**Split Type:** {txn['split_type'].capitalize()}")
                    st.markdown(f"**Transaction ID:** {txn['transaction_id']}")

if __name__ == "__main__":
    main()
