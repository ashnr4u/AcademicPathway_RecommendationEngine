
import os
import streamlit as st
import time
import re
from datetime import datetime
from supabase import create_client
from groq import Groq, APIError, APIConnectionError, RateLimitError
from dotenv import load_dotenv

load_dotenv()

# Custom exceptions
class GroqAPIError(Exception):
    pass

class SupabaseError(Exception):
    pass

class ValidationError(Exception):
    pass

# Configuration class
class Config:
    @staticmethod
    def get_supabase_url():
        return os.getenv("SUPABASE_URL")
    
    @staticmethod
    def get_supabase_key():
        return os.getenv("SUPABASE_KEY")
    
    @staticmethod
    def get_groq_api_key():
        return os.getenv("GROQ_API_KEY")
    
    @staticmethod
    def get_groq_model():
        return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Supabase Manager
class SupabaseManager:
    def __init__(self):
        self.client = None
        self.table_name = "submissions"
        self._initialize()
    
    def _initialize(self):
        try:
            url = Config.get_supabase_url()
            key = Config.get_supabase_key()
            if url and key:
                self.client = create_client(url, key)
                print("Supabase client initialized successfully")  # Debug
            else:
                print("Supabase credentials missing")  # Debug
        except Exception as e:
            print(f"Failed to initialize Supabase: {str(e)}")  # Debug
    
    def is_healthy(self):
        if not self.client:
            return False
        try:
            self.client.table(self.table_name).select("count").limit(1).execute()
            return True
        except Exception as e:
            print(f"Health check failed: {str(e)}")  # Debug
            return False
    
    def save_submission(self, profile, recommendation, max_retries=3):
        if not self.client:
            raise SupabaseError("Supabase client not initialized")
        
        # Verify table exists
        try:
            self.client.table(self.table_name).select("count").limit(1).execute()
        except Exception as e:
            if "does not exist" in str(e).lower():
                raise SupabaseError("Table 'submissions' doesn't exist. Please create it in Supabase.")
            raise SupabaseError(f"Database error: {str(e)}")
        
        data = {
            "full_name": profile['full_name'],
            "email": profile['email'],
            "highest_qualification": profile['qualification'],
            "years_experience": profile['experience'],
            "current_profession": profile['profession'],
            "career_goal": profile['goal'],
            "recommendation": recommendation,
            "created_at": datetime.now().isoformat()
        }
        
        for attempt in range(max_retries):
            try:
                result = self.client.table(self.table_name).insert(data).execute()
                return True
            except Exception as e:
                error_msg = str(e).lower()
                if "connection" in error_msg or "network" in error_msg:
                    if attempt == max_retries - 1:
                        raise SupabaseError(f"Network error after {max_retries} attempts")
                    time.sleep(2 ** attempt)
                elif "duplicate" in error_msg:
                    raise SupabaseError("Duplicate entry. This email may already exist.")
                elif attempt == max_retries - 1:
                    raise SupabaseError(f"Failed to save: {str(e)}")
                time.sleep(1)
        return False
    
    def get_submissions(self, limit=100):
        if not self.client:
            raise SupabaseError("Supabase client not initialized")
        try:
            response = self.client.table(self.table_name).select(
                "full_name", "email", "career_goal", "recommendation", "created_at"
            ).order("created_at", desc=True).limit(limit).execute()
            return response.data
        except Exception as e:
            raise SupabaseError(f"Failed to fetch submissions: {str(e)}")

# Groq Manager
class GroqManager:
    def __init__(self):
        self.client = None
        self.model = Config.get_groq_model()
        self._initialize()
    
    def _initialize(self):
        try:
            api_key = Config.get_groq_api_key()
            if api_key:
                self.client = Groq(api_key=api_key)
                print("Groq client initialized successfully")  # Debug
            else:
                print("Groq API key missing")  # Debug
        except Exception as e:
            print(f"Failed to initialize Groq: {str(e)}")  # Debug
    
    def is_healthy(self):
        if not self.client:
            return False
        try:
            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
                timeout=5
            )
            return True
        except Exception as e:
            print(f"Groq health check failed: {str(e)}")  # Debug
            return False
    
    def get_recommendation(self, profile, max_retries=3, timeout=30):
        if not self.client:
            raise GroqAPIError("Groq client not initialized. API key missing.")
        
        prompt = f"""Based on the following user profile, suggest ONE specific recommendation from these categories:

Choose the MOST APPROPRIATE from:
1. A SPECIFIC Certification Program (e.g., "AWS Certified Solutions Architect", "PMP",
 "Google Data Analytics Professional Certificate", "Certified Scrum Master", "Microsoft Azure Fundamentals")
2. DBA (Doctor of Business Administration)
3. PhD (Doctor of Philosophy) in a specific field
4. Honorary Doctorate

Profile:
- Current Qualification: {profile['qualification']}
- Years of Experience: {profile['experience']}
- Current Profession: {profile['profession']}
- Career Goal: {profile['goal']}

IMPORTANT RULES:
- If suggesting a Certification Program, name a REAL, SPECIFIC certification (not just "Certification Program")
- Match the certification to their profession and career goal
- Consider their current qualification level
- For PhD/DBA, suggest a specific field of study based on their goal
- Respond with ONLY the recommendation name (e.g., "PMP Certification" or "PhD in Computer Science")
commendation name (e.g., "PhD")."""
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=20,
                    timeout=timeout
                )
                return response.choices[0].message.content.strip()
            except APIConnectionError as e:
                if attempt == max_retries - 1:
                    raise GroqAPIError(f"Network error: Cannot connect to Groq API. {str(e)}")
                time.sleep(2 ** attempt)
            except RateLimitError as e:
                if attempt == max_retries - 1:
                    raise GroqAPIError(f"Rate limit exceeded. Try again later. {str(e)}")
                time.sleep(5)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise GroqAPIError(f"API error: {str(e)}")
                time.sleep(1)
        
        return "Unable to generate recommendation"

# Validator class
class Validator:
    @staticmethod
    def validate_email(email):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_profile(profile):
        if not all([profile.get('full_name'), profile.get('email'), 
                   profile.get('qualification'), profile.get('profession'), 
                   profile.get('goal')]):
            return False, "Please fill in all required fields"
        
        if not Validator.validate_email(profile['email']):
            return False, "Please enter a valid email address"
        
        if profile.get('experience', 0) < 0 or profile.get('experience', 0) > 50:
            return False, "Experience must be between 0 and 50 years"
        
        if not profile.get('qualification'):
            return False, "Please select a qualification"
        
        return True, "Valid"

# Health checker
class HealthChecker:
    def __init__(self, supabase_manager, groq_manager):
        self.supabase = supabase_manager
        self.groq = groq_manager
    
    def check(self):
        return {
            "supabase": self.supabase.is_healthy(),
            "groq": self.groq.is_healthy()
        }
    
    def display(self):
        health = self.check()
        if health["supabase"]:
            st.success("Supabase: Connected")
        else:
            st.error("Supabase: Disconnected - Check URL/Key in .env")
        if health["groq"]:
            st.success("Groq API: Ready")
        else:
            st.error("Groq API: Unavailable - Check API key in .env")