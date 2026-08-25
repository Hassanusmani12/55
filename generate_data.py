import pandas as pd
import numpy as np

print("Generating advanced educational data...")
np.random.seed(42)
num_students = 1000

# Base metrics
attendance = np.random.uniform(40, 100, num_students)
assignments = np.random.uniform(30, 100, num_students)
participation = np.random.uniform(20, 100, num_students)

# 1. Final Grade Calculation
final_grade = (attendance * 0.4) + (assignments * 0.4) + (participation * 0.2) + np.random.normal(-3, 3, num_students)
final_grade = np.clip(final_grade, 0, 100)

# 2. Dropout Flag (1 = Dropped out, 0 = Stayed)
# Students with low attendance and low grades are highly likely to drop out
dropout_prob = 1 - ((attendance * 0.5 + final_grade * 0.5) / 100)
dropout_flag = (np.random.rand(num_students) < dropout_prob).astype(int)

# 3. Inject Anomalies (e.g., 95% attendance but 20% final grade, or vice versa)
anomaly_indices = np.random.choice(num_students, size=50, replace=False)
for idx in anomaly_indices:
    if np.random.rand() > 0.5:
        attendance[idx] = 95.0
        final_grade[idx] = 25.0 # High attendance, terrible grade (Anomaly)
    else:
        attendance[idx] = 30.0
        final_grade[idx] = 85.0 # Terrible attendance, great grade (Anomaly)

df = pd.DataFrame({
    'student_id': range(1, num_students + 1),
    'attendance_pct': np.round(attendance, 1),
    'assignment_avg': np.round(assignments, 1),
    'participation_score': np.round(participation, 1),
    'final_grade': np.round(final_grade, 1),
    'dropout_flag': dropout_flag
})

df.to_csv('student_historical_data.csv', index=False)
print("Success: Advanced dataset created with dropouts and anomalies!")