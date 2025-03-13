import os
import random
from flask import Flask, request, render_template, session, redirect, url_for
from supabase import create_client
from datetime import datetime

# 🔹 Supabase Setup
SUPABASE_URL = "https://dfckzgwvefprwuythpnl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRmY2t6Z3d2ZWZwcnd1eXRocG5sIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkyNjM0MTEsImV4cCI6MjA1NDgzOTQxMX0.5EnzP0Ck3VhxBOVoVX_nsozSU8OYe57aySSCPH2BCWU"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🔹 Flask Setup
app = Flask(__name__)
app.secret_key = "supersecretkey"

# ======================================================
def get_current_dlc():
    response = supabase.table("dlc_settings").select("current_dlc").execute()
    if response.data and len(response.data) > 0:
        return response.data[0]['current_dlc']
    return None

# ======================================================
def fetch_locked_or_lock_questions(flow, limit=15):
    current_dlc = get_current_dlc()
    if not current_dlc:
        print(f"❗ No current DLC found.")
        return []

    locked_response = supabase.table("dlc_question_lock").select("question_id").eq("dlc_id", current_dlc).eq("flow", flow).execute()
    locked_question_ids = [entry['question_id'] for entry in locked_response.data]

    if locked_question_ids:
        print(f"🔒 Found {len(locked_question_ids)} locked questions for {flow} in {current_dlc}")

        table_name = get_table_name(flow)
        locked_questions = []
        for qid in locked_question_ids:
            question_resp = supabase.table(table_name).select("*").eq("id", qid).single().execute()
            if question_resp.data:
                locked_questions.append(question_resp.data)

        return locked_questions

    # No locks yet? Let's create them.
    new_questions = select_questions(flow, limit)

    if not new_questions:
        print(f"❗ No questions found to lock for {flow}")
        return []

    quiz_table = "quiz_questions" if flow == "services" else "quiz_questions_engagement"

    # ✅ THIS IS THE BLOCK CAUSING THE INDENTATION ERROR
    for question in new_questions:
        supabase.table("dlc_question_lock").insert({
            "dlc_id": current_dlc,
            "question_id": question['id'],
            "flow": flow,
            "locked_at": datetime.utcnow().isoformat()
        }).execute()

        supabase.table(quiz_table).insert({
            "question": question.get('question'),
            "correct_answer": question.get('correct_answer'),
            "answers": [
                question.get('correct_answer'),
                question.get('answer_2'),
                question.get('answer_3'),
                question.get('answer_4'),
                question.get('answer_5')
            ],
            "timestamp": int(datetime.utcnow().timestamp())  # Use BIGINT timestamp for now
        }).execute()

    print(f"✅ Locked and populated {len(new_questions)} questions for {flow} in {current_dlc}")
    return new_questions


# ======================================================
def select_questions(flow, limit=15):
    table_name = get_table_name(flow)
    if not table_name:
        return []

    # Step 1: Get all push questions (always included)
    push_response = supabase.table(table_name).select("*").eq('status', 'push').execute()
    push_questions = push_response.data or []
    print(f"📌 {flow} - Found {len(push_questions)} push questions")

    remaining_slots = limit - len(push_questions)

    # Step 2: Get remaining questions (status not 'inactive' or 'push')
    if remaining_slots > 0:
        active_response = supabase.table(table_name).select("*").not_.in_('status', ['inactive', 'push']).execute()
        available_pool = active_response.data or []
        random.shuffle(available_pool)
        active_questions = available_pool[:remaining_slots]
    else:
        active_questions = []

    all_questions = push_questions + active_questions
    random.shuffle(all_questions)

    print(f"✅ {flow} - Selected {len(all_questions)} total questions (Push: {len(push_questions)}, Random Active: {len(active_questions)})")
    return all_questions

# ======================================================
def get_table_name(flow):
    if flow == "services":
        return "player_services_question_bank"
    elif flow == "engagement":
        return "player_engagement_question_bank"
    return None

# ======================================================
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        session["email"] = request.form.get("email")
        session["site"] = request.form.get("site")
        session["flow"] = request.form.get("flow")

        if not session["flow"]:
            return "⚠️ Please select an area (Player Engagement or Player Services).", 400

        print(f"✅ Flow selected: {session['flow']}")
        return redirect(url_for("display_questions"))

    return render_template("start.html")

# ======================================================
@app.route('/quiz', methods=['GET', 'POST'])
def display_questions():
    flow = session.get("flow")
    if not flow:
        return "⚠️ Flow not specified. Please start again.", 400

    selected_questions = fetch_locked_or_lock_questions(flow, limit=15)

    if not selected_questions:
        return "⚠️ No questions available for this DLC.", 404

    processed_questions = []
    for idx, q in enumerate(selected_questions):
        answers = [
            (q.get('correct_answer') or '').strip(),
            (q.get('answer_2') or '').strip(),
            (q.get('answer_3') or '').strip(),
            (q.get('answer_4') or '').strip(),
            (q.get('answer_5') or '').strip(),
        ]
        answers = [a for a in answers if a]
        random.shuffle(answers)

        processed_questions.append({
            "id": idx + 1,
            "question": q.get('question', ''),
            "correct_answer": q.get('correct_answer', ''),
            "answers": answers,
            "name": f"question_{idx + 1}"
        })

    session["selected_questions"] = processed_questions
    return render_template("quiz.html", questions=processed_questions)

# ======================================================
@app.route('/submit', methods=['POST'])
def submit_quiz():
    email = session.get('email')
    site = session.get('site')
    flow = session.get('flow')
    selected_questions = session.get('selected_questions')
    current_dlc = get_current_dlc()

    if not all([email, site, flow, selected_questions, current_dlc]):
        return "⚠️ Missing data. Please restart the DLC.", 400

    results_table = "quiz_results" if flow == "services" else "quiz_results_engagement"

    existing_entry = supabase.table(results_table).select("email").eq("email", email).eq("dlc_id", current_dlc).execute()
    if existing_entry.data:
        return "⚠️ You have already completed this DLC.", 400

    correct_count = 0
    question_scores = {}
    total_questions = len(selected_questions)

    for i in range(1, total_questions + 1):
        question_scores[f'question_{i}_score'] = 0

    for idx, question in enumerate(selected_questions):
        question_name = f'question_{idx + 1}'
        user_answer = request.form.get(question_name, "").strip().lower()
        correct_answer = (question.get('correct_answer') or '').strip().lower()

        if user_answer and user_answer != "no_answer":
            is_correct = 1 if user_answer == correct_answer else 0
            question_scores[f'{question_name}_score'] = is_correct
            if is_correct:
                correct_count += 1

    session['score'] = correct_count
    session['total_questions'] = total_questions

    supabase.table(results_table).insert({
        "email": email,
        "site": site,
        "dlc_id": current_dlc,
        "overall_score": correct_count,
        **question_scores
    }).execute()

    return redirect(url_for('results'))

# ======================================================
@app.route('/results')
def results():
    score = session.get('score', 0)
    total_questions = session.get('total_questions', 15)
    flow = session.get('flow')

    title = "Player Engagement DLC Completed!" if flow == "engagement" else "Player Services DLC Completed!"

    return render_template('results.html', score=score, total_questions=total_questions, title=title)

# ======================================================
if __name__ == "__main__":
    app.run(debug=True)
