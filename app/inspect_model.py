import joblib

model = joblib.load("churn_model.pkl")

print("===== MODEL STRUCTURE =====")
print(model)

print("\n===== EXPECTED FEATURES =====")

try:
    print(model.feature_names_in_)
except AttributeError:
    print("This model does not have feature_names_in_")
