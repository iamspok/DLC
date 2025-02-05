import pandas as pd
import random

# Step 1: Load the Excel file
file_path = r'C:\Users\mwatt2\Downloads\DLC Question Bank.xlsx'  # Update this path if necessary
sheet_name = 'Question Bank (EN)'  # Change this if the sheet name is different

# Load the data from the Excel file
df = pd.read_excel(file_path, sheet_name=sheet_name)

# Step 2: Filter out the "green status" questions
# Assume the status column (Column G) has the word "green" for questions that are excluded.
df_filtered = df[df['G'].str.lower() != 'green']

# Step 3: Initialize list to store selected questions and answers
selected_questions = []

# Step 4: Loop to randomly select 15 questions
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

# Step 5: Display the selected questions and answers
# For now, we can print them to check
for idx, item in enumerate(selected_questions, start=1):
    print(f"Question {idx}: {item['question']}")
    for ans_idx, answer in enumerate(item['answers'], start=1):
        print(f"  {ans_idx}. {answer}")
    print()  # Empty line for spacing
