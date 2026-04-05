from django.db import models

class BRDExtraction(models.Model):
    transcript = models.TextField()
    extracted_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Extraction {self.id}"


class MOMExtraction(models.Model):
    transcript = models.TextField()
    extracted_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"MOM Extraction {self.id}"