import uuid

from django.db import migrations, models
from pgvector.django import VectorExtension, VectorField


class Migration(migrations.Migration):
    dependencies = [("matching", "0001_initial")]

    operations = [
        VectorExtension(),
        migrations.CreateModel(
            name="Embedding",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("entity_type", models.CharField(max_length=50)),
                ("entity_id", models.UUIDField()),
                ("model_name", models.CharField(max_length=100)),
                ("embedding", VectorField()),
            ],
            options={
                "db_table": "embeddings",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("entity_type", "entity_id", "model_name"),
                        name="embeddings_entity_model_unique",
                    ),
                ],
            },
        ),
    ]
