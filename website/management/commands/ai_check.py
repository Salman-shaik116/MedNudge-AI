import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verify AI provider configuration and (optionally) attempt a minimal model call."

    def add_arguments(self, parser):
        parser.add_argument(
            "--invoke",
            action="store_true",
            help="Actually invoke the model with a tiny prompt (requires valid API key).",
        )
        parser.add_argument(
            "--list-models",
            action="store_true",
            help="List available model IDs from the provider (requires valid API key).",
        )

    def handle(self, *args, **options):
        from mediscanner.llm import pick_provider, create_chat_model

        provider = pick_provider()
        self.stdout.write(self.style.SUCCESS(f"provider: {provider}"))

        if provider == "groq":
            self.stdout.write(f"GROQ_MODEL: {os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')}")
            self.stdout.write(f"GROQ_API_KEY set: {bool(os.getenv('GROQ_API_KEY'))}")
        else:
            self.stdout.write(f"XAI_BASE_URL: {os.getenv('XAI_BASE_URL', 'https://api.x.ai/v1')}")
            self.stdout.write(f"XAI_MODEL: {os.getenv('XAI_MODEL', 'grok-beta')}")
            self.stdout.write(
                f"XAI_API_KEY/GROK_API_KEY set: {bool(os.getenv('XAI_API_KEY') or os.getenv('GROK_API_KEY'))}"
            )

        model = create_chat_model(temperature=0.0)
        self.stdout.write(self.style.SUCCESS(f"model_class: {type(model)}"))

        if options["list_models"]:
            if provider == "xai":
                base_url = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")
                api_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
                if not api_key:
                    raise SystemExit("Missing XAI_API_KEY/GROK_API_KEY; cannot list models.")

                try:
                    from openai import OpenAI
                except ImportError as exc:
                    raise SystemExit("Missing dependency: openai. Install requirements.txt") from exc

                client = OpenAI(api_key=api_key, base_url=base_url)
                models = client.models.list()
                ids = [m.id for m in getattr(models, "data", [])]
                self.stdout.write(self.style.SUCCESS(f"models_count: {len(ids)}"))
                for mid in ids[:25]:
                    self.stdout.write(f"- {mid}")
            else:
                self.stdout.write("Model listing is not implemented for Groq in this command.")

            # continue; listing doesn't require invocation

        if not options["invoke"]:
            self.stdout.write("Skipped invocation (pass --invoke to test a real response).")
            return

        try:
            result = model.invoke("Reply with exactly: OK")
            content = (getattr(result, "content", None) or "").strip()
        except Exception as exc:
            raise SystemExit(f"Invocation failed: {type(exc).__name__}: {exc}")

        self.stdout.write(self.style.SUCCESS(f"invoke_result: {content}"))
