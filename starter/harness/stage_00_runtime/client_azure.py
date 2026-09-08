"""Azure OpenAI and Key Vault client construction."""

from __future__ import annotations

import os
from typing import Any

from .config import DEFAULT_API_VERSION

try:
    from azure.identity import DeviceCodeCredential
    from azure.keyvault.secrets import SecretClient
except ImportError:
    DeviceCodeCredential = None
    SecretClient = None

try:
    from openai import AzureOpenAI
except ImportError:
    AzureOpenAI = None


class KeyVaultSecretService:
    def __init__(self, vault_url: str):
        if SecretClient is None or DeviceCodeCredential is None:
            raise RuntimeError(
                "Azure Key Vault dependencies are not installed. Install "
                "'azure-identity' and 'azure-keyvault-secrets', or set "
                "AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and "
                "AZURE_OPENAI_DEPLOYMENT to skip Key Vault."
            )
        self.client = SecretClient(
            vault_url=vault_url,
            credential=DeviceCodeCredential(),
        )

    def get_secret(self, name: str) -> str:
        return self.client.get_secret(name).value


def create_azure_client(
    vault_url: str | None,
    model: str | None = None,
) -> tuple[Any, str]:
    """Create one Azure OpenAI client, authenticating through device code if needed."""
    if AzureOpenAI is None:
        raise RuntimeError("The 'openai' package is not installed. Install it with 'pip install openai'.")
    if not vault_url:
        raise ValueError("Azure Key Vault URL is required. Set AZURE_KEY_VAULT_URL or pass --vault-url.")

    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", os.environ.get("FOUNDRY_ENDPOINT"))
    api_key = os.environ.get("AZURE_OPENAI_API_KEY", os.environ.get("FOUNDRY_KEY"))
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", os.environ.get("FOUNDRY_DEPLOYMENT"))
    api_version = os.environ.get(
        "AZURE_OPENAI_API_VERSION",
        os.environ.get("FOUNDRY_API_VERSION", DEFAULT_API_VERSION),
    )

    if not all([endpoint, api_key, deployment]):
        secrets = KeyVaultSecretService(vault_url)
        endpoint = secrets.get_secret("foundry-endpoint")
        api_key = secrets.get_secret("foundry-key")
        deployment = secrets.get_secret("foundry-deployment")

    return (
        AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        ),
        model or deployment,
    )
