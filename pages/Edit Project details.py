# =========================
# Edit Project Page
# =========================

import streamlit as st
from datetime import date, datetime
from supabase import create_client, Client

# -------------------------
# Page & Supabase Setup
# -------------------------
st.set_page_config(page_title="Edit Project")

@st.cache_resource
def get_supabase_client() -> Client:
    url = "https://ogecahtzmpsznesragam.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZWNhaHR6bXBzem5lc3JhZ2FtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5MzE0NDEsImV4cCI6MjA2NTUwNzQ0MX0.SVPUtm2-bhTRjc0XZnUII8pHt2Jc435Mr_fsEkmKpvs"
    return create_client(url, key)

supabase = get_supabase_client()

# -------------------------
# Utility Helpers
# -------------------------
def fetch_users():
    """Get list of users for pickers."""
    r = supabase.table("users").select("id, name").order("name").execute()
    return r.data or []

def fetch_projects_like(term: str):
    """Search projects by (case-insensitive) name."""
    r = (supabase.table("projects")
         .select("project_id, project_name")
         .ilike("project_name", f"%{term}%")
         .order("project_name")
         .execute())
    return r.data or []

def fetch_project_full(project_id: int):
    """Fetch project basics + partners + sub-partners in one go."""
    proj = (supabase.table("projects")
            .select("*")
            .eq("project_id", project_id)
            .single()
            .execute()
            .data)

    partners = (supabase.table("partners")
                .select("*")
                .eq("project_id", project_id)
                .order("partner_id")
                .execute()
                .data or [])

    subs_by_partner = {}
    if partners:
        partner_ids = [p["partner_id"] for p in partners]
        subs = (supabase.table("sub_partners")
                .select("*")
                .in_("partner_id", partner_ids)
                .order("sub_partner_id")
                .execute()
                .data or [])
        for sp in subs:
            subs_by_partner.setdefault(sp["partner_id"], []).append(sp)

    return proj, partners, subs_by_partner

def get_user_name(user_id: int, users_by_id: dict[int, str]) -> str:
    """Resolve user name locally (we already fetch all users)."""
    return users_by_id.get(user_id, f"User {user_id}")

def fnum(x) -> float:
    """Coerce numeric inputs safely to float."""
    try:
        return float(x)
    except Exception:
        return 0.0

def result_counts():
    """Counters for a friendly post-save summary."""
    return {"partners_inserted": 0, "partners_updated": 0, "partners_deleted": 0,
            "subs_inserted": 0, "subs_updated": 0, "subs_deleted": 0}

# -------------------------
# Session State Skeleton
# -------------------------
if "edit_state" not in st.session_state:
    st.session_state.edit_state = {
        "project_id": None,   # currently selected project_id
        "partners": [],       # UI rows: [{partner_id, partner_user_id, share_percentage, subs:[{sub_partner_id, sub_partner_user_id, share_percentage}]}]
    }
if "project_form" not in st.session_state:
    st.session_state.project_form = {
        "project_name": "",
        "description": "",
        "start_date": date.today(),
        "expected_cost": 0.0,
    }

# -------------------------
# Search & Select Project
# -------------------------
st.title("Edit Project")

top = st.container()
with top:
    cols = st.columns([3, 1])
    with cols[0]:
        search = st.text_input("Search project by name")
    with cols[1]:
        if st.button("🔄 Refresh"):
            st.rerun()

if search.strip():
    results = fetch_projects_like(search.strip())
    if results:
        labels = [f"{r['project_name']} (ID: {r['project_id']})" for r in results]
        choice = st.selectbox("Select a project", labels, key="project_choice")
        selected_project_id = results[labels.index(choice)]["project_id"]
    else:
        st.info("No matching projects found.")
        selected_project_id = None
else:
    selected_project_id = None

# Load selected project into state (once picked or changed)
if selected_project_id and st.session_state.edit_state["project_id"] != selected_project_id:
    proj, partners, subs_by_partner = fetch_project_full(selected_project_id)

    partner_rows = []
    for p in partners:
        partner_rows.append({
            "partner_id": p["partner_id"],
            "partner_user_id": p["partner_user_id"],
            "share_percentage": fnum(p["share_percentage"] or 0),
            "subs": [
                {
                    "sub_partner_id": sp["sub_partner_id"],
                    "sub_partner_user_id": sp["sub_partner_user_id"],
                    "share_percentage": fnum(sp["share_percentage"] or 0),
                }
                for sp in subs_by_partner.get(p["partner_id"], [])
            ],
        })

    st.session_state.edit_state["project_id"] = selected_project_id
    st.session_state.edit_state["partners"] = partner_rows
    st.session_state.project_form = {
        "project_name": proj.get("project_name", "") or "",
        "description": proj.get("description", "") or "",
        "start_date": date.fromisoformat(proj["start_date"]) if proj.get("start_date") else date.today(),
        "expected_cost": fnum(proj.get("expected_cost") or 0.0),
    }

