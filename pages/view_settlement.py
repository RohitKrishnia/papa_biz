import streamlit as st
import mysql.connector
from collections import defaultdict

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
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT project_id, project_name FROM projects")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

# ---------- Fetch All Debts ----------

def get_all_debts(project_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # cursor.execute("""
    #     SELECT owes_to, owes_from, amount FROM transaction_splits
    #     WHERE project_id = %s
    # """, (project_id,))

    cursor.execute("""
                   SELECT 
                          ts.owes_from as debtor,
                          ts.owes_to as creditor,
                          ts.amount 
                   FROM transaction_splits ts
            JOIN transactions t
                   ON t.transaction_id = ts.transaction_id
                   WHERE t.project_id = %s
                   """, (project_id,))
    debts = cursor.fetchall()

    cursor.close()
    conn.close()
    return debts

# ---------- Fetch Settlements ----------

def get_all_settlements(project_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT payer_name AS debtor, payee_name AS creditor, amount
        FROM settlements
        WHERE project_id = %s
    """, (project_id,))
    settlements = cursor.fetchall()

    cursor.close()
    conn.close()
    return settlements

# ---------- Compute Net Settlements ----------

def calculate_net_balances(debts, settlements):
    balance_sheet = defaultdict(lambda: defaultdict(float))

    # Add all pending debts
    for entry in debts:
        d = entry['debtor']
        c = entry['creditor']
        amt = float(entry['amount'])
        balance_sheet[d][c] += amt


    # Subtract recorded payments
    for entry in settlements:
        d = entry['debtor']
        c = entry['creditor']
        amt = float(entry['amount'])
        balance_sheet[d][c] -= amt


    # st.write(balance_sheet)

    net_balances = defaultdict(float)

    for settlement in settlements:
        net_balances[settlement['owes_from']] -= float(row['split_amount'])
        net_balances[row['owes_to']] += float(row['split_amount'])






    # for row in rows:
    #     net_balances[row['owes_from']] -= float(row['split_amount'])
    #     net_balances[row['owes_to']] += float(row['split_amount'])
    #
    # # Now build who owes whom based on net balances
    # owes = []
    # debtors = [(k, v) for k, v in net_balances.items() if v < 0]
    # creditors = [(k, v) for k, v in net_balances.items() if v > 0]
    #
    # debtors.sort(key=lambda x: x[1])
    # creditors.sort(key=lambda x: x[1], reverse=True)



    # Clean up near-zero values and flatten

    # i, j = 0, 0
    # settlements = []
    #
    # while i < len(debtors) and j < len(creditors):
    #     debtor, d_amt = debtors[i]
    #     creditor, c_amt = creditors[j]
    #
    #     transfer = min(-d_amt, c_amt)
    #     settlements.append((debtor, creditor, round(transfer, 2)))
    #
    #     debtors[i] = (debtor, d_amt + transfer)
    #     creditors[j] = (creditor, c_amt - transfer)
    #
    #     if abs(debtors[i][1]) < 1e-2:
    #         i += 1
    #     if abs(creditors[j][1]) < 1e-2:
    #         j += 1
    #
    #
    # return settlements
    final_settlements = []
    for d, creditors in balance_sheet.items():
        for c, amt in creditors.items():
            if round(amt, 2) > 0:
                final_settlements.append({
                    "from": d,
                    "to": c,
                    "amount": round(amt, 2)
                })

    return final_settlements

# ---------- Streamlit UI ----------
def total_settlements(project_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
                   SELECT ts.owes_from as debtor,
                          ts.owes_to   as creditor,
                          ts.amount
                   FROM transaction_splits ts
                            JOIN transactions t
                                 ON t.transaction_id = ts.transaction_id
                   WHERE t.project_id = %s
                   """, (project_id,))
    rows1 = cursor.fetchall()
    cursor.execute("""
                   SELECT payer_name AS debtor, payee_name AS creditor, amount
                   FROM settlements
                   WHERE project_id = %s
                   """, (project_id,))
    rows2 = cursor.fetchall()
    net_balances = defaultdict(float)
    for row in rows1:
        net_balances[row['debtor']] -= float(row['amount'])
        net_balances[row['creditor']] += float(row['amount'])
    for row in rows2:
        net_balances[row['debtor']] -= float(row['amount'])
        net_balances[row['creditor']] += float(row['amount'])




    cursor.close()
    conn.close()

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
    st.title("💰 Project Settlements Overview")

    projects = get_projects()
    if not projects:
        st.warning("No projects available.")
        return

    project_map = {p["project_name"]: p["project_id"] for p in projects}
    selected_project = st.selectbox("Select a Project", list(project_map.keys()))
    project_id = project_map[selected_project]

    # debts = get_all_debts(project_id)
    settlements = total_settlements(project_id)

    st.subheader("Net Settlements")
    if settlements:
        for debtor, creditor, amount in settlements:
            st.markdown(f"🔄 **{debtor}** owes **₹{amount}** to **{creditor}**")
    else:
        st.success("✅ All dues are settled!")



    # if not debts:
    #     st.info("No debt records found for this project.")
    #     return





if __name__ == "__main__":
    main()
