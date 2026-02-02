import streamlit as st
import api_client # Our custom module

st.set_page_config(
    page_title="AHP Student Profiler",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 AHP-Based Student Profiler")
st.markdown("Upload a student's academic transcript (PDF) to receive a professional profile recommendation.")

# --- UI Components ---

# 1. File Uploader
uploaded_file = st.file_uploader(
    "Choose a PDF transcript file", 
    type="pdf",
    help="The system is designed for the standard university transcript format."
)

# 2. AHP Weights Configuration in a sidebar
st.sidebar.header("⚙️ AHP Configuration")
st.sidebar.markdown("Adjust the importance of each criterion in the calculation.")

w_foundation = st.sidebar.slider(
    "Foundation Weight (wF)", 
    0.0, 1.0, 0.2, 
    help="How important are strong grades in fundamental courses (Sem 1-4)?"
)
w_competency = st.sidebar.slider(
    "Competency Weight (wC)", 
    0.0, 1.0, 0.5,
    help="How important are strong grades in specialized electives (Sem 5+)?"
)
w_density = st.sidebar.slider(
    "Density/Interest Weight (wD)", 
    0.0, 1.0, 0.3,
    help="How important is it for a student to have taken a high number of courses in a specific profile?"
)

# --- Logic ---

if uploaded_file is not None:
    # 3. Analyze Button
    if st.button("Analyze Transcript", type="primary", use_container_width=True):
        
        weights = {
            "w_foundation": w_foundation,
            "w_competency": w_competency,
            "w_density": w_density,
        }
        
        # Check if weights sum to 1.0
        if abs(sum(weights.values()) - 1.0) > 0.01:
            st.error("Error: The sum of the weights must be exactly 1.0.")
        else:
            with st.spinner("Parsing PDF and running analysis... Please wait."):
                result = api_client.analyze_transcript(uploaded_file, weights)

            if result:
                st.success("Analysis Complete!")
                
                # --- Display Results ---
                meta = result.get("student_metadata", {})
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Student Name", meta.get("name", "N/A"))
                col2.metric("Student ID", meta.get("id", "N/A"))
                col3.metric("Total Credits", result.get("total_credits", 0))

                st.subheader("Profile Recommendations")

                for rec in result.get("recommendations", []):
                    st.markdown(f"---")
                    rank = rec.get('rank')
                    profile = rec.get('profile')
                    score = rec.get('score', 0)
                    
                    st.markdown(f"### Rank {rank}: **{profile}**")
                    st.progress(score, text=f"Final Score: {score:.4f}")
                    
                    st.info(f"**Explanation:** {rec.get('explanation', 'No explanation provided.')}")
                    
                    with st.expander("Show Detailed Score Breakdown"):
                        details = rec.get('details', {})
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Foundation Score", f"{details.get('foundation_score', 0):.4f}")
                        c2.metric("Competency Score", f"{details.get('competency_score', 0):.4f}")
                        c3.metric("Density Score", f"{details.get('density_score', 0):.4f}")