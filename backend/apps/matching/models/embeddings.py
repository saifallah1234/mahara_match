from typing import Any

from django.db import models
from pgvector.django import VectorField

from backend.common.models import UUIDTimestampedModel


class Embedding(UUIDTimestampedModel):
    entity_type: Any = models.CharField(max_length=50)
    entity_id: Any = models.UUIDField()
    model_name: Any = models.CharField(max_length=100)
    embedding: Any = VectorField()

    class Meta:
        db_table = "embeddings"
        constraints = [
            models.UniqueConstraint(
                fields=["entity_type", "entity_id", "model_name"],
                name="embeddings_entity_model_unique",
            ),
        ]
