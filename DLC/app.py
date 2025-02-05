import os
import random
import pandas as pd
from flask import Flask, jsonify

app = Flask(__name__)

# Step 1: Define file path for the Excel file in the same directory
file_path = 'DLC Question Bank.xlsx'  # Make sure this file is in the same folder as app.py
sheet_name = 'Question Bank (EN)'  # Adjust if necessary

# Step 2: Load the Excel file
df = pd.read_excel(file_path, sheet_name=sheet_name)

# Step 3: Filter out the "green status" questions (Assume status column is 'G')
df_filtered = df[df['G'].str.lower() != 'green']

# Step 4: Initialize list to store selected questions and answers
selected_questions = []

# Step 5: Loop to randomly select 15 questions
while len(selected_questions) < 15:
    # Randomly pick a question row
    question_row = df_filtered.sample(n=1).iloc[0]
    
    question = question_row['A']  # Question text in Column A
    correct_answer = question_row['B']  # Correct answer in Column B
    answers = [correct_answer]  # Start with the correct answer
    
    # Get the incorrect answers (Columns C-F) and exclude the blanks
    incorrect_answers = [question_row[col] for col in ['C', 'D', 'E', 'F'] if question_row[col] != '/']
    
    # Add a few random incorrect answers
    answers.extend(random.sample(incorrect_answers, min(3, len(incorrect_answers))))
    
    # Shuffle the answers to mix up the correct answer position
    random.shuffle(answers)
    
    # Add the question and its answers to the selected list
    selected_questions.append({
        'question': question,
        'answers': answers,
        'correct_answer': correct_answer
    })

# Step 6: Create the Flask route to display the selected questions
@app.route('/')
def display_questions():
    questions_output = []
    for idx, item in enumerate(selected_questions, start=1):
        question_data = {
            'question_number': idx,
            'question': item['question'],
            'answers': item['answers'],
            'correct_answer': item['correct_answer']
        }
        questions_output.append(question_data)

    return jsonify(questions_output)

if __name__ == '__main__':
    app.run(debug=True)
