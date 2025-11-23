# import streamlit as st
# from supabase import create_client, Client

# st.set_page_config(page_title="Add Users")

# @st.cache_resource
# def get_supabase() -> Client:
#     url = "https://ogecahtzmpsznesragam.supabase.co"
#     key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZWNhaHR6bXBzem5lc3JhZ2FtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5MzE0NDEsImV4cCI6MjA2NTUwNzQ0MX0.SVPUtm2-bhTRjc0XZnUII8pHt2Jc435Mr_fsEkmKpvs"
#     return create_client(url, key)

# supabase = get_supabase()




# st.header("Add New User")

# # 1. User details
# name = st.text_input("Name").strip()
# mobile = st.text_input("Mobile Number").strip()
# email = st.text_input("Email").strip()

# # Fetch existing users for parent selection
# users_list = supabase.table("users").select("id, name").execute().data
# user_options = {u["name"]: u["id"] for u in users_list}
# parent_name = st.selectbox("Parent User (optional)", ["None"] + list(user_options.keys()))
# parent_id = user_options.get(parent_name) if parent_name != "None" else None

# # 2. Bank accounts section
# st.subheader("Bank Accounts")

# # List of major Indian banks
# bank_name_options = [
#     "State Bank of India (SBI)",
#     "Punjab National Bank (PNB)",
#     "HDFC Bank",
#     "ICICI Bank",
#     "Axis Bank",
#     "Kotak Mahindra Bank",
#     "Bank of Baroda",
#     "Union Bank of India",
#     "Canara Bank",
#     "IndusInd Bank",
#     "Yes Bank",
#     "IDFC FIRST Bank",
#     "Central Bank of India",
#     "Indian Bank",
#     "Bank of India",
# ]

# bank_accounts = []
# num_accounts = st.number_input("Number of Bank Accounts", min_value=0, step=1)

# for i in range(num_accounts):
#     st.markdown(f"**Bank Account {i+1}**")
#     bank_name = st.selectbox(
#         f"Bank Name {i+1}",
#         bank_name_options,
#         key=f"bank_name_{i}"
#     )
#     account_number = st.text_input(f"Account Number {i+1}", key=f"account_number_{i}")
#     bank_accounts.append({"bank_name": bank_name, "account_number": account_number})


# # 3. Submit
# if st.button("Add User"):
#     # --- Check if user already exists ---
#     existing_user = supabase.table("users").select("id, name, mobile_number").or_(
#         f"name.eq.{name},mobile_number.eq.{mobile}"
#     ).execute().data




#     if existing_user:
#         existing = existing_user[0]
#         if existing["name"] == name:
#             st.error(f"A user with the name '{name}' already exists.")
#         elif existing["mobile_number"] == mobile:
#             st.error(f"A user with the mobile number '{mobile}' already exists.")
#     else:
#         # --- Insert into users table ---
#         user_insert = supabase.table("users").insert({
#             "name": name,
#             "mobile_number": mobile,
#             "email": email,
#             "parent_user_id": parent_id
#         }).execute()

#         if user_insert.data:
#             user_id = user_insert.data[0]["id"]

#             # Insert bank accounts
#             for account in bank_accounts:
#                 supabase.table("bank_accounts").insert({
#                     "user_id": user_id,
#                     "bank_name": account["bank_name"],
#                     "account_number": account["account_number"]
#                 }).execute()

#             st.success("User and bank accounts added successfully!")
#         else:
#             st.error("Error adding user")



import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="Add Users")

@st.cache_resource
def get_supabase() -> Client:
    url = "https://ogecahtzmpsznesragam.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZWNhaHR6bXBzem5lc3JhZ2FtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5MzE0NDEsImV4cCI6MjA2NTUwNzQ0MX0.SVPUtm2-bhTRjc0XZnUII8pHt2Jc435Mr_fsEkmKpvs"
    return create_client(url, key)

supabase = get_supabase()

st.header("Add New User")

# Utility → convert blank string to None
def to_null(value: str):
    value = (value or "").strip()
    return value if value else None


# 1. User details
name   = (st.text_input("Name") or "").strip()      # keep Name required
mobile = to_null(st.text_input("Mobile Number"))
email  = to_null(st.text_input("Email"))

# Fetch existing users for parent selection
users_list = supabase.table("users").select("id, name").execute().data
user_options = {u["name"]: u["id"] for u in users_list}
parent_name = st.selectbox("Parent User (optional)", ["None"] + list(user_options.keys()))
parent_id   = user_options.get(parent_name) if parent_name != "None" else None

# 2. Bank accounts section
st.subheader("Bank Accounts")

bank_name_options = [
    "State Bank of India (SBI)", "Punjab National Bank (PNB)", "HDFC Bank", "ICICI Bank",
    "Axis Bank", "Kotak Mahindra Bank", "Bank of Baroda", "Union Bank of India",
    "Canara Bank", "IndusInd Bank", "Yes Bank", "IDFC FIRST Bank",
    "Central Bank of India", "Indian Bank", "Bank of India",
]

bank_accounts = []
num_accounts = st.number_input("Number of Bank Accounts", min_value=0, step=1)

for i in range(num_accounts):
    st.markdown(f"**Bank Account {i+1}**")
    bank_name = st.selectbox(
        f"Bank Name {i+1}",
        bank_name_options,
        key=f"bank_name_{i}"
    )
    account_number = st.text_input(f"Account Number {i+1}", key=f"account_number_{i}")
    bank_accounts.append({
        "bank_name": to_null(bank_name),
        "account_number": to_null(account_number),
    })


# 3. Submit
if st.button("Add User"):

    if not name:
        st.error("Name is required.")
        st.stop()

    # --- Duplicate check only when non-null ---
    filters = []
    if mobile:
        filters.append(f"mobile_number.eq.{mobile}")
    if name:
        filters.append(f"name.eq.{name}")

    existing_user = []
    if filters:
        filter_string = ",".join(filters)
        existing_user = supabase.table("users").select("id, name, mobile_number").or_(filter_string).execute().data

    if existing_user:
        existing = existing_user[0]
        if existing["name"] == name:
            st.error(f"A user with the name '{name}' already exists.")
        elif mobile and existing["mobile_number"] == mobile:
            st.error(f"A user with the mobile number '{mobile}' already exists.")

    else:
        # --- Insert into users table (mobile/email can be None → NULL) ---
        user_insert = supabase.table("users").insert({
            "name": name,
            "mobile_number": mobile,
            "email": email,
            "parent_user_id": parent_id
        }).execute()

        if user_insert.data:
            user_id = user_insert.data[0]["id"]

            # Filter valid bank accounts — store only those with both name + number
            valid_accounts = [
                acct for acct in bank_accounts
                if acct["bank_name"] is not None and acct["account_number"] is not None
            ]

            # Insert valid bank accounts
            for account in valid_accounts:
                supabase.table("bank_accounts").insert({
                    "user_id": user_id,
                    "bank_name": account["bank_name"],
                    "account_number": account["account_number"]
                }).execute()

            st.success("✅ User and bank accounts added successfully!")
        else:
            st.error("❌ Error adding user")
