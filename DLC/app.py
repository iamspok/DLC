import os
import random
import pandas as pd
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# Global variable for selected questions
selected_questions = []

def load_questions():
    """
    Loads questions from an Excel file and populates `selected_questions`.
    It filters out:
      1) Rows with 'green' status,
      2) Rows missing 'Questions' or 'Correct Answer',
      3) Rows that do not have at least one valid incorrect answer
         (or adjust logic if you truly need 3).
    Then it samples up to 15 questions from what remains.
    """
    global selected_questions

    try:
        file_path = 'DLC Question Bank.xlsx'
        sheet_name = 'Question Bank (EN)'

        if not os.path.exists(file_path):
            print(f"Error: File '{file_path}' not found.")
            return

        df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')

        # Ensure required columns exist
        required_cols = ['Status', 'Questions', 'Correct Answer']
        for col in required_cols:
            if col not in df.columns:
                print(f"Error: Required column '{col}' missing in Excel.")
                return

        # 1) Filter out rows with 'green' status
        df_filtered = df[df['Status'].astype(str).str.lower() != 'green']

        # 2) Drop rows that have missing question or correct answer
        df_filtered = df_filtered.dropna(subset=['Questions', 'Correct Answer'])

        # 3) Ensure there is at least one valid incorrect answer
        #    (If you actually require 3 incorrect answers, adjust the condition.)
        answer_cols = ['Answer 2', 'Answer 3', 'Answer 4', 'Answer 5']

        def has_valid_incorrect_answers(row):
            # Build a list of any non-empty, non-'/', non-'nan', non-'None' answers
            valid_incorrects = []
            for col in answer_cols:
                val = row.get(col, '')
                val_str = str(val).strip().lower()

                # Discard if it's empty, '/', 'nan', or 'none'
                if val_str not in ['', '/', 'nan', 'none']:
                    valid_incorrects.append(val_str)

            # Return True if there's at least 1 valid incorrect answer
            # If you truly need 3, use: return len(valid_incorrects) >= 3
            return len(valid_incorrects) >= 1

        df_filtered = df_filtered[df_filtered.apply(has_valid_incorrect_answers, axis=1)]

        # Now df_filtered has only rows with:
        #   - Non-green status
        #   - Non-empty 'Questions' and 'Correct Answer'
        #   - At least 1 valid incorrect answer
        print(f"Total questions after filtering: {len(df_filtered)}")

        # 4) Sample up to 15 questions
        num_questions = min(15, len(df_filtered))
        if num_questions == 0:
            print("No valid questions available after filtering!")
            return

        selected_rows = df_filtered.sample(n=num_questions, random_state=None)

        # Clear out previously selected questions
        selected_questions.clear()

        # Build the final list of question dictionaries
        for _, question_row in selected_rows.iterrows():
            question = question_row['Questions'].strip()
            correct_answer = question_row['Correct Answer'].strip()

            # Gather possible incorrect answers (already validated)
            incorrect_answers = []
            for col in answer_cols:
                val = question_row.get(col, '')
                val_str = str(val).strip()
                # Check again if valid
                if val_str.lower() not in ['', '/', 'nan', 'none']:
                    incorrect_answers.append(val_str)

            # Pick up to 3 from the incorrect answers
            chosen_incorrects = random.sample(incorrect_answers, min(3, len(incorrect_answers)))

            # Combine correct + chosen incorrect and shuffle
            answers = [correct_answer] + chosen_incorrects
            random.shuffle(answers)

            selected_questions.append({
                'question': question,
                'answers': answers,
                'correct_answer': correct_answer
            })

        print(f"Final selected questions count: {len(selected_questions)}")

    except Exception as e:
        print(f"Error loading questions: {e}")

# Load questions on startup
load_questions()

@app.route('/')
def display_questions():
    """
    Route that renders a template or returns JSON if no questions are loaded.
    """
    try:
        if not selected_questions:
            return jsonify({'error': 'No questions loaded. Please check the Excel file or server logs.'})

        # Pass the questions to the template
        return render_template('quiz.html', questions=selected_questions)
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
 
