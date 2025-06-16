import streamlit as st
import mysql.connector
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

# ---------- Fetch All Unique Names ----------

def get_all_people_names():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all names from partners and sub_partners
    cursor.execute("SELECT DISTINCT partner_name FROM partners")
    partner_names = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT sub_partner_name FROM sub_partners")
    sub_partner_names = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT receiver_name FROM transaction_splits")
    debtors = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT payer_name FROM transaction_splits")
    creditors = [row[0] for row in cursor.fetchall()]

    # Settlements
    cursor.execute("SELECT DISTINCT payer_name FROM settlements")
    payers = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT payee_name FROM settlements")
    payees = [row[0] for row in cursor.fetchall()]

    all_names = set(partner_names + sub_partner_names + debtors + creditors + payers + payees)

    cursor.close()
    conn.close()

    return sorted(list(all_names))

# ---------- Compute Total Owed Between Two People ----------

def compute_owed_amount(person1, person2):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Total owed from person1 to person2
    cursor.execute("""
        SELECT SUM(amount) AS total_debt
        FROM transaction_splits
        WHERE receiver_name= %s AND payer_name = %s
    """, (person1, person2))
    debt_result = cursor.fetchone()
    total_debt = debt_result['total_debt'] if debt_result['total_debt'] else 0.0




    # Total settled payments from person1 to person2
    cursor.execute("""
        SELECT SUM(amount) AS total_paid
        FROM settlements
        WHERE payer_name = %s AND payee_name = %s
    """, (person1, person2))
    payment_result = cursor.fetchone()
    total_paid = payment_result['total_paid'] if payment_result['total_paid'] else 0.0



    cursor.close()
    conn.close()

    net_amount = round(float(total_debt) - float(total_paid), 2)
    return net_amount

# ---------- Streamlit UI ----------

def main():
    st.set_page_config(page_title="Person-to-Person Debt Summary")
    st.title("🔍 Person-to-Person Net Owed Amount Across All Projects")

    all_names = get_all_people_names()

    person1 = st.selectbox("Select Debtor (Person 1)", all_names)
    person2 = st.selectbox("Select Creditor (Person 2)", all_names)

    if person1 == person2:
        st.warning("Please select two different people.")
        return

    if st.button("Calculate"):
        amount = compute_owed_amount(person1, person2)
        if amount <= 0:
            st.success(f"✅ {person1} owes nothing to {person2}.")
        else:
            st.error(f"💰 {person1} owes ₹{amount} to {person2} across all projects.")

if __name__ == "__main__":
    main()




