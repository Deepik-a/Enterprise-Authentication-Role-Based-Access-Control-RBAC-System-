import re


class UppercaseAndSpecialCharacterValidator:
    def validate(self, password, user=None):
        errors = []
        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter.")
        if not re.search(r"[^A-Za-z0-9]", password):
            errors.append("Password must contain at least one special character.")
        if errors:
            from django.core.exceptions import ValidationError
            raise ValidationError(errors)

    def get_help_text(self):
        return "Your password must contain an uppercase letter and a special character."
