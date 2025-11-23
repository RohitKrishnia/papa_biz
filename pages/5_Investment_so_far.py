# investment_so_far_by_sources.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from supabase import create_client, Client
from datetime import date

# -------------------------
# Config + Supabase client
# -------------------------
st.set_page_config(page_title="Investments So Far (by sources)")

@st.cache_resource
def get_supabase() -> Client:
    url = "https://ogecahtzmpsznesragam.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZWNhaHR6bXBzem5lc3JhZ2FtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5MzE0NDEsImV4cCI6MjA2NTUwNzQ0MX0.SVPUtm2-bhTRjc0XZnUII8pHt2Jc435Mr_fsEkmKpvs"
    return create_client(url, key)

supabase = get_supabase()

# -------------------------
# Helpers: DB reads & logic
# -------------------------
def fetch_projects():
    r = supabase.table("projects").select("project_id, project_name, expected_cost").order("project_name").execute()
    return r.data or []

def fetch_users_basic():
    # id, name, parent_user_id
    r = supabase.table("users").select("id, name, parent_user_id").execute()
    return r.data or []

def fetch_partners(project_id: int):
    r = supabase.table("partners").select("partner_id, partner_user_id, share_percentage").eq("project_id", project_id).execute()
    return r.data or []

def fetch_subpartners_for(partner_ids: list):
    if not partner_ids:
        return []
    r = supabase.table("sub_partners").select("partner_id, sub_partner_user_id, share_percentage").in_("partner_id", partner_ids).execute()
    return r.data or []

def compute_effective_ownership(project_id: int):
    """
    Return ownership_map: {user_id: fraction (0..1)}
    and debug_rows: [(role, user_id, frac)]
    """
    partners = fetch_partners(project_id)
    partner_meta = {p["partner_id"]: {"user_id": p["partner_user_id"], "share": float(p.get("share_percentage") or 0.0)} for p in partners}
    partner_ids = list(partner_meta.keys())
    subs = fetch_subpartners_for(partner_ids)

    ownership = {}
    rows = []
    for pid, meta in partner_meta.items():
        P = meta["share"] / 100.0
        subs_for_pid = [s for s in subs if s["partner_id"] == pid]
        sub_total = 0.0
        for s in subs_for_pid:
            rel = float(s.get("share_percentage") or 0.0) / 100.0
            sub_abs = P * rel
            uid = s.get("sub_partner_user_id")
            ownership[uid] = ownership.get(uid, 0.0) + sub_abs
            sub_total += sub_abs
            rows.append(("sub-partner", uid, sub_abs))
        partner_uid = meta["user_id"]
        partner_eff = max(P - sub_total, 0.0)
        ownership[partner_uid] = ownership.get(partner_uid, 0.0) + partner_eff
        rows.append(("partner", partner_uid, partner_eff))
    return ownership, rows

def fetch_transactions(project_id: int):
    # fetch transactions for project
    r = supabase.table("transactions").select("transaction_id, amount, paid_by").eq("project_id", project_id).order("transaction_id", desc=False).execute()
    return r.data or []

def fetch_sources_for_transaction(transaction_id: int):
    r = supabase.table("transaction_sources").select("source_id, amount").eq("transaction_id", transaction_id).execute()
    return r.data or []

# -------------------------
# Core attribution algorithm
# -------------------------
def compute_contributions_by_stakeholder(project_id: int):
    """
    Implements the logic you described:
      - For each txn:
          - map paid_by -> stakeholder (if paid_by is stakeholder use it; if paid_by is child of stakeholder map to parent; else None)
          - iterate sources:
              - if source is stakeholder -> credit that stakeholder
              - elif source's parent is stakeholder -> credit that parent stakeholder
              - else -> credit to paid_by_stakeholder (if exists) as the non-stakeholder funded it on behalf of paid_by
          - leftover = txn.amount - sum(sources); leftover credited to paid_by_stakeholder (if exists)
    Returns:
      contributions: {stakeholder_id: amount}
      total_all_distributions: sum of all source amounts (for debugging)
      external_unattributed: amount that couldn't be attributed to any stakeholder (paid_by was external and sources external)
    """
    # 1) Build stakeholder set and maps
    ownership_map, _ = compute_effective_ownership(project_id)
    stakeholder_ids = set(ownership_map.keys())  # set of user_ids who are stakeholders (partners + subs)

    users = fetch_users_basic()  # list of {id, name, parent_user_id}
    user_parent = {u["id"]: u.get("parent_user_id") for u in users}
    user_name = {u["id"]: u.get("name") for u in users}

    # child_to_parent: map a user -> its parent (if parent exists and is a stakeholder)
    # We will check any user's parent and see if that parent is a stakeholder.
    # The user can have at most one parent (per your rule).
    contributions = {uid: 0.0 for uid in stakeholder_ids}
    total_all_sources = 0.0
    external_unattributed = 0.0

    # 2) iterate transactions
    txns = fetch_transactions(project_id)
    for t in txns:
        tid = t.get("transaction_id")
        txn_amount = float(t.get("amount") or 0.0)
        paid_by = t.get("paid_by")  # could be None
        # map paid_by to stakeholder if possible
        paid_by_stakeholder = None
        if paid_by in stakeholder_ids:
            paid_by_stakeholder = paid_by
        else:
            parent = user_parent.get(paid_by)
            if parent in stakeholder_ids:
                paid_by_stakeholder = parent
        # fetch sources for this txn
        sources = fetch_sources_for_transaction(tid)
        sum_sources = 0.0
        # iterate each source
        for s in sources:
            s_id = s.get("source_id")
            s_amt = float(s.get("amount") or 0.0)
            sum_sources += s_amt
            total_all_sources += s_amt

            # if source itself is stakeholder => credit directly
            if s_id in stakeholder_ids:
                contributions[s_id] = contributions.get(s_id, 0.0) + s_amt
            else:
                # check if its parent is stakeholder
                s_parent = user_parent.get(s_id)
                if s_parent in stakeholder_ids:
                    contributions[s_parent] = contributions.get(s_parent, 0.0) + s_amt
                else:
                    # neither source nor its parent stakeholder -> credit to paid_by_stakeholder (if exists)
                    if paid_by_stakeholder is not None:
                        contributions[paid_by_stakeholder] = contributions.get(paid_by_stakeholder, 0.0) + s_amt
                    else:
                        # cannot attribute this amount to any stakeholder; track as external
                        external_unattributed += s_amt

        # leftover = txn_amount - sum_sources
        leftover = round(txn_amount - sum_sources, 2)
        if leftover > 0.0:
            if paid_by_stakeholder is not None:
                contributions[paid_by_stakeholder] = contributions.get(paid_by_stakeholder, 0.0) + leftover
            else:
                external_unattributed += leftover
        else:
            # if leftover is slightly negative due to rounding, treat it as zero
            if leftover < -0.01:
                # large negative indicates data inconsistency (sources > txn amount)
                st.warning(f"Transaction {tid}: sources exceed transaction amount by {-leftover:.2f}. Please check data.")
    return contributions, total_all_sources, external_unattributed, user_name, stakeholder_ids, ownership_map

