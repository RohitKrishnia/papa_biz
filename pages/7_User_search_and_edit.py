# import streamlit as st
# from supabase import create_client, Client

# st.set_page_config(page_title="Search & Edit User")

# @st.cache_resource
# def get_supabase() -> Client:
#     url = "https://ogecahtzmpsznesragam.supabase.co"
#     key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZWNhaHR6bXBzem5lc3JhZ2FtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5MzE0NDEsImV4cCI6MjA2NTUwNzQ0MX0.SVPUtm2-bhTRjc0XZnUII8pHt2Jc435Mr_fsEkmKpvs"
#     return create_client(url, key)

# supabase = get_supabase()

# st.title("Edit User Details")

# # --- Predefined Bank Options ---
# BANK_OPTIONS = [
#     "State Bank of India",
#     "HDFC Bank",
#     "ICICI Bank",
#     "Punjab National Bank",
#     "Axis Bank",
#     "Kotak Mahindra Bank",
#     "Union Bank of India",
#     "Bank of Baroda",
#     "Canara Bank",
#     "Yes Bank"
# ]

# # --- Search User ---
# search_term = st.text_input("Search by name (partial) or phone number")

# users_found = []
# if search_term:
#     users_resp = supabase.table("users").select("*").ilike("name", f"%{search_term}%").execute()
#     phone_resp = supabase.table("users").select("*").eq("mobile_number", search_term).execute()
#     users_found = list({u["id"]: u for u in users_resp.data + phone_resp.data}.values())

# if users_found:
#     user_names = [f"{u['name']} ({u['mobile_number']})" for u in users_found]
#     selected_user = st.selectbox("Select a user to edit", user_names)
#     user = users_found[user_names.index(selected_user)]

#     # --- Get Parent Name ---
#     parent_name = ""
#     if user.get("parent_user_id"):
#         parent_resp = supabase.table("users").select("name").eq("id", user["parent_user_id"]).execute()
#         if parent_resp.data:
#             parent_name = parent_resp.data[0]["name"]


#     all_users_resp = supabase.table("users").select("id", "name").execute()
#     all_users = all_users_resp.data

#     parent_options = [""] + [u["name"] for u in all_users if u["id"] != user["id"]]  # exclude self
#     current_parent_name = parent_name if parent_name in parent_options else ""



#     # --- Editable fields ---
#     new_name = st.text_input("Name", value=user["name"])
#     new_mobile = st.text_input("Mobile Number", value=user["mobile_number"])
#     new_email = st.text_input("Email", value=user["email"] or "")
#     new_parent_name = st.selectbox(
#         "Parent Name",
#         options=parent_options,
#         index=parent_options.index(current_parent_name) if current_parent_name in parent_options else 0
#     )

#     # --- Bank Accounts Editing ---
#     st.subheader("Bank Accounts")
#     bank_accounts_resp = supabase.table("bank_accounts").select("*").eq("user_id", user["id"]).execute()
#     bank_accounts = bank_accounts_resp.data

#     updated_bank_accounts = []
#     for idx, bank in enumerate(bank_accounts):
#         with st.expander(f"🏦 Bank Account {idx+1}"):
#             acc_no = st.text_input(f"Account Number {idx+1}", value=bank["account_number"], key=f"acc_{idx}")

#             # Dropdown for bank name
#             bank_name = st.selectbox(
#                 f"Bank Name {idx+1}",
#                 BANK_OPTIONS,
#                 index=BANK_OPTIONS.index(bank["bank_name"]) if bank["bank_name"] in BANK_OPTIONS else 0,
#                 key=f"bank_{idx}"
#             )

#             updated_bank_accounts.append({"id": bank["id"], "account_number": acc_no, "bank_name": bank_name})

#     # --- Add New Bank Account in Expander ---
#     with st.expander("➕ Add New Bank Account"):
#         new_acc_no = st.text_input("New Account Number", key="new_acc_no")
#         new_bank_name = st.selectbox("New Bank Name", BANK_OPTIONS, key="new_bank_name")

#     # --- Save Button ---
#     if st.button("Save Changes"):
#         # --- Get Parent ID from Name ---
#         parent_id_val = None
#         if new_parent_name:
#             parent_lookup = supabase.table("users").select("id").eq("name", new_parent_name).execute()
#             if parent_lookup.data:
#                 parent_id_val = parent_lookup.data[0]["id"]
#             else:
#                 st.error("❌ Parent name not found. Please enter a valid name.")
#                 st.stop()

