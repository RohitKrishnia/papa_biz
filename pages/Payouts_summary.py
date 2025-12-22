# view_payouts_summary_by_distributions.py
import streamlit as st
import pandas as pd
from supabase import create_client, Client

# ----------------------------
# Page config + Supabase client
# ----------------------------
st.set_page_config(page_title="Payouts Summary — By Distributions")

@st.cache_resource
def get_supabase() -> Client:
    url = "https://ogecahtzmpsznesragam.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZWNhaHR6bXBzem5lc3JhZ2FtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5MzE0NDEsImV4cCI6MjA2NTUwNzQ0MX0.SVPUtm2-bhTRjc0XZnUII8pHt2Jc435Mr_fsEkmKpvs"
    return create_client(url, key)

supabase = get_supabase()
TOLERANCE = 0.01  # rupee tolerance for totals checks

# ----------------------------
# Helpers
# ----------------------------
def fetch_projects():
    """Return list of projects."""
    resp = supabase.table("projects").select("project_id, project_name").order("project_name").execute()
    return resp.data or []

def build_ownership_map(project_id: int):
    """
    Compute effective ownership % for each stakeholder user_id.
    Logic:
      - partner.share_percentage is absolute %
      - sub_partners.share_percentage is percentage OF partner's share
      - sub_abs = partner.share * (sub.share_percentage / 100)
      - subtract sub_abs from parent's effective share
    Returns (ownership_map, stakeholder_ids_set)
    """
    partners = (supabase.table("partners")
                .select("partner_id, partner_user_id, share_percentage")
                .eq("project_id", project_id)
                .execute().data or [])
    partner_meta = {p["partner_id"]: {"user_id": p["partner_user_id"], "share": float(p.get("share_percentage") or 0)} for p in partners}
    partner_ids = list(partner_meta.keys())

    subs = []
    if partner_ids:
        subs = (supabase.table("sub_partners")
                .select("partner_id, sub_partner_user_id, share_percentage")
                .in_("partner_id", partner_ids)
                .execute().data or [])

    ownership = {}
    # start with partner absolute shares
    for pid, meta in partner_meta.items():
        uid = meta["user_id"]
        if uid is None:
            continue
        ownership[uid] = ownership.get(uid, 0.0) + meta["share"]

    # handle subs: compute absolute share and move from parent to sub
    for sp in subs:
        pid = sp.get("partner_id")
        sub_uid = sp.get("sub_partner_user_id")
        rel_pct = float(sp.get("share_percentage") or 0.0)
        if pid not in partner_meta or sub_uid is None:
            continue
        p_meta = partner_meta[pid]
        parent_uid = p_meta["user_id"]
        parent_share = p_meta["share"]
        sub_abs = parent_share * rel_pct / 100.0
        # add to sub
        ownership[sub_uid] = ownership.get(sub_uid, 0.0) + sub_abs
        # subtract from parent
        if parent_uid is not None:
            ownership[parent_uid] = ownership.get(parent_uid, 0.0) - sub_abs

    stakeholder_ids = set(ownership.keys())
    return ownership, stakeholder_ids

def fetch_all_distributions_for_project(project_id: int):
    """
    Fetch all payout_distributions for payouts belonging to a project.
    Returns list of dicts: {payout_id, user_id, amount}
    """
    # fetch payout_ids for project
    payouts = supabase.table("payouts").select("payout_id").eq("project_id", project_id).execute().data or []
    payout_ids = [p["payout_id"] for p in payouts]
    if not payout_ids:
        return []
    drows = (supabase.table("payout_distributions")
             .select("payout_id, user_id, amount")
             .in_("payout_id", payout_ids)
             .execute().data or [])
    return drows

def fetch_user_names(user_ids: list):
    """Return {id: name} for provided user_ids."""
    if not user_ids:
        return {}
    rows = supabase.table("users").select("id, name").in_("id", user_ids).execute().data or []
    return {r["id"]: r["name"] for r in rows}

# ----------------------------
# UI
# ----------------------------
st.title("Payouts Summary (calculated from payout_distributions)")

# 1) project selector
projects = fetch_projects()
if not projects:
    st.warning("No projects found.")
    st.stop()

proj_map = {p["project_name"]: p["project_id"] for p in projects}
project_name = st.selectbox("Select project", list(proj_map.keys()))
project_id = proj_map[project_name]

