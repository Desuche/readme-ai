"""
OpenAI API LLM handler implementation, with Ollama support.
"""

import os
from typing import List, Tuple

import aiohttp
import openai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from readmeai.cli.options import ModelOptions as llms
from readmeai.config.settings import ConfigLoader
from readmeai.core.models import BaseModelHandler
from readmeai.models.tokens import token_handler
from readmeai.utils.text_cleaner import clean_response



class AzureOpenAIHandler(BaseModelHandler):
    """Azure OpenAI API LLM implementation."""

    def __init__(self, config_loader: ConfigLoader) -> None:
        """Initialize Azure OpenAI API LLM handler."""
        super().__init__(config_loader)
        self._model_settings()

    def _model_settings(self):
        """Set default values for Azure OpenAI API."""
        self.model = self.config.llm.model
        self.temperature = self.config.llm.temperature
        self.tokens = self.config.llm.tokens
        self.top_p = self.config.llm.top_p

        
        self.endpoint = self.config.llm.base_url
        self.client = openai.OpenAI(
            api_key=os.environ.get("AZURE_API_KEY")
        )
        self.headers = {"api-key": self.client.api_key}

    async def _build_payload(self, prompt: str, tokens: int) -> dict:
        """Build payload for POST request to Azure OpenAI API."""
        return {
            "messages": [
                {
                    "role": "system",
                    "content": self.sys_content,
                },
                {"role": "user", "content": prompt},
            ],
            "model": self.model,
            "max_tokens": tokens,
            "temperature": self.temperature,
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(
            (
                aiohttp.ClientError,
                aiohttp.ClientResponseError,
                aiohttp.ClientConnectorError,
                openai.OpenAIError,
            )
        ),
    )
    async def _make_request(
        self,
        index: str,
        prompt: str,
        tokens: int,
        raw_files: List[Tuple[str, str]] = None,
    ) -> Tuple[str, str]:
        """Processes Azure OpenAI API LLM responses and returns generated text."""
        try:
            prompt = await token_handler(self.config, index, prompt, tokens)
            parameters = await self._build_payload(prompt, tokens)

            async with self._session.post(
                self.endpoint,
                headers=self.headers,
                json=parameters,
            ) as response:
                response.raise_for_status()
                response = await response.json()
                text = response["choices"][0]["message"]["content"]
                self._logger.info(f"Response for '{index}':\n{text}")
                return index, clean_response(index, text)

        except (
            aiohttp.ClientError,
            aiohttp.ClientResponseError,
            aiohttp.ClientConnectorError,
            openai.OpenAIError,
        ) as exc:
            message = f"Error making request for - `{index}`: {exc}"
            self._logger.error(message)
            return index, self.config.md.placeholder
