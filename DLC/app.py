import os
import time
import random
import pandas as pd
from flask import Flask, jsonify, render_template

app = Flask(__name__)

selected_questions = []
last_load_time = 0  # or None
CACHE_DURATION = 60 * 60  # 60 minutes in seconds

def load_questions(force_reload=False):
    """
    Loads questions from the Excel file, unless:
      - We already loaded them recently, and
      - The cache hasn't expired yet.
    
    Set `force_reload=True` if you want an immediate refresh (optional).
    """
    global selected_questions, last_load_time

    # Check if the cache is still fresh
    current_time = time.time()
    if not force_reload and (current_time - last_load_time) < CACHE_DURATION and selected_questions:
        print("Cache is still valid; skipping reload.")
        return  # Use existing questions

    print("Loading questions from the Excel file...")

    try:
        file_path = 'DLC Question Bank.xlsx'
        sheet_name = 'Question Bank (EN)'

        if not os.path.exists(file_path):
            print(f"Error: File '{file_path}' not found.")
            return

        df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')

        required_cols = ['Status', 'Questions', 'Correct Answer']
        for col in required_cols:
            if col not in df.columns:
                print(f"Error: Required column '{col}' missing in Excel.")
                return

        # Filter out 'green' status
        df_filtered = df[df['Status'].astype(str).str.lower() != 'green']

        # Drop rows missing question or correct answer
        df_filtered = df_filtered.dropna(subset=['Questions', 'Correct Answer'])

        # Ensure there's at least one valid incorrect answer
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

        print(f"Total questions after filtering: {len(df_filtered)}")

        # Sample up to 15
        num_questions = min(15, len(df_filtered))
        if num_questions == 0:
            print("No valid questions available after filtering!")
            return

        selected_rows = df_filtered.sample(n=num_questions)

        selected_questions.clear()
        for _, question_row in selected_rows.iterrows():
            question = question_row['Questions'].strip()
            correct_answer = question_row['Correct Answer'].strip()

            # Possible incorrect answers
            incorrect_answers = []
            for col in answer_cols:
                val = question_row.get(col, '')
                val_str = str(val).strip()
                if val_str.lower() not in ['', '/', 'nan', 'none']:
                    incorrect_answers.append(val_str)

            chosen_incorrects = random.sample(incorrect_answers, min(3, len(incorrect_answers)))
            answers = [correct_answer] + chosen_incorrects
            random.shuffle(answers)

            selected_questions.append({
                'question': question,
                'answers': answers,
                'correct_answer': correct_answer
            })

        print(f"Final selected questions count: {len(selected_questions)}")

        # Update the load time
        last_load_time = time.time()

    except Exception as e:
        print(f"Error loading questions: {e}")

@app.route('/')
def display_questions():
    """
    Whenever this route is accessed, we'll refresh questions
    only if the cache is expired.
    """
    # Only reload if cache expired (or first time)
    load_questions()

    if not selected_questions:
        return jsonify({'error': 'No questions loaded. Check server logs or Excel file.'})

    return render_template('quiz.html', questions=selected_questions)

if __name__ == '__main__':
    # Initial load at startup (optional)
    load_questions()
    app.run(debug=True)
 
