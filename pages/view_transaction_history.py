# import streamlit as st
# import mysql.connector
# from mysql.connector import Error
#
# # Database connection
# def get_db_connection():
#     return mysql.connector.connect(
#         host="localhost",
#         user="root",
#         password="scooter4230",
#         database="real_estate_db"
#     )
#
# # Get all projects
# def get_projects():
#     conn = get_db_connection()
#     cursor = conn.cursor(dictionary=True)
#     cursor.execute("SELECT project_id, project_name FROM projects")
#     projects = cursor.fetchall()
#     cursor.close()
#     conn.close()
#     return projects
#
# # Get transactions for a project
# def get_transactions(project_id):
#     conn = get_db_connection()
#     cursor = conn.cursor(dictionary=True)
#     cursor.execute("""
#         SELECT transaction_id, transaction_type, paid_by, amount, mode, purpose, split_type, created_at
#         FROM transactions
#         WHERE project_id = %s
#         ORDER BY created_at DESC
#     """, (project_id,))
#     transactions = cursor.fetchall()
#     cursor.close()
#     conn.close()
#     return transactions
#
# # Streamlit page
# def main():
#     st.set_page_config(page_title="View Transaction History")
#     st.title("📜 View Transaction History")
#
#     projects = get_projects()
#     if not projects:
#         st.warning("No projects found.")
#         return
#
#     project_names = {p["project_name"]: p["project_id"] for p in projects}
#     selected_project = st.selectbox("Select a Project", list(project_names.keys()))
#
#     if selected_project:
#         project_id = project_names[selected_project]
#         transactions = get_transactions(project_id)
#
#         if not transactions:
#             st.info("No transactions found for this project.")
#         else:
#             st.subheader(f"Transaction History for '{selected_project}'")
#
#             for txn in transactions:
#                 with st.expander(f"{txn['transaction_type'].capitalize()} | ₹{txn['amount']} | {txn['created_at'].strftime('%Y-%m-%d')}"):
#                     st.markdown(f"**Paid By:** {txn['paid_by']}")
#                     st.markdown(f"**Payment Mode:** {txn['mode']}")
#                     st.markdown(f"**Purpose:** {txn['purpose']}")
#                     st.markdown(f"**Split Type:** {txn['split_type'].capitalize()}")
#                     st.markdown(f"**Transaction ID:** {txn['transaction_id']}")
#
# if __name__ == "__main__":
#     main()

# OG code







import streamlit as st
import mysql.connector
import pandas as pd

# ---------- DB Connection ----------

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="scooter4230",
        database="real_estate_db"
    )

# ---------- Fetch Project List ----------

def get_projects():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT project_name FROM projects")
    projects = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return projects

# ---------- Fetch Transactions ----------

def get_transactions(project_name):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT project_id FROM projects WHERE project_name = %s", (project_name,))
    project = cursor.fetchone()
    if not project:
        return [], []

    project_id = project["project_id"]

    cursor.execute("""
        SELECT  transaction_type, paid_by, amount, mode, purpose, split_type, created_at
        FROM transactions
        WHERE project_id = %s
        ORDER BY created_at DESC
    """, (project_id,))
    transactions = cursor.fetchall()

    cursor.close()
    conn.close()
    return transactions, project_id

# ---------- Fetch Settlements ----------

def get_settlements(project_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT payer_name, payee_name, amount, settled_at
        FROM settlements
        WHERE project_id = %s
        ORDER BY settled_at DESC
    """, (project_id,))
    settlements = cursor.fetchall()

    cursor.close()
    conn.close()
    return settlements

# ---------- Streamlit UI ----------

def main():
    st.set_page_config(page_title="Project Transactions & Settlements")
    st.title("📜 View Transaction History & Settlements")

    projects = get_projects()
    selected_project = st.selectbox("Select a Project", projects)

    if selected_project:
        st.subheader("📌 Transactions")
        transactions, project_id = get_transactions(selected_project)

        if transactions:
            df_trans = pd.DataFrame(transactions)
            df_trans.columns = [col.replace("_", " ").title() for col in df_trans.columns]
            st.dataframe(df_trans)
        else:
            st.info("No transactions found for this project.")

        st.subheader("💸 Settlements")
        settlements = get_settlements(project_id)

        if settlements:
            df_settle = pd.DataFrame(settlements)
            df_settle.columns = [col.replace("_", " ").title() for col in df_settle.columns]
            st.dataframe(df_settle)
        else:
            st.info("No settlements recorded for this project.")

if __name__ == "__main__":
    main()
