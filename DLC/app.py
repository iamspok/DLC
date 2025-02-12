import os
import time
import csv
import random
import pandas as pd
from flask import Flask, request, jsonify, render_template, send_file
from supabase import create_client

# Supabase Setup
SUPABASE_URL = "https://dfckzgwvefprwuythpnl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRmY2t6Z3d2ZWZwcnd1eXRocG5sIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkyNjM0MTEsImV4cCI6MjA1NDgzOTQxMX0.5EnzP0Ck3VhxBOVoVX_nsozSU8OYe57aySSCPH2BCWU"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

selected_questions = []
CACHE_DURATION = 60 * 60 * 24 * 30  # 30 days in seconds
CSV_FILE = "quiz_results.csv"  # CSV file for results storage

def load_questions_from_supabase():
    """Load questions from Supabase if available."""
    one_month_ago = int(time.time()) - CACHE_DURATION

    response = supabase.table("quiz_questions").select("*").gte("timestamp", one_month_ago).execute()
    if response.data:
        print("✅ Using cached questions from Supabase.")
        return [
            {
                "question": q["question"],
                "correct_answer": q["correct_answer"],
                "answers": eval(q["answers"])  # Convert string back to list
            }
            for q in response.data
        ]
    return None

def save_questions_to_supabase(questions):
    """Save selected questions to Supabase."""
    for q in questions:
        data = {
            "question": q["question"],
            "correct_answer": q["correct_answer"],
            "answers": str(q["answers"]),
            "timestamp": int(time.time())
        }
        supabase.table("quiz_questions").insert(data).execute()

def load_questions_from_excel():
    """Loads and filters questions from Excel."""
    file_path = 'DLC Question Bank.xlsx'
    sheet_name = 'Question Bank (EN)'

    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return []

    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')

    required_cols = ['Status', 'Questions', 'Correct Answer']
    for col in required_cols:
        if col not in df.columns:
            print(f"Error: Required column '{col}' missing in Excel.")
            return []

    df_filtered = df[df['Status'].astype(str).str.lower() != 'green']
    df_filtered = df_filtered.dropna(subset=['Questions', 'Correct Answer'])

    answer_cols = ['Answer 2', 'Answer 3', 'Answer 4', 'Answer 5']

    def has_valid_incorrect_answers(row):
        valid_incorrects = []
        for col in answer_cols:
            val = row.get(col, '')
            val_str = str(val).strip().lower()
            if val_str not in ['', '/', 'nan', 'none']:
                valid_incorrects.append(val_str)
        return len(valid_incorrects) >= 1

    df_filtered = df_filtered[df_filtered.apply(has_valid_incorrect_answers, axis=1)]

    if df_filtered.empty:
        print("No valid questions available after filtering!")
        return []

    selected_rows = df_filtered.sample(n=min(15, len(df_filtered)))

    questions = []
    for _, question_row in selected_rows.iterrows():
        question = question_row['Questions'].strip()
        correct_answer = question_row['Correct Answer'].strip()

        incorrect_answers = []
        for col in answer_cols:
            val = question_row.get(col, '')
            val_str = str(val).strip()
            if val_str.lower() not in ['', '/', 'nan', 'none']:
                incorrect_answers.append(val_str)

        chosen_incorrects = random.sample(incorrect_answers, min(3, len(incorrect_answers)))
        answers = [correct_answer] + chosen_incorrects
        random.shuffle(answers)

        questions.append({
            'question': question,
            'answers': answers,
            'correct_answer': correct_answer
        })

    return questions

def load_questions(force_reload=False):
    """Loads questions from Supabase if available, otherwise from Excel."""
    global selected_questions

    if not force_reload:
        cached_questions = load_questions_from_supabase()
        if cached_questions:
            selected_questions = cached_questions
            return

    print("🔄 Loading new questions from Excel...")
    selected_questions = load_questions_from_excel()

    if selected_questions:
        save_questions_to_supabase(selected_questions)

@app.route('/')
def display_questions():
    """Display the quiz questions."""
    load_questions()

    if not selected_questions:
        return jsonify({'error': 'No questions loaded. Check server logs or Excel file.'})

    return render_template('quiz.html', questions=selected_questions)

@app.route('/submit', methods=['POST'])
def submit_quiz():
    """Handles quiz submission."""
    email = request.form.get('email')
    site = request.form.get('site')

    user_answers = {}
    correct_count = 0

    for idx, question in enumerate(selected_questions):
        user_answer = request.form.get(f'question_{idx}')
        correct_answer = question['correct_answer']

        user_answers[question['question']] = {
            "user_answer": user_answer,
            "correct_answer": correct_answer
        }

        if user_answer == correct_answer:
            correct_count += 1

    total_questions = len(selected_questions)
    score = f"{correct_count}/{total_questions}"

    # Store in Supabase
    supabase.table("quiz_results").insert({
        "email": email,
        "site": site,
        "score": score,
        "answers": str(user_answers),
        "timestamp": int(time.time())
    }).execute()

    return f"Quiz submitted! Your score: {score}"

@app.route('/admin/results')
def download_results():
    """Download results as CSV."""
    return send_file(CSV_FILE, as_attachment=True)

if __name__ == '__main__':
    load_questions()
    app.run(debug=True)
