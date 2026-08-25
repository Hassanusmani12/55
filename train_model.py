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

# --- 4. COURSE DEMAND PREDICTOR ---
courses = {0: "Advance Diploma in Software Engineering", 1: "Intermediate Computer Science", 2: "MERN Stack Web Development", 3: "Flutter Mobile App Development"}
demand_list = []
for year in range(2021, 2027):
    for term in range(1, 3):
        for c_id in courses.keys():
            base = 100 + (c_id * 15)
            growth = (year - 2020) * 12
            noise = np.random.randint(-15, 25)
            demand_list.append([year, term, c_id, base + growth + noise])
df_demand = pd.DataFrame(demand_list, columns=['year', 'term', 'course_id', 'enrollments'])
X_dem = df_demand[['year', 'term', 'course_id']]
y_dem = df_demand['enrollments']
demand_model = RandomForestRegressor(n_estimators=100, random_state=42)
demand_model.fit(X_dem, y_dem)
joblib.dump(demand_model, 'demand_model.pkl')
print("[4/4] Course Demand Model trained.")

print("\nAll models saved successfully! ML Suite is now 100% complete.")