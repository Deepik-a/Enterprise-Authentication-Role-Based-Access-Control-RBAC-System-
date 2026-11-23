

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('roles', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='permission',
            unique_together={('module', 'action')},
        ),
    ]
