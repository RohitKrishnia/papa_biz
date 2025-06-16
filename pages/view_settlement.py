import streamlit as st
from collections import defaultdict
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
    cursor.execute("SELECT project_id, project_name FROM projects")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"project_id": row[0], "project_name": row[1]} for row in rows]

# ---------- Fetch All Debts ----------

def get_all_debts(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            ts.receiver_name as debtor,
            ts.payer_name as creditor,
            ts.amount 
        FROM transaction_splits ts
        JOIN transactions t ON t.transaction_id = ts.transaction_id
        WHERE t.project_id = %s
    """, (project_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"debtor": r[0], "creditor": r[1], "amount": r[2]} for r in rows]

# ---------- Fetch Settlements ----------

def get_all_settlements(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT payer_name AS debtor, payee_name AS creditor, amount
        FROM settlements
        WHERE project_id = %s
    """, (project_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"debtor": r[0], "creditor": r[1], "amount": r[2]} for r in rows]

# ---------- Compute Net Settlements (Not used in main but fixed anyway) ----------

def calculate_net_balances(debts, settlements):
    balance_sheet = defaultdict(lambda: defaultdict(float))

    for entry in debts:
        balance_sheet[entry['debtor']][entry['creditor']] += float(entry['amount'])

    for entry in settlements:
        balance_sheet[entry['debtor']][entry['creditor']] -= float(entry['amount'])

    final_settlements = []
    for debtor, creditors in balance_sheet.items():
        for creditor, amt in creditors.items():
            if round(amt, 2) > 0:
                final_settlements.append({
                    "from": debtor,
                    "to": creditor,
                    "amount": round(amt, 2)
                })
    return final_settlements

# ---------- Compute Net Summary for Display ----------

def total_settlements(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Debts
    cursor.execute("""
        SELECT ts.receiver_name as debtor,
               ts.payer_name   as creditor,
               ts.amount
        FROM transaction_splits ts
        JOIN transactions t ON t.transaction_id = ts.transaction_id
        WHERE t.project_id = %s
    """, (project_id,))
    rows1 = cursor.fetchall()

    # Settlements
    cursor.execute("""
        SELECT paid_by AS creditor, paid_to AS debtor, amount
        FROM settlements
        WHERE project_id = %s
    """, (project_id,))
    rows2 = cursor.fetchall()

    cursor.close()
    conn.close()

    net_balances = defaultdict(float)

    for row in rows1:
        net_balances[row[0]] -= float(row[2])  # debtor
        net_balances[row[1]] += float(row[2])  # creditor

    for row in rows2:
        net_balances[row[1]] -= float(row[2])  # debtor
        net_balances[row[0]] += float(row[2])  # creditor

    # Create final settlements
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

    return settlements

# ---------- Streamlit UI ----------

def main():
    st.set_page_config(page_title="View Settlements")
    st.title("💰 Project Settlements Overview")

    projects = get_projects()
    if not projects:
        st.warning("No projects available.")
        return

    project_map = {p["project_name"]: p["project_id"] for p in projects}
    selected_project = st.selectbox("Select a Project", list(project_map.keys()))
    project_id = project_map[selected_project]

    settlements = total_settlements(project_id)

    st.subheader("Net Settlements")
    if settlements:
        for debtor, creditor, amount in settlements:
            st.markdown(f"🔄 **{debtor}** owes **₹{amount}** to **{creditor}**")
    else:
        st.success("✅ All dues are settled!")

if __name__ == "__main__":
    main()
