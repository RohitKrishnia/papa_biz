import streamlit as st
import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="scooter4230",
        database="real_estate_db"
    )

def clear_all_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Disable foreign key checks to allow truncating in the right order
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

        tables = ["transaction_splits", "transactions", "attachments", "sub_partners", "partners", "projects"]
        for table in tables:
            cursor.execute(f"TRUNCATE TABLE {table}")

        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
        return True
    except mysql.connector.Error as e:
        st.error(f"Error clearing data: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def main():
    st.set_page_config(page_title="⚠️ Clear All Data")
    st.title("⚠️ Danger Zone: Clear All Project Data")

    st.warning("This will permanently delete all projects, partners, transactions, and documents.")

    if st.checkbox("Yes, I understand the consequences"):
        if st.button("Delete Everything"):
            if clear_all_tables():
                st.success("✅ All tables cleared successfully.")
            else:
                st.error("Something went wrong.")

if __name__ == "__main__":
    main()
