from django.core.management.base import BaseCommand

from teams.models import AzureDevOpsSettings
from teams.sync import run_support_ado_sync


class Command(BaseCommand):
    help = (
        "Run the team-wide Azure DevOps support-ticket sync (the same one the Support tab's "
        "'Save & Sync' button runs). Wire this up to an external daily cron (e.g. a Render "
        "Cron Job or GitHub Actions scheduled workflow) for a reliable schedule, rather than "
        "relying only on the in-app opportunistic sync that runs on page views."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Run even if automatic sync is turned off in Azure DevOps settings.",
        )

    def handle(self, *args, **options):
        settings_obj = AzureDevOpsSettings.load()
        if not settings_obj.support_auto_sync_enabled and not options["force"]:
            self.stdout.write(
                self.style.WARNING(
                    "Automatic support-ticket sync is disabled in Azure DevOps settings — "
                    "skipping. Pass --force to run anyway."
                )
            )
            return

        result, error = run_support_ado_sync(settings_obj)
        if error:
            self.stderr.write(self.style.ERROR(f"Sync failed: {error}"))
            return

        summary = f"Synced {result['matched']} item(s) across {result['employee_count']} employee(s)."
        if result["unmatched"]:
            summary += f" {len(result['unmatched'])} item(s) skipped — no employee matched."
        self.stdout.write(self.style.SUCCESS(summary))
