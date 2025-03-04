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
        selected_questions = []
        
        for idx, q in enumerate(response.data):
            correct_answer = q["correct_answer"].strip()  # Make sure it's clean
            all_answers = eval(q["answers"])  # Convert string to list
            
            # Ensure the correct answer is included in the answer choices
            if correct_answer not in all_answers:
                all_answers.append(correct_answer)

            # Shuffle the answers so it's not always in the same spot
            random.shuffle(all_answers)

            selected_questions.append({
                "id": idx + 1,
                "question": q["question"],
                "correct_answer": correct_answer,
                "answers": all_answers,
                "name": f"question_{idx+1}"
            })
        
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

@app.route('/quiz', methods=['POST', 'GET'])
def display_questions():
    """Display the quiz questions with unique names."""
    load_questions()

    if not selected_questions:
        return jsonify({'error': 'No questions loaded. Check server logs or Excel file.'})

    # Assign unique names to each question (question_1, question_2, ..., question_15)
    for idx, question in enumerate(selected_questions):
        question['name'] = f"question_{idx+1}"

    return render_template("quiz.html", questions=selected_questions)

@app.route('/submit', methods=['POST'])
def submit_quiz():
    """Handles quiz submission."""
    email = session.get('email')
    site = session.get('site')

    if not email:
        email = request.form.get('email')
    if not site:
        site = request.form.get('site')

    if not email or not site:
        return "Error: Email and site are required!", 400

    correct_count = 0
    question_scores = {}

    for idx, question in enumerate(selected_questions):
        question_name = f'question_{idx+1}'
        user_answer = request.form.get(question_name, "").strip()
        correct_answer = question.get('correct_answer', "").strip()

        # Handle "NO_ANSWER" responses
        if user_answer == "NO_ANSWER":
            print(f"⚠️ Question {idx+1} was left unanswered")
            question_scores[f'{question_name}_score'] = 0
            continue  # Skip checking this question

        # Debugging output
        print(f"🔍 Checking Q{idx+1}:")
        print(f"User Answer: '{user_answer}' | Correct Answer: '{correct_answer}'")

        is_correct = 1 if user_answer.lower() == correct_answer.lower() else 0
        question_scores[f'{question_name}_score'] = is_correct

        if is_correct:
            correct_count += 1

    total_questions = len(selected_questions)
    score = correct_count

    # ✅ Store the score in the session before redirecting
    session['score'] = score
    session['total_questions'] = total_questions

    print(f"✅ DEBUG: Storing score {score}/{total_questions} in session")

    # Store results in Supabase
    supabase.table("quiz_results").insert({
        "email": email,
        "site": site,
        "overall_score": score,
        **question_scores
    }).execute()

    return redirect(url_for('results'))


@app.route('/results')
def results():
    """Displays the user's score after submitting the quiz."""
    score = session.get('score', 0)  # Default to 0 if missing
    total_questions = session.get('total_questions', 15)  # Default to 15

    return render_template('results.html', score=score, total_questions=total_questions)
