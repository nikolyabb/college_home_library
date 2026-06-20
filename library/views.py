from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import BookForm, BorrowingForm, CustomUserCreationForm
from .models import Book, Borrowing


def home(request):
    context = {}
    if request.user.is_authenticated:
        context["total_books"] = Book.objects.count()
        context["borrowed_books"] = Book.objects.filter(
            borrowings__returned_at__isnull=True
        ).count()
        context["my_books"] = Book.objects.filter(owner=request.user).count()
    return render(request, "home.html", context)


def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Регистрация прошла успешно.")
            return redirect("book_list")
    else:
        form = CustomUserCreationForm()
    return render(request, "register.html", {"form": form})


class CustomLoginView(LoginView):
    template_name = "login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse("book_list")


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy("home")


class BookListView(LoginRequiredMixin, ListView):
    model = Book
    template_name = "library/book_list.html"
    context_object_name = "books"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related("owner")
        q = self.request.GET.get("q")
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) | Q(author__icontains=q)
            )

        sort = self.request.GET.get("sort") or "title"
        order = self.request.GET.get("order") or "desc"
        allowed_sorts = {"title": "title", "author": "author", "created_at": "created_at"}
        sort_field = allowed_sorts.get(sort, "title")
        if order == "asc":
            queryset = queryset.order_by(sort_field)
        else:
            queryset = queryset.order_by(f"-{sort_field}")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["sort"] = self.request.GET.get("sort") or "title"
        context["order"] = self.request.GET.get("order") or "desc"
        return context


class BookDetailView(LoginRequiredMixin, DetailView):
    model = Book
    template_name = "library/book_detail.html"
    context_object_name = "book"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["borrowing_form"] = BorrowingForm()
        context["history"] = self.object.borrowings.select_related("borrower").all()
        return context


class BookCreateView(LoginRequiredMixin, CreateView):
    model = Book
    form_class = BookForm
    template_name = "library/book_form.html"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, "Книга добавлена.")
        return super().form_valid(form)


class OwnerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        book = self.get_object()
        return book.owner == self.request.user

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("У вас нет прав на редактирование этой книги.")
        return super().handle_no_permission()


class BookUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    model = Book
    form_class = BookForm
    template_name = "library/book_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Книга обновлена.")
        return super().form_valid(form)


class BookDeleteView(LoginRequiredMixin, OwnerRequiredMixin, DeleteView):
    model = Book
    template_name = "library/book_confirm_delete.html"
    success_url = reverse_lazy("book_list")

    def form_valid(self, form):
        messages.success(self.request, "Книга удалена.")
        return super().form_valid(form)


@login_required
def borrow_book(request, pk):
    book = get_object_or_404(Book, pk=pk)

    if not book.is_available():
        messages.error(request, "Эта книга уже занята.")
        return redirect(book)

    form = BorrowingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        borrowing = form.save(commit=False)
        borrowing.book = book
        borrowing.borrower = request.user
        try:
            with transaction.atomic():
                borrowing.save()
        except IntegrityError:
            messages.error(request, "Эта книга уже занята.")
            return redirect(book)
        messages.success(
            request,
            f"Вы взяли книгу «{book.title}». Не забудьте вернуть до {borrowing.due_date.strftime('%d.%m.%Y')}."
            if borrowing.due_date
            else f"Вы взяли книгу «{book.title}».",
        )
        return redirect(book)

    return render(request, "library/borrow_form.html", {"book": book, "form": form})


@login_required
def return_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    borrowing = book.current_borrowing()

    if not borrowing:
        messages.error(request, "Эта книга никем не занята.")
        return redirect(book)

    if borrowing.borrower != request.user and book.owner != request.user:
        raise PermissionDenied("Вы не можете вернуть эту книгу.")

    if request.method == "POST":
        borrowing.returned_at = timezone.now()
        borrowing.save()
        messages.success(request, f"Книга «{book.title}» возвращена.")
        return redirect(book)

    return render(request, "library/return_confirm.html", {"book": book, "borrowing": borrowing})


class DashboardView(LoginRequiredMixin, ListView):
    template_name = "library/dashboard.html"
    context_object_name = "my_books"

    def get_queryset(self):
        return Book.objects.filter(owner=self.request.user).prefetch_related(
            "borrowings__borrower"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["my_borrowings"] = Borrowing.objects.filter(
            borrower=self.request.user, returned_at__isnull=True
        ).select_related("book", "book__owner")
        context["history"] = Borrowing.objects.filter(
            borrower=self.request.user, returned_at__isnull=False
        ).select_related("book")[:10]
        return context
