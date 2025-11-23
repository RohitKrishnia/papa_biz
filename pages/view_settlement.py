# =========================================
# View Settlements (Before & After)
# =========================================

import streamlit as st
import pandas as pd
from supabase import create_client, Client

# -------------------------------
# Setup
# -------------------------------
st.set_page_config(page_title="View Settlements (Before & After)")

@st.cache_resource
def get_supabase() -> Client:
    url = "https://ogecahtzmpsznesragam.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZWNhaHR6bXBzem5lc3JhZ2FtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5MzE0NDEsImV4cCI6MjA2NTUwNzQ0MX0.SVPUtm2-bhTRjc0XZnUII8pHt2Jc435Mr_fsEkmKpvs"
    return create_client(url, key)

supabase = get_supabase()
EPS = 1e-6

# -------------------------------
# Helpers
# -------------------------------
def f2(x):  # money format helper
    return float(x or 0.0)

def fetch_projects():
    r = supabase.table("projects").select("project_id, project_name").order("project_name").execute()
    return r.data or []

def fetch_users():
    r = supabase.table("users").select("id, name, parent_user_id").order("name").execute()
    return r.data or []

def users_by_id(users):
    return {u["id"]: {"name": u["name"], "parent_user_id": u.get("parent_user_id")} for u in users}

def users_id_by_name(users):
    # name is UNIQUE in schema, safe to map
    return {u["name"]: u["id"] for u in users if u.get("name")}

def build_ownership_and_childmap(project_id: int):
    # partners
    partners = (supabase.table("partners")
                .select("partner_id, partner_user_id, share_percentage")
                .eq("project_id", project_id).execute().data or [])
    partner_ids = [p["partner_id"] for p in partners]
    partner_meta = {p["partner_id"]: {"user_id": p["partner_user_id"], "share": f2(p["share_percentage"])} for p in partners}

    # sub-partners
    subs = (supabase.table("sub_partners")
            .select("partner_id, sub_partner_user_id, share_percentage")
            .in_("partner_id", partner_ids).execute().data or []) if partner_ids else []

    # effective ownership %
    ownership = {}
    for pid, meta in partner_meta.items():
        uid = meta["user_id"]
        if uid is not None:
            ownership[uid] = ownership.get(uid, 0.0) + meta["share"]

    for sp in subs:
        pid = sp["partner_id"]
        sub_uid = sp.get("sub_partner_user_id")
        rel = f2(sp.get("share_percentage"))
        if pid not in partner_meta or sub_uid is None:
            continue
        p_uid = partner_meta[pid]["user_id"]
        p_share = partner_meta[pid]["share"]
        sub_abs = p_share * rel / 100.0
        ownership[sub_uid] = ownership.get(sub_uid, 0.0) + sub_abs
        if p_uid is not None:
            ownership[p_uid] = ownership.get(p_uid, 0.0) - sub_abs

    stakeholders = set(ownership.keys())

    # children of stakeholders
    child_to_parent = {}
    if stakeholders:
        kids = (supabase.table("users")
                .select("id, parent_user_id")
                .in_("parent_user_id", list(stakeholders)).execute().data or [])
        for k in kids:
            cid, pid = k["id"], k.get("parent_user_id")
            if pid in stakeholders:
                child_to_parent[cid] = pid

    return stakeholders, ownership, child_to_parent

def fetch_project_txns_and_sources(project_id: int):
    txns = (supabase.table("transactions")
            .select("transaction_id, amount, paid_by")
            .eq("project_id", project_id).execute().data or [])
    txn_ids = [t["transaction_id"] for t in txns]
    srcs = (supabase.table("transaction_sources")
            .select("transaction_id, source_id, amount")
            .in_("transaction_id", txn_ids).execute().data or []) if txn_ids else []
    src_by_txn = {}
    for s in srcs:
        src_by_txn.setdefault(s["transaction_id"], []).append(s)
    return txns, src_by_txn

def compute_contributions(project_id: int):
    """
    Returns: (contrib: dict[user_id->amount], total_invested: float)
    Uses your approved logic:
      - credit internal sources (stakeholders or their children) to their (parent) stakeholder
      - paid_by stakeholder gets (txn.amount - internal_sources_total)
      - external sources ignored
    """
    stakeholders, ownership, childmap = build_ownership_and_childmap(project_id)
    txns, src_by_txn = fetch_project_txns_and_sources(project_id)
    contrib = {sid: 0.0 for sid in stakeholders}

    for t in txns:
        tid = t["transaction_id"]
        amount = f2(t.get("amount"))
        pb = t.get("paid_by")

        # effective payer stakeholder
        if pb in stakeholders:
            payer = pb
        elif pb in childmap:
            payer = childmap[pb]
        else:
            payer = None

        internal_total = 0.0
        for s in src_by_txn.get(tid, []):
            sid = s.get("source_id")
            amt = f2(s.get("amount"))
            if sid in stakeholders:  # stakeholder
                contrib[sid] = contrib.get(sid, 0.0) + amt
                internal_total += amt
            elif sid in childmap:    # child of stakeholder
                parent = childmap[sid]
                contrib[parent] = contrib.get(parent, 0.0) + amt
                internal_total += amt
            # else external → ignore

        if payer is not None:
            contrib[payer] = contrib.get(payer, 0.0) + (amount - internal_total)

    total = sum(contrib.values())
    return contrib, total, ownership, stakeholders