# Stop if nothing selected yet
if not st.session_state.edit_state["project_id"]:
    st.info("Search and select a project to edit.")
    st.stop()

# -------------------------
# Project Basics Editor
# -------------------------
users = fetch_users()
users_by_id = {u["id"]: u["name"] for u in users}

st.divider()
st.subheader("Project Basics")

c1, c2 = st.columns(2)
with c1:
    st.session_state.project_form["project_name"] = st.text_input(
        "Project Name",
        value=st.session_state.project_form["project_name"]
    )
    st.session_state.project_form["description"] = st.text_area(
        "Project Description",
        value=st.session_state.project_form["description"]
    )
with c2:
    st.session_state.project_form["start_date"] = st.date_input(
        "Start Date",
        value=st.session_state.project_form["start_date"]
    )
    st.session_state.project_form["expected_cost"] = st.number_input(
        "Expected Total Investment (₹)",
        min_value=0.0, step=1000.0, value=st.session_state.project_form["expected_cost"]
    )
    if st.session_state.project_form["expected_cost"]:
        lakhs = st.session_state.project_form["expected_cost"] / 1_00_000
        st.caption(f"= **₹{lakhs:.2f} Lakhs**")

# -------------------------
# Partners & Sub-partners UI
# -------------------------
st.divider()
st.subheader("Partners & Ownership")

def user_options_excluding(exclude_ids: set[int]):
    """User dropdown options excluding certain IDs."""
    return [u for u in users if u["id"] not in exclude_ids]

# Track used IDs across partners + subs to prevent duplicates
used_ids = set()
for prow in st.session_state.edit_state["partners"]:
    if prow.get("partner_user_id"):
        used_ids.add(prow["partner_user_id"])
    for sp in prow.get("subs", []):
        if sp.get("sub_partner_user_id"):
            used_ids.add(sp["sub_partner_user_id"])

# Render each partner row
remove_partner_indices = []
for i, prow in enumerate(st.session_state.edit_state["partners"]):
    with st.expander(f"Partner {i+1}  {'(new)' if not prow.get('partner_id') else ''}", expanded=True):
        cc1, cc2, cc3 = st.columns([1.2, 0.8, 0.6])

        # Partner user picker (allow keeping existing even if excluded)
        with cc1:
            exclude = used_ids - {prow.get("partner_user_id")}
            options = user_options_excluding(exclude)
            if prow.get("partner_user_id") and prow["partner_user_id"] not in [u["id"] for u in options]:
                # Ensure current selection remains selectable
                options = [{"id": prow["partner_user_id"], "name": get_user_name(prow["partner_user_id"], users_by_id)}] + options

            current_index = 0
            if prow.get("partner_user_id"):
                for idx, u in enumerate(options):
                    if u["id"] == prow["partner_user_id"]:
                        current_index = idx
                        break

            chosen = st.selectbox(
                "Partner User",
                options=options,
                index=current_index,
                format_func=lambda x: x["name"],
                key=f"partner_user_{i}"
            )
            prow["partner_user_id"] = chosen["id"]

        # Partner share (% of project)
        with cc2:
            prow["share_percentage"] = st.number_input(
                "Share (%)",
                min_value=0.0, step=0.1,
                value=fnum(prow.get("share_percentage")),
                key=f"partner_share_{i}"
            )

        # Delete partner
        with cc3:
            st.write("")
            if st.button("🗑️ Delete Partner", key=f"del_partner_{i}"):
                remove_partner_indices.append(i)

        # ---- Sub-partners (relative to this partner) ----
        st.markdown("**Sub-partners (relative % of this partner)**")
        rm_sub_idx = []
        for j, sp in enumerate(prow.get("subs", [])):
            sc1, sc2, sc3 = st.columns([1.2, 0.8, 0.6])
            with sc1:
                exclude = used_ids - {prow.get("partner_user_id"), sp.get("sub_partner_user_id")}
                opts = user_options_excluding(exclude)
                if sp.get("sub_partner_user_id") and sp["sub_partner_user_id"] not in [u["id"] for u in opts]:
                    opts = [{"id": sp["sub_partner_user_id"], "name": get_user_name(sp["sub_partner_user_id"], users_by_id)}] + opts

                current_sub_index = 0
                if sp.get("sub_partner_user_id"):
                    for idx, u in enumerate(opts):
                        if u["id"] == sp["sub_partner_user_id"]:
                            current_sub_index = idx
                            break

                chosen_sub = st.selectbox(
                    f"Sub-Partner {j+1} User",
                    options=opts,
                    index=current_sub_index,
                    format_func=lambda x: x["name"],
                    key=f"sub_user_{i}_{j}"
                )
                sp["sub_partner_user_id"] = chosen_sub["id"]

            with sc2:
                sp["share_percentage"] = st.number_input(
                    "Relative Share (%)",
                    min_value=0.0, step=0.1,
                    value=fnum(sp.get("share_percentage")),
                    key=f"sub_share_{i}_{j}"
                )
                # Show effective % of project
                effective_abs = (fnum(sp["share_percentage"]) / 100.0) * fnum(prow.get("share_percentage"))
                st.caption(f"Effective share = **{effective_abs:.2f}%** of project")

            with sc3:
                st.write("")
                if st.button("Remove", key=f"rm_sub_{i}_{j}"):
                    rm_sub_idx.append(j)

        # Apply sub deletions
        for idx in reversed(rm_sub_idx):
            uid = prow["subs"][idx].get("sub_partner_user_id")
            if uid in used_ids:
                used_ids.remove(uid)
            prow["subs"].pop(idx)

        # Add sub-partner
        if st.button("➕ Add Sub-Partner", key=f"add_sub_{i}"):
            prow.setdefault("subs", []).append({
                "sub_partner_id": None,
                "sub_partner_user_id": None,
                "share_percentage": 0.0,
            })

