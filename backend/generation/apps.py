from django.apps import AppConfig


class GenerationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'generation'
    def ready(self):
        import generation.signals  