import json
import httpx
import pytest
import asyncio
import os

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

async def classify_email(email_body: str):
    async with httpx.AsyncClient(timeout=30.0) as client:
        prompt = f"Classify this email for a B2B CRM. Is it a legitimate business lead or interest? Respond with ONLY a JSON object: {{\"is_worth_saving\": true/false}}\n\nEmail: {email_body}"
        
        response = await client.post(
            f"{OLLAMA_URL}/chat/completions",
            json={
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0
            }
        )
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        return json.loads(content)

@pytest.mark.asyncio
async def test_model_accuracy():
    with open("tests/golden_dataset.json", "r") as f:
        dataset = json.load(f)

    correct = 0
    total = len(dataset)

    # Run classifications in parallel
    tasks = [classify_email(item["email_body"]) for item in dataset]
    results = await asyncio.gather(*tasks)

    for i, result in enumerate(results):
        expected = dataset[i]["expected_is_worth_saving"]
        actual = result.get("is_worth_saving")
        
        if actual == expected:
            correct += 1
        else:
            print(f"FAILED: {dataset[i]['label']} | Expected: {expected}, Got: {actual}")

    accuracy = (correct / total) * 100
    print(f"\nModel Accuracy: {accuracy:.2f}% ({correct}/{total})")
    
    assert accuracy >= 90.0, f"Accuracy {accuracy:.2f}% is below the 90% threshold!"
