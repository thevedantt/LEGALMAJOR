import requests

URL = "http://127.0.0.1:1234/v1/chat/completions"

def test_model():
    payload = {
        "model": "mistral-7b-instruct-v0.2",
        "messages": [
            {
                "role": "user",
                "content": "Instruction: You are a legal analyzer. When user says hello, respond with: Legal Analyzer is live.\n\nUser: hello"
            }
        ],
        "temperature": 0.1,
        "max_tokens": 50
    }

    response = requests.post(URL, json=payload)

    if response.status_code == 200:
        result = response.json()
        print("[SUCCESS] Response:")
        print(result["choices"][0]["message"]["content"])
    else:
        print("[ERROR] Error:", response.text)


if __name__ == "__main__":
    test_model()