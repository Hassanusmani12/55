import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, IsolationForest
from sklearn.metrics import mean_squared_error, accuracy_score
import joblib

# Load Data
df = pd.read_csv('student_historical_data.csv') 
X_features = df[['attendance_pct', 'assignment_avg', 'participation_score']]

print("Training ML Models...")

# --- 1. PERFORMANCE PREDICTOR (Regressor) ---
y_grade = df['final_grade']
X_train, X_test, y_train, y_test = train_test_split(X_features, y_grade, test_size=0.2, random_state=42)
perf_model = RandomForestRegressor(n_estimators=100, random_state=42)
perf_model.fit(X_train, y_train)
joblib.dump(perf_model, 'performance_model.pkl')
print(f"[1/4] Performance Model trained. (MSE: {mean_squared_error(y_test, perf_model.predict(X_test)):.2f})")

# --- 2. DROPOUT PREDICTOR (Classifier) ---
y_dropout = df['dropout_flag']
X_train_d, X_test_d, y_train_d, y_test_d = train_test_split(X_features, y_dropout, test_size=0.2, random_state=42)
drop_model = RandomForestClassifier(n_estimators=100, random_state=42)
drop_model.fit(X_train_d, y_train_d)
joblib.dump(drop_model, 'dropout_model.pkl')
print(f"[2/4] Dropout Model trained. (Accuracy: {accuracy_score(y_test_d, drop_model.predict(X_test_d)) * 100:.2f}%)")

# --- 3. ANOMALY DETECTOR (Isolation Forest) ---
X_anomaly = df[['attendance_pct', 'assignment_avg', 'final_grade']]
anomaly_model = IsolationForest(contamination=0.05, random_state=42)
anomaly_model.fit(X_anomaly)
joblib.dump(anomaly_model, 'anomaly_model.pkl')
print("[3/4] Anomaly Detection Model trained.")

# --- 4. COURSE DEMAND PREDICTOR (New) ---
# Simulating historical course demand data
demand_data = pd.DataFrame({
    'course_difficulty': np.random.randint(1, 10, 200),
    'teacher_rating': np.random.uniform(3.0, 5.0, 200),
    'past_enrollments': np.random.randint(10, 100, 200)
})
# Target: Next semester's predicted enrollment
y_demand = (demand_data['past_enrollments'] * 1.1 + demand_data['teacher_rating'] * 5).astype(int)

demand_model = RandomForestRegressor(n_estimators=100, random_state=42)
demand_model.fit(demand_data, y_demand)
joblib.dump(demand_model, 'demand_model.pkl')
print("[4/4] Course Demand Model trained.")

print("\nAll models saved successfully! ML Suite is now 100% complete.")