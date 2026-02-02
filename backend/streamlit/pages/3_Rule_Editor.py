import streamlit as st
import api_client

st.set_page_config(page_title="Rule Editor", layout="wide")
st.title("⚖️ AHP Rule Editor")
st.markdown("Modify the relevance weights for each course.")

# --- Load Data ---
courses = api_client.get_courses()
if not courses:
    st.error("No courses found. Please add courses in the Course Editor first.")
    st.stop()

course_options = {c['name']: c['code'] for c in courses}
selected_name = st.selectbox(
    "Select a Course to Edit",
    options=course_options.keys()
)

if selected_name:
    selected_code = course_options[selected_name]
    st.subheader(f"Editing Rules for: `{selected_code}`")
    
    # --- Form for Editing ---
    with st.form(key="rule_form"):
        st.markdown("#### Define Course Type")
        c_type = st.radio(
            "Is this a Foundation or Competency course?",
            ("FOUNDATION", "COMPETENCY"),
            horizontal=True
        )

        st.markdown("#### Define Relevance Weights (0.0 to 1.0)")
        col1, col2 = st.columns(2)
        
        w_ai = col1.number_input("AI Weight", min_value=0.0, max_value=1.0, value=0.0, step=0.1)
        w_dms = col1.number_input("DMS Weight", min_value=0.0, max_value=1.0, value=0.0, step=0.1)
        w_psd = col2.number_input("PSD Weight", min_value=0.0, max_value=1.0, value=0.0, step=0.1)
        w_infra = col2.number_input("INFRA Weight", min_value=0.0, max_value=1.0, value=0.0, step=0.1)
        
        submitted = st.form_submit_button("Save Rule Changes", use_container_width=True)

        if submitted:
            payload = {
                "code": selected_code,
                "type": c_type,
                "weights": {
                    "AI": w_ai,
                    "DMS": w_dms,
                    "PSD": w_psd,
                    "INFRA": w_infra,
                }
            }
            api_client.update_relevance_rules(payload)