# -------------------------
# Page UI & Display
# -------------------------
def fmt_currency(x):
    return f"₹{x:,.2f}"

def main():
    st.title("Investments So Far (attributed from transaction_sources)")

    # Project selector
    projects = fetch_projects()
    if not projects:
        st.warning("No projects found. Create a project first.")
        return
    proj_map = {p["project_name"]: (p["project_id"], float(p.get("expected_cost") or 0.0)) for p in projects}
    proj_name = st.selectbox("Select Project", list(proj_map.keys()))
    project_id, expected_cost = proj_map[proj_name]

    # Compute contributions using algorithm
    st.info("Computing contributions from every transaction's sources — this may take a moment for large projects.")
    contributions, total_sources, external_unattributed, user_name_map, stakeholder_ids, ownership_map = compute_contributions_by_stakeholder(project_id)

    # Prepare expected map (expected investment = expected_cost * ownership_fraction)
    expected_map = {uid: expected_cost * frac for uid, frac in ownership_map.items()}

    # Build summary rows
    rows = []
    total_contributed = 0.0
    total_expected = 0.0
    for uid in sorted(stakeholder_ids, key=lambda u: user_name_map.get(u, "")):
        name = user_name_map.get(uid, f"User {uid}")
        contributed = round(contributions.get(uid, 0.0), 2)
        expected_amt = round(expected_map.get(uid, 0.0), 2)
        diff = round(contributed - expected_amt, 2)
        pct_of_expected = (contributed / expected_amt * 100.0) if expected_amt > 0 else None
        rows.append({
            "Stakeholder": name,
            "Effective Ownership %": round(ownership_map.get(uid, 0.0) * 100.0, 6),
            "Contributed (from sources + leftover) (₹)": contributed,
            "Expected Investment (₹)": expected_amt,
            "Over / (Under) (₹)": diff,
            "% of Expected": f"{pct_of_expected:.1f}%" if pct_of_expected is not None else "—"
        })
        total_contributed += contributed
        total_expected += expected_amt

    df = pd.DataFrame(rows)
    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Project Expected Cost", fmt_currency(expected_cost))
    c2.metric("Total Expected (sum of stakeholders)", fmt_currency(total_expected))
    c3.metric("Total Contributed (attributed from txns)", fmt_currency(total_contributed))

    if external_unattributed > 0:
        st.caption(f"Note: {fmt_currency(external_unattributed)} could not be attributed to any stakeholder (paid_by and sources were external).")

    st.subheader("Stakeholder breakdown (contributed vs expected)")
    st.dataframe(df.sort_values("Stakeholder").reset_index(drop=True), use_container_width=True)

    # Bar chart: contributed vs expected
    st.subheader("Contributed vs Expected (bar chart)")
    names = df["Stakeholder"].tolist()
    contributed_vals = df["Contributed (from sources + leftover) (₹)"].tolist()
    expected_vals = df["Expected Investment (₹)"].tolist()

    fig, ax = plt.subplots(figsize=(max(6, len(names)*0.6), 4))
    x = range(len(names))
    width = 0.4
    ax.bar([i - width/2 for i in x], contributed_vals, width, label="Contributed")
    ax.bar([i + width/2 for i in x], expected_vals, width, label="Expected")
    ax.set_xticks(list(x))
    ax.set_xticklabels(names, rotation=30, ha="right")
    ax.set_ylabel("Amount (INR)")
    ax.set_title("Contributed vs Expected by Stakeholder")
    ax.legend()
    st.pyplot(fig)

    # Optional: show some diagnostics
    with st.expander("Diagnostics / Debug"):
        st.write(f"Total of all source rows (sum of transaction_sources.amount): {fmt_currency(total_sources)}")
        st.write(f"Total attributed (sum of contributions): {fmt_currency(total_contributed)}")
        st.write("Note: total attributed may be >= total_sources because leftover amounts are also attributed (txn.amount - sum(sources)).")
        st.write("Ownership fractions used:")
        for uid, frac in ownership_map.items():
            st.write(f"- {user_name_map.get(uid, uid)} : {frac*100:.4f}%")

if __name__ == "__main__":
    main()
