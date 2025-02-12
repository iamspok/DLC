import os
import time
import random
import pandas as pd
from flask import Flask, jsonify, render_template
from supabase import create_client

# ✅ Supabase Setup (Ensure API Keys Are Correct)
SUPABASE_URL = "https://dfckzgwvefprwuythpnl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRmY2t6Z3d2ZWZwcnd1eXRocG5sIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkyNjM0MTEsImV4cCI6MjA1NDgzOTQxMX0.5EnzP0Ck3VhxBOVoVX_nsozSU8OYe57aySSCPH2BCWU"  # 🔴 Make sure this is correct
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

CACHE_DURATION = 60 * 60 * 24 * 30  # 30 days
selected_questions = []  # Global variable for storing questions

# ✅ Load Questions from Supabase (If Available)
def load_questions_from_supabase():
    one_month_ago = int(time.time()) - CACHE_DURATION

    response = supabase.table("quiz_questions").select("*").gte("timestamp", one_month_ago).execute()
    if response.data:
        print("✅ Using cached questions from Supabase.")
        return [
            {
                "question": q["question"],
                "correct_answer": q["correct_answer"],
                "answers": eval(q["answers"])  # Convert stored string back to list
            }
            for q in response.data
        ]
    return None

# ✅ Save New Questions to Supabase
def save_questions_to_supabase(questions):
    supabase.table("quiz_questions").delete().execute()  # 🗑️ Clear old questions
    for q in questions:
        data = {
            "question": q["question"],
            "correct_answer": q["correct_answer"],
            "answers": str(q["answers"]),  # Convert list to string
            "timestamp": int(time.time())
        }
        supabase.table("quiz_questions").insert(data).execute()

# ✅ Load Questions from Excel (ONLY IF NO SUPABASE QUESTIONS EXIST)
def load_questions_from_excel():
    file_path = 'DLC Question Bank.xlsx'
    sheet_name = 'Question Bank (EN)'

    if not os.path.exists(file_path):
        print(f"❌ Error: File '{file_path}' not found.")
        return []

    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')

    required_cols = ['Status', 'Questions', 'Correct Answer']
    for col in required_cols:
        if col not in df.columns:
            print(f"❌ Error: Required column '{col}' missing in Excel.")
            return []

    df_filtered = df[df['Status'].astype(str).str.lower() != 'green']
    df_filtered = df_filtered.dropna(subset=['Questions', 'Correct Answer'])

    answer_cols = ['Answer 2', 'Answer 3', 'Answer 4', 'Answer 5']

    def has_valid_incorrect_answers(row):
        return any(str(row[col]).strip().lower() not in ['', '/', 'nan', 'none'] for col in answer_cols)

    df_filtered = df_filtered[df_filtered.apply(has_valid_incorrect_answers, axis=1)]

    if df_filtered.empty:
        print("❌ No valid questions available after filtering!")
        return []

    selected_rows = df_filtered.sample(n=min(15, len(df_filtered)))

    questions = []
    for _, question_row in selected_rows.iterrows():
        question = question_row['Questions'].strip()
        correct_answer = question_row['Correct Answer'].strip()
        incorrect_answers = [
            str(question_row[col]).strip() for col in answer_cols
            if str(question_row[col]).strip().lower() not in ['', '/', 'nan', 'none']
        ]

        chosen_incorrects = random.sample(incorrect_answers, min(3, len(incorrect_answers)))
        answers = [correct_answer] + chosen_incorrects
        random.shuffle(answers)

        questions.append({
            "question": question,
            "answers": answers,
            "correct_answer": correct_answer
        })

    return questions

# ✅ Main Function to Load Questions
def load_questions(force_reload=False):
    global selected_questions

    if not force_reload:
        cached_questions = load_questions_from_supabase()
        if cached_questions:
            selected_questions = cached_questions
            return

    print("📌 Loading new questions from Excel...")
    selected_questions = load_questions_from_excel()

    if selected_questions:
        save_questions_to_supabase(selected_questions)

# ✅ Flask Route to Display Questions
@app.route('/')
def display_questions():
    load_questions()
    if not selected_questions:
        return jsonify({'error': 'No questions loaded. Check server logs or Excel file.'})

    return render_template('quiz.html', questions=enumerate(selected_questions))

if __name__ == '__main__':
    load_questions()
    app.run(debug=True)
