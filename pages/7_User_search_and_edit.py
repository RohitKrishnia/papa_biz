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
import base64

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
    # Only show mobile number if it exists and is not None/empty
    user_names = [
        f"{u['name']} ({u['mobile_number']})" if u.get('mobile_number') else u['name']
        for u in users_found
    ]
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
                ifsc_code = st.text_input(f"IFSC Code {idx+1} (optional)", value=bank.get("ifsc_code") or "", key=f"ifsc_{idx}")
                
                # Display existing document if available
                if bank.get("document_file_name"):
                    doc_col1, doc_col2 = st.columns([2, 1])
                    with doc_col1:
                        st.markdown(f"**Current Document:** {bank['document_file_name']}")
                        # Fetch and decode document for download
                        try:
                            bank_full = supabase.table("bank_accounts").select("document_file_data, document_file_name, document_mime_type").eq("id", bank["id"]).single().execute().data
                            if bank_full.get("document_file_data"):
                                doc_data = base64.b64decode(bank_full["document_file_data"])
                                mime_type = bank_full.get("document_mime_type") or "application/octet-stream"
                                st.download_button(
                                    "📥 Download Document",
                                    data=doc_data,
                                    file_name=bank_full["document_file_name"],
                                    mime=mime_type,
                                    key=f"download_doc_{idx}"
                                )
                        except Exception as e:
                            st.error(f"Could not load document: {e}")
                    with doc_col2:
                        if st.button("🗑️ Remove Document", key=f"rm_doc_{idx}"):
                            try:
                                supabase.table("bank_accounts").update({
                                    "document_file_data": None,
                                    "document_file_name": None,
                                    "document_mime_type": None
                                }).eq("id", bank["id"]).execute()
                                st.success("Document removed.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Could not remove document: {e}")
                
                # Upload new/update document
                new_doc = st.file_uploader(f"Upload/Update Document {idx+1} (PDF/JPEG) - optional", type=["pdf", "jpg", "jpeg"], key=f"new_doc_{idx}")
                
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

            updated_bank_accounts.append({
                "id": bank["id"], 
                "account_number": acc_no, 
                "bank_name": bank_name,
                "ifsc_code": ifsc_code,
                "new_document": new_doc
            })

    # --- Add New Bank Account in Expander ---
    with st.expander("➕ Add New Bank Account"):
        new_acc_no = st.text_input("New Account Number", key="new_acc_no")
        new_bank_name = st.selectbox("New Bank Name", BANK_OPTIONS, key="new_bank_name")
        new_ifsc_code = st.text_input("IFSC Code (optional)", key="new_ifsc_code")
        new_doc_file = st.file_uploader("Upload Document (PDF/JPEG) - optional", type=["pdf", "jpg", "jpeg"], key="new_doc_file")

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
                update_data = {
                    "account_number": bank["account_number"],
                    "bank_name": bank["bank_name"],
                    "ifsc_code": (bank.get("ifsc_code") or "").strip() or None
                }
                
                # Handle document update if new document uploaded
                if bank.get("new_document"):
                    update_data["document_file_data"] = base64.b64encode(bank["new_document"].read()).decode("utf-8")
                    update_data["document_file_name"] = bank["new_document"].name
                    # Determine MIME type
                    if bank["new_document"].name.lower().endswith('.pdf'):
                        update_data["document_mime_type"] = "application/pdf"
                    elif bank["new_document"].name.lower().endswith(('.jpg', '.jpeg')):
                        update_data["document_mime_type"] = "image/jpeg"
                
                supabase.table("bank_accounts").update(update_data).eq("id", bank["id"]).execute()
        except Exception as e:
            st.error(f"Updating bank accounts failed: {e}")
            st.stop()

        # --- Insert New Bank Account if provided ---
        try:
            if new_acc_no.strip():
                new_account_data = {
                    "user_id": user["id"],
                    "account_number": new_acc_no.strip(),
                    "bank_name": new_bank_name,
                    "ifsc_code": (new_ifsc_code or "").strip() or None
                }
                
                # Handle document upload if provided
                if new_doc_file:
                    new_account_data["document_file_data"] = base64.b64encode(new_doc_file.read()).decode("utf-8")
                    new_account_data["document_file_name"] = new_doc_file.name
                    # Determine MIME type
                    if new_doc_file.name.lower().endswith('.pdf'):
                        new_account_data["document_mime_type"] = "application/pdf"
                    elif new_doc_file.name.lower().endswith(('.jpg', '.jpeg')):
                        new_account_data["document_mime_type"] = "image/jpeg"
                
                supabase.table("bank_accounts").insert(new_account_data).execute()
        except Exception as e:
            st.error(f"Adding new bank account failed: {e}")
            st.stop()

        st.success("✅ User details updated successfully!")

    # --- Delete User Section ---
    st.divider()
    st.subheader("⚠️ Danger Zone")
    
    with st.expander("🗑️ Delete User", expanded=False):
        st.warning("**WARNING:** This will permanently delete the user. This action cannot be undone!")
        st.markdown("""
        **The user can only be deleted if they are not referenced in:**
        - Any transactions (as paid_by, paid_to, or paid_via)
        - Any transaction sources
        - Any partners or sub-partners
        - Any payouts or payout distributions
        - Any comments
        - Any bank accounts
        - As a parent of another user
        """)
        
        if st.button("🗑️ Delete User", type="primary", use_container_width=True):
            user_id = user["id"]
            
            # Check all references
            references = []
            
            # 1. Check transactions (paid_by, paid_to, paid_via)
            txn_paid_by = supabase.table("transactions").select("transaction_id, project_id, paid_by").eq("paid_by", user_id).execute().data or []
            if txn_paid_by:
                project_ids = list(set([t["project_id"] for t in txn_paid_by]))
                projects = supabase.table("projects").select("project_id, project_name").in_("project_id", project_ids).execute().data or []
                project_names = [p["project_name"] for p in projects]
                references.append(f"**Transactions (Paid By):** {len(txn_paid_by)} transaction(s) in project(s): {', '.join(project_names)}")
            
            txn_paid_to = supabase.table("transactions").select("transaction_id, project_id, paid_to").eq("paid_to", user_id).execute().data or []
            if txn_paid_to:
                project_ids = list(set([t["project_id"] for t in txn_paid_to]))
                projects = supabase.table("projects").select("project_id, project_name").in_("project_id", project_ids).execute().data or []
                project_names = [p["project_name"] for p in projects]
                references.append(f"**Transactions (Paid To):** {len(txn_paid_to)} transaction(s) in project(s): {', '.join(project_names)}")
            
            txn_paid_via = supabase.table("transactions").select("transaction_id, project_id, paid_via").eq("paid_via", user_id).execute().data or []
            if txn_paid_via:
                project_ids = list(set([t["project_id"] for t in txn_paid_via]))
                projects = supabase.table("projects").select("project_id, project_name").in_("project_id", project_ids).execute().data or []
                project_names = [p["project_name"] for p in projects]
                references.append(f"**Transactions (Paid Via):** {len(txn_paid_via)} transaction(s) in project(s): {', '.join(project_names)}")
            
            # 2. Check transaction_sources
            txn_sources = supabase.table("transaction_sources").select("transaction_id, source_id").eq("source_id", user_id).execute().data or []
            if txn_sources:
                txn_ids = list(set([s["transaction_id"] for s in txn_sources]))
                txns = supabase.table("transactions").select("transaction_id, project_id").in_("transaction_id", txn_ids).execute().data or []
                project_ids = list(set([t["project_id"] for t in txns]))
                projects = supabase.table("projects").select("project_id, project_name").in_("project_id", project_ids).execute().data or []
                project_names = [p["project_name"] for p in projects]
                references.append(f"**Transaction Sources:** {len(txn_sources)} source entry/entries in project(s): {', '.join(project_names)}")
            
            # 3. Check partners
            partners = supabase.table("partners").select("partner_id, project_id, partner_user_id").eq("partner_user_id", user_id).execute().data or []
            if partners:
                project_ids = list(set([p["project_id"] for p in partners]))
                projects = supabase.table("projects").select("project_id, project_name").in_("project_id", project_ids).execute().data or []
                project_names = [p["project_name"] for p in projects]
                references.append(f"**Partners:** Partner in {len(partners)} project(s): {', '.join(project_names)}")
            
            # 4. Check sub_partners
            sub_partners = supabase.table("sub_partners").select("sub_partner_id, partner_id, sub_partner_user_id").eq("sub_partner_user_id", user_id).execute().data or []
            if sub_partners:
                partner_ids = list(set([sp["partner_id"] for sp in sub_partners]))
                partners_data = supabase.table("partners").select("partner_id, project_id").in_("partner_id", partner_ids).execute().data or []
                project_ids = list(set([p["project_id"] for p in partners_data]))
                projects = supabase.table("projects").select("project_id, project_name").in_("project_id", project_ids).execute().data or []
                project_names = [p["project_name"] for p in projects]
                references.append(f"**Sub-Partners:** Sub-partner in {len(sub_partners)} project(s): {', '.join(project_names)}")
            
            # 5. Check payouts (received_by)
            payouts = supabase.table("payouts").select("payout_id, project_id, received_by").eq("received_by", user_id).execute().data or []
            if payouts:
                project_ids = list(set([p["project_id"] for p in payouts]))
                projects = supabase.table("projects").select("project_id, project_name").in_("project_id", project_ids).execute().data or []
                project_names = [p["project_name"] for p in projects]
                references.append(f"**Payouts:** {len(payouts)} payout(s) in project(s): {', '.join(project_names)}")
            
            # 6. Check payout_distributions
            payout_dists = supabase.table("payout_distributions").select("distribution_id, payout_id, user_id").eq("user_id", user_id).execute().data or []
            if payout_dists:
                payout_ids = list(set([pd["payout_id"] for pd in payout_dists]))
                payouts_data = supabase.table("payouts").select("payout_id, project_id").in_("payout_id", payout_ids).execute().data or []
                project_ids = list(set([p["project_id"] for p in payouts_data]))
                projects = supabase.table("projects").select("project_id, project_name").in_("project_id", project_ids).execute().data or []
                project_names = [p["project_name"] for p in projects]
                references.append(f"**Payout Distributions:** {len(payout_dists)} distribution(s) in project(s): {', '.join(project_names)}")
            
            # 7. Check comments
            comments = supabase.table("comments").select("comment_id, transaction_id, user_id").eq("user_id", user_id).execute().data or []
            if comments:
                txn_ids = list(set([c["transaction_id"] for c in comments if c.get("transaction_id")]))
                if txn_ids:
                    txns = supabase.table("transactions").select("transaction_id, project_id").in_("transaction_id", txn_ids).execute().data or []
                    project_ids = list(set([t["project_id"] for t in txns]))
                    projects = supabase.table("projects").select("project_id, project_name").in_("project_id", project_ids).execute().data or []
                    project_names = [p["project_name"] for p in projects]
                    references.append(f"**Comments:** {len(comments)} comment(s) in project(s): {', '.join(project_names)}")
                else:
                    references.append(f"**Comments:** {len(comments)} comment(s)")
            
            # 8. Check bank_accounts
            bank_accounts = supabase.table("bank_accounts").select("id, user_id").eq("user_id", user_id).execute().data or []
            if bank_accounts:
                references.append(f"**Bank Accounts:** {len(bank_accounts)} bank account(s) associated")
            
            # 9. Check if user is a parent of another user
            children = supabase.table("users").select("id, name, parent_user_id").eq("parent_user_id", user_id).execute().data or []
            if children:
                child_names = [c["name"] for c in children]
                references.append(f"**Parent User:** Has {len(children)} child user(s): {', '.join(child_names)}")
            
            # If there are references, show error and prevent deletion
            if references:
                st.error("❌ **Cannot delete user.** The user is referenced in the following:")
                for ref in references:
                    st.markdown(f"- {ref}")
                st.stop()
            
            # If no references, proceed with deletion
            try:
                # Delete bank accounts first (if any exist, though we checked above)
                supabase.table("bank_accounts").delete().eq("user_id", user_id).execute()
                
                # Delete the user
                supabase.table("users").delete().eq("id", user_id).execute()
                
                st.success(f"✅ User '{user['name']}' deleted successfully!")
                st.toast("User deleted.", icon="✅")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Failed to delete user: {e}")

else:
    if search_term:
        st.warning("No users found for the given search term.")
