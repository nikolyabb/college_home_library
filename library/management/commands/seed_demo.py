from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from library.models import Book, Borrowing


USERS = [
    {"username": "alice", "email": "alice@example.com", "password": "demo-pass-12345"},
    {"username": "bob", "email": "bob@example.com", "password": "demo-pass-12345"},
    {"username": "carol", "email": "carol@example.com", "password": "demo-pass-12345"},
]

BOOKS = [
    {"title": "Мастер и Маргарита", "author": "М. Булгаков", "isbn": "978-5-04-089000-1", "owner": "alice"},
    {"title": "Преступление и наказание", "author": "Ф. Достоевский", "isbn": "978-5-699-12345-2", "owner": "alice"},
    {"title": "Война и мир. Том 1", "author": "Л. Толстой", "isbn": "", "owner": "bob"},
    {"title": "Анна Каренина", "author": "Л. Толстой", "isbn": "978-5-389-05001-3", "owner": "bob"},
    {"title": "Евгений Онегин", "author": "А. Пушкин", "isbn": "978-5-04-090001-4", "owner": "carol"},
    {"title": "Мёртвые души", "author": "Н. Гоголь", "isbn": "", "owner": "carol"},
]


class Command(BaseCommand):
    help = "Наполняет базу демонстрационными пользователями, книгами и выдачами."

    def handle(self, *args, **options):
        users = {}
        for u in USERS:
            user, created = User.objects.get_or_create(
                username=u["username"],
                defaults={"email": u["email"]},
            )
            user.email = u["email"]
            user.set_password(u["password"])
            user.save()
            users[u["username"]] = user
            action = "Создан" if created else "Обновлён"
            self.stdout.write(f"  {action} пользователь: {user.username}")

        books = {}
        for b in BOOKS:
            owner = users[b["owner"]]
            book, created = Book.objects.get_or_create(
                title=b["title"],
                owner=owner,
                defaults={k: v for k, v in b.items() if k != "owner"},
            )
            books[book.title] = book
            action = "Создана" if created else "Существует"
            self.stdout.write(f"  {action} книга: «{book.title}»")

        active_borrowing, created = Borrowing.objects.get_or_create(
            book=books["Анна Каренина"],
            borrower=users["alice"],
            returned_at=None,
            defaults={"due_date": (timezone.now() + timezone.timedelta(days=30)).date().replace(day=1)},
        )
        self.stdout.write(
            f"  {'Создана' if created else 'Существует'} активная выдача: "
            f"«Анна Каренина» → alice"
        )

        returned_borrowing, created = Borrowing.objects.get_or_create(
            book=books["Мастер и Маргарита"],
            borrower=users["bob"],
            returned_at__isnull=False,
            defaults={
                "returned_at": timezone.now() - timezone.timedelta(days=10),
                "due_date": (timezone.now() - timezone.timedelta(days=40)).date().replace(day=1),
            },
        )
        self.stdout.write(
            f"  {'Создана' if created else 'Существует'} завершённая выдача: "
            f"«Мастер и Маргарита» → bob (возвращена)"
        )

        self.stdout.write(self.style.SUCCESS("Демо-данные готовы."))