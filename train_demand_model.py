import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import joblib

print("Generating historical course demand data...")
np.random.seed(42)

# Course catalog
courses = {
    0: "Advance Diploma in Software Engineering",
    1: "Intermediate Computer Science",
    2: "MERN Stack Web Development",
    3: "Flutter Mobile App Development"
}

data = []
# Simulate 5 years of enrollment data across 2 terms per year
for year in range(2021, 2027):
    for term in range(1, 3):  # 1 = Spring, 2 = Fall
        for c_id, c_name in courses.items():
            # Base demand + year-over-year growth + random seasonal noise
            base_enrollment = 100 + (c_id * 15)
            growth = (year - 2020) * 12
            noise = np.random.randint(-15, 25)
            total_enrollment = base_enrollment + growth + noise
            data.append([year, term, c_id, total_enrollment])

df = pd.DataFrame(data, columns=['year', 'term', 'course_id', 'enrollments'])
df.to_csv('course_demand_data.csv', index=False)

print("Training Course Demand Model...")
X = df[['year', 'term', 'course_id']]
y = df['enrollments']

demand_model = RandomForestRegressor(n_estimators=100, random_state=42)
demand_model.fit(X, y)

joblib.dump(demand_model, 'demand_model.pkl')
print("Success: Model trained and saved as demand_model.pkl!")