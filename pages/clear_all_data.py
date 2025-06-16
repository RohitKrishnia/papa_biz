import streamlit as st
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

# ---------- Clear All Tables ----------

def clear_all_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # PostgreSQL: disable constraint checks temporarily
        cursor.execute("SET session_replication_role = 'replica';")

        tables = [
            "transaction_splits",
            "transactions",
            "attachments",
            "sub_partners",
            "partners",
            "settlements",
            "projects"
        ]

        for table in tables:
            cursor.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")

        cursor.execute("SET session_replication_role = 'origin';")
        conn.commit()
        return True

    except Exception as e:
        st.error(f"❌ Error clearing data: {e}")
        return False

    finally:
        cursor.close()
        conn.close()

# ---------- Streamlit UI ----------

def main():
    st.set_page_config(page_title="⚠️ Clear All Data")
    st.title("⚠️ Danger Zone: Clear All Project Data")

    st.warning("This will permanently delete all projects, partners, transactions, and documents.")

    if st.checkbox("Yes, I understand the consequences"):
        if st.button("🧨 Delete Everything"):
            if clear_all_tables():
                st.success("✅ All tables cleared successfully.")
            else:
                st.error("Something went wrong during the cleanup.")

if __name__ == "__main__":
    main()
