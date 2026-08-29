import random
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from projects.models import Application, Area, Project, Task, TransitionDocument, TransitionSystem
from teams.models import DEFAULT_ROLES, Employee, EmployeeNote, Role, SupportTicket, WorkItem


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
        roles = {}
        for order, role_name in enumerate(DEFAULT_ROLES):
            role, _ = Role.objects.get_or_create(name=role_name, defaults={"order": order})
            roles[role_name] = role

        lead, _ = Employee.objects.get_or_create(
            name="Ananya Krishnan",
            defaults={
                "email": "ananya.krishnan@example.com",
                "emp_id": "EMP001",
                "designation": "Engineering Manager",
                "country": "India",
                "doj": date(2022, 1, 10),
                "rtb_efficiency": 12.5,
                "gsc_efficiency": 8.0,
                "ai_efficiency": 15.0,
            },
        )
        lead.roles.set([roles["Project Lead"]])
        sdm, _ = Employee.objects.get_or_create(
            name="Arjun Malhotra",
            defaults={
                "email": "arjun.malhotra@example.com",
                "emp_id": "EMP002",
                "designation": "Service Delivery Manager",
                "country": "India",
                "doj": date(2021, 6, 1),
            },
        )
        sdm.roles.set([roles["Service Delivery Manager"]])
        platform_lead, _ = Employee.objects.get_or_create(
            name="Vikram Nair",
            defaults={
                "email": "vikram.nair@example.com",
                "manager": lead,
                "emp_id": "EMP003",
                "designation": "Lead Software Engineer",
                "country": "India",
                "doj": date(2022, 3, 15),
            },
        )
        platform_lead.roles.set([roles["Platform Engineer Lead"]])

        # A few people intentionally span more than one role, to reflect
        # resources who work across, e.g., DevOps and Database, or
        # Platform Engineering and general development.
        employees_data = [
            (
                "Divya Menon",
                ["Platform Engineer"],
                platform_lead,
                {
                    "emp_id": "EMP004",
                    "designation": "Specialist Software Engineer",
                    "country": "India",
                    "doj": date(2022, 7, 1),
                    "line_manager": lead,
                    "rtb_efficiency": 10,
                    "gsc_efficiency": 5,
                    "ai_efficiency": 20,
                },
            ),
            (
                "Sanjay Iyer",
                ["Platform Engineer", "Developer"],
                platform_lead,
                {
                    "emp_id": "EMP005",
                    "designation": "Software Engineer",
                    "country": "Poland",
                    "doj": date(2023, 1, 16),
                    "line_manager": lead,
                },
            ),
            (
                "Rohit Deshmukh",
                ["Database Engineer"],
                lead,
                {
                    "emp_id": "EMP006",
                    "designation": "Specialist System Engineer",
                    "country": "India",
                    "doj": date(2022, 9, 1),
                },
            ),
            (
                "Priya Raghavan",
                ["DevOps / Integration"],
                lead,
                {
                    "emp_id": "EMP007",
                    "designation": "Lead Software Engineer",
                    "country": "United States",
                    "doj": date(2021, 11, 20),
                },
            ),
            (
                "Karthik Subramaniam",
                ["DevOps / Integration", "Database Engineer"],
                lead,
                {
                    "emp_id": "EMP008",
                    "designation": "Specialist Software Engineer",
                    "country": "India",
                    "doj": date(2022, 2, 14),
                    "awards": "Aug'26 - SDQ Award - SCHREMS Project & NIST Controls.",
                },
            ),
            (
                "Neha Kulkarni",
                ["DevOps / Integration", "Developer"],
                lead,
                {
                    "emp_id": "EMP009",
                    "designation": "Software Engineer",
                    "country": "Poland",
                    "doj": date(2023, 5, 8),
                },
            ),
        ]
        employees = {"Ananya Krishnan": lead, "Vikram Nair": platform_lead, "Arjun Malhotra": sdm}
        for name, role_names, manager, extra in employees_data:
            emp, _ = Employee.objects.get_or_create(
                name=name,
                defaults={
                    "manager": manager,
                    "email": f"{name.lower().replace(' ', '.')}@example.com",
                    **extra,
                },
            )
            emp.roles.set([roles[r] for r in role_names])
            employees[name] = emp

        # -- WFH exceptions / achievements / escalations (repeatable, dated logs) --
        notes_data = [
            ("Divya Menon", EmployeeNote.Category.ACHIEVEMENT, date(2025, 11, 5), "Reduced OTP failure rate by 30%.", "US-4102"),
            ("Divya Menon", EmployeeNote.Category.ACHIEVEMENT, date(2026, 3, 18), "Shipped PAN validation caching layer ahead of schedule.", "US-4310"),
            ("Rohit Deshmukh", EmployeeNote.Category.ESCALATION, date(2026, 3, 2), "P1 - Refund DB outage (resolved same day).", "INC-1187"),
            ("Rohit Deshmukh", EmployeeNote.Category.ESCALATION, date(2026, 6, 21), "P2 - Slow query alert on reconciliation batch.", ""),
            ("Priya Raghavan", EmployeeNote.Category.WFH_EXCEPTION, date(2025, 9, 1), "Approved - relocated to Pune.", ""),
            ("Priya Raghavan", EmployeeNote.Category.WFH_EXCEPTION, date(2026, 4, 14), "Approved - extended for family care, 2 weeks.", ""),
            ("Karthik Subramaniam", EmployeeNote.Category.ACHIEVEMENT, date(2026, 8, 1), "SDQ Award nomination - SCHREMS project & NIST controls.", "US-4498"),
        ]
        for name, category, note_date, description, work_item_ref in notes_data:
            EmployeeNote.objects.get_or_create(
                employee=employees[name],
                category=category,
                date=note_date,
                description=description,
                defaults={"work_item_ref": work_item_ref},
            )

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

        # -- Employee <-> Project associations (editable from the Team page) --
        for employee in employees.values():
            project_ids = set(Task.objects.filter(assignee=employee).values_list("project_id", flat=True))
            project_ids.update(Project.objects.filter(lead=employee).values_list("id", flat=True))
            if project_ids:
                employee.projects.set(project_ids)

        # -- Applications ------------------------------------------------
        applications_data = [
            {
                "name": "e-Filing Core Engine 4.0", "domain": "Tax Filing", "sensitivity": "3-high", "container": "eSuvidha-Digital",
                "procurement": "in_house", "apptype": "business_capabilities", "officer": "Priya Raghavan",
                "p_level": "P1", "backup_status": "Configured", "backup_solution": "Veeam",
                "backup_coverage_level": "Total", "rebuild_confidence": "high",
                "last_backup_date": "Daily, 02:00 IST", "last_restore_date": "12 Jun 2026",
                "last_rebuild_date": "Never required", "backup_limitations": "None known.",
                "description": "Core engine handling ITR intake, validation, and submission workflow.",
                "status": "Active",
            },
            {
                "name": "TDS-CPC Integration Gateway", "domain": "Tax Filing", "sensitivity": "3-high", "container": "eSuvidha-Digital",
                "procurement": "in_house", "apptype": "it_capabilities", "officer": "Karthik Subramaniam",
                "p_level": "P1", "backup_status": "Configured", "backup_solution": "TSM",
                "backup_coverage_level": "Partial", "rebuild_confidence": "medium",
                "last_backup_date": "Weekly, Sunday", "last_restore_date": "Never restored",
                "last_rebuild_date": "Never", "backup_limitations": "Queue state is not included in the backup window.",
                "description": "Gateway service synchronizing TDS credit data with the CPC upstream system.",
                "status": "Active",
            },
            {
                "name": "PAN Validation Service", "domain": "Identity & KYC", "sensitivity": "3-high", "container": "eSuvidha-Digital",
                "procurement": "software_package", "apptype": "business_capabilities", "officer": "Divya Menon",
                "p_level": "P2", "backup_status": "Configured", "backup_solution": "Commvault",
                "backup_coverage_level": "Total", "rebuild_confidence": "high",
                "last_backup_date": "Daily, 01:00 IST", "last_restore_date": "3 Feb 2026",
                "last_rebuild_date": "Never required", "backup_limitations": "None known.",
                "description": "Validates PAN details against the NSDL registry before submission.",
                "status": "Active",
            },
            {
                "name": "Aadhaar e-KYC Connector", "domain": "Identity & KYC", "sensitivity": "2-critical", "container": "eSuvidha-Digital",
                "procurement": "software_package", "apptype": "it_capabilities", "officer": "Sanjay Iyer",
                "p_level": "P0", "backup_status": "Configured", "backup_solution": "Veeam + offsite replica",
                "backup_coverage_level": "Total", "rebuild_confidence": "high",
                "last_backup_date": "Continuous replication", "last_restore_date": "18 Jan 2026",
                "last_rebuild_date": "Never required", "backup_limitations": "None known.",
                "description": "Connector brokering UIDAI e-KYC verification requests and responses.",
                "status": "Active",
            },
            {
                "name": "Refund Banking Interface", "domain": "Payments", "sensitivity": "2-critical", "container": "eSuvidha-Digital",
                "procurement": "in_house", "apptype": "business_capabilities", "officer": "Rohit Deshmukh",
                "p_level": "P0", "backup_status": "Configured", "backup_solution": "Veeam",
                "backup_coverage_level": "Total / Full backup + transaction log", "rebuild_confidence": "high",
                "last_backup_date": "Daily, 00:30 IST", "last_restore_date": "Not recently tested",
                "last_rebuild_date": "Never required",
                "backup_limitations": "Restore of the full transaction log can take several hours for high-volume months.",
                "description": "Interfaces with partner banks to process refund disbursement.",
                "status": "Active",
            },
            {
                "name": "Taxpayer Grievance CRM", "domain": "Grievance Management", "sensitivity": "4-medium", "container": "eSuvidha-Digital",
                "procurement": "software_package", "apptype": "business_capabilities", "officer": "Neha Kulkarni",
                "p_level": "P2", "backup_status": "Pending vendor confirmation", "backup_solution": "Still pending vendor feedback",
                "backup_coverage_level": "Still pending vendor feedback", "rebuild_confidence": "",
                "last_backup_date": "Still pending vendor feedback", "last_restore_date": "Still pending vendor feedback",
                "last_rebuild_date": "Still pending vendor feedback",
                "backup_limitations": "Awaiting confirmation of backup scope from the SaaS vendor.",
                "description": "CRM used to log, route, and track taxpayer grievance tickets.",
                "status": "Active",
            },
            {
                "name": "Form 26AS Sync Service", "domain": "Reporting & Compliance", "sensitivity": "3-high", "container": "eSuvidha-Digital",
                "procurement": "in_house", "apptype": "it_capabilities", "officer": "Priya Raghavan",
                "p_level": "P1", "backup_status": "Configured", "backup_solution": "TSM",
                "backup_coverage_level": "Total", "rebuild_confidence": "medium",
                "last_backup_date": "Daily, 03:00 IST", "last_restore_date": "Never restored",
                "last_rebuild_date": "Never",
                "backup_limitations": "Full application rebuild has not been tested end-to-end.",
                "description": "Keeps cached Form 26AS records in sync with the upstream tax credit statement service.",
                "status": "Active",
            },
            {
                "name": "OTP & Notification Gateway", "domain": "Notifications", "sensitivity": "3-high", "container": "eSuvidha-Digital",
                "procurement": "software_package", "apptype": "it_capabilities", "officer": "Karthik Subramaniam",
                "p_level": "P1", "backup_status": "Not applicable", "backup_solution": "Not applicable",
                "backup_coverage_level": "Not applicable", "rebuild_confidence": "medium",
                "last_backup_date": "Not applicable", "last_restore_date": "Not applicable",
                "last_rebuild_date": "Not applicable",
                "backup_limitations": "Stateless service; redeployed from source control rather than restored from backup.",
                "description": "Sends OTP and status notifications by SMS and email.",
                "status": "Active",
            },
        ]
        for app_data in applications_data:
            Application.objects.get_or_create(
                name=app_data["name"],
                defaults={
                    "domain": app_data["domain"],
                    "sensitivity": app_data["sensitivity"],
                    "architecture_container": app_data["container"],
                    "gsc_owner": "Vikram Nair",
                    "it_perimeter_lvl2": "eSuvidha-Digital",
                    "it_perimeter_lvl3": "All",
                    "object_type": Application.ObjectType.APPLICATION,
                    "procurement_type": app_data["procurement"],
                    "application_type": app_data["apptype"],
                    "officer": app_data["officer"],
                    "country": "India",
                    "p_level": app_data["p_level"],
                    "globalgov_lvl1": "Core Platform Governance",
                    "globalgov_lvl2": "HUB eSuvidha-Digital",
                    "backup_status": app_data["backup_status"],
                    "backup_solution": app_data["backup_solution"],
                    "backup_coverage_level": app_data["backup_coverage_level"],
                    "rebuild_confidence": app_data["rebuild_confidence"],
                    "last_backup_date": app_data["last_backup_date"],
                    "last_restore_date": app_data["last_restore_date"],
                    "last_rebuild_date": app_data["last_rebuild_date"],
                    "backup_limitations": app_data["backup_limitations"],
                    "description": app_data["description"],
                    "status": app_data["status"],
                },
            )

        # -- Link each project to the application it delivers ----------------
        project_to_application = {
            "ITR e-Filing Portal": "e-Filing Core Engine 4.0",
            "TDS Reconciliation Engine": "TDS-CPC Integration Gateway",
            "PAN-Aadhaar Linking Service": "Aadhaar e-KYC Connector",
            "Refund Processing Pipeline": "Refund Banking Interface",
            "Form 26AS Integration": "Form 26AS Sync Service",
            "Taxpayer Grievance Redressal": "Taxpayer Grievance CRM",
        }
        for project_name, application_name in project_to_application.items():
            application = Application.objects.filter(name=application_name).first()
            project = projects.get(project_name)
            if application and project and project.application_id != application.id:
                project.application = application
                project.save(update_fields=["application"])

        # -- Transition plan -----------------------------------------------
        system_names = ["CPC-ITR", "TRACES", "PFMS", "NSDL-PAN", "UIDAI-eKYC", "Payment Gateway"]
        systems = {n: TransitionSystem.objects.get_or_create(name=n)[0] for n in system_names}

        transition_data = [
            ("Introduction", "Transition Plan", "Defines scope, timelines, transition waves, roles, milestones, and acceptance criteria.", "Engineering Team", ["CPC-ITR", "TRACES", "NSDL-PAN"], True),
            ("Introduction", "Overview & Governance of Platform and Database Engineering", "Overview, team structure, and governance model for the onshore and offshore engineering teams.", "Engineering Team", [], True),
            ("Governance & Transition Management", "Stakeholder Register", "Lists all key stakeholders across every site.", "Engineering Team", ["CPC-ITR", "TRACES", "PFMS", "NSDL-PAN"], True),
            ("Governance & Transition Management", "RACI Matrix", "Responsible/Accountable/Consulted/Informed per activity.", "Engineering Team", ["CPC-ITR", "TRACES"], False),
            ("Governance & Transition Management", "Risk Register & Mitigation Plan", "Identifies risks (knowledge loss, downtime, access, etc.) with mitigations.", "Engineering Team", ["CPC-ITR"], False),
            ("Governance & Transition Management", "Communication Plan", "Defines meeting cadence, escalation path, and communication tools.", "Engineering Team", [], False),
            ("Application & Technical Documentation", "Physical & Logical Architecture Diagrams", "High-level and detailed diagrams of the application, middleware, databases, and integrations.", "Architect", ["CPC-ITR", "TRACES", "PFMS", "NSDL-PAN", "UIDAI-eKYC"], True),
            ("Application & Technical Documentation", "Infrastructure, Network Topology & Server Inventory", "Server inventory (on-prem/cloud), OS, DB, network, storage, and backup details.", "Architect", [], False),
            ("Application & Technical Documentation", "Environment Matrix", "Dev/UAT/Prod mapping across web, app, DB, middleware, and schedulers.", "Architect", ["CPC-ITR", "TRACES"], True),
            ("Application & Technical Documentation", "Component Inventory", "Web servers, app servers, DBs, middleware, and schedulers.", "Architect", [], False),
            ("Application & Technical Documentation", "Access Control Matrix (RBAC)", "User roles, profiles, and permissions.", "Engineering Team", [], False),
            ("Application & Technical Documentation", "Configuration & Customization Document", "Modules configured, custom code, extensions, reports, forms, and workflows.", "Engineering Team", [], False),
            ("Application & Technical Documentation", "Data Dictionary & Data Flow Diagram", "Entity relationships, master data sources, and transformation rules.", "Engineering Team", ["CPC-ITR", "PFMS"], True),
            ("Application & Technical Documentation", "Environment & Server List", "Dev, UAT, Prod, and DR environment details, URLs, and credentials (secured).", "Engineering Team", [], False),
            ("Application & Technical Documentation", "Application Technologies & Versions", "Programming languages & frameworks used across app, platform, load balancer, middleware, DB, and storage.", "Engineering Team", [], False),
            ("Application & Technical Documentation", "Deployment Pipelines & CI/CD Process", "Deployment pipelines and CI/CD process documentation.", "DevOps", [], False),
            ("Application & Technical Documentation", "Compliance Framework Status", "Latest status against applicable compliance/security frameworks.", "Engineering Team", [], False),
            ("Integration & Interdependency Landscape", "Country List", "Details of every country the platform operates in.", "Integration Team", [], True),
            ("Integration & Interdependency Landscape", "UpStream Systems", "Source systems feeding data in.", "Integration Team", ["NSDL-PAN", "UIDAI-eKYC"], False),
            ("Integration & Interdependency Landscape", "DownStream Systems", "Systems consuming reports and output.", "Integration Team", ["PFMS", "Payment Gateway"], False),
            ("Integration & Interdependency Landscape", "Dependency Matrix", "System X feeds Y for purpose Z.", "Integration Team", ["CPC-ITR", "TRACES"], False),
            ("Integration & Interdependency Landscape", "Integration Landscape Document", "Details of all inbound/outbound interfaces, file transfers, APIs, and protocols.", "Integration Team", [], False),
            ("Operations & Support", "Maintenance Plan", "Daily/weekly/monthly tasks, maintenance, health checks, and backups.", "Technical Support", [], False),
            ("Operations & Support", "Support Pack", "Support handbook covering escalation contacts and run-books.", "Technical Support", [], True),
            ("Operations & Support", "Monitoring & Alerts", "Infrastructure and application monitoring setup (CPU, memory, interface failures).", "Technical Support", [], True),
            ("Operations & Support", "Incident Management SOP & Classification", "Defines ticketing process, SLAs, escalation path, and ticket categorization (P1-P4).", "Technical Support", [], False),
            ("Operations & Support", "Disaster Recovery / BCP Plan", "Recovery objectives (RTO/RPO), DR procedures, and test schedule.", "Technical Support", ["CPC-ITR"], True),
            ("Operations & Support", "Change & Release Management Plan", "Details version control, release cycle, and rollback procedure.", "DevOps", [], False),
            ("Knowledge Transfer", "Knowledge Transfer (KT) Plan", "Lists KT topics, owners, and schedule of sessions.", "Transition Lead", [], True),
            ("Knowledge Transfer", "KT Session Decks & Recordings", "Materials shared during KT sessions.", "Application Owners", [], False),
            ("Knowledge Transfer", "Process Flow Documents", "Business process walkthroughs.", "Functional Lead", [], False),
            ("Knowledge Transfer", "FAQ & Known Issues Repository", "Past incidents, recurring problems, and workarounds.", "Support Lead", [], False),
            ("Knowledge Transfer", "Skill Matrix", "Skills required and current coverage per team member.", "Support Lead", [], False),
            ("Compliance & Administrative", "Audit & Compliance Checklist", "Checklist covering GDPR and other applicable regulatory/audit requirements.", "Transition Manager", [], False),
            ("Compliance & Administrative", "Latest Application Security Assessment / PenTest", "Application security assessment and vulnerability scan results.", "Transition Manager", [], False),
            ("Compliance & Administrative", "Licensing Model", "Details of the software licensing model in use.", "Transition Manager", [], False),
            ("Audit & Compliance Checklist", "Database Archiving & Retention Policies", "Data archiving and retention policy for each database.", "Transition Manager", [], False),
            ("Audit & Compliance Checklist", "Team Members with Prod Access", "List of team members with production access and the justification for each.", "Application Team", [], True),
            ("Audit & Compliance Checklist", "Developer Access Review", "Confirms developer access to production is restricted to a need-to-have basis, reviewed periodically.", "Application Team", [], False),
            ("Audit & Compliance Checklist", "Segregation of Duties (DevOps vs Dev)", "Segregation of duties between the DevOps and development teams.", "Application Team", [], False),
            ("Audit & Compliance Checklist", "Audit Log Enablement", "Confirms audit logging is enabled for key data stores.", "Application Team", [], False),
            ("Audit & Compliance Checklist", "Application Testing Strategy", "Test cases and sign-offs across all environments, and the patching strategy.", "Application Team", [], False),
            ("Audit & Compliance Checklist", "Code Quality Review", "Static code analysis and code quality gate results.", "Application Team", [], False),
            ("Audit & Compliance Checklist", "Release/Change Management Report", "Deployment report across dev/UAT/prod environments.", "Application Team", [], False),
            ("Audit & Compliance Checklist", "Change Management Policy", "Ensures development, UAT approval, and production deployment are performed by separate individuals.", "Application Team", [], False),
            ("Audit & Compliance Checklist", "Policy & Procedures Review", "Documented policy and procedures, reviewed and approved annually.", "Application Team", [], False),
            ("Audit & Compliance Checklist", "Data Masking", "Data masking approach for lower environments.", "Application Team", [], False),
            ("Audit & Compliance Checklist", "GDPR Compliance", "Confirms alignment with GDPR regulations.", "Application Team", [], False),
            ("Audit & Compliance Checklist", "Access Deactivation List", "Process to revoke a departing user's access to all dependent systems.", "Application Team", [], False),
            ("Deployment", "Patchset & Change Management Deployment Guideline", "Agreed guidelines for patch release and production deployment sign-off.", "DevOps", [], False),
            ("Risk", "Known Risks & Gaps", "Documents risks identified during the project (e.g. missing specs, incomplete reporting tooling).", "Transition Manager", [], False),
            ("Risk", "Ticketing Tool Adoption", "Status of adopting the standard ticketing solution.", "Transition Manager", [], False),
            ("Risk", "Project Management Tool Adoption", "Status of adopting the standard project management tool.", "Transition Manager", [], False),
            ("Risk", "Outdated Technology List", "List of any outdated technologies still in use.", "Transition Manager", [], False),
        ]
        for order, (category, document, purpose, owner, sys_names, available) in enumerate(transition_data):
            doc, _ = TransitionDocument.objects.get_or_create(
                document=document,
                defaults={"category": category, "purpose": purpose, "owner": owner, "order": order, "available": available},
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
        sample_descriptions = [
            "Concurrent OTP verification requests could double-count retries, occasionally locking out valid attempts.",
            "The grievance list loads all records at once; add server-side pagination to keep page loads fast as volume grows.",
            "Tune batch-window configuration and reconciliation job scheduling to fit within the nightly maintenance window.",
            "UIDAI e-KYC occasionally returns a null PAN field, which currently throws an unhandled exception.",
            "Replace the fixed-interval refund status poller with an event-driven update to reduce unnecessary API calls.",
            "Admin console actions are not currently logged; add an audit trail for compliance reporting.",
            "Generic upload failures confuse taxpayers; surface the specific validation errors returned by the parser.",
            "Form 26AS lookups hit the upstream service on every request; add a short-lived cache to reduce load.",
            "Due dates render in UTC instead of the taxpayer's local timezone on the grievance dashboard.",
            "Add configurable retry parameters (max attempts, backoff) for failed outbound webhook deliveries.",
        ]
        sample_areas = [
            "eSuvidha-Digital\\Notifications",
            "eSuvidha-Digital\\Grievance",
            "eSuvidha-Digital\\Reconciliation",
            "eSuvidha-Digital\\Integration",
            "eSuvidha-Digital\\Refunds",
            "eSuvidha-Digital\\Portal",
            "eSuvidha-Digital\\Portal",
            "eSuvidha-Digital\\Reconciliation",
            "eSuvidha-Digital\\Grievance",
            "eSuvidha-Digital\\Integration",
        ]
        sample_tags = ["backend", "customer-impact", "regression", "performance", "security", "ui"]
        for emp_name in ["Divya Menon", "Sanjay Iyer"]:
            employee = employees[emp_name]
            for i in range(10):
                months_ago = 9 - i
                closed = today.replace(day=1) - timedelta(days=months_ago * 30 - random.randint(0, 20))
                is_open = i == 9
                WorkItem.objects.get_or_create(
                    employee=employee,
                    external_id=f"{1000 + i}",
                    defaults={
                        "source": WorkItem.Source.EXCEL,
                        "title": sample_titles[i],
                        "description": sample_descriptions[i],
                        "work_item_type": random.choice(work_item_types),
                        "state": "Active" if is_open else random.choice(states),
                        "story_points": random.choice([1, 2, 3, 5, 8]),
                        "project_label": "eSuvidha-Digital",
                        "area_path": sample_areas[i],
                        "priority": random.choice([1, 2, 3, 4]),
                        "tags": ", ".join(random.sample(sample_tags, k=random.choice([1, 2]))),
                        "created_date": closed - timedelta(days=random.randint(3, 14)),
                        "closed_date": None if is_open else closed,
                    },
                )

        # -- Sample support ticket history (for the Team page's Support view) --
        ticket_types = ["Incident", "Service Request", "Bug"]
        ticket_states = ["Resolved", "Resolved", "Resolved", "In Progress"]
        support_titles = [
            "Taxpayer unable to download Form 16",
            "Payment gateway timeout on refund page",
            "Reset access for locked officer account",
            "TRACES report export stuck at 90%",
            "Grievance status not updating after closure",
            "SMS OTP delayed for e-KYC verification",
            "Duplicate challan entries in reconciliation",
            "Portal login fails after password change",
            "Bulk upload template rejected as invalid",
            "Dashboard widget showing stale counts",
        ]
        support_descriptions = [
            "Taxpayer reports the Form 16 PDF download link returns a blank page for AY 2024-25 records.",
            "Refund status page times out intermittently when the payment gateway is under high load.",
            "Field officer account locked after repeated failed logins; needs manual unlock and password reset.",
            "TRACES report export progress bar freezes at 90% for exports over 5,000 rows.",
            "Grievance ticket marked resolved by the agent but the taxpayer-facing status still shows pending.",
            "e-KYC OTP delivery is delayed by several minutes during peak evening hours, causing session timeouts.",
            "Nightly reconciliation shows duplicate challan entries when a payment is retried after a gateway error.",
            "Users are unable to log in immediately after a password reset; error clears after roughly 15 minutes.",
            "Bulk upload rejects a correctly formatted CSV template, citing a column mismatch that isn't present.",
            "Admin dashboard widgets show counts from the previous day instead of refreshing on page load.",
        ]
        support_components = [
            "eSuvidha-Digital\\Documents",
            "eSuvidha-Digital\\Payments",
            "eSuvidha-Digital\\AccessControl",
            "eSuvidha-Digital\\Reporting",
            "eSuvidha-Digital\\Grievance",
            "eSuvidha-Digital\\Notifications",
            "eSuvidha-Digital\\Reconciliation",
            "eSuvidha-Digital\\AccessControl",
            "eSuvidha-Digital\\Integration",
            "eSuvidha-Digital\\Reporting",
        ]
        support_tags = ["taxpayer-facing", "peak-hours", "data-quality", "third-party", "auth", "reporting"]
        open_ages = {7: 4, 8: 12, 9: 35}
        for emp_name in ["Divya Menon", "Sanjay Iyer"]:
            employee = employees[emp_name]
            for i in range(10):
                months_ago = 9 - i
                closed = today.replace(day=1) - timedelta(days=months_ago * 30 - random.randint(0, 20))
                is_open = i in open_ages
                created = today - timedelta(days=open_ages[i]) if is_open else closed - timedelta(days=random.randint(1, 5))
                SupportTicket.objects.get_or_create(
                    employee=employee,
                    external_id=f"{2000 + i}",
                    defaults={
                        "source": SupportTicket.Source.EXCEL,
                        "title": support_titles[i],
                        "description": support_descriptions[i],
                        "work_item_type": random.choice(ticket_types),
                        "state": "In Progress" if is_open else random.choice(ticket_states),
                        "story_points": random.choice([1, 2, 3, 5]),
                        "project_label": "eSuvidha-Digital",
                        "area_path": support_components[i],
                        "priority": random.choice([1, 2, 3, 4]),
                        "tags": ", ".join(random.sample(support_tags, k=random.choice([1, 2]))),
                        "created_date": created,
                        "closed_date": None if is_open else closed,
                    },
                )

        self.stdout.write(self.style.SUCCESS("Seeded demo data (employees, projects, tickets, applications, transition plan)."))
        self.stdout.write(self.style.SUCCESS("Default login: admin / Admin@123 (demo only — change before any real deployment)."))
