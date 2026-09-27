from django import forms

MIN_OPTIONS = 2
MAX_OPTIONS = 5
OPTION_MAX_LENGTH = 80


class PollForm(forms.Form):
    question = forms.CharField(
        label="Sorun",
        max_length=200,
        widget=forms.TextInput(
            attrs={"class": "form-control", "maxlength": 200, "aria-describedby": "id_question_help"}
        ),
        error_messages={
            "required": "Bir soru yazmalısın.",
            "max_length": "Soru en fazla 200 karakter olabilir.",
        },
    )
    description = forms.CharField(
        label="Açıklama (isteğe bağlı)",
        required=False,
        max_length=500,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "maxlength": 500,
                "aria-describedby": "id_description_help",
            }
        ),
        error_messages={"max_length": "Açıklama en fazla 500 karakter olabilir."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.options = []

    @property
    def option_values(self):
        """Option texts to re-render in the form (at least the minimum number of inputs)."""
        if self.is_bound:
            values = list(self.data.getlist("option"))[:MAX_OPTIONS]
        else:
            values = []
        values += [""] * (MIN_OPTIONS - len(values))
        return values

    def clean_question(self):
        question = self.cleaned_data["question"].strip()
        if len(question) < 5:
            raise forms.ValidationError("Soru en az 5 karakter olmalı.")
        return question

    def clean(self):
        cleaned = super().clean()

        raw = self.data.getlist("option")
        options = [text.strip() for text in raw if text.strip()]

        if any(len(text) > OPTION_MAX_LENGTH for text in options):
            self.add_error(None, f"Her seçenek en fazla {OPTION_MAX_LENGTH} karakter olabilir.")
        elif len(options) < MIN_OPTIONS:
            self.add_error(None, f"En az {MIN_OPTIONS} seçenek girmelisin.")
        elif len(options) > MAX_OPTIONS:
            self.add_error(None, f"En fazla {MAX_OPTIONS} seçenek girebilirsin.")
        elif len({text.casefold() for text in options}) != len(options):
            self.add_error(None, "Aynı seçeneği birden fazla kez yazamazsın.")

        self.options = options
        return cleaned
