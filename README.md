# Academic Pathway Recommender

An AI-powered recommendation system that suggests the most suitable academic pathway (Certification Program, DBA, PhD, or Honorary Doctorate) based on a user's education, professional experience, current role, and career goals.

Live Link: https://academicpathwayrecommendationengine.streamlit.app/


## Features

* AI-powered academic pathway recommendations using Groq LLM
* Simple and interactive Streamlit interface
* Supabase database integration for storing submissions
* Input validation and error handling
* Recommendation history tracking

## Tech Stack

* **Frontend:** Streamlit
* **Backend:** Python
* **LLM:** LLaMA 3.3 70B via Groq API
* **Database:** Supabase (PostgreSQL)

## Architecture

```text
User → Streamlit → Groq API
                ↓
            Supabase
```

## Installation

Clone the repository:

```bash
git clone <repository-url>
cd academic-pathway-recommender
```

Install dependencies:

```bash
pip install -r requirements.txt
```
## Database Setup (Supabase)

Create a new project in Supabase and run the following SQL in the SQL Editor:

```sql
CREATE TABLE public.submissions (
  id serial NOT NULL,
  full_name text NOT NULL,
  email text NOT NULL,
  highest_qualification text NOT NULL,
  years_experience integer NOT NULL,
  current_profession text NOT NULL,
  career_goal text NOT NULL,
  recommendation text,
  created_at timestamp without time zone,
  CONSTRAINT submissions_pkey PRIMARY KEY (id)
);
```

After creating the table, copy your:

* `SUPABASE_URL`
* `SUPABASE_KEY`

and add them to your `.env` file.

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
GROQ_API_KEY=your_groq_api_key
```

Run the application:

```bash
streamlit run app.py
```

## Example

**Input**

* Qualification: Master's Degree
* Experience: 8 Years
* Profession: Data Scientist
* Goal: Lead AI research teams

**Output**

* Recommended Pathway: PhD

## Future Improvements

* Recommendation confidence scores
* Detailed recommendation explanations
* User authentication
* Analytics dashboard

## Author

Ashutosh Narayan
