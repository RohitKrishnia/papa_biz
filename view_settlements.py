import streamlit as st
import mysql.connector
from collections import defaultdict

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="scooter4230",
        database="real_estate_db"
    )

def calculate_settlements(project_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get all transactions for the project
    cursor.execute("""
        SELECT t.transaction_id, t.amount, t.paid_by, ts.owes_from, ts.owes_to, ts.amount AS split_amount #owes_to is receiver and owes_ from is payer
        FROM transactions t
        JOIN transaction_splits ts ON t.transaction_id = ts.transaction_id
        WHERE t.project_id = %s
    """, (project_id,))

    rows = cursor.fetchall()
    net_balances = defaultdict(float)





    for row in rows:
        net_balances[row['owes_from']] -= float(row['split_amount'])
        net_balances[row['owes_to']] += float(row['split_amount'])

    # Now build who owes whom based on net balances
    owes = []
    debtors = [(k, v) for k, v in net_balances.items() if v < 0]
    creditors = [(k, v) for k, v in net_balances.items() if v > 0]

    debtors.sort(key=lambda x: x[1])
    creditors.sort(key=lambda x: x[1], reverse=True)

    i, j = 0, 0
    settlements = []

    while i < len(debtors) and j < len(creditors):
        debtor, d_amt = debtors[i]
        creditor, c_amt = creditors[j]

        transfer = min(-d_amt, c_amt)
        settlements.append((debtor, creditor, round(transfer, 2)))

        debtors[i] = (debtor, d_amt + transfer)
        creditors[j] = (creditor, c_amt - transfer)

        if abs(debtors[i][1]) < 1e-2:
            i += 1
        if abs(creditors[j][1]) < 1e-2:
            j += 1

    cursor.close()
    conn.close()
    return settlements

def main():
    st.set_page_config(page_title="View Settlements")
    st.title("Project Settlement Viewer")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT project_id, project_name FROM projects")
    projects = cursor.fetchall()
    project_dict = {name: pid for pid, name in projects}
    cursor.close()
    conn.close()

    selected_project = st.selectbox("Select a Project", list(project_dict.keys()))
    if selected_project:
        settlements = calculate_settlements(project_dict[selected_project])
        st.subheader("Net Settlements")
        if settlements:
            for debtor, creditor, amount in settlements:
                st.markdown(f"🔄 **{debtor}** owes **₹{amount}** to **{creditor}**")
        else:
            st.success("✅ All dues are settled!")

if __name__ == "__main__":
    main()
