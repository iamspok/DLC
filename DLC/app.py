import os
import random
import pandas as pd
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# Global variable for selected questions
selected_questions = []

def load_questions():
    global selected_questions
    try:
        file_path = 'DLC Question Bank.xlsx'
        sheet_name = 'Question Bank (EN)'

        if not os.path.exists(file_path):
            print(f"Error: File '{file_path}' not found.")
            return

        df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')

        if 'Status' not in df.columns or 'Questions' not in df.columns:
            print("Error: Required columns missing from Excel file.")
            return

        # Filter out "green" status AND drop rows with missing questions
        df_filtered = df[df['Status'].astype(str).str.lower() != 'green'].dropna(subset=['Questions'])

        print("Filtered DataFrame:", df_filtered.head())

        selected_questions = []  

        while len(selected_questions) < 15 and not df_filtered.empty:
            question_row = df_filtered.sample(n=1).iloc[0]

            question = question_row.get('Questions', '').strip()
            correct_answer = question_row.get('Correct Answer', '').strip()

            if not question or not correct_answer:  # Skip if question or answer is missing
                continue

            incorrect_answers = [
                str(question_row.get(col, '/')).strip() for col in ['Answer 2', 'Answer 3', 'Answer 4', 'Answer 5']
                if str(question_row.get(col, '/')).strip() not in ['/', '', 'nan']
            ]

            answers = [correct_answer] + random.sample(incorrect_answers, min(3, len(incorrect_answers)))
            random.shuffle(answers)

            selected_questions.append({
                'question': question,
                'answers': answers,
                'correct_answer': correct_answer
            })

    except Exception as e:
        print(f"Error loading questions: {e}")

# Load questions on startup
load_questions()

@app.route('/')
def display_questions():
    try:
        if not selected_questions:
            return jsonify({'error': 'No questions loaded. Please check the Excel file or server logs.'})

        print("DEBUG: Passing questions to template", selected_questions)  # Debugging
        return render_template('quiz.html', questions=selected_questions)
    except Exception as e:
        return jsonify({'error': str(e)})


if __name__ == '__main__':
    app.run(debug=True)
