from django.conf import settings
from django.db import models

TINT_COUNT = 5


class Poll(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="polls"
    )
    question = models.CharField("soru", max_length=200)
    description = models.TextField("açıklama", blank=True, max_length=500)
    is_active = models.BooleanField("oylamaya açık", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.question

    @property
    def total_votes(self):
        # Prefer the value annotated by the list queries to avoid extra queries.
        annotated = getattr(self, "vote_count", None)
        if annotated is not None:
            return annotated
        return self.votes.count()

    @property
    def tint_index(self):
        """Stable color index used to tint the poll card."""
        return self.pk % TINT_COUNT if self.pk else 0


class Option(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="options")
    text = models.CharField("seçenek", max_length=80)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text


class Vote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="votes")
    option = models.ForeignKey(Option, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="votes",
    )
    voter_token = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["poll", "voter_token"], name="unique_vote_per_token"),
            models.UniqueConstraint(
                fields=["poll", "user"],
                condition=models.Q(user__isnull=False),
                name="unique_vote_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.poll_id} → {self.option_id}"
