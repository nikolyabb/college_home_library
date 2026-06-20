from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime

from .models import Book, Borrowing


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com"}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ("email",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Имя пользователя"
        self.fields["password1"].label = "Пароль"
        self.fields["password2"].label = "Подтверждение пароля"

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise ValidationError("Пользователь с таким email уже существует.")
        return email


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ["title", "author", "isbn", "description"]
        labels = {
            "title": "Название",
            "author": "Автор",
            "isbn": "ISBN",
            "description": "Описание",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class BorrowingForm(forms.ModelForm):
    due_date = forms.DateField(
        label="Срок возврата",
        input_formats=["%Y-%m"],
        widget=forms.DateInput(
            attrs={"type": "month", "placeholder": "2026-08"},
        ),
        required=True,
    )

    class Meta:
        model = Borrowing
        fields = ["due_date"]

    def clean_due_date(self):
        due_date = self.cleaned_data.get("due_date")
        if due_date:
            due_date = due_date.replace(day=1)

        today = timezone.now().date()
        today_first = today.replace(day=1)
        max_date = today + timezone.timedelta(days=365)
        if due_date < today_first:
            raise ValidationError("Срок возврата не может быть в прошлом.")
        if due_date > max_date:
            raise ValidationError(
                f"Срок возврата не может превышать {max_date.strftime('%d.%m.%Y')} (365 дней)."
            )
        return due_date
