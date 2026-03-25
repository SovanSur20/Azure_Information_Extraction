from azure.identity import DefaultAzureCredential, ManagedIdentityCredential, ClientSecretCredential
from azure.core.credentials import TokenCredential
from typing import Optional
import logging

from src.config.settings import settings

logger = logging.getLogger(__name__)


class AzureAuthManager:
    _instance: Optional['AzureAuthManager'] = None
    _credential: Optional[TokenCredential] = None

    def __new__(cls) -> 'AzureAuthManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._credential is None:
            self._initialize_credential()

    def _initialize_credential(self) -> None:
        try:
            if settings.use_managed_identity:
                logger.info("Initializing Managed Identity credential")
                self._credential = ManagedIdentityCredential()
            else:
                logger.info("Initializing DefaultAzureCredential")
                self._credential = DefaultAzureCredential(
                    exclude_interactive_browser_credential=True,
                    exclude_shared_token_cache_credential=True,
                    exclude_visual_studio_code_credential=False,
                    exclude_cli_credential=False,
                    exclude_environment_credential=False,
                )
            
            token = self._credential.get_token("https://management.azure.com/.default")
            logger.info(f"Successfully authenticated with Azure AD. Token expires at: {token.expires_on}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure credential: {str(e)}")
            raise

    def get_credential(self) -> TokenCredential:
        if self._credential is None:
            self._initialize_credential()
        return self._credential

    def get_token(self, scope: str) -> str:
        credential = self.get_credential()
        token = credential.get_token(scope)
        return token.token

    def get_storage_token(self) -> str:
        return self.get_token("https://storage.azure.com/.default")

    def get_cognitive_services_token(self) -> str:
        return self.get_token("https://cognitiveservices.azure.com/.default")

    def get_search_token(self) -> str:
        return self.get_token("https://search.azure.com/.default")

    def get_sql_token(self) -> str:
        return self.get_token("https://database.windows.net/.default")


auth_manager = AzureAuthManager()
