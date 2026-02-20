# In a new migration file
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('courses', '0016_merge_0014_refund_0015_add_achievement_code'),  # Use your actual last migration
    ]

    operations = [
        migrations.AddIndex(
            model_name='comment',
            index=models.Index(fields=['lesson', 'created_at'], name='comment_lesson_created_idx'),
        ),
        migrations.AddIndex(
            model_name='comment',
            index=models.Index(fields=['parent'], name='comment_parent_idx'),
        ),
    ]