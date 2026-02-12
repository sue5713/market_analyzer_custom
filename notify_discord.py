import requests
import os
import time

def send_discord_message(content):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("Error: DISCORD_WEBHOOK_URL not found.")
        return False
    
    data = {"content": content}
    try:
        response = requests.post(webhook_url, json=data)
        response.raise_for_status()
        print("Message sent successfully.")
        return True
    except Exception as e:
        print(f"Failed to send message: {e}")
        if 'response' in locals():
            print(f"Response: {response.text}")
        return False

def main():
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("Error: DISCORD_WEBHOOK_URL env var is missing.")
        return

    output_file = "analysis_output.txt"
    if not os.path.exists(output_file):
        print(f"Error: {output_file} not found.")
        return

    with open(output_file, "r", encoding="utf-8") as f:
        content = f.read()

    delimiter = "--------------------"
    raw_chunks = content.split(delimiter)
    
    # Discord limit is 2000 chars. We target 1900 to be safe.
    messages_to_send = []
    current_buffer = ""
    MAX_LENGTH = 1900
    
    for chunk in raw_chunks:
        clean_chunk = chunk.strip()
        if not clean_chunk: continue
        
        # Re-add delimiter for visual separation
        formatted_chunk = clean_chunk + "\n\n" + "-"*20 + "\n\n"
        
        if len(current_buffer) + len(formatted_chunk) > MAX_LENGTH:
            messages_to_send.append(current_buffer.strip())
            current_buffer = formatted_chunk
        else:
            current_buffer += formatted_chunk
            
    if current_buffer:
        messages_to_send.append(current_buffer.strip())

    print(f"Total messages to send: {len(messages_to_send)}")
    
    for i, msg in enumerate(messages_to_send):
        print(f"Sending message {i+1}/{len(messages_to_send)}...")
        
        header = f"**({i+1}/{len(messages_to_send)})**\n"
        final_msg = header + msg
        
        if len(final_msg) > 2000:
             print("Warning: Message > 2000 chars! Truncating.")
             final_msg = final_msg[:2000]
        
        success = send_discord_message(final_msg)
        if not success:
            print("Stopping due to error.")
            break
        
        time.sleep(1)

if __name__ == "__main__":
    main()
