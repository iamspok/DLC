import os
import random
import pandas as pd
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# Initialize selected_questions to avoid undefined variable errors
selected_questions = []

try:
    file_path = 'DLC Question Bank.xlsx'
    sheet_name = 'Question Bank (EN)'

    # Step 1: Load the Excel file
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')

    print("Columns in Excel:", df.columns.tolist())
    
    # Step 2: Filter out "green status" questions
    df_filtered = df[df['Status'].str.lower() != 'green']
    print("Filtered DataFrame:", df_filtered.head())

    # Step 3: Select random questions
    while len(selected_questions) < 15:
        question_row = df_filtered.sample(n=1).iloc
        print("Selected question row:", question_row.to_dict())
        question = question_row['Questions']
        correct_answer = question_row['Correct Answer']
        answers = [correct_answer]

        incorrect_answers = [question_row[col] for col in ['Answer 2', 'Answer 3', 'Answer 4', 'Answer 5'] if question_row[col] != '/']
        answers.extend(random.sample(incorrect_answers, min(3, len(incorrect_answers))))
        random.shuffle(answers)

        selected_questions.append({
            'question': question,
            'answers': answers,
            'correct_answer': correct_answer
        })

except Exception as e:
    print(f"Error during initialization: {e}")  # This will show up in Heroku logs

@app.route('/')
def display_questions():
    try:
        if not selected_questions:
            return jsonify({'error': 'No questions loaded. Please check the Excel file or server logs.'})

        return render_template('quiz.html', questions=selected_questions)
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
