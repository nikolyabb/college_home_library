from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.CustomLogoutView.as_view(), name="logout"),
    path("books/", views.BookListView.as_view(), name="book_list"),
    path("books/add/", views.BookCreateView.as_view(), name="book_add"),
    path("books/<pk>/", views.BookDetailView.as_view(), name="book_detail"),
    path("books/<pk>/edit/", views.BookUpdateView.as_view(), name="book_edit"),
    path("books/<pk>/delete/", views.BookDeleteView.as_view(), name="book_delete"),
    path("books/<pk>/borrow/", views.borrow_book, name="book_borrow"),
    path("books/<pk>/return/", views.return_book, name="book_return"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
]