# 2) compute ownership map and stakeholders
ownership_map, stakeholder_ids = build_ownership_map(project_id)
if not stakeholder_ids:
    st.info("No stakeholders (partners/sub-partners) defined for this project.")
    st.stop()

# 3) fetch all distributions for this project and compute totals
dist_rows = fetch_all_distributions_for_project(project_id)

# total payouts is sum of distributions (NOT payouts.amount_received)
total_payouts = round(sum(float(d.get("amount") or 0.0) for d in dist_rows), 2)

# aggregate received amounts per user (from distributions)
received_by_user = {}
for d in dist_rows:
    uid = d.get("user_id")
    amt = float(d.get("amount") or 0.0)
    received_by_user[uid] = received_by_user.get(uid, 0.0) + amt

# ensure all stakeholders appear even if they received 0
for sid in stakeholder_ids:
    received_by_user.setdefault(sid, 0.0)
    ownership_map.setdefault(sid, 0.0)

# 4) fetch names for stakeholders
all_user_ids = sorted(list(set(list(stakeholder_ids) + list(received_by_user.keys()))))
user_names = fetch_user_names(all_user_ids)

# 5) build summary rows
rows = []
for uid in sorted(list(stakeholder_ids), key=lambda x: user_names.get(x, "")):
    name = user_names.get(uid, f"User {uid}")
    own_pct = round(ownership_map.get(uid, 0.0), 6)
    should_have = round((own_pct / 100.0) * total_payouts, 2)
    received = round(received_by_user.get(uid, 0.0), 2)
    diff = round(received - should_have, 2)
    rows.append({
        "Stakeholder": name,
        "Ownership %": own_pct,
        "Should Have (₹)": should_have,
        "Received (₹)": received,
        "Over / (Under) (₹)": diff
    })

df = pd.DataFrame(rows)

# 6) render
total_payouts_lakhs = round(total_payouts/1e5,2)
st.metric("Total Payouts (Lakhs)", f"₹{total_payouts_lakhs:,.2f}")


st.subheader("Per-stakeholder summary")
st.dataframe(df.sort_values("Stakeholder").reset_index(drop=True), use_container_width=True)

st.subheader("Who got more / less (sorted by Over / (Under))")
df_sorted = df.sort_values("Over / (Under) (₹)", ascending=False).reset_index(drop=True)
st.dataframe(df_sorted, use_container_width=True)

# 7) totals sanity checks
total_received_from_agg = round(df["Received (₹)"].sum(), 2)
if abs(total_received_from_agg - total_payouts) > TOLERANCE:
    st.warning(f"Sum of distributions ({total_received_from_agg:.2f}) does not equal computed total payouts ({total_payouts:.2f}).")
else:
    st.success("Sum of distributions matches total payouts.")

# 8) optional: breakdown per payout (toggle)
if st.checkbox("Show per-payout distribution breakdown"):
    # fetch payout rows for project to display date / amount etc.
    payouts = supabase.table("payouts").select("payout_id, payout_date, mode").eq("project_id", project_id).order("payout_date", desc=True).execute().data or []
    payouts_map = {p["payout_id"]: p for p in payouts}
    # build breakdown rows
    br_rows = []
    for d in dist_rows:
        pid = d.get("payout_id")
        br_rows.append({
            "Payout ID": pid,
            "Payout Date": payouts_map.get(pid, {}).get("payout_date"),
            "Mode": payouts_map.get(pid, {}).get("mode"),
            "Recipient": user_names.get(d.get("user_id"), f"User {d.get('user_id')}"),
            "Amount (₹)": float(d.get("amount") or 0.0)
        })
    if br_rows:
        st.dataframe(pd.DataFrame(br_rows).sort_values(["Payout Date", "Payout ID"], ascending=[False, False]).reset_index(drop=True), use_container_width=True)
    else:
        st.info("No distribution rows found for this project.")

st.caption(
    "Notes:\n"
    "- This report *only* uses payout_distributions to determine who actually received money.\n"
    "- 'Should Have' = Ownership % × Total payouts (total payouts = sum of all distribution rows).\n"
    "- Ownership % is computed from partners.share_percentage and sub_partners.share_percentage (sub % is % of partner's share)."
)
