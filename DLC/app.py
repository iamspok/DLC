import os
import time
import random
import json  # Ensure this is here!
import pandas as pd
from flask import Flask, jsonify, render_template
from supabase import create_client

# Supabase Setup
SUPABASE_URL = "https://dfckzgwvefprwuythpnl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRmY2t6Z3d2ZWZwcnd1eXRocG5sIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkyNjM0MTEsImV4cCI6MjA1NDgzOTQxMX0.5EnzP0Ck3VhxBOVoVX_nsozSU8OYe57aySSCPH2BCWU"  # Ensure this is stored securely
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

selected_questions = []
CACHE_DURATION = 60 * 60 * 24 * 30  # 30 days in seconds

def load_questions_from_supabase():
    """Load questions from Supabase if available."""
    one_month_ago = int(time.time()) - CACHE_DURATION

    response = supabase.table("quiz_questions").select("*").gte("timestamp", one_month_ago).execute()
    if response.data:
        print("Using cached questions from Supabase.")
        return [
            {
                "id": q["id"],  # Ensure ID is included
                "question": q["question"],
                "correct_answer": q["correct_answer"],
                "answers": json.loads(q["answers"])  # Convert string to list properly
            }
            for q in response.data
        ]
    return None

def save_questions_to_supabase(questions):
    """Save questions to Supabase."""
    for q in questions:
        data = {
            "id": q["id"],  # Ensure ID is stored
            "question": q["question"],
            "correct_answer": q["correct_answer"],
            "answers": json.dumps(q["answers"]),  # Convert list to JSON string
            "timestamp": int(time.time())
        }
        supabase.table("quiz_questions").insert(data).execute()

def load_questions_from_supabase():
    """Load questions from Supabase if available."""
    try:
        one_month_ago = int(time.time()) - CACHE_DURATION
        response = supabase.table("quiz_questions").select("*").gte("timestamp", one_month_ago).execute()

        if response.data:
            print("Using cached questions from Supabase.")
            return [
                {
                    "id": q.get("id", index),  # Ensure there's always an ID
                    "question": q["question"],
                    "correct_answer": q["correct_answer"],
                    "answers": json.loads(q["answers"])  # Fix JSON parsing
                }
                for index, q in enumerate(response.data)
            ]
        return None
    except Exception as e:
        print(f"Error loading from Supabase: {e}")
        return None

    # Filter out 'green' status
    df_filtered = df[df['Status'].astype(str).str.lower() != 'green']

    # Drop rows missing question or correct answer
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

    # Sample up to 15
    selected_rows = df_filtered.sample(n=min(15, len(df_filtered)))

    questions = []
    for i, (_, question_row) in enumerate(selected_rows.iterrows()):
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
            "id": i + 1,  # Generate a unique ID if missing
            "question": question,
            "answers": answers,
            "correct_answer": correct_answer
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

    print("Loading new questions from Excel...")
    selected_questions = load_questions_from_excel()

    if selected_questions:
        save_questions_to_supabase(selected_questions)

@app.route('/')
def display_questions():
    """Display the quiz questions."""
    print("📌 Loading questions...")  # Debugging line
    load_questions()
    print(f"📌 Loaded {len(selected_questions)} questions.")  # Debugging line

    if not selected_questions:
        print("❌ No questions loaded!")  # Debugging line
        return jsonify({'error': 'No questions loaded. Check server logs or Excel file.'})

    return render_template('quiz.html', questions=selected_questions)

if __name__ == '__main__':
    load_questions()
    app.run(debug=True)
