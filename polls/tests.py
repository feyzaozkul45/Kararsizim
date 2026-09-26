from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Option, Poll, Vote
from .utils import VOTER_COOKIE

User = get_user_model()


def make_poll(author, question="Bugün ne yapsam?", options=("Sinema", "Yemek"), **kwargs):
    poll = Poll.objects.create(author=author, question=question, **kwargs)
    for index, text in enumerate(options):
        Option.objects.create(poll=poll, text=text, order=index)
    return poll


class PollCreateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ayse", "ayse@example.com", "Sifre-12345-xyz")
        self.url = reverse("poll_create")

    def post(self, options, question="Bugün ne yapsam?"):
        return self.client.post(self.url, {"question": question, "option": options})

    def test_guest_is_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")

    def test_guest_sees_login_message(self):
        response = self.client.get(self.url, follow=True)
        self.assertContains(response, "Anket açmak için giriş yapmalısın")

    def test_member_can_create_poll_with_blank_options_ignored(self):
        self.client.force_login(self.user)
        response = self.post(["Sinema", "", "Yemek", "  "])
        poll = Poll.objects.get()
        self.assertRedirects(response, reverse("poll_detail", args=[poll.pk]))
        self.assertEqual([o.text for o in poll.options.all()], ["Sinema", "Yemek"])
        self.assertEqual(poll.author, self.user)

    def test_option_count_must_be_between_two_and_five(self):
        self.client.force_login(self.user)
        self.assertEqual(self.post(["Sadece bir"]).status_code, 200)
        self.assertEqual(self.post(["1", "2", "3", "4", "5", "6"]).status_code, 200)
        self.assertFalse(Poll.objects.exists())

        self.assertEqual(self.post(["1", "2", "3", "4", "5"]).status_code, 302)
        self.assertEqual(Poll.objects.get().options.count(), 5)

    def test_duplicate_options_are_rejected_ignoring_case_and_spaces(self):
        self.client.force_login(self.user)
        response = self.post(["Sinema", "  sinema "])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aynı seçeneği")
        self.assertFalse(Poll.objects.exists())

    def test_question_length_is_validated(self):
        self.client.force_login(self.user)
        self.assertEqual(self.post(["A", "B"], question="abc").status_code, 200)
        self.assertEqual(self.post(["A", "B"], question="x" * 201).status_code, 200)
        self.assertFalse(Poll.objects.exists())

    def test_option_longer_than_80_chars_is_rejected(self):
        self.client.force_login(self.user)
        self.assertEqual(self.post(["A", "b" * 81]).status_code, 200)
        self.assertFalse(Poll.objects.exists())

    def test_form_keeps_typed_options_on_error(self):
        self.client.force_login(self.user)
        response = self.post(["Sinema"])
        self.assertContains(response, 'value="Sinema"')


class VoteTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("sahip", "sahip@example.com", "Sifre-12345-xyz")
        self.poll = make_poll(self.owner)
        self.option_a, self.option_b = self.poll.options.all()
        self.url = reverse("poll_vote", args=[self.poll.pk])

    def vote(self, client, option, **extra):
        return client.post(self.url, {"option": option.pk}, **extra)

    def test_guest_can_vote_and_gets_cookie(self):
        response = self.vote(self.client, self.option_a)
        self.assertRedirects(response, reverse("poll_detail", args=[self.poll.pk]))
        vote = Vote.objects.get()
        self.assertIsNone(vote.user)
        self.assertEqual(response.cookies[VOTER_COOKIE].value, vote.voter_token)
        self.assertTrue(response.cookies[VOTER_COOKIE]["httponly"])

    def test_second_vote_from_same_browser_is_blocked(self):
        self.vote(self.client, self.option_a)
        response = self.vote(self.client, self.option_b)
        self.assertRedirects(response, reverse("poll_detail", args=[self.poll.pk]))
        self.assertEqual(Vote.objects.count(), 1)

    def test_second_vote_json_returns_409(self):
        self.vote(self.client, self.option_a)
        response = self.vote(self.client, self.option_b, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json(), {"ok": False, "error": "Bu ankete zaten oy verdin."}
        )

    def test_different_browser_can_vote(self):
        self.vote(self.client, self.option_a)
        self.vote(Client(), self.option_b)
        self.assertEqual(Vote.objects.count(), 2)

    def test_json_response_shape(self):
        response = self.vote(self.client, self.option_a, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["total_votes"], 1)
        self.assertEqual(data["voted_option_id"], self.option_a.pk)
        self.assertEqual(
            data["results"][0],
            {"id": self.option_a.pk, "text": "Sinema", "votes": 1, "percent": 100},
        )

    def test_option_of_another_poll_is_rejected(self):
        other = make_poll(self.owner, question="Başka bir anket")
        response = self.vote(self.client, other.options.first(), HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Vote.objects.exists())

    def test_closed_poll_does_not_accept_votes(self):
        self.poll.is_active = False
        self.poll.save()
        response = self.vote(self.client, self.option_a, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Vote.objects.exists())

    def test_member_cannot_vote_twice_even_with_new_cookie(self):
        member = User.objects.create_user("uye", "uye@example.com", "Sifre-12345-xyz")
        self.client.force_login(member)
        self.vote(self.client, self.option_a)
        self.assertEqual(Vote.objects.get().user, member)

        del self.client.cookies[VOTER_COOKIE]  # keep the session, drop the voter token
        self.vote(self.client, self.option_b)
        self.assertEqual(Vote.objects.count(), 1)

    def test_owner_can_vote_on_own_poll(self):
        self.client.force_login(self.owner)
        self.vote(self.client, self.option_a)
        self.assertEqual(Vote.objects.count(), 1)

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)


class ResultVisibilityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("sahip", "sahip@example.com", "Sifre-12345-xyz")
        self.poll = make_poll(self.owner)
        self.option_a = self.poll.options.first()
        self.detail = reverse("poll_detail", args=[self.poll.pk])

    def test_results_hidden_before_voting(self):
        response = self.client.get(self.detail)
        self.assertFalse(response.context["show_results"])
        self.assertContains(response, "Sonuçları görmek için önce oy ver")
        self.assertNotContains(response, "result-bar")
        self.assertNotContains(response, "%0")

    def test_results_visible_after_voting(self):
        self.client.post(reverse("poll_vote", args=[self.poll.pk]), {"option": self.option_a.pk})
        response = self.client.get(self.detail)
        self.assertTrue(response.context["show_results"])
        self.assertTrue(response.context["has_voted"])
        self.assertContains(response, "✓")

    def test_owner_always_sees_results(self):
        self.client.force_login(self.owner)
        self.assertTrue(self.client.get(self.detail).context["show_results"])

    def test_closed_poll_shows_results_to_everyone(self):
        self.poll.is_active = False
        self.poll.save()
        response = self.client.get(self.detail)
        self.assertTrue(response.context["show_results"])
        self.assertFalse(response.context["can_vote"])


class OwnerActionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("sahip", "sahip@example.com", "Sifre-12345-xyz")
        self.other = User.objects.create_user("baska", "baska@example.com", "Sifre-12345-xyz")
        self.poll = make_poll(self.owner)

    def test_non_owner_cannot_delete_or_toggle(self):
        self.client.force_login(self.other)
        delete = self.client.post(reverse("poll_delete", args=[self.poll.pk]))
        toggle = self.client.post(reverse("poll_toggle", args=[self.poll.pk]))
        self.assertEqual(delete.status_code, 403)
        self.assertEqual(toggle.status_code, 403)
        self.poll.refresh_from_db()
        self.assertTrue(self.poll.is_active)

    def test_owner_can_toggle_and_delete(self):
        self.client.force_login(self.owner)
        self.client.post(reverse("poll_toggle", args=[self.poll.pk]))
        self.poll.refresh_from_db()
        self.assertFalse(self.poll.is_active)

        response = self.client.post(reverse("poll_delete", args=[self.poll.pk]))
        self.assertRedirects(response, reverse("my_polls"))
        self.assertFalse(Poll.objects.exists())

    def test_actions_require_post(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("poll_delete", args=[self.poll.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse("poll_toggle", args=[self.poll.pk])).status_code, 405)

    def test_toggle_ignores_unsafe_next_url(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("poll_toggle", args=[self.poll.pk]), {"next": "https://evil.example/"}
        )
        self.assertRedirects(response, reverse("my_polls"))

    def test_my_polls_lists_only_own_polls(self):
        make_poll(self.other, question="Başkasının anketi")
        self.client.force_login(self.owner)
        response = self.client.get(reverse("my_polls"))
        self.assertEqual([p.pk for p in response.context["polls"]], [self.poll.pk])

    def test_my_polls_requires_login(self):
        response = self.client.get(reverse("my_polls"))
        self.assertEqual(response.status_code, 302)


class PollListTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("sahip", "sahip@example.com", "Sifre-12345-xyz")

    def test_empty_state(self):
        response = self.client.get(reverse("poll_list"))
        self.assertContains(response, "Henüz kimse kararsız değil")
        self.assertContains(response, "Sen de sor!")

    def test_pagination_and_query_count(self):
        for i in range(15):
            make_poll(self.owner, question=f"Soru numarası {i}")
        with self.assertNumQueries(2):  # count + page
            response = self.client.get(reverse("poll_list"))
        self.assertEqual(len(response.context["page"]), 12)
        response = self.client.get(reverse("poll_list") + "?page=2")
        self.assertEqual(len(response.context["page"]), 3)

    def test_unknown_poll_returns_themed_404(self):
        response = self.client.get(reverse("poll_detail", args=[999]))
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "kaybolmuş", status_code=404)

    def test_forbidden_page_is_themed(self):
        other = User.objects.create_user("baska", "baska@example.com", "Sifre-12345-xyz")
        poll = make_poll(self.owner)
        self.client.force_login(other)
        response = self.client.post(reverse("poll_delete", args=[poll.pk]))
        self.assertContains(response, "Buna iznin yok", status_code=403)
