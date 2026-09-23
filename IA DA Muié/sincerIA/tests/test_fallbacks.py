import asyncio
import unittest
from unittest.mock import patch

from backend.core.config import settings
from backend.orchestration.fallback import execute_fallback_chain
from backend.orchestration.router import orchestrator
from backend.orchestration.types import RouteType
from backend.providers.base import ImageInput, ProviderError, ProviderResponse
from backend.providers.gemini import GeminiProvider
from backend.providers.groq import GroqProvider
from backend.providers.nvidia import NvidiaProvider
from backend.providers.openrouter import OpenRouterProvider
from backend.providers.venice import VeniceProvider


class GeminiFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_keys_do_not_crash_backend_import(self):
        with patch.object(settings, "GROQ_API_KEY", ""), \
             patch.object(settings, "OPENROUTER_API_KEY", ""), \
             patch.object(settings, "NVIDIA_API_KEY", ""), \
             patch.object(settings, "VENICE_API_KEY", ""), \
             patch.object(settings, "GEMINI_API_KEY", ""):
            for provider in (GroqProvider(), OpenRouterProvider(), NvidiaProvider(), VeniceProvider(), GeminiProvider()):
                self.assertFalse(provider.configured)
                self.assertIsNone(provider.client)

    async def test_vision_has_second_provider_without_affecting_text(self):
        self.assertEqual(orchestrator.get_chain(RouteType.VISION), ["gemini", "groq_vision"])
        self.assertIn("groq_qwen", orchestrator.get_chain(RouteType.CONVERSATION))
        self.assertIn("gemini", orchestrator.get_chain(RouteType.CONVERSATION))

    async def test_groq_photo_is_attached_to_last_user_message(self):
        provider = object.__new__(GroqProvider)
        provider.api_key = "test"
        provider.model = settings.QWEN_MODEL
        class Client:
            class Chat:
                class Completions:
                    async def create(self, **kwargs):
                        self.request = kwargs
                        return type("Response", (), {"choices": [type("Choice", (), {"message": type("Message", (), {"content": "Vi."})()})()]})()
                completions = Completions()
            chat = Chat()
        provider.client = Client()
        result = await provider.chat([
            {"role": "user", "content": "Antes"},
            {"role": "assistant", "content": "Certo"},
            {"role": "user", "content": "Agora"},
        ], images=[ImageInput(b"photo", "image/png", "foto.png")])
        self.assertEqual(result.content, "Vi.")
        sent = provider.client.chat.completions.request["messages"]
        self.assertEqual(sent[0]["content"], "Antes")
        self.assertEqual(sent[2]["content"][0]["text"], "Agora")
        self.assertTrue(sent[2]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,"))

    async def test_second_gemini_model_runs_after_timeout(self):
        provider = object.__new__(GeminiProvider)
        provider.api_key = "test"
        provider.primary_model = "primary"
        provider.fallback_model = "secondary"
        provider.models = ["primary", "secondary"]
        provider.model_timeouts = {"primary": 1, "secondary": 1}
        provider.logger = __import__("logging").getLogger("test")
        provider._convert_messages = lambda messages, images: ("", [object()])

        async def fake_call(model, **_):
            if model == "primary":
                raise asyncio.TimeoutError()
            return ProviderResponse("vi a imagem", "gemini", model)

        provider._call_model = fake_call
        result = await provider.chat([{"role": "user", "content": "analise"}])
        self.assertEqual(result.model, "secondary")

    async def test_orchestrator_tries_next_provider(self):
        class Broken:
            configured, supports_vision, model = True, False, "broken"
            def timeout_budget(self): return 0
            async def chat(self, **_): raise ProviderError("HTTP 503")
        class Working:
            configured, supports_vision, model = True, False, "working"
            def timeout_budget(self): return 0
            async def chat(self, **_): return ProviderResponse("ok", "working", self.model)
        with patch("backend.orchestration.fallback.PROVIDERS", {"broken-test": Broken(), "working-test": Working()}):
            result = await execute_fallback_chain(["broken-test", "working-test"], RouteType.CONVERSATION, [{"role": "user", "content": "oi"}])
        self.assertEqual(result.provider, "working")
        self.assertEqual(len(result.attempts), 2)


if __name__ == "__main__":
    unittest.main()
