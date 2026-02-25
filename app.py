from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import pandas as pd
import os
import json
import logging
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# ==============================
# Logging Setup
# ==============================
logging.basicConfig(level=logging.INFO)

# ==============================
# Load Environment Variables
# ==============================
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ==============================
# Initialize FastAPI
# ==============================
app = FastAPI()

# ==============================
# Load ML Model
# ==============================
model = joblib.load("churn_model.pkl")

# ==============================
# Initialize Groq LLM
# ==============================
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.2,
    api_key=GROQ_API_KEY
)

# ==============================
# Request Schema
# ==============================
class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
def chat(request: ChatRequest):

    try:
        user_message = request.message

        if not user_message.strip():
            return {
                "status": "error",
                "message": "Empty message received"
            }

        # ==============================
        # LLM EXTRACTION
        # ==============================
        extraction_prompt = f"""
        Extract customer data from this text and return ONLY valid JSON.

        Required fields:
        gender, Senior_Citizen, Is_Married, Dependents, tenure,
        Phone_Service, Dual, Internet_Service, Online_Security,
        Online_Backup, Device_Protection, Tech_Support,
        Streaming_TV, Streaming_Movies, Contract,
        Paperless_Billing, Payment_Method,
        Monthly_Charges, Total_Charges.

        Text:
        {user_message}
        """

        llm_response = llm.invoke(extraction_prompt)
        generated_text = llm_response.content

        # ==============================
        # Safe JSON Extraction
        # ==============================
        try:
            start = generated_text.find("{")
            end = generated_text.rfind("}") + 1
            json_string = generated_text[start:end]
            customer_data = json.loads(json_string)
        except Exception as e:
            logging.error(f"JSON parsing failed: {e}")
            return {
                "status": "error",
                "message": "Failed to parse LLM response"
            }

        text_lower = user_message.lower()

        # ==============================
        # NORMALIZATION
        # ==============================
        if any(word in text_lower for word in ["female", "lady", "woman"]):
            customer_data["gender"] = "Female"
        else:
            customer_data["gender"] = "Male"

        if any(word in text_lower for word in ["two year", "24 month", "24 months"]):
            customer_data["Contract"] = "Two year"
        elif any(word in text_lower for word in ["one year", "yearly", "annual", "12 month", "12 months"]):
            customer_data["Contract"] = "One year"
        else:
            customer_data["Contract"] = "Month-to-month"

        if any(word in text_lower for word in ["fiber", "fibre", "optic fiber"]):
            customer_data["Internet_Service"] = "Fiber optic"
        elif "dsl" in text_lower:
            customer_data["Internet_Service"] = "DSL"
        else:
            customer_data["Internet_Service"] = "No"

        if any(word in text_lower for word in ["electronic", "e-check", "e check"]):
            customer_data["Payment_Method"] = "Electronic check"
        elif any(word in text_lower for word in ["credit card", "card"]):
            customer_data["Payment_Method"] = "Credit card (automatic)"
        elif any(word in text_lower for word in ["bank", "auto debit"]):
            customer_data["Payment_Method"] = "Bank transfer (automatic)"
        else:
            customer_data["Payment_Method"] = "Bank transfer (automatic)"

        yes_no_columns = [
            "Is_Married", "Dependents", "Phone_Service", "Dual",
            "Online_Security", "Online_Backup", "Device_Protection",
            "Tech_Support", "Streaming_TV", "Streaming_Movies",
            "Paperless_Billing"
        ]

        for col in yes_no_columns:
            value = str(customer_data.get(col, "")).lower()
            if value in ["yes", "true", "1"]:
                customer_data[col] = "Yes"
            else:
                customer_data[col] = "No"

        numeric_cols = ["Senior_Citizen", "tenure", "Monthly_Charges", "Total_Charges"]

        for col in numeric_cols:
            try:
                customer_data[col] = float(customer_data.get(col, 0))
            except:
                customer_data[col] = 0.0

        if customer_data["Total_Charges"] == 0 and customer_data["tenure"] > 0:
            customer_data["Total_Charges"] = (
                customer_data["tenure"] * customer_data["Monthly_Charges"]
            )

        expected_columns = model.feature_names_in_

        for col in expected_columns:
            if col not in customer_data:
                if col in numeric_cols:
                    customer_data[col] = 0.0
                else:
                    customer_data[col] = "No"

        df = pd.DataFrame([customer_data])
        df = df[expected_columns]
        df = df.fillna(0)

        # ==============================
        # PREDICTION
        # ==============================
        try:
            prediction = model.predict(df)[0]
            probability = model.predict_proba(df)[0][1]
        except Exception as e:
            logging.error(f"Prediction failed: {e}")
            return {
                "status": "error",
                "message": "Model prediction failed"
            }

        risk_level = "HIGH" if prediction == 1 else "LOW"

        # ==============================
        # EXPLANATION
        # ==============================
        explanation_prompt = f"""
        You are a business AI assistant for a telecom company.

        Customer profile:
        {customer_data}

        Churn probability: {probability:.2f}
        Risk level: {risk_level}

        Explain clearly and briefly why this is the case.
        """

        explanation_response = llm.invoke(explanation_prompt)
        explanation_text = explanation_response.content

        return {
            "status": "success",
            "structured_data": customer_data,
            "prediction": int(prediction),
            "churn_probability": float(probability),
            "risk_level": risk_level,
            "explanation": explanation_text
        }

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return {
            "status": "error",
            "message": "Unexpected server error"
        }