# Apply partner deletions after loop
if remove_partner_indices:
    for idx in reversed(remove_partner_indices):
        delrow = st.session_state.edit_state["partners"][idx]
        if delrow.get("partner_user_id") in used_ids:
            used_ids.remove(delrow["partner_user_id"])
        for sp in delrow.get("subs", []):
            if sp.get("sub_partner_user_id") in used_ids:
                used_ids.remove(sp["sub_partner_user_id"])
        st.session_state.edit_state["partners"].pop(idx)

# Add partner
if st.button("➕ Add Partner"):
    st.session_state.edit_state["partners"].append({
        "partner_id": None,
        "partner_user_id": None,
        "share_percentage": 0.0,
        "subs": []
    })

# -------------------------
# Validations (pre-save)
# -------------------------
# 1) Partner totals must be exactly 100%
total_partner_share = sum(fnum(p.get("share_percentage")) for p in st.session_state.edit_state["partners"])
EPS = 1e-6
if total_partner_share < 100.0 - EPS:
    st.warning(
        f"⚠️ Total partner share is **{total_partner_share:.2f}%** (short by **{100.0 - total_partner_share:.2f}%**). "
        "Ownership must sum to exactly 100%."
    )
elif total_partner_share > 100.0 + EPS:
    st.error(
        f"❌ Total partner share is **{total_partner_share:.2f}%** (exceeds by **{total_partner_share - 100.0:.2f}%**). "
        "Reduce shares to make it exactly 100%."
    )

# 2) Warn if any partner’s sub-partners (absolute) exceed the partner share
for i, p in enumerate(st.session_state.edit_state["partners"]):
    partner_share = fnum(p.get("share_percentage"))
    total_sub_abs = sum((fnum(sp.get("share_percentage")) / 100.0) * partner_share for sp in p.get("subs", []))
    if total_sub_abs > partner_share + EPS:
        st.warning(
            f"⚠️ Partner {i+1}: sub-partners combined absolute share **{total_sub_abs:.2f}%** "
            f"exceeds partner share **{partner_share:.2f}%**."
        )

# -------------------------
# Save All Changes (DB Sync)
# -------------------------
pid = st.session_state.edit_state["project_id"]

