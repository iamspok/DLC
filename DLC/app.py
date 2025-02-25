import os
import time
import random
import pandas as pd
from flask import Flask, request, render_template, send_file, session, redirect, url_for
from supabase import create_client

# Supabase Setup
SUPABASE_URL = "https://dfckzgwvefprwuythpnl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRmY2t6Z3d2ZWZwcnd1eXRocG5sIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkyNjM0MTEsImV4cCI6MjA1NDgzOTQxMX0.5EnzP0Ck3VhxBOVoVX_nsozSU8OYe57aySSCPH2BCWU"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = "supersecretkey"

selected_questions = []
CACHE_DURATION = 60 * 60 * 24 * 30  # 30 days in seconds

# ✅ Load Questions from Supabase
def load_questions():
    global selected_questions
    one_month_ago = int(time.time()) - CACHE_DURATION

    response = supabase.table("quiz_questions").select("*").gte("timestamp", one_month_ago).execute()
    if response.data:
        selected_questions = [
            {
                "id": idx + 1,
                "question": q["question"],
                "correct_answer": q["correct_answer"],
                "answers": eval(q["answers"])  # Convert string back to list
            }
            for idx, q in enumerate(response.data)
        ]
        return

    print("🔄 Loading new questions from Excel...")
    selected_questions = load_questions_from_excel()
    if selected_questions:
        save_questions_to_supabase(selected_questions)

@app.route("/", methods=["GET", "POST"])
def index():
    """Step 1: Collect email & site before starting the quiz"""
    if request.method == "POST":
        session["email"] = request.form.get("email")
        session["site"] = request.form.get("site")
        return redirect(url_for("display_questions"))

    return render_template("start.html")  # Only email & site fields

@app.route("/quiz", methods=["GET"])
def display_questions():
    """Step 2: Show quiz questions (without credentials or results)"""
    load_questions()
    if not selected_questions:
        return "No questions loaded, please try again later."

    return render_template("quiz.html", questions=selected_questions)

@app.route('/submit', methods=['POST'])
def submit_quiz():
    """Handles quiz submission."""
    email = request.form.get('email')
    site = request.form.get('site')

    user_answers = {}
    correct_count = 0
    question_scores = {}

    for idx, question in enumerate(selected_questions):
        user_answer = request.form.get(f'question_{idx+1}', '')  # Ensure an empty string instead of None
        correct_answer = question['correct_answer']

        is_correct = 1 if user_answer == correct_answer else 0  # Default to 0 if unanswered
        question_scores[f'question_{idx+1}_score'] = is_correct

        if is_correct:
            correct_count += 1

    total_questions = len(selected_questions)
    score = correct_count

    # Store in Supabase (Ensure all columns are filled)
    supabase.table("quiz_results").insert({
        "email": email,
        "site": site,
        "overall_score": score,
        **question_scores  # Ensure every question has a value (0 or 1)
    }).execute()

    return redirect(url_for('results'))


@app.route("/results")
def results():
    """Step 4: Show final score & feedback"""
    score = session.get("score")
    total_questions = session.get("total_questions")

    return render_template("results.html", score=score, total_questions=total_questions)

if __name__ == "__main__":
    app.run(debug=True)
