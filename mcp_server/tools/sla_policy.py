import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_search_client():
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    key = os.getenv("AZURE_SEARCH_KEY")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")

    if not all([endpoint, key, index_name]):
        raise ValueError("❌ Missing Azure Search Config in .env")

    credential = AzureKeyCredential(key)
    return SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)

def lookup_sla(description: str) -> str:
    """
    Queries Azure AI Search to find the SLA Policy based on the issue description.
    """
    try:
        client = get_search_client()
        print(f"🔎 [Azure Search] Searching index for: '{description}'...")

        # Query the 'content' field (where your PDF text lives)
        results = client.search(
            search_text=description,
            select=["content", "metadata_storage_name"], # Fields from your screenshot
            top=1
        )

        response_text = ""
        for result in results:
            source = result.get("metadata_storage_name", "Unknown File")
            # Grab first 1500 chars to avoid token limits
            content = result.get("content", "")[:1500] 
            response_text += f"--- POLICY SOURCE: {source} ---\n{content}\n"

        if not response_text:
            return "No specific policy found. Defaulting to Standard Support (P3)."
            
        return response_text

    except Exception as e:
        return f"Error querying Azure Search: {str(e)}"