def greedy_settlement(balances: dict[int, float]):
    """
    balances: user_id -> (paid - should)
      >0 creditor, <0 debtor
    Returns list of {from_id, to_id, amount}
    """
    creditors, debtors = [], []
    for uid, bal in balances.items():
        if bal > EPS:  creditors.append([uid, bal])
        elif bal < -EPS: debtors.append([uid, -bal])

    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)

    transfers, i, j = [], 0, 0
    while i < len(debtors) and j < len(creditors):
        d_uid, d_need = debtors[i]
        c_uid, c_surplus = creditors[j]
        amt = min(d_need, c_surplus)
        if amt > EPS:
            transfers.append({"from_id": d_uid, "to_id": c_uid, "amount": round(amt, 2)})
            d_need -= amt
            c_surplus -= amt
        if d_need <= EPS: i += 1
        else: debtors[i][1] = d_need
        if c_surplus <= EPS: j += 1
        else: creditors[j][1] = c_surplus
    return transfers

def fetch_settlements(project_id: int):
    r = (supabase.table("settlements")
         .select("paid_by, paid_to, amount, date, mode, remarks")
         .eq("project_id", project_id)
         .order("date", desc=True)
         .execute())
    return r.data or []

# -------------------------------
# UI
# -------------------------------
st.title("View Settlements (Before & After)")

# Project selector
projects = fetch_projects()
if not projects:
    st.warning("No projects found.")
    st.stop()

proj_map = {p["project_name"]: p["project_id"] for p in projects}
project_name = st.selectbox("Project", list(proj_map.keys()))
project_id = proj_map[project_name]

# Users maps
users = fetch_users()
uid_map = users_by_id(users)
id_by_name = users_id_by_name(users)

# Contributions & ownership
contrib, total_invested, ownership, stakeholders = compute_contributions(project_id)
if not stakeholders:
    st.info("No stakeholders found for this project.")
    st.stop()

# --- BEFORE settlements ---
st.subheader("Before Settlements")
before_rows = []
balances_before = {}
for sid in stakeholders:
    own = ownership.get(sid, 0.0)
    paid = contrib.get(sid, 0.0)
    should = total_invested * own / 100.0
    bal = paid - should
    balances_before[sid] = bal
    before_rows.append({
        "Stakeholder": uid_map.get(sid, {}).get("name", f"User {sid}"),
        "Ownership %": round(own, 4),
        "Contributed": round(paid, 2),
        "Should Have Paid": round(should, 2),
        "Net Balance (Paid - Should)": round(bal, 2),
    })

st.dataframe(pd.DataFrame(before_rows).sort_values("Stakeholder").reset_index(drop=True), use_container_width=True)

# Suggested transfers (pre-settlement)
pre_plan = greedy_settlement(balances_before)
if pre_plan:
    st.markdown("**Who owes whom (pre-settlement):**")
    st.dataframe(pd.DataFrame([
        {"From": uid_map.get(t["from_id"], {}).get("name"),
         "To": uid_map.get(t["to_id"], {}).get("name"),
         "Amount": t["amount"]}
    for t in pre_plan]), use_container_width=True)
else:
    st.success("All square before considering settlements.")

st.divider()

# --- APPLIED settlements ---
st.subheader("Applied Settlements")
sett_rows = fetch_settlements(project_id)
if not sett_rows:
    st.info("No settlements recorded yet.")
else:
    # show a simple table
    st.dataframe(pd.DataFrame([{
        "Date": r.get("date"),
        "Paid By": r.get("paid_by"),
        "Paid To": r.get("paid_to"),
        "Amount": round(f2(r.get("amount")), 2),
        "Mode": r.get("mode"),
        "Remarks": r.get("remarks")
    } for r in sett_rows]), use_container_width=True)

# Apply settlements as inter-stakeholder transfers to balances
balances_after = balances_before.copy()
for r in sett_rows:
    by_name = (r.get("paid_by") or "").strip()
    to_name = (r.get("paid_to") or "").strip()
    amt = f2(r.get("amount"))

    # map names → ids; ignore if not a known stakeholder
    by_id = id_by_name.get(by_name)
    to_id = id_by_name.get(to_name)
    if by_id in stakeholders and to_id in stakeholders:
        balances_after[by_id] = balances_after.get(by_id, 0.0) + amt
        balances_after[to_id] = balances_after.get(to_id, 0.0) - amt

st.divider()

# --- AFTER settlements ---
st.subheader("After Settlements")
after_rows = []
for sid in stakeholders:
    after_rows.append({
        "Stakeholder": uid_map.get(sid, {}).get("name", f"User {sid}"),
        "Net Balance After Settlements": round(balances_after.get(sid, 0.0), 2)
    })
st.dataframe(pd.DataFrame(after_rows).sort_values("Stakeholder").reset_index(drop=True), use_container_width=True)

post_plan = greedy_settlement(balances_after)
if post_plan:
    st.markdown("**Who still owes whom (after applying settlements):**")
    st.dataframe(pd.DataFrame([
        {"From": uid_map.get(t["from_id"], {}).get("name"),
         "To": uid_map.get(t["to_id"], {}).get("name"),
         "Amount": t["amount"]}
    for t in post_plan]), use_container_width=True)
else:
    st.success("All square after applying settlements. 🎉")

# Sanity: totals should net to ~0
sum_pos = sum(v for v in balances_after.values() if v > 0)
sum_neg = -sum(v for v in balances_after.values() if v < 0)
if abs(sum_pos - sum_neg) > 0.01:
    st.warning(f"Balances don’t net to zero (pos={sum_pos:.2f}, neg={sum_neg:.2f}). Check ownership data and rounding.")

st.caption(
    "Notes: (1) Pre-settlement plan uses contributions vs pro-rata shares. "
    "(2) Each settlement reduces debtor’s deficit and creditor’s surplus. "
    "(3) The final table shows what is still owed after applying all recorded settlements."
)
