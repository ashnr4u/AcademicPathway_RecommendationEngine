
import streamlit as st
from utils import SupabaseManager, GroqManager, Validator, HealthChecker, GroqAPIError, SupabaseError

# Initialize managers
supabase_manager = SupabaseManager()
groq_manager = GroqManager()
validator = Validator()
health_checker = HealthChecker(supabase_manager, groq_manager)

# Page config
st.set_page_config(
    page_title="Academic Pathway Recommender",
    page_icon="🎓",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: bold;
    }
    .recommendation-box {
        background: #f0fdf4;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin: 20px 0;
    }
    .warning-box {
        background: #fef3c7;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #f59e0b;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

# Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Main Page", "View Submissions"])

# Display health status
with st.sidebar.expander("System Health", expanded=False):
    health_checker.display()

# Main Page
if page == "Main Page":
    st.title("Academic Pathway Recommender")
    st.markdown("*Get AI-powered recommendations for your academic future*")
    
    health = health_checker.check()
    if not health["groq"] or not health["supabase"]:
        st.warning("Some services are unavailable. Check system health in sidebar.")
        
        with st.expander("Troubleshooting"):
            if not health["groq"]:
                st.markdown("""
                **Groq Issues:**
                - Verify GROQ_API_KEY in .env file
                - Check internet connection
                """)
            if not health["supabase"]:
                st.markdown("""
                **Supabase Issues:**
                - Verify SUPABASE_URL and SUPABASE_KEY in .env file
                - Ensure 'submissions' table exists
                """)
    
    with st.form("recommendation_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            full_name = st.text_input("Full Name *", placeholder="John Doe")
            email = st.text_input("Email *", placeholder="john@example.com")
            qualification = st.selectbox(
                "Highest Qualification *",
                ["", "High School", "Bachelor's Degree", "Master's Degree", 
                 "Professional Certificate", "Doctorate"]
            )
            experience = st.number_input("Years of Work Experience *", 
                                        min_value=0, max_value=50, step=1)
        
        with col2:
            profession = st.text_input("Current Profession *", 
                                      placeholder="Software Engineer, Teacher, etc.")
            goal = st.text_area("Career Goal *", 
                               placeholder="e.g., Become a research professor, Lead AI teams, etc.",
                               height=150)
        
        submitted = st.form_submit_button("Generate Recommendation", use_container_width=True)
        
        if submitted:
            profile = {
                'full_name': full_name,
                'email': email,
                'qualification': qualification,
                'experience': experience,
                'profession': profession,
                'goal': goal
            }
            
            is_valid, message = validator.validate_profile(profile)
            if not is_valid:
                st.error(message)
            else:
                try:
                    with st.spinner("AI is analyzing your profile..."):
                        recommendation = groq_manager.get_recommendation(profile)
                        st.success("Recommendation generated successfully!")
                    
                    with st.spinner("Saving your recommendation..."):
                        if supabase_manager.save_submission(profile, recommendation):
                            st.success("Recommendation saved to database!")
                            
                            st.markdown(f"""
                            <div class="recommendation-box">
                                <h3>Your AI-Powered Recommendation</h3>
                                <h1 style="color: #15803d;">{recommendation}</h1>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            st.balloons()
                            st.info("A confirmation email will be sent to you shortly")
                            
                except GroqAPIError as e:
                    st.error(f"Failed to get recommendation: {str(e)}")
                except SupabaseError as e:
                    st.error(f"Failed to save: {str(e)}")
                    if 'recommendation' in locals():
                        st.markdown(f"""
                        <div class="warning-box">
                            <b>Your recommendation was generated but not saved:</b><br/>
                            {recommendation}
                        </div>
                        """, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Unexpected error: {str(e)}")

# View Submissions Page
elif page == "View Submissions":
    st.title("Previous Submissions")
    st.markdown("*Showing: Name, Email, Career Goal, and Recommendation*")
    
    if not supabase_manager.client:
        st.error("Supabase client not available")
    else:
        with st.spinner("Loading submissions..."):
            try:
                submissions = supabase_manager.get_submissions()
                
                if not submissions:
                    st.info("No submissions yet. Go to Main Page to create one.")
                else:
                    st.dataframe(
                        submissions,
                        column_config={
                            "full_name": "Full Name",
                            "email": "Email",
                            "career_goal": "Career Goal",
                            "recommendation": "Recommendation",
                            "created_at": "Submission Date"
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                    st.caption(f"Total submissions: {len(submissions)}")
                    
                    if st.button("Refresh Data"):
                        st.rerun()
                        
            except SupabaseError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Error: {str(e)}")