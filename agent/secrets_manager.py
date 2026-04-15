import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from dotenv import load_dotenv

load_dotenv()

_secret_client = None

def get_secret(secret_name: str) -> str:
    """
    Fetches a secret from Azure Key Vault. 
    Falls back to local .env if Key Vault is not configured.
    """
    kv_url = os.getenv("KEY_VAULT_URL")
    
    # 1. If no Key Vault URL is provided, fall back to local .env
    if not kv_url:
        return os.getenv(secret_name)
    
    # 2. Initialize the Azure Key Vault Client (Singleton pattern for performance)
    global _secret_client
    if not _secret_client:
        try:
            credential = DefaultAzureCredential()
            _secret_client = SecretClient(vault_url=kv_url, credential=credential)
            print(f"🔐 Connected to Azure Key Vault: {kv_url}")
        except Exception as e:
            print(f"⚠️ Failed to connect to Key Vault: {e}")
            return os.getenv(secret_name)

    # 3. Fetch the secret from Key Vault
    try:
        # NOTE: Azure Key Vault does NOT allow underscores (_) in secret names.
        # We automatically convert names like 'SNOW_PASSWORD' to 'SNOW-PASSWORD'.
        kv_secret_name = secret_name.replace("_", "-")
        
        secret = _secret_client.get_secret(kv_secret_name)
        return secret.value
    except Exception as e:
        print(f"⚠️ Secret '{kv_secret_name}' not found in Key Vault. Falling back to .env.")
        return os.getenv(secret_name)