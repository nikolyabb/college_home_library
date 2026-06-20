from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from library.forms import CustomUserCreationForm, BorrowingForm
from library.models import Book, Borrowing


class AuthTests(TestCase):
    def test_register_new_user(self):
        response = self.client.post(reverse("register"), {
            "username": "alice",
            "email": "alice@example.com",
            "password1": "complexpass123",
            "password2": "complexpass123",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="alice").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_register_duplicate_username(self):
        User.objects.create_user(username="alice", email="alice@example.com", password="pass")
        response = self.client.post(reverse("register"), {
            "username": "alice",
            "email": "alice2@example.com",
            "password1": "complexpass123",
            "password2": "complexpass123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "уже существует")

    def test_register_duplicate_email(self):
        User.objects.create_user(username="bob", email="bob@example.com", password="pass")
        response = self.client.post(reverse("register"), {
            "username": "alice",
            "email": "bob@example.com",
            "password1": "complexpass123",
            "password2": "complexpass123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Пользователь с таким email уже существует")

    def test_login_and_logout(self):
        user = User.objects.create_user(username="alice", email="alice@example.com", password="pass12345")
        response = self.client.post(reverse("login"), {
            "username": user.username,
            "password": "pass12345",
        })
        self.assertEqual(response.status_code, 302)
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, 302)


class BookModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass12345")
        self.book = Book.objects.create(
            title="Тестовая книга",
            author="Автор Тестов",
            owner=self.user,
        )

    def test_book_creation(self):
        self.assertEqual(self.book.title, "Тестовая книга")
        self.assertEqual(self.book.owner, self.user)
        self.assertTrue(self.book.is_available())

    def test_book_availability_after_borrowing(self):
        borrower = User.objects.create_user(username="borrower", password="pass12345")
        Borrowing.objects.create(book=self.book, borrower=borrower)
        self.assertFalse(self.book.is_available())
        self.assertEqual(self.book.current_borrower(), borrower)


class BorrowingTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pass12345")
        self.borrower = User.objects.create_user(username="borrower", password="pass12345")
        self.book = Book.objects.create(title="Книга", owner=self.owner)

    def test_borrowing_creates_history(self):
        Borrowing.objects.create(book=self.book, borrower=self.borrower)
        self.assertEqual(Borrowing.objects.filter(book=self.book).count(), 1)

    def test_return_book_makes_available(self):
        borrowing = Borrowing.objects.create(book=self.book, borrower=self.borrower)
        borrowing.returned_at = timezone.now()
        borrowing.save()
        self.assertTrue(self.book.is_available())


class FormTests(TestCase):
    def test_due_date_within_365_days(self):
        month_value = (timezone.now().date() + timedelta(days=30)).strftime("%Y-%m")
        form = BorrowingForm(data={
            "due_date": month_value,
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["due_date"].day, 1)

    def test_due_date_over_365_days(self):
        month_value = (timezone.now().date() + timedelta(days=380)).strftime("%Y-%m")
        form = BorrowingForm(data={
            "due_date": month_value,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("due_date", form.errors)


class ViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pass12345")
        self.other = User.objects.create_user(username="other", password="pass12345")
        self.book = Book.objects.create(title="Книга владельца", owner=self.owner)

    def test_add_book_requires_login(self):
        response = self.client.get(reverse("book_add"))
        self.assertEqual(response.status_code, 302)

    def test_owner_can_edit_book(self):
        self.client.login(username="owner", password="pass12345")
        response = self.client.post(reverse("book_edit", kwargs={"pk": self.book.pk}), {
            "title": "Новое название",
            "author": "Новый автор",
        })
        self.assertEqual(response.status_code, 302)
        self.book.refresh_from_db()
        self.assertEqual(self.book.title, "Новое название")

    def test_other_cannot_edit_book(self):
        self.client.login(username="other", password="pass12345")
        response = self.client.post(reverse("book_edit", kwargs={"pk": self.book.pk}), {
            "title": "Взломанное название",
            "author": "Взлом",
        })
        self.assertEqual(response.status_code, 403)

    def test_borrow_and_return_flow(self):
        self.client.login(username="other", password="pass12345")
        due = (timezone.now().date() + timedelta(days=14)).strftime("%Y-%m")
        response = self.client.post(reverse("book_borrow", kwargs={"pk": self.book.pk}), {
            "due_date": due,
        })
        self.assertEqual(response.status_code, 302)
        self.book.refresh_from_db()
        self.assertFalse(self.book.is_available())

        response = self.client.post(reverse("book_return", kwargs={"pk": self.book.pk}))
        self.assertEqual(response.status_code, 302)
        self.book.refresh_from_db()
        self.assertTrue(self.book.is_available())

    def test_cannot_borrow_already_borrowed(self):
        Borrowing.objects.create(book=self.book, borrower=self.other)
        third = User.objects.create_user(username="third", password="pass12345")
        self.client.login(username="third", password="pass12345")
        response = self.client.post(reverse("book_borrow", kwargs={"pk": self.book.pk}), {
            "due_date": (timezone.now().date() + timedelta(days=14)).strftime("%Y-%m"),
        })
        self.assertEqual(response.status_code, 302)
        self.book.refresh_from_db()
        self.assertFalse(self.book.is_available())

    def test_borrow_race_returns_redirect_not_500(self):
        from django.db import IntegrityError
        from unittest.mock import patch

        self.client.login(username="other", password="pass12345")
        due = (timezone.now().date() + timedelta(days=14)).strftime("%Y-%m")
        with patch("library.views.Borrowing.save", side_effect=IntegrityError):
            response = self.client.post(
                reverse("book_borrow", kwargs={"pk": self.book.pk}),
                {"due_date": due},
            )
        self.assertEqual(response.status_code, 302)

    def test_can_borrow_other_book_while_one_is_borrowed(self):
        Borrowing.objects.create(book=self.book, borrower=self.other)
        other_book = Book.objects.create(title="Другая книга", owner=self.owner)
        self.client.login(username="other", password="pass12345")
        due = (timezone.now().date() + timedelta(days=14)).strftime("%Y-%m")
        response = self.client.post(
            reverse("book_borrow", kwargs={"pk": other_book.pk}),
            {"due_date": due},
        )
        self.assertEqual(response.status_code, 302)
        other_book.refresh_from_db()
        self.assertFalse(other_book.is_available())

    def test_unique_constraint_blocks_second_active_borrowing(self):
        from django.db import IntegrityError

        Borrowing.objects.create(book=self.book, borrower=self.other)
        with self.assertRaises(IntegrityError):
            Borrowing.objects.create(book=self.book, borrower=self.owner)
