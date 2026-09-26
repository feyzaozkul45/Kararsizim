from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import PollForm
from .models import Option, Poll, Vote
from .utils import get_voter_token, new_voter_token, set_voter_cookie

POLLS_PER_PAGE = 12


def member_required(message):
    """Redirect guests to the login page with a friendly message."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.info(request, message)
                return redirect_to_login(request.get_full_path())
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def polls_with_counts():
    return (
        Poll.objects.select_related("author")
        .annotate(vote_count=Count("votes"))
        .order_by("-created_at", "-id")
    )


def find_existing_vote(poll, user, token):
    """Look for a previous vote: first by user, then by voter token."""
    if user.is_authenticated:
        vote = Vote.objects.filter(poll=poll, user=user).first()
        if vote:
            return vote
    if token:
        return Vote.objects.filter(poll=poll, voter_token=token).first()
    return None


def build_results(poll):
    """Per-option vote counts and percentages, in display order."""
    options = list(poll.options.annotate(vote_count=Count("votes")))
    total = sum(option.vote_count for option in options)
    return total, [
        {
            "id": option.id,
            "text": option.text,
            "votes": option.vote_count,
            "percent": round(option.vote_count * 100 / total, 1) if total else 0,
        }
        for option in options
    ]


def poll_list(request):
    paginator = Paginator(polls_with_counts(), POLLS_PER_PAGE)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "polls/poll_list.html", {"page": page})


def poll_detail(request, pk):
    poll = get_object_or_404(Poll.objects.select_related("author"), pk=pk)
    token = get_voter_token(request)
    existing_vote = find_existing_vote(poll, request.user, token)

    is_owner = request.user.is_authenticated and poll.author_id == request.user.id
    show_results = is_owner or not poll.is_active or existing_vote is not None
    can_vote = poll.is_active and existing_vote is None

    total, results = build_results(poll)
    voted_option_id = existing_vote.option_id if existing_vote else None
    for result in results:
        result["mine"] = result["id"] == voted_option_id

    context = {
        "poll": poll,
        "is_owner": is_owner,
        "show_results": show_results,
        "can_vote": can_vote,
        "total_votes": total,
        "results": results,
        "has_voted": existing_vote is not None,
    }
    return render(request, "polls/poll_detail.html", context)


def _vote_error(request, poll, message, status, wants_json):
    if wants_json:
        return JsonResponse({"ok": False, "error": message}, status=status)
    messages.error(request, message)
    return redirect("poll_detail", pk=poll.pk)


@require_POST
def poll_vote(request, pk):
    poll = get_object_or_404(Poll, pk=pk)
    wants_json = (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
    )

    if not poll.is_active:
        return _vote_error(request, poll, "Bu anket oylamaya kapalı.", 403, wants_json)

    try:
        option = poll.options.get(pk=int(request.POST.get("option", "")))
    except (ValueError, Option.DoesNotExist):
        return _vote_error(request, poll, "Geçerli bir seçenek seç.", 400, wants_json)

    token = get_voter_token(request)
    if find_existing_vote(poll, request.user, token):
        return _vote_error(request, poll, "Bu ankete zaten oy verdin.", 409, wants_json)

    issued_token = token or new_voter_token()
    try:
        with transaction.atomic():
            Vote.objects.create(
                poll=poll,
                option=option,
                user=request.user if request.user.is_authenticated else None,
                voter_token=issued_token,
            )
    except IntegrityError:
        return _vote_error(request, poll, "Bu ankete zaten oy verdin.", 409, wants_json)

    if wants_json:
        total, results = build_results(poll)
        response = JsonResponse(
            {"ok": True, "total_votes": total, "voted_option_id": option.id, "results": results}
        )
    else:
        messages.success(request, "Oyun kaydedildi! 🎉")
        response = redirect("poll_detail", pk=poll.pk)

    if token is None:
        set_voter_cookie(response, issued_token)
    return response


@member_required("Anket açmak için giriş yapmalısın 👋")
def poll_create(request):
    if request.method == "POST":
        form = PollForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                poll = Poll.objects.create(
                    author=request.user,
                    question=form.cleaned_data["question"],
                    description=form.cleaned_data["description"].strip(),
                )
                Option.objects.bulk_create(
                    Option(poll=poll, text=text, order=index)
                    for index, text in enumerate(form.options)
                )
            messages.success(request, "Anketin yayında! 🚀")
            return redirect("poll_detail", pk=poll.pk)
    else:
        form = PollForm()
    return render(request, "polls/poll_create.html", {"form": form})


@member_required("Anketlerini görmek için giriş yapmalısın 👋")
def my_polls(request):
    polls = polls_with_counts().filter(author=request.user)
    return render(request, "polls/my_polls.html", {"polls": polls})


def _get_owned_poll(request, pk):
    poll = get_object_or_404(Poll, pk=pk)
    if poll.author_id != request.user.id:
        raise PermissionDenied
    return poll


@require_POST
@member_required("Bu işlem için giriş yapmalısın 👋")
def poll_toggle(request, pk):
    poll = _get_owned_poll(request, pk)
    poll.is_active = not poll.is_active
    poll.save(update_fields=["is_active"])
    messages.success(
        request, "Anket oylamaya açıldı." if poll.is_active else "Anket oylamaya kapatıldı."
    )
    return _redirect_back(request, "my_polls")


@require_POST
@member_required("Bu işlem için giriş yapmalısın 👋")
def poll_delete(request, pk):
    poll = _get_owned_poll(request, pk)
    poll.delete()
    messages.success(request, "Anket silindi.")
    return redirect("my_polls")


def _redirect_back(request, default):
    """Redirect to the POSTed `next` URL when it is safe, otherwise to `default`."""
    next_url = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect(default)


# --- Error pages (same theme as the rest of the site) -----------------------

def error_403(request, exception=None):
    return render(request, "403.html", status=403)


def error_404(request, exception=None):
    return render(request, "404.html", status=404)


def error_500(request):
    return render(request, "500.html", status=500)
