import requests
import os
import sys
import json

def send_line_push(message, access_token, user_id):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    payload = {
        "to": user_id,
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }
    
    try:
        r = requests.post(url, headers=headers, data=json.dumps(payload))
        r.raise_for_status()
        print("Message sent successfully.")
    except Exception as e:
        print(f"Failed to send message: {e}")
        if 'r' in locals():
            print(f"Response: {r.text}")

def main():
    access_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")
    
    if not access_token:
        print("Error: LINE_CHANNEL_ACCESS_TOKEN not found.")
        return
    if not user_id:
        print("Error: LINE_USER_ID not found.")
        return

    output_file = "analysis_output.txt"
    if not os.path.exists(output_file):
        print(f"Error: {output_file} not found.")
        return

    with open(output_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Messaging API limit is 2000 characters per text message, up to 5 messages per request.
    # We will be safe and use 1500 chars per chunk.
    chunk_size = 1500
    
    # Prepend a header
    header = "\n【天才投資家レポート】\n"
    full_text = header + content
    
    chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]
    
    for i, chunk in enumerate(chunks):
        print(f"Sending chunk {i+1}/{len(chunks)}...")
        send_line_push(chunk, access_token, user_id)

if __name__ == "__main__":
    main()
