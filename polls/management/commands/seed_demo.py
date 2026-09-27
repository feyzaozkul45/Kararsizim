import os
import random
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from polls.models import Option, Poll, Vote

User = get_user_model()

DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "")

DEMO_USERS = [
    {"username": "demo_ayse", "email": "demo.ayse@example.com"},
    {"username": "demo_mert", "email": "demo.mert@example.com"},
    {"username": "demo_zeynep", "email": "demo.zeynep@example.com"},
    {"username": "demo_kaan", "email": "demo.kaan@example.com"},
]

# (question, options, author index into DEMO_USERS, hours ago it was created, is_active)
DEMO_POLLS = [
    ("Hafta sonu kamp mı, şehirde konser mi?", ["Kamp", "Konser"], 0, 2, True),
    ("Hangi diziye başlasam?", ["Fantastik dizi", "Suç draması", "Komedi", "Bilim kurgu"], 1, 5, True),
    ("Sınav haftası müzik listesi ne olsun?", ["Lo-fi", "Pop", "Sessizlik", "Klasik"], 2, 8, True),
    ("Yaz stajı: uzaktan mı ofis mi?", ["Uzaktan", "Ofis", "Hibrit"], 3, 12, True),
    ("Doğum günü partisi teması ne olsun?", ["Retro", "Neon", "Pijama partisi", "Tema yok"], 0, 20, True),
    (
        "Ders çalışırken en çok ne dikkat dağıtıyor?",
        ["Telefon", "Sosyal medya", "Açlık", "Yorgunluk", "Gürültü"],
        1,
        30,
        True,
    ),
    ("Kahve mi çay mı?", ["Kahve", "Çay"], 2, 40, False),
    ("Yeni telefon alırken en önemli şey ne?", ["Kamera", "Pil ömrü", "Fiyat", "Depolama"], 3, 50, True),
    ("Tatilde deniz mi dağ mı?", ["Deniz", "Dağ"], 0, 70, True),
    (
        "Grup projesinde en can sıkıcı şey ne?",
        ["Son dakika işi", "İletişimsizlik", "Eşit olmayan iş bölümü"],
        1,
        90,
        False,
    ),
]


class Command(BaseCommand):
    help = "Creates demo users and polls for local development. Refuses to run when DEBUG=False."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Bu komut yalnızca DEBUG=True iken çalışır (canlı veritabanına yanlışlıkla "
                "sahte veri eklenmesini önlemek için)."
            )
        if not DEMO_PASSWORD:
            raise CommandError(
                "DEMO_PASSWORD ortam değişkenini .env dosyanda tanımlamalısın "
                "(demo kullanıcıların şifresi olarak kullanılır)."
            )

        users = [self._get_or_create_user(data) for data in DEMO_USERS]

        created_count = 0
        for question, option_texts, author_index, hours_ago, is_active in DEMO_POLLS:
            poll, created = self._get_or_create_poll(
                users[author_index], question, option_texts, is_active, hours_ago
            )
            if created:
                created_count += 1
                self._add_random_votes(poll, users)

        self.stdout.write(
            self.style.SUCCESS(
                f"{len(users)} demo kullanıcı hazır, {created_count} yeni anket eklendi "
                f"(toplam {Poll.objects.filter(author__in=users).count()} demo anketi)."
            )
        )

    def _get_or_create_user(self, data):
        user, created = User.objects.get_or_create(
            username=data["username"], defaults={"email": data["email"]}
        )
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save()
        return user

    @transaction.atomic
    def _get_or_create_poll(self, author, question, option_texts, is_active, hours_ago):
        poll, created = Poll.objects.get_or_create(
            author=author,
            question=question,
            defaults={"is_active": is_active},
        )
        if created:
            Option.objects.bulk_create(
                Option(poll=poll, text=text, order=index)
                for index, text in enumerate(option_texts)
            )
            # Backdate for a realistic "en yeni" order; update() bypasses auto_now_add.
            Poll.objects.filter(pk=poll.pk).update(
                created_at=timezone.now() - timedelta(hours=hours_ago)
            )
        return poll, created

    def _add_random_votes(self, poll, users):
        options = list(poll.options.all())
        weights = [random.uniform(0.5, 3.0) for _ in options]
        voted_user_ids = set()

        for _ in range(random.randint(5, 40)):
            option = random.choices(options, weights=weights, k=1)[0]
            # Mostly anonymous visitors, occasionally one of the demo members.
            if random.random() < 0.3:
                user = random.choice(users)
                if user.id in voted_user_ids:
                    continue
                voted_user_ids.add(user.id)
                Vote.objects.create(poll=poll, option=option, user=user, voter_token=str(uuid.uuid4()))
            else:
                Vote.objects.create(poll=poll, option=option, voter_token=str(uuid.uuid4()))