if st.button("💾 Save All Changes"):
    errors = []

    # Required fields
    if not st.session_state.project_form["project_name"].strip():
        errors.append("Project name is required.")

    # No duplicate users across partners & sub-partners; each selection must exist
    seen = set()
    for p in st.session_state.edit_state["partners"]:
        uid = p.get("partner_user_id")
        if uid is None:
            errors.append("Each partner row must have a user selected.")
        elif uid in seen:
            errors.append("Duplicate user found across partners/sub-partners.")
        else:
            seen.add(uid)
        for sp in p.get("subs", []):
            suid = sp.get("sub_partner_user_id")
            if suid is None:
                errors.append("Each sub-partner row must have a user selected.")
            elif suid in seen:
                errors.append("Duplicate user found across partners/sub-partners.")
            else:
                seen.add(suid)

    # Hard block: partner shares must equal 100
    if abs(total_partner_share - 100.0) > EPS:
        if total_partner_share < 100.0:
            errors.append(
                f"Total partner share is **{total_partner_share:.2f}%** "
                f"(short by **{100.0 - total_partner_share:.2f}%**). Must be exactly 100%."
            )
        else:
            errors.append(
                f"Total partner share is **{total_partner_share:.2f}%** "
                f"(exceeds by **{total_partner_share - 100.0:.2f}%**). Must be exactly 100%."
            )

    if errors:
        st.error("Please fix the following:\n\n- " + "\n- ".join(errors))
        st.stop()

    # ---- Persist to DB (deterministic sync) ----
    summary = result_counts()
    form = st.session_state.project_form

    try:
        # 1) Update project basics
        supabase.table("projects").update({
            "project_name": form["project_name"].strip(),
            "description": (form["description"] or "").strip(),
            "start_date": form["start_date"].isoformat(),
            "expected_cost": fnum(form["expected_cost"]),
        }).eq("project_id", pid).execute()

        # 2) Compute partner deletions
        existing_partner_rows = (supabase.table("partners")
                                 .select("partner_id")
                                 .eq("project_id", pid)
                                 .execute()
                                 .data or [])
        existing_partner_ids = {r["partner_id"] for r in existing_partner_rows}
        current_partner_ids = {p["partner_id"] for p in st.session_state.edit_state["partners"] if p.get("partner_id")}
        to_delete_partner_ids = list(existing_partner_ids - current_partner_ids)

        # 2a) Delete their sub-partners first (FK safe), then partners
        if to_delete_partner_ids:
            supabase.table("sub_partners").delete().in_("partner_id", to_delete_partner_ids).execute()
            supabase.table("partners").delete().in_("partner_id", to_delete_partner_ids).execute()
            summary["partners_deleted"] += len(to_delete_partner_ids)
            # (Counting deleted subs exactly would require querying before delete; optional)

        # 2b) Upsert partners (update existing, insert new and store generated IDs)
        for p in st.session_state.edit_state["partners"]:
            if p.get("partner_id"):  # update
                supabase.table("partners").update({
                    "partner_user_id": p["partner_user_id"],
                    "share_percentage": fnum(p["share_percentage"]),
                }).eq("partner_id", p["partner_id"]).execute()
                summary["partners_updated"] += 1
            else:                     # insert
                ins = supabase.table("partners").insert({
                    "project_id": pid,
                    "partner_user_id": p["partner_user_id"],
                    "share_percentage": fnum(p["share_percentage"]),
                }).execute()
                p["partner_id"] = ins.data[0]["partner_id"]
                summary["partners_inserted"] += 1

        # 3) For each partner, sync sub-partners
        for p in st.session_state.edit_state["partners"]:
            partner_id_actual = p["partner_id"]

            # Existing subs
            existing_sub_rows = (supabase.table("sub_partners")
                                 .select("sub_partner_id")
                                 .eq("partner_id", partner_id_actual)
                                 .execute()
                                 .data or [])
            existing_sub_ids = {r["sub_partner_id"] for r in existing_sub_rows}
            current_sub_ids = {sp["sub_partner_id"] for sp in p.get("subs", []) if sp.get("sub_partner_id")}

            # Deletions
            del_sub_ids = list(existing_sub_ids - current_sub_ids)
            if del_sub_ids:
                supabase.table("sub_partners").delete().in_("sub_partner_id", del_sub_ids).execute()
                summary["subs_deleted"] += len(del_sub_ids)

            # Inserts / Updates
            for sp in p.get("subs", []):
                if sp.get("sub_partner_id"):  # update
                    supabase.table("sub_partners").update({
                        "sub_partner_user_id": sp["sub_partner_user_id"],
                        "share_percentage": fnum(sp["share_percentage"]),
                    }).eq("sub_partner_id", sp["sub_partner_id"]).execute()
                    summary["subs_updated"] += 1
                else:                          # insert
                    ins = supabase.table("sub_partners").insert({
                        "partner_id": partner_id_actual,
                        "sub_partner_user_id": sp["sub_partner_user_id"],
                        "share_percentage": fnum(sp["share_percentage"]),
                    }).execute()
                    sp["sub_partner_id"] = ins.data[0]["sub_partner_id"]
                    summary["subs_inserted"] += 1

        # 4) Success UI
        st.success(
            "✅ Changes saved to database.\n\n"
            f"- Project updated\n"
            f"- Partners: +{summary['partners_inserted']} / ✎{summary['partners_updated']} / −{summary['partners_deleted']}\n"
            f"- Sub-partners: +{summary['subs_inserted']} / ✎{summary['subs_updated']} / −{summary['subs_deleted']}"
        )
        st.toast("Project, partners, and sub-partners updated.", icon="✅")
        st.rerun()

    except Exception as e:
        st.error(
            "❌ Failed to save changes.\n\n"
            f"**Reason:** {e}\n\n"
            "Tips: verify RLS policies allow INSERT/UPDATE/DELETE for this role and that FK IDs exist."
        )
