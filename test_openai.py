import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

# Load your existing .env file
load_dotenv()

async def test_token_usage():
    print("🚀 Initializing Azure OpenAI Client...")
    client = AsyncAzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION")
    )
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    # 1. Simulate a standard chat history
    messages =[
        {"role": "system", "content": "You are an intelligent IT Service Desk Assistant. You help users troubleshoot issues and create ServiceNow tickets."},
        {"role": "user", "content": "My React application is crashing with a 404 error. Can you help?"}
    ]

    # 2. Simulate providing tools to the AI (Tools consume tokens too!)
    dummy_tools =[{
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Creates a new incident in ServiceNow.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "priority": {"type": "string"}
                },
                "required": ["description"]
            }
        }
    }]

    print("🤖 Thinking...\n")
    
    # 3. Call the API
    response = await client.chat.completions.create(
        model=deployment,
        messages=messages,
        tools=dummy_tools,
        tool_choice="auto"
    )

    reply_text = response.choices[0].message.content
    usage = response.usage # 🚀 THIS IS THE MAGIC OBJECT!

    # 4. Print the exact token consumption
    print("========================================")
    print("💬 AI REPLY:")
    print(reply_text if reply_text else "[AI decided to call a tool]")
    print("========================================")
    print("📊 TOKEN USAGE REPORT:")
    print(f"   Input (Prompt) Tokens:      {usage.prompt_tokens}")
    print(f"   Output (Completion) Tokens: {usage.completion_tokens}")
    print(f"   Total Tokens Billed:        {usage.total_tokens}")
    print("========================================")

if __name__ == "__main__":
    asyncio.run(test_token_usage())