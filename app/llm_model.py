import os
import requests
from langchain_groq import ChatGroq
os.environ["GROQ_API_KEY"] = "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"

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.3
)

response = llm.invoke(
    "hello"
)

print(response.content)
