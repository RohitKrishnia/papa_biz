import streamlit as st
from supabase import create_client, Client

# ---------- DB Connection ----------
st.set_page_config(page_title="⚠️ Clear All Data")

@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)

supabase = get_supabase_client()

# ---------- Clear All Tables ----------

def clear_all_tables():
    try:
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
            if table == "transaction_splits":

                response = supabase.table(table).delete().neq(table[12:-1] + "_id", -1).execute()
            else:
                response = supabase.table(table).delete().neq(table[:-1] + "_id", -1).execute()

            if response.data is None:
                raise Exception(f"Failed to clear table '{table}': {response}")

        return True

    except Exception as e:
        st.error(f"❌ Error clearing data: {e}")
        return False

def main():
    
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
