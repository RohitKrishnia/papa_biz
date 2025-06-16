import streamlit as st
import pandas as pd
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
    cursor = conn.cursor()

    cursor.execute("SELECT project_id FROM projects WHERE project_name = %s", (project_name,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        return [], None

    project_id = row[0]

    cursor.execute("""
        SELECT transaction_type, paid_by, amount, mode, purpose, split_type, created_at
        FROM transactions
        WHERE project_id = %s
        ORDER BY created_at DESC
    """, (project_id,))
    rows = cursor.fetchall()
    colnames = [desc[0] for desc in cursor.description]
    transactions = [dict(zip(colnames, r)) for r in rows]

    cursor.close()
    conn.close()
    return transactions, project_id

# ---------- Fetch Settlements ----------

def get_settlements(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT paid_by, paid_to, amount, created_at
        FROM settlements
        WHERE project_id = %s
        ORDER BY created_at DESC
    """, (project_id,))
    rows = cursor.fetchall()
    colnames = [desc[0] for desc in cursor.description]
    settlements = [dict(zip(colnames, r)) for r in rows]

    cursor.close()
    conn.close()
    return settlements

# ---------- Streamlit UI ----------

def main():
    st.set_page_config(page_title="Project Transactions & Settlements")
    st.title("📜 View Transaction History & Settlements")

    projects = get_projects()
    if not projects:
        st.warning("No projects found.")
        return

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
        if project_id is not None:
            settlements = get_settlements(project_id)
            if settlements:
                df_settle = pd.DataFrame(settlements)
                df_settle.columns = [col.replace("_", " ").title() for col in df_settle.columns]
                st.dataframe(df_settle)
            else:
                st.info("No settlements recorded for this project.")

if __name__ == "__main__":
    main()
