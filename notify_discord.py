import requests
import os
import time

def send_discord_message(content=None, file_path=None):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("Error: DISCORD_WEBHOOK_URL not found.")
        return False
    
    data = {}
    files = None
    
    if content:
        data["content"] = content
    
    if file_path:
        try:
            files = {"file": (os.path.basename(file_path), open(file_path, "rb"))}
        except Exception as e:
             print(f"Error opening file: {e}")
             return False

    try:
        response = requests.post(webhook_url, data=data, files=files)
        response.raise_for_status()
        print("Message/File sent successfully.")
    except Exception as e:
        print(f"Failed to send message: {e}")
        if 'response' in locals():
            print(f"Response: {response.text}")
        return False
    finally:
        if files:
            files["file"][1].close()
    return True

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
    
    # Discord limit is 2000 chars. 
    # We target 1950 to be safe but maximize length.
    messages_to_send = []
    current_buffer = ""
    MAX_LENGTH = 1950
    
    for chunk in raw_chunks:
        clean_chunk = chunk.strip()
        if not clean_chunk: continue
        
        # Re-add delimiter
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
             final_msg = final_msg[:2000]
        
        send_discord_message(content=final_msg)
        time.sleep(1)
        
    # Send the full file at the end for easy copying
    print("Sending full report file...")
    send_discord_message(content="📊 Full Report File", file_path=output_file)

if __name__ == "__main__":
    main()
