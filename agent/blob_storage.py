# agent/blob_storage.py
import json
import urllib.parse
from typing import Dict, List
from botbuilder.core import Storage
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError

class EntraIdBlobStorage(Storage):
    """Custom Async Bot Storage using Entra ID (DefaultAzureCredential)"""
    
    def __init__(self, account_url: str, container_name: str):
        self.account_url = account_url
        self.container_name = container_name
        self._container_client = None

    async def _get_client(self):
        # Lazy initialization ensures it runs safely inside the Python async event loop
        if not self._container_client:
            credential = DefaultAzureCredential()
            client = BlobServiceClient(account_url=self.account_url, credential=credential)
            self._container_client = client.get_container_client(self.container_name)
            
            try:
                # Auto-create the container if it doesn't exist
                if not await self._container_client.exists():
                    await self._container_client.create_container()
            except Exception as e:
                print(f"⚠️ Container check failed (Check 'Storage Blob Data Contributor' RBAC role): {e}")
                
        return self._container_client

    async def read(self, keys: List[str]) -> Dict[str, object]:
        store_items = {}
        container = await self._get_client()
        for key in keys:
            try:
                # Sanitize the Bot Framework key (removes special chars)
                safe_key = urllib.parse.quote(key, safe='')
                blob_client = container.get_blob_client(safe_key)
                
                stream = await blob_client.download_blob()
                data = await stream.readall()
                store_items[key] = json.loads(data)
            except ResourceNotFoundError:
                continue # Expected behavior for brand new users
            except Exception as e:
                print(f"❌ Error reading state {key}: {e}")
        return store_items

    async def write(self, changes: Dict[str, object]):
        container = await self._get_client()
        for key, item in changes.items():
            try:
                safe_key = urllib.parse.quote(key, safe='')
                blob_client = container.get_blob_client(safe_key)
                
                # Convert the object to a JSON string safely
                json_str = json.dumps(item, default=lambda o: o.__dict__ if hasattr(o, '__dict__') else str(o))
                await blob_client.upload_blob(json_str, overwrite=True)
            except Exception as e:
                print(f"❌ Error writing state {key}: {e}")

    async def delete(self, keys: List[str]):
        container = await self._get_client()
        for key in keys:
            try:
                safe_key = urllib.parse.quote(key, safe='')
                blob_client = container.get_blob_client(safe_key)
                await blob_client.delete_blob()
            except ResourceNotFoundError:
                pass
            except Exception as e:
                print(f"❌ Error deleting state {key}: {e}")