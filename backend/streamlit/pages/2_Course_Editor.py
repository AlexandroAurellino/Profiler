import streamlit as st
import pandas as pd
import api_client

st.set_page_config(page_title="Course Editor", layout="wide")
st.title("⚙️ Course Editor")
st.markdown("Add, edit, or remove courses from the Knowledge Base (`courses.yaml`).")

# --- Load Data ---
courses_data = api_client.get_courses()

if not courses_data:
    st.warning("Could not load course data from the backend. Is it running?")
else:
    # --- Main Editor ---
    df = pd.DataFrame(courses_data)
    st.info("Edit values directly in the table. A 'Save Changes' button will appear below.")
    
    edited_df = st.data_editor(
        df,
        key="course_editor",
        num_rows="dynamic", # Allow adding/deleting rows
        use_container_width=True,
        # Hide the index column
        hide_index=True
    )

    # --- Save Logic ---
    if st.button("Save All Changes", type="primary"):
        # This is a simplified approach. In a real app, you'd compare the
        # original df with edited_df to find what changed.
        # For simplicity, we'll just re-submit everything.
        with st.spinner("Saving changes..."):
            for row in edited_df.to_dict(orient="records"):
                if all(row.values()): # Ensure no empty values
                    api_client.upsert_course(row)
        st.success("All changes have been submitted to the backend.")
        st.rerun() # Refresh the page to show latest state