#         # --- Update User ---
#         update_user_data = {
#             "name": new_name,
#             "mobile_number": new_mobile,
#             "email": new_email,
#             "parent_user_id": parent_id_val
#         }
#         supabase.table("users").update(update_user_data).eq("id", user["id"]).execute()

#         # --- Update Existing Bank Accounts ---
#         for bank in updated_bank_accounts:
#             supabase.table("bank_accounts").update({
#                 "account_number": bank["account_number"],
#                 "bank_name": bank["bank_name"]
#             }).eq("id", bank["id"]).execute()

#         # --- Insert New Bank Account if provided ---
#         if new_acc_no.strip():
#             supabase.table("bank_accounts").insert({
#                 "user_id": user["id"],
#                 "account_number": new_acc_no,
#                 "bank_name": new_bank_name
#             }).execute()

#         st.success("✅ User details updated successfully!")
       

# else:
#     if search_term:
#         st.warning("No users found for the given search term.")


import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="Search & Edit User")

@st.cache_resource
def get_supabase() -> Client:
    url = "https://ogecahtzmpsznesragam.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZWNhaHR6bXBzem5lc3JhZ2FtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5MzE0NDEsImV4cCI6MjA2NTUwNzQ0MX0.SVPUtm2-bhTRjc0XZnUII8pHt2Jc435Mr_fsEkmKpvs"
    return create_client(url, key)

supabase = get_supabase()

st.title("Edit User Details")

# --- Predefined Bank Options ---
BANK_OPTIONS = [
    "State Bank of India",
    "HDFC Bank",
    "ICICI Bank",
    "Punjab National Bank",
    "Axis Bank",
    "Kotak Mahindra Bank",
    "Union Bank of India",
    "Bank of Baroda",
    "Canara Bank",
    "Yes Bank"
]

# --- Search User ---
search_term = st.text_input("Search by name (partial) or phone number")

users_found = []
if search_term:
    try:
        users_resp = supabase.table("users").select("*").ilike("name", f"%{search_term}%").execute()
        phone_resp = supabase.table("users").select("*").eq("mobile_number", search_term).execute()
        users_found = list({u["id"]: u for u in (users_resp.data + phone_resp.data)}.values())
    except Exception as e:
        st.error(f"Search failed: {e}")

if users_found:
    user_names = [f"{u['name']} ({u['mobile_number']})" for u in users_found]
    selected_user = st.selectbox("Select a user to edit", user_names)
    user = users_found[user_names.index(selected_user)]

    # --- Get Parent Name ---
    parent_name = ""
    if user.get("parent_user_id"):
        parent_resp = supabase.table("users").select("name").eq("id", user["parent_user_id"]).execute()
        if parent_resp.data:
            parent_name = parent_resp.data[0]["name"]

    all_users_resp = supabase.table("users").select("id", "name").execute()
    all_users = all_users_resp.data

    parent_options = [""] + [u["name"] for u in all_users if u["id"] != user["id"]]  # exclude self
    current_parent_name = parent_name if parent_name in parent_options else ""

    # --- Editable fields ---
    new_name = st.text_input("Name", value=user["name"])
    new_mobile = st.text_input("Mobile Number", value=user["mobile_number"])
    new_email = st.text_input("Email", value=user["email"] or "")
    new_parent_name = st.selectbox(
        "Parent Name",
        options=parent_options,
        index=parent_options.index(current_parent_name) if current_parent_name in parent_options else 0
    )

    # --- Bank Accounts (Edit / Delete) ---
    st.subheader("Bank Accounts")
    bank_accounts_resp = supabase.table("bank_accounts").select("*").eq("user_id", user["id"]).execute()
    bank_accounts = bank_accounts_resp.data

    updated_bank_accounts = []
    for idx, bank in enumerate(bank_accounts):
        with st.expander(f"🏦 Bank Account {idx+1}"):
            c1, c2 = st.columns([3, 1])
            with c1:
                acc_no = st.text_input(f"Account Number {idx+1}", value=bank["account_number"], key=f"acc_{idx}")
                bank_name = st.selectbox(
                    f"Bank Name {idx+1}",
                    BANK_OPTIONS,
                    index=BANK_OPTIONS.index(bank["bank_name"]) if bank["bank_name"] in BANK_OPTIONS else 0,
                    key=f"bank_{idx}"
                )
            with c2:
                st.write("")  # spacing
                st.write("")  # spacing
                if st.button("🗑️ Delete", key=f"del_{bank['id']}"):
                    try:
                        supabase.table("bank_accounts").delete().eq("id", bank["id"]).execute()
                        st.success("Bank account deleted.")
                        st.rerun()  # refresh the list immediately
                    except Exception as e:
                        st.error(f"Could not delete bank account: {e}")

            updated_bank_accounts.append({"id": bank["id"], "account_number": acc_no, "bank_name": bank_name})

    # --- Add New Bank Account in Expander ---
    with st.expander("➕ Add New Bank Account"):
        new_acc_no = st.text_input("New Account Number", key="new_acc_no")
        new_bank_name = st.selectbox("New Bank Name", BANK_OPTIONS, key="new_bank_name")

    # --- Save Button ---
    if st.button("Save Changes"):
        # --- Resolve Parent ID from Name ---
        parent_id_val = None
        if new_parent_name:
            parent_lookup = supabase.table("users").select("id").eq("name", new_parent_name).execute()
            if parent_lookup.data:
                parent_id_val = parent_lookup.data[0]["id"]
            else:
                st.error("❌ Parent name not found. Please select a valid name.")
                st.stop()

        # --- Soft duplicate checks (no error page) ---
        # Checks if another user (id != current) already has the same name/mobile/email
        errors = []

        try:
            if new_name.strip():
                dup_name = (
                    supabase.table("users")
                    .select("id,name")
                    .eq("name", new_name.strip())
                    .neq("id", user["id"])
                    .execute()
                )
                if dup_name.data:
                    errors.append("Name is already taken by another user.")

            if (new_mobile.strip() != ""):
                dup_mobile = (
                    supabase.table("users")
                    .select("id,mobile_number")
                    .eq("mobile_number", new_mobile.strip())
                    .neq("id", user["id"])
                    .execute()
                )
                if dup_mobile.data:
                    errors.append("Mobile number is already associated with another user.")

            if (new_email.strip() !=""):
                dup_email = (
                    supabase.table("users")
                    .select("id,email")
                    .eq("email", new_email.strip())
                    .neq("id", user["id"])
                    .execute()
                )
                if dup_email.data:
                    errors.append("Email is already associated with another user.")
        except Exception as e:
            st.error(f"Validation failed: {e}")
            st.stop()

        if errors:
            st.error("❌ " + "  \n".join(errors))
            st.stop()

        # --- Update User (wrapped to avoid error page) ---
        try:
            update_user_data = {
                "name": new_name,
                "mobile_number": new_mobile,
                "email": new_email,
                "parent_user_id": parent_id_val
            }
            supabase.table("users").update(update_user_data).eq("id", user["id"]).execute()
        except Exception as e:
            # If DB still throws (e.g., a unique constraint race), surface friendly message
            msg = str(e)
            if "duplicate key" in msg.lower() or "unique" in msg.lower():
                st.error("Update failed: one of Name / Mobile / Email is already used by another user.")
            else:
                st.error(f"Update failed: {e}")
            st.stop()

        # --- Update Existing Bank Accounts ---
        try:
            for bank in updated_bank_accounts:
                supabase.table("bank_accounts").update({
                    "account_number": bank["account_number"],
                    "bank_name": bank["bank_name"]
                }).eq("id", bank["id"]).execute()
        except Exception as e:
            st.error(f"Updating bank accounts failed: {e}")
            st.stop()

        # --- Insert New Bank Account if provided ---
        try:
            if new_acc_no.strip():
                supabase.table("bank_accounts").insert({
                    "user_id": user["id"],
                    "account_number": new_acc_no.strip(),
                    "bank_name": new_bank_name
                }).execute()
        except Exception as e:
            st.error(f"Adding new bank account failed: {e}")
            st.stop()

        st.success("✅ User details updated successfully!")

else:
    if search_term:
        st.warning("No users found for the given search term.")
