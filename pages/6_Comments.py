# pages/comments.py
import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# ---------- Page config ----------
st.set_page_config(page_title="Transaction Comments")

# ---------- Supabase client ----------
@st.cache_resource
def get_supabase() -> Client:
    url = "https://ogecahtzmpsznesragam.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZWNhaHR6bXBzem5lc3JhZ2FtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5MzE0NDEsImV4cCI6MjA2NTUwNzQ0MX0.SVPUtm2-bhTRjc0XZnUII8pHt2Jc435Mr_fsEkmKpvs"
    return create_client(url, key)
    
supabase = get_supabase()

# ---------- Helpers ----------
def get_projects():
    res = supabase.table("projects").select("project_id, project_name").order("project_name").execute()
    return res.data or []

def get_transactions_for_project(project_id):
    res = supabase.table("transactions").select("transaction_id, paid_by, amount, transaction_date, purpose, created_at").eq("project_id", project_id).order("created_at", desc=True).execute()
    return res.data or []

def get_stakeholders_for_project(project_id):
    """
    Returns a list of user dicts: [{'id': id, 'name': name}, ...]
    Includes partners and sub-partners (their user IDs are stored in partner_user_id / sub_partner_user_id).
    """
    # 1) partners for project
    partners = supabase.table("partners").select("partner_id, partner_user_id").eq("project_id", project_id).execute().data or []
    partner_user_ids = [p["partner_user_id"] for p in partners if p.get("partner_user_id") is not None]
    partner_ids = [p["partner_id"] for p in partners if p.get("partner_id") is not None]

    # 2) sub-partners whose partner_id is in partner_ids
    subpartners = []
    if partner_ids:
        subpartners = supabase.table("sub_partners").select("sub_partner_user_id, partner_id").in_("partner_id", partner_ids).execute().data or []
    sub_user_ids = [s["sub_partner_user_id"] for s in subpartners if s.get("sub_partner_user_id") is not None]

    # combine unique user ids
    all_user_ids = []
    for uid in partner_user_ids + sub_user_ids:
        if uid not in all_user_ids:
            all_user_ids.append(uid)

    if not all_user_ids:
        return []

    # fetch user names for these ids
    users = supabase.table("users").select("id, name").in_("id", all_user_ids).execute().data or []
    # preserve ordering of all_user_ids
    id_to_name = {u["id"]: u.get("name") for u in users}
    ordered_users = [{"id": uid, "name": id_to_name.get(uid, f"User {uid}")} for uid in all_user_ids]
    return ordered_users

def fetch_comments_for_transaction(transaction_id):
    res = supabase.table("comments").select("comment_id, parent_comment_id, user_id, content, created_at, edited_at, deleted").eq("transaction_id", transaction_id).order("created_at", desc=False).execute()
    return res.data or []

def post_comment(transaction_id, parent_comment_id, user_id, content):
    payload = {
        "transaction_id": transaction_id,
        "parent_comment_id": parent_comment_id,
        "user_id": user_id,
        "content": content
    }
    return supabase.table("comments").insert(payload).execute()

def update_comment(comment_id, new_content):
    payload = {"content": new_content, "edited_at": datetime.utcnow().isoformat()}
    return supabase.table("comments").update(payload).eq("comment_id", comment_id).execute()

# ---------- Tree helpers ----------
def build_comment_tree(comments):
    by_id = {c["comment_id"]: dict(c) for c in comments}
    child_map = {}
    for c in comments:
        pid = c.get("parent_comment_id")
        child_map.setdefault(pid, []).append(c["comment_id"])

    def recurse(parent_id=None, depth=0):
        nodes = []
        for cid in child_map.get(parent_id, []):
            node = by_id[cid]
            node["_depth"] = depth
            node["_children"] = recurse(cid, depth + 1)
            nodes.append(node)
        return nodes

    return recurse(None, 0)

def render_comment(node, users_map, key_prefix):
    depth = node.get("_depth", 0)
    user_name = users_map.get(node["user_id"], "Unknown")
    created_at = node.get("created_at")
    created_str = created_at.split("T")[0] if isinstance(created_at, str) else str(created_at)
    edited = bool(node.get("edited_at"))
    indent_px = depth * 12

    cols = st.columns([0.03, 0.85, 0.12])
    with cols[1]:
        st.markdown(f"<div style='margin-left:{indent_px}px'><b>{user_name}</b> · <small style='color:gray'>{created_str}{' · edited' if edited else ''}</small></div>", unsafe_allow_html=True)
        st.markdown(f"<div style='margin-left:{indent_px}px'>{node['content']}</div>", unsafe_allow_html=True)
    with cols[2]:
        if st.button("Reply", key=f"reply_{key_prefix}_{node['comment_id']}"):
            st.session_state.active_reply_to = node["comment_id"]
            st.session_state.active_edit = None
        if st.button("Edit", key=f"edit_{key_prefix}_{node['comment_id']}"):
            st.session_state.active_edit = node["comment_id"]
            st.session_state.active_reply_to = None

# ---------- session state init ----------
if "active_reply_to" not in st.session_state:
    st.session_state.active_reply_to = None
if "active_edit" not in st.session_state:
    st.session_state.active_edit = None
