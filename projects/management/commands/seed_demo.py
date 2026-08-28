import random
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from projects.models import Application, Area, Project, Task, TransitionDocument, TransitionSystem
from teams.models import Employee, WorkItem


class Command(BaseCommand):
    help = "Seed the database with realistic fictitious demo data (no real org data)."

    def handle(self, *args, **options):
        random.seed(42)
        today = date.today()

        # -- Default login (demo only — change before any real deployment) --
        admin_user, _ = User.objects.get_or_create(
            username="admin", defaults={"email": "admin@example.com"}
        )
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.set_password("Admin@123")
        admin_user.save()

        # -- Team --------------------------------------------------------
        lead, _ = Employee.objects.get_or_create(
            name="Ananya Krishnan", defaults={"role": Employee.Role.LEAD, "email": "ananya.krishnan@example.com"}
        )
        sdm, _ = Employee.objects.get_or_create(
            name="Arjun Malhotra", defaults={"role": Employee.Role.SDM, "email": "arjun.malhotra@example.com"}
        )
        platform_lead, _ = Employee.objects.get_or_create(
            name="Vikram Nair",
            defaults={"role": Employee.Role.PLATFORM_LEAD, "email": "vikram.nair@example.com", "manager": lead},
        )
        employees_data = [
            ("Divya Menon", Employee.Role.PLATFORM_ENGINEER, platform_lead),
            ("Sanjay Iyer", Employee.Role.PLATFORM_ENGINEER, platform_lead),
            ("Rohit Deshmukh", Employee.Role.DATABASE_ENGINEER, lead),
            ("Priya Raghavan", Employee.Role.DEVOPS, lead),
            ("Karthik Subramaniam", Employee.Role.DEVOPS, lead),
            ("Neha Kulkarni", Employee.Role.DEVOPS, lead),
        ]
        employees = {"Ananya Krishnan": lead, "Vikram Nair": platform_lead, "Arjun Malhotra": sdm}
        for name, role, manager in employees_data:
            emp, _ = Employee.objects.get_or_create(
                name=name,
                defaults={
                    "role": role,
                    "manager": manager,
                    "email": f"{name.lower().replace(' ', '.')}@example.com",
                },
            )
            employees[name] = emp

        # -- Areas ---------------------------------------------------------
        area_names = ["Portal", "Integration", "Infra", "Patching", "Security", "Audit"]
        areas = {n: Area.objects.get_or_create(name=n)[0] for n in area_names}

        # -- Projects --------------------------------------------------------
        projects_data = [
            ("ITR e-Filing Portal", "Citizen-facing income tax return filing portal.", platform_lead),
            ("TDS Reconciliation Engine", "Reconciles TDS deductions against deductor filings.", lead),
            ("PAN-Aadhaar Linking Service", "Links PAN records to Aadhaar via UIDAI e-KYC.", platform_lead),
            ("Refund Processing Pipeline", "Validates bank details and disburses refunds.", lead),
            ("Form 26AS Integration", "Nightly sync of tax credit statements.", platform_lead),
            ("Taxpayer Grievance Redressal", "Ticketing and SLA tracking for taxpayer grievances.", lead),
        ]
        projects = {}
        for name, desc, project_lead in projects_data:
            proj, _ = Project.objects.get_or_create(name=name, defaults={"description": desc, "lead": project_lead})
            projects[name] = proj

        # -- Tickets (Planned + Ad Hoc) --------------------------------------
        tickets_data = [
            ("ITR e-Filing Portal", "Vulnerability Remediation - Login Module", "Security", "planned", "todo", True, 10),
            ("ITR e-Filing Portal", "Annual Patch Cycle - All Lower Environments", "Patching", "planned", "in_progress", False, 20),
            ("ITR e-Filing Portal", "Space Optimization - Archive Old Assessment Years", "Infra", "planned", "todo", False, 30),
            ("TDS Reconciliation Engine", "Batch Job Performance Tuning", "Portal", "planned", "in_progress", True, 15),
            ("TDS Reconciliation Engine", "Dynamic Retries for Failed Deductor Uploads", "Integration", "planned", "todo", False, 45),
            ("PAN-Aadhaar Linking Service", "Retry Logic for Failed e-KYC Matches", "Integration", "planned", "todo", False, 25),
            ("PAN-Aadhaar Linking Service", "Automated Incident Creation on Match Failures", "Portal", "planned", "todo", True, 60),
            ("Refund Processing Pipeline", "Bank Account Validation Enhancement", "Portal", "adhoc", "in_progress", False, 12),
            ("Refund Processing Pipeline", "Duplicate Transaction Reference Fix", "Integration", "adhoc", "done", False, -5),
            ("Form 26AS Integration", "Nightly Sync Failure Investigation", "Infra", "adhoc", "done", False, -2),
            ("Form 26AS Integration", "Migrate Sync Service to New Region", "Infra", "planned", "todo", False, 40),
            ("Taxpayer Grievance Redressal", "SLA Breach Alerting", "Portal", "planned", "in_progress", True, 18),
            ("Taxpayer Grievance Redressal", "KPMG Audit Requirement - Access Logs", "Audit", "planned", "todo", False, 35),
            ("ITR e-Filing Portal", "OTP Gateway - SMS Provider Failover", "Integration", "adhoc", "todo", True, 8),
        ]
        assignees = ["Divya Menon", "Sanjay Iyer", "Rohit Deshmukh", "Priya Raghavan", "Karthik Subramaniam", "Neha Kulkarni"]
        remarks_pool = ["", "", "Initiatives", "For all regional centres", "Pending vendor confirmation"]
        for i, (proj_name, title, area_name, ttype, status, sdm_attn, offset) in enumerate(tickets_data):
            Task.objects.get_or_create(
                title=title,
                project=projects[proj_name],
                defaults={
                    "area": areas[area_name],
                    "ticket_type": ttype,
                    "status": status,
                    "assigned_by": sdm,
                    "assignee": employees[assignees[i % len(assignees)]],
                    "due_date": today + timedelta(days=offset),
                    "sdm_attention": sdm_attn,
                    "remarks": remarks_pool[i % len(remarks_pool)],
                },
            )

        # -- Applications ------------------------------------------------
        applications_data = [
            ("e-Filing Core Engine 4.0", "3-high", "eSuvidha-Digital", "in_house", "business_capabilities", "Priya Raghavan"),
            ("TDS-CPC Integration Gateway", "3-high", "eSuvidha-Digital", "in_house", "it_capabilities", "Karthik Subramaniam"),
            ("PAN Validation Service", "3-high", "eSuvidha-Digital", "software_package", "business_capabilities", "Divya Menon"),
            ("Aadhaar e-KYC Connector", "2-critical", "eSuvidha-Digital", "software_package", "it_capabilities", "Sanjay Iyer"),
            ("Refund Banking Interface", "2-critical", "eSuvidha-Digital", "in_house", "business_capabilities", "Rohit Deshmukh"),
            ("Taxpayer Grievance CRM", "4-medium", "eSuvidha-Digital", "software_package", "business_capabilities", "Neha Kulkarni"),
            ("Form 26AS Sync Service", "3-high", "eSuvidha-Digital", "in_house", "it_capabilities", "Priya Raghavan"),
            ("OTP & Notification Gateway", "3-high", "eSuvidha-Digital", "software_package", "it_capabilities", "Karthik Subramaniam"),
        ]
        for name, sensitivity, container, procurement, apptype, officer in applications_data:
            Application.objects.get_or_create(
                name=name,
                defaults={
                    "sensitivity": sensitivity,
                    "architecture_container": container,
                    "gsc_owner": "Vikram Nair",
                    "it_perimeter_lvl2": "eSuvidha-Digital",
                    "it_perimeter_lvl3": "All",
                    "object_type": Application.ObjectType.APPLICATION,
                    "procurement_type": procurement,
                    "application_type": apptype,
                    "officer": officer,
                    "country": "India",
                },
            )

        # -- Transition plan -----------------------------------------------
        system_names = ["CPC-ITR", "TRACES", "PFMS", "NSDL-PAN", "UIDAI-eKYC", "Payment Gateway"]
        systems = {n: TransitionSystem.objects.get_or_create(name=n)[0] for n in system_names}

        transition_data = [
            ("Introduction", "Transition Plan", "Defines scope, timelines, transition waves, roles.", "Engineering Team", ["CPC-ITR", "TRACES", "NSDL-PAN"]),
            ("Governance & Transition Management", "Stakeholder Register", "Lists all key stakeholders.", "Engineering Team", ["CPC-ITR", "TRACES", "PFMS", "NSDL-PAN"]),
            ("Governance & Transition Management", "RACI Matrix", "Responsible/Accountable/Consulted/Informed per activity.", "Engineering Team", ["CPC-ITR", "TRACES"]),
            ("Governance & Transition Management", "Risk Register & Mitigation Plan", "Identifies risks with mitigations.", "Engineering Team", ["CPC-ITR"]),
            ("Application & Technical Documentation", "Physical & Logical Architecture Diagrams", "High-level and detailed architecture diagrams.", "Architect", ["CPC-ITR", "TRACES", "PFMS", "NSDL-PAN", "UIDAI-eKYC"]),
            ("Application & Technical Documentation", "Environment Matrix", "Dev/UAT/Prod environment mapping.", "Architect", ["CPC-ITR", "TRACES"]),
            ("Application & Technical Documentation", "Access Control Matrix (RBAC)", "User roles, profiles and permissions.", "Engineering Team", []),
            ("Application & Technical Documentation", "Data Dictionary & Data Flow Diagram", "Entity relationships and transformation rules.", "Engineering Team", ["CPC-ITR", "PFMS"]),
            ("Integration & Interdependency Landscape", "UpStream Systems", "Systems feeding data in.", "Integration Team", ["NSDL-PAN", "UIDAI-eKYC"]),
            ("Integration & Interdependency Landscape", "DownStream Systems", "Systems consuming output.", "Integration Team", ["PFMS", "Payment Gateway"]),
            ("Integration & Interdependency Landscape", "Dependency Matrix", "System X feeds Y for purpose Z.", "Integration Team", ["CPC-ITR", "TRACES"]),
            ("Operations & Support", "Monitoring & Alerts", "Infrastructure and application monitoring setup.", "Technical Support", []),
            ("Operations & Support", "Disaster Recovery / BCP Plan", "RTO/RPO and DR test schedule.", "Technical Support", ["CPC-ITR"]),
            ("Knowledge Transfer", "Knowledge Transfer Plan", "Lists KT topics, owners, and schedule.", "Transition Lead", []),
        ]
        for order, (category, document, purpose, owner, sys_names) in enumerate(transition_data):
            doc, _ = TransitionDocument.objects.get_or_create(
                document=document,
                defaults={"category": category, "purpose": purpose, "owner": owner, "order": order},
            )
            if sys_names:
                doc.systems.set([systems[n] for n in sys_names])

        # -- Sample work item history (for the Team page's Analysis view) --
        work_item_types = ["User Story", "Bug", "Task"]
        states = ["Closed", "Closed", "Closed", "Active"]
        sample_titles = [
            "Fix OTP retry race condition",
            "Add pagination to grievance list",
            "Optimize nightly reconciliation job",
            "Handle null PAN in e-KYC response",
            "Refactor refund status polling",
            "Add audit log for admin actions",
            "Improve error messages on ITR upload",
            "Cache Form 26AS lookups",
            "Fix timezone bug in due-date display",
            "Add retry queue for failed webhooks",
        ]
        for emp_name in ["Divya Menon", "Sanjay Iyer"]:
            employee = employees[emp_name]
            for i in range(10):
                months_ago = 9 - i
                closed = today.replace(day=1) - timedelta(days=months_ago * 30 - random.randint(0, 20))
                WorkItem.objects.get_or_create(
                    employee=employee,
                    external_id=f"{1000 + i}",
                    defaults={
                        "source": WorkItem.Source.MANUAL,
                        "title": sample_titles[i],
                        "work_item_type": random.choice(work_item_types),
                        "state": random.choice(states),
                        "story_points": random.choice([1, 2, 3, 5, 8]),
                        "project_label": "eSuvidha-Digital",
                        "created_date": closed - timedelta(days=random.randint(3, 14)),
                        "closed_date": closed,
                    },
                )

        self.stdout.write(self.style.SUCCESS("Seeded demo data (employees, projects, tickets, applications, transition plan)."))
        self.stdout.write(self.style.SUCCESS("Default login: admin / Admin@123 (demo only — change before any real deployment)."))
