"""Generates a realistic, self-contained demo dataset (Phase 13 bullet 8) so
the app can be shown without ever touching the live Google Sheet. Every
record is synthetic (source='app'), tagged with DEMO_MARKER in remarks so a
re-run cleanly replaces the previous batch instead of accumulating duplicates.

Unlike sync-time fabrication (forbidden by §7 — "do not port that seeding
logic into the app"), filling in team/engaged_resources/engagement here is
correct: this command IS the dedicated seed script §7 anticipates, not the
sync path.
"""

import datetime
import random

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.bids.models import Bid, Client, Person, Team

DEMO_MARKER = "[DEMO]"

CLIENTS = [
    ("Alpha Development Authority", "Government"),
    ("Beta Power Board", "Government"),
    ("Gamma Highways Corporation", "Government"),
    ("Delta National Bank PLC", "Banking & Fintech"),
    ("Epsilon Microfinance Ltd", "Banking & Fintech"),
    ("Zeta Telecom Bangladesh", "Telecom"),
    ("Eta Mobile Networks", "Telecom"),
    ("Theta University of Technology", "Education & Research"),
    ("Iota Research Institute", "Education & Research"),
    ("Kappa Retail Holdings", "Enterprise"),
    ("Lambda Manufacturing Group", "Enterprise"),
    ("Mu Logistics & Freight", "Enterprise"),
]

PEOPLE = [
    "Rahim Chowdhury", "Farhana Islam", "Tanvir Ahmed", "Nusrat Jahan",
    "Kamrul Hasan", "Sadia Afrin", "Mahmudul Karim", "Rifat Hossain",
    "Sabrina Akter", "Imran Kabir", "Nazia Sultana", "Shakil Rahman",
    "Tasnim Anwar", "Jubayer Alam", "Rumana Begum",
]

STAGES = ["TENDER", "RFP", "RFQ", "EOI", "ENLISTMENT", "EGP-RFP"]
INITIATION_MODES = ["SALES EFFORT", "TENDER MELA", "E-GP NOTICE", "CPTU NOTICE"]
SECURITY_MODES = ["BANK GUARANTEE", "NOT APPLICABLE", "PAY ORDER"]
BANKS = ["Standard Chartered Bank", "BRAC Bank", "Dutch-Bangla Bank", "City Bank"]
PAST_RESULTS = ["WON", "LOST", "PENDING", "QUALIFIED", "LOWEST", "CANCELLED"]
PAST_RESULT_WEIGHTS = [0.22, 0.22, 0.2, 0.14, 0.12, 0.1]


class Command(BaseCommand):
    help = "Seed a realistic demo dataset of app-native bids (never touches the Google Sheet)."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=40, help="Number of demo bids to generate.")

    def handle(self, *args, **options):
        count = options["count"]
        rng = random.Random(42)
        today = datetime.date.today()

        with transaction.atomic():
            removed, _ = Bid.all_objects.filter(remarks__startswith=DEMO_MARKER).delete()
            if removed:
                self.stdout.write(f"Removed {removed} previous demo bid(s).")

            teams = {t.name: t for t in Team.objects.all()}
            clients = {}
            for name, _team in CLIENTS:
                client, _ = Client.objects.get_or_create(canonical_name=name.lower(), defaults={"name": name})
                clients[name] = client

            people = {}
            for name in PEOPLE:
                person, _ = Person.objects.get_or_create(canonical_name=name)
                people[name] = person

            created = 0
            for _ in range(count):
                client_name, team_name = rng.choice(CLIENTS)
                is_future = rng.random() < 0.35

                if is_future:
                    submission_date = today + datetime.timedelta(days=rng.randint(1, 45))
                    result = "PENDING"
                    submission_status = "NOT SUBMITTED"
                else:
                    submission_date = today - datetime.timedelta(days=rng.randint(1, 180))
                    result = rng.choices(PAST_RESULTS, weights=PAST_RESULT_WEIGHTS)[0]
                    submission_status = "SUBMITTED"

                published_date = submission_date - datetime.timedelta(days=rng.randint(14, 45))
                has_team_data = rng.random() < 0.7
                has_security = rng.random() < 0.6

                bid = Bid(
                    client=clients[client_name],
                    description=f"Supply, installation and commissioning of systems for {client_name}",
                    cam=people[rng.choice(PEOPLE)],
                    sales_resource=people[rng.choice(PEOPLE)],
                    bid_manager=people[rng.choice(PEOPLE)],
                    team=teams.get(team_name) if has_team_data else None,
                    stage=rng.choice(STAGES),
                    initiation_mode=rng.choice(INITIATION_MODES),
                    is_goods=rng.random() < 0.5,
                    is_works=rng.random() < 0.3,
                    is_service=rng.random() < 0.6,
                    tender_id=f"DEMO/{today.year}/{rng.randint(1000, 9999)}",
                    published_date=published_date,
                    submission_date=submission_date,
                    submission_status=submission_status,
                    result=result,
                    remarks=f"{DEMO_MARKER} synthetic record for demo purposes only.",
                )

                if has_security:
                    amount = rng.randint(5, 300) * 10000
                    bid.security_mode = "BANK GUARANTEE"
                    bid.security_amount_raw = f"{amount:,}"
                    bid.security_amount = amount
                    bid.security_currency = Bid.Currency.BDT
                    bid.bg_issue_date = published_date
                    bid.bg_bank = rng.choice(BANKS)
                    bid.bg_reference = f"BG-{rng.randint(100000, 999999)}"
                    bid.bg_expiry_date = submission_date + datetime.timedelta(days=rng.randint(90, 400))
                else:
                    bid.security_mode = "NOT APPLICABLE"

                if has_team_data:
                    bid.engagement_from = published_date
                    bid.engagement_to = submission_date

                bid.save()

                if has_team_data:
                    engaged = rng.sample(PEOPLE, k=rng.randint(2, 5))
                    bid.engaged_resources.set([people[name] for name in engaged])

                created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {created} demo bid(s)."))