if "refresh_key" not in st.session_state:
    st.session_state.refresh_key = 0

# ---------- UI ----------
def main():
    st.title("💬 Transaction Comments")

    projects = get_projects()
    if not projects:
        st.warning("No projects found.")
        return

    proj_map = {p["project_name"]: p["project_id"] for p in projects}
    project_name = st.selectbox("Select Project", list(proj_map.keys()), key="proj_select")
    project_id = proj_map[project_name]

    transactions = get_transactions_for_project(project_id)
    if not transactions:
        st.info("No transactions for this project yet.")
        return

    tx_options = [f"#{t['transaction_id']} — ₹{t['amount']} — {t.get('transaction_date') or t.get('created_at','')}" for t in transactions]
    tx_map = {opt: t["transaction_id"] for opt, t in zip(tx_options, transactions)}
    selected_tx_label = st.selectbox("Select Transaction", tx_options, key="tx_select")
    transaction_id = tx_map[selected_tx_label]

    stakeholders = get_stakeholders_for_project(project_id)  # list of {id,name}
    if not stakeholders:
        st.warning("No stakeholders found. Comments require selecting a stakeholder user.")
        return

    # map for forms and lookups
    stakeholder_names = [s["name"] for s in stakeholders]
    stakeholder_map = {s["id"]: s["name"] for s in stakeholders}

    # new top-level comment form (use st.form to avoid session_state mutation crashes)
    st.markdown("### Post a new comment")
    with st.form("new_comment_form", clear_on_submit=True):
        poster = st.selectbox("Commenter (stakeholder)", stakeholder_names, key="poster_select")
        poster_id = next(s["id"] for s in stakeholders if s["name"] == poster)
        new_text = st.text_area("Write your comment here...", key="new_comment_text")
        submitted = st.form_submit_button("Post Comment")
        if submitted:
            if not new_text.strip():
                st.warning("Comment cannot be empty.")
            else:
                resp = post_comment(transaction_id, None, poster_id, new_text.strip())
                if resp.data:
                    st.success("Comment posted.")
                    st.session_state.refresh_key += 1
                else:
                    st.error(f"Failed to post comment: {resp}")

    st.markdown("---")

    # Fetch comments and build tree
    comments = fetch_comments_for_transaction(transaction_id)
    # fetch names used in comments
    user_ids = list({c["user_id"] for c in comments if c.get("user_id")})
    users_map = {}
    if user_ids:
        uresp = supabase.table("users").select("id, name").in_("id", user_ids).execute()
        for u in (uresp.data or []):
            users_map[u["id"]] = u.get("name")
    # fallback include stakeholders
    users_map.update({s["id"]: s["name"] for s in stakeholders})

    tree = build_comment_tree(comments)

    st.markdown("### Comments")
    if not comments:
        st.info("No comments yet for this transaction.")
    else:
        def render_nodes(nodes, prefix=""):
            for n in nodes:
                if n.get("deleted"):
                    st.markdown("_Comment deleted_")
                else:
                    render_comment(n, users_map, prefix)

                    # reply form for this node (if active)
                    if st.session_state.active_reply_to == n["comment_id"]:
                        with st.form(f"reply_form_{n['comment_id']}", clear_on_submit=True):
                            reply_user = st.selectbox("Reply as", stakeholder_names, key=f"reply_user_{n['comment_id']}")
                            reply_user_id = next(s["id"] for s in stakeholders if s["name"] == reply_user)
                            reply_text = st.text_area("Reply...", key=f"reply_text_{n['comment_id']}")
                            post_reply = st.form_submit_button("Post Reply")
                            if post_reply:
                                if not reply_text.strip():
                                    st.warning("Reply can't be empty.")
                                else:
                                    r = post_comment(transaction_id, n["comment_id"], reply_user_id, reply_text.strip())
                                    if r.data:
                                        st.success("Reply posted.")
                                        st.session_state.active_reply_to = None
                                        st.session_state.refresh_key += 1
                                    else:
                                        st.error(f"Failed to post reply: {r}")

                    # edit form for this node (if active)
                    if st.session_state.active_edit == n["comment_id"]:
                        with st.form(f"edit_form_{n['comment_id']}", clear_on_submit=False):
                            author = users_map.get(n["user_id"], "Unknown")
                            st.markdown(f"Editing comment by **{author}**")
                            edit_text = st.text_area("Edit comment", value=n["content"], key=f"edit_text_{n['comment_id']}")
                            save = st.form_submit_button("Save")
                            cancel = st.form_submit_button("Cancel")
                            if save:
                                if not edit_text.strip():
                                    st.warning("Edited text cannot be empty.")
                                else:
                                    r = update_comment(n["comment_id"], edit_text.strip())
                                    if r.data is not None:
                                        st.success("Comment updated.")
                                        st.session_state.active_edit = None
                                        st.session_state.refresh_key += 1
                                    else:
                                        st.error(f"Update failed: {r}")
                            if cancel:
                                st.session_state.active_edit = None

                if n.get("_children"):
                    render_nodes(n["_children"], prefix + f"{n['comment_id']}_")

        render_nodes(tree)

    if st.button("Refresh comments"):
        st.session_state.refresh_key += 1

if __name__ == "__main__":
    main()
