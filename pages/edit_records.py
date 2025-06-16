import streamlit as st
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import psycopg2

def get_db_connection():
    conn = psycopg2.connect(
                        host="db.ogecahtzmpsznesragam.supabase.co",
                        database="postgres",
                        user="postgres",
                        password="vDKOd0VmurNGkYkJ",
                        port=5432
    )
    return conn

def fetch_combined_entries(project_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 'transaction' AS type, transaction_id AS id, created_at, paid_by, amount, mode, purpose, split_type
        FROM transactions WHERE project_id = %s
    """, (project_id,))
    transactions = cursor.fetchall()

    cursor.execute("""
        SELECT 'settlement' AS type, settlement_id AS id, settled_at AS created_at, payer_name, payee_name, amount
        FROM settlements WHERE project_id = %s
    """, (project_id,))
    settlements = cursor.fetchall()

    combined = transactions + settlements
    combined.sort(key=lambda x: x['created_at'], reverse=True)

    cursor.close()
    conn.close()
    return combined


def main():
    st.set_page_config(page_title="Edit Transactions & Settlements")
    st.title("Edit Transactions and Settlements")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT project_id, project_name FROM projects")
    projects = cursor.fetchall()
    project_map = {proj["project_name"]: proj["project_id"] for proj in projects}

    selected_project_name = st.selectbox("Select Project", list(project_map.keys()))
    selected_project_id = project_map[selected_project_name]

    # --- Pagination ---
    page_size = 10
    page_number = st.number_input("Page Number", min_value=1, step=1, value=1)

    offset = (page_number - 1) * page_size

    # --- Fetch Transactions ---
    cursor.execute("""
        SELECT * FROM transactions 
        WHERE project_id = %s 
        ORDER BY created_at ASC 
        LIMIT %s OFFSET %s
    """, (selected_project_id, page_size, offset))
    transactions = cursor.fetchall()

    st.subheader("Transactions")
    for txn in transactions:
        with st.expander(f"Paid by: {txn['paid_by']} | Amount: ₹{txn['amount']} | Date: {txn['created_at'].strftime('%d-%m-%Y')}"):
            updated_paid_by = st.text_input("Paid By", txn["paid_by"], key=f"paid_by_{txn['transaction_id']}")
            updated_amount = st.number_input("Amount", value=float(txn["amount"]), key=f"amount_{txn['transaction_id']}")
            updated_mode = st.selectbox("Mode", ["cash", "online"], index=["cash", "online"].index(txn["mode"]), key=f"mode_{txn['transaction_id']}")
            updated_purpose = st.text_area("Purpose", txn["purpose"], key=f"purpose_{txn['transaction_id']}")
            updated_split_type = st.selectbox("Split Type", ["auto", "custom"], index=["auto", "custom"].index(txn["split_type"]), key=f"split_{txn['transaction_id']}")
            updated_date = st.date_input("Transaction Date", txn["created_at"].date(), key=f"date_{txn['transaction_id']}")

            if st.button("Update", key=f"update_{txn['transaction_id']}"):
                cursor.execute("""
                    UPDATE transactions SET paid_by = %s, amount = %s, mode = %s,
                    purpose = %s, split_type = %s, created_at = %s
                    WHERE transaction_id = %s
                """, (
                    updated_paid_by, updated_amount, updated_mode,
                    updated_purpose, updated_split_type, updated_date,
                    txn["transaction_id"]
                ))
                conn.commit()
                st.success("Transaction updated successfully.")
                st.rerun()

    # --- Settlements Section ---
    st.subheader("Settlements")
    cursor.execute("""
        SELECT * FROM settlements
        WHERE project_id = %s
        ORDER BY settled_at ASC
        LIMIT %s OFFSET %s
    """, (selected_project_id, page_size, offset))
    settlements = cursor.fetchall()

    for s in settlements:
        with st.expander(f"{s['payer_name']} paid {s['payee_name']} ₹{s['amount']} on {s['settled_at'].strftime('%d-%m-%Y')}"):
            updated_paid_by = st.text_input("Paid By", s["payer_name"], key=f"settle_paid_by_{s['settlement_id']}")
            updated_paid_to = st.text_input("Paid To", s["payee_name"], key=f"settle_paid_to_{s['settlement_id']}")
            updated_amount = st.number_input("Amount", value=float(s["amount"]), key=f"settle_amt_{s['settlement_id']}")
            updated_date = st.date_input("Settlement Date", s["settled_at"], key=f"settle_date_{s['settlement_id']}")

            if st.button("Update", key=f"settle_update_{s['settlement_id']}"):
                cursor.execute("""
                    UPDATE settlements
                    SET payer_name = %s, payee_name = %s, amount = %s, settled_at = %s
                    WHERE settlement_id = %s
                """, (
                    updated_paid_by, updated_paid_to, updated_amount, updated_date,
                    s["settlement_id"]
                ))
                conn.commit()
                st.success("Settlement updated successfully.")
                st.rerun()

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
