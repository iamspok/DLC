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
    if request.method == "POST":
        session["email"] = request.form.get("email")
        session["site"] = request.form.get("site")
        session["flow"] = request.form.get("flow")  # ✅ Grab the flow selection

        if not session["flow"]:
            return "⚠️ Please select an area (Player Engagement or Player Services).", 400

        print(f"✅ Flow selected: {session['flow']}")
        return redirect(url_for("display_questions"))

    return render_template("start.html")

@app.route('/quiz', methods=['POST', 'GET'])
def display_questions():
    # ✅ Get the flow the user selected
    flow = session.get("flow")

    if not flow:
        return "⚠️ Flow not specified. Please start again.", 400

    # ✅ Decide which table to query
    if flow == "services":
        table_name = "quiz_questions"  # existing services path
    elif flow == "engagement":
        table_name = "quiz_questions_engagement"  # new engagement path
    else:
        return "⚠️ Invalid flow. Please select a valid area.", 400

    # ✅ Fetch the questions from Supabase
    response = supabase.table(table_name).select("*").execute()

    if not response.data:
        return f"⚠️ No questions found for {flow}.", 404

    # ✅ Process the questions (same as before)
    selected_questions = []
    for idx, q in enumerate(response.data):
        correct_answer = q["correct_answer"].strip()
        answers = eval(q["answers"])  # Stored as a stringified list

        if correct_answer not in answers:
            answers.append(correct_answer)

        import random
        random.shuffle(answers)

        selected_questions.append({
            "id": idx + 1,
            "question": q["question"],
            "correct_answer": correct_answer,
            "answers": answers,
            "name": f"question_{idx+1}"
        })

    # ✅ Save selected questions to session
    session["selected_questions"] = selected_questions

    return render_template("quiz.html", questions=selected_questions)

def get_latest_dlc():
    """Fetches the current active DLC ID from the Supabase settings table."""
    response = supabase.table("dlc_settings").select("current_dlc").execute()
    
    if response.data and len(response.data) > 0:
        return response.data[0]["current_dlc"]
    
    return None  # If no DLC is found

@app.route('/submit', methods=['POST'])
def submit_quiz():
    """Handles quiz submission and stores results in Supabase."""
    email = session.get('email')
    site = session.get('site')
    dlc_id = get_latest_dlc()  # ✅ Ensure DLC ID is fetched correctly

    if not email:
        email = request.form.get('email')
    if not site:
        site = request.form.get('site')

    if not email or not site or not dlc_id:
        return "Error: Email, site, and DLC ID are required!", 400

    # ✅ Debug: Print all submitted form data
    print(f"📩 DEBUG: Received form data: {dict(request.form)}")

    if not selected_questions:
        load_questions()

    correct_count = 0
    question_scores = {}

    total_questions = len(selected_questions)

    for i in range(1, total_questions + 1):
        question_scores[f'question_{i}_score'] = 0

    for idx, question in enumerate(selected_questions):
        question_name = f'question_{idx+1}'
        user_answer = request.form.get(question_name, "").strip().lower()
        correct_answer = question.get('correct_answer', "").strip().lower()

        print(f"🔍 Checking {question_name}:")
        print(f"User Answer: '{user_answer}' | Correct Answer: '{correct_answer}'")

        if user_answer and user_answer != "no_answer":
            is_correct = 1 if user_answer == correct_answer else 0
            question_scores[f'{question_name}_score'] = is_correct

            if is_correct:
                correct_count += 1

    score = correct_count

    session['score'] = score
    session['total_questions'] = total_questions

    print(f"✅ DEBUG: Storing score {score}/{total_questions} in session")

    # ✅ Store results in Supabase
    supabase.table("quiz_results").insert({
        "email": email,
        "site": site,
        "dlc_id": dlc_id,  # ✅ Store DLC ID in database
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
