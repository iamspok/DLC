import os
import time
import random
import pandas as pd
from flask import Flask, request, render_template, session, redirect, url_for
from supabase import create_client

# 🔹 Supabase Setup
SUPABASE_URL = "https://dfckzgwvefprwuythpnl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRmY2t6Z3d2ZWZwcnd1eXRocG5sIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkyNjM0MTEsImV4cCI6MjA1NDgzOTQxMX0.5EnzP0Ck3VhxBOVoVX_nsozSU8OYe57aySSCPH2BCWU"  # Use your key
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Flask Setup
app = Flask(__name__)
app.secret_key = "supersecretkey"

# 🔹 Routes Start Here 🔹

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        session["email"] = request.form.get("email")
        session["site"] = request.form.get("site")
        session["flow"] = request.form.get("flow")  # Player Services or Engagement

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

    # ✅ Decide which table to query based on the flow
    if flow == "services":
        table_name = "quiz_questions"  # Player Services
    elif flow == "engagement":
        table_name = "quiz_questions_engagement"  # Player Engagement
    else:
        return "⚠️ Invalid flow. Please select a valid area.", 400

    # ✅ Fetch the current DLC ID (optional, if your table includes dlc_id filtering)
    dlc_id = get_latest_dlc()

    # ✅ Fetch the selected 15 questions from the correct table
    # ❗ If you're storing DLC-specific questions in these tables, use `.eq("dlc_id", dlc_id)`
    response = supabase.table(table_name).select("*").eq("dlc_id", dlc_id).execute()

    if not response.data:
        return f"⚠️ No questions found for {flow} in DLC {dlc_id}.", 404

    # ✅ Process the selected questions (manual naming enforced)
    selected_questions = []
    for idx, q in enumerate(response.data):
        correct_answer = q["correct_answer"].strip()
        answers = eval(q["answers"])  # Stored as stringified list

        if correct_answer not in answers:
            answers.append(correct_answer)

        random.shuffle(answers)

        selected_questions.append({
            "id": idx + 1,
            "question": q["question"],
            "correct_answer": correct_answer,
            "answers": answers,
            "name": f"question_{idx + 1}"  # ✅ Manual naming, ensures one answer per question
        })

    # ✅ Save selected questions in session for submission
    session["selected_questions"] = selected_questions

    return render_template("quiz.html", questions=selected_questions)

@app.route('/submit', methods=['POST'])
def submit_quiz():
    email = session.get('email')
    site = session.get('site')
    flow = session.get('flow')
    selected_questions = session.get('selected_questions')
    dlc_id = get_latest_dlc()

    if not all([email, site, flow, selected_questions, dlc_id]):
        return "⚠️ Missing data. Please restart the DLC.", 400

    # ✅ Determine which results table to use
    if flow == "services":
        results_table = "quiz_results"
    elif flow == "engagement":
        results_table = "quiz_results_engagement"
    else:
        return "⚠️ Invalid flow. Cannot submit results.", 400

    # ✅ Check for duplicate submissions within the same DLC
    existing_entry = supabase.table(results_table).select("email").eq("email", email).eq("dlc_id", dlc_id).execute()
    if existing_entry.data:
        return "⚠️ You have already completed this DLC.", 400

    correct_count = 0
    question_scores = {}
    total_questions = len(selected_questions)

    # ✅ Initialize scores (defaults to 0)
    for i in range(1, total_questions + 1):
        question_scores[f'question_{i}_score'] = 0

    # ✅ Grade the answers (manual naming ensures one answer only)
    for idx, question in enumerate(selected_questions):
        question_name = f'question_{idx + 1}'
        user_answer = request.form.get(question_name, "").strip().lower()
        correct_answer = question.get('correct_answer', "").strip().lower()

        print(f"🔍 {question_name}: User Answer = '{user_answer}' | Correct Answer = '{correct_answer}'")

        if user_answer and user_answer != "no_answer":
            is_correct = 1 if user_answer == correct_answer else 0
            question_scores[f'{question_name}_score'] = is_correct
            if is_correct:
                correct_count += 1

    session['score'] = correct_count
    session['total_questions'] = total_questions

    print(f"✅ {email} scored {correct_count}/{total_questions} in {flow}.")

    # ✅ Save results
    supabase.table(results_table).insert({
        "email": email,
        "site": site,
        "dlc_id": dlc_id,
        "overall_score": correct_count,
        **question_scores
    }).execute()

    return redirect(url_for('results'))


@app.route('/results')
def results():
    score = session.get('score', 0)
    total_questions = session.get('total_questions', 15)
    flow = session.get('flow')

    if flow == "engagement":
        title = "Player Engagement DLC Completed!"
    else:
        title = "Player Services DLC Completed!"

    return render_template('results.html', score=score, total_questions=total_questions, title=title)


# ✅ Utility: Get latest DLC period
def get_latest_dlc():
    response = supabase.table("dlc_settings").select("current_dlc").execute()

    if response.data and len(response.data) > 0:
        return response.data[0]["current_dlc"]

    return None


if __name__ == "__main__":
    app.run(debug=True)
