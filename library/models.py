from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse


class Book(models.Model):
    title = models.CharField(max_length=200, verbose_name="Название")
    author = models.CharField(max_length=200, blank=True, verbose_name="Автор")
    isbn = models.CharField(max_length=20, blank=True, verbose_name="ISBN")
    description = models.TextField(blank=True, verbose_name="Описание")
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="books",
        verbose_name="Владелец",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")

    class Meta:
        verbose_name = "Книга"
        verbose_name_plural = "Книги"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("book_detail", kwargs={"pk": self.pk})

    def is_available(self):
        return not self.borrowings.filter(returned_at__isnull=True).exists()

    def current_borrowing(self):
        return self.borrowings.filter(returned_at__isnull=True).first()

    def current_borrower(self):
        borrowing = self.current_borrowing()
        return borrowing.borrower if borrowing else None


class Borrowing(models.Model):
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="borrowings",
        verbose_name="Книга",
    )
    borrower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="borrowings",
        verbose_name="Читатель",
    )
    borrowed_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата выдачи"
    )
    returned_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Дата возврата"
    )
    due_date = models.DateField(
        null=True, blank=True, verbose_name="Срок возврата"
    )

    class Meta:
        verbose_name = "Выдача"
        verbose_name_plural = "Выдачи"
        ordering = ["-borrowed_at"]
        constraints = [
            models.UniqueConstraint(
                "book_id",
                condition=models.Q(returned_at__isnull=True),
                name="unique_active_borrowing_per_book",
            ),
        ]

    def __str__(self):
        return f"{self.book.title} — {self.borrower.username}"

    def is_active(self):
        return self.returned_at is None

    def is_overdue(self):
        from django.utils import timezone

        if self.due_date and self.is_active():
            return timezone.now().date() > self.due_date
        return False
