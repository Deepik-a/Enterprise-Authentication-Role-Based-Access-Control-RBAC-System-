

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='auditlog',
            options={'ordering': ['-timestamp', '-id']},
        ),
        migrations.AddField(
            model_name='auditlog',
            name='object_repr',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AlterField(
            model_name='auditlog',
            name='action',
            field=models.CharField(choices=[('CREATE', 'Create'), ('UPDATE', 'Update'), ('DELETE', 'Delete'), ('ASSIGN_ROLES', 'Assign roles'), ('ASSIGN_PERMISSIONS', 'Assign permissions'), ('ACTIVATE', 'Activate'), ('DEACTIVATE', 'Deactivate'), ('PASSWORD_CHANGE', 'Password change'), ('PASSWORD_RESET', 'Password reset')], max_length=32),
        ),
    ]
