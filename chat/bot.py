from brick import BrickClient

# 1. Configuration
API_KEY = "YOUR_API_KEY_HERE" # Ensure this matches your DB
SYSTEM_PROMPT = "You are a helpful assistant. Keep answers short."

# 2. Initialize the Client
client = BrickClient(
    api_key=API_KEY, 
    system_prompt=SYSTEM_PROMPT, 
    model="smollm2"
)

# 3. List Available Models
print("Available Models:", client.list_models())
print("------------------------------------------------")
print("Bot initialized. Type 'exit' to quit.")
print("------------------------------------------------")

while True:
    # Get user input
    try:
        query = input("\nYou: ").strip()
    except KeyboardInterrupt:
        break

    # Check for exit commands
    if query.lower() in ["bye", "exit", "quit"]:
        print("Bot: Goodbye! 👋")
        break
    
    if not query:
        continue

    # Get response
    res = client.ask(query)
    
    # Print response (Added \n at the end for clean formatting)
    print(f"Bot: {res}")