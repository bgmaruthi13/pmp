# Backlog

Future feature ideas for the eSuvidha Ops Portal — not built yet, kept here as a
working reference for a later session. Add new items below as they come up.

## Tickets should require a linked User Story

Every Task/Ticket should be associated with a "user story" before it counts as
real work — and if a ticket doesn't have one yet, there should be a way to
create one directly from the ticket, instead of having to go create it
somewhere else first.

No decision has been made yet between two approaches:

**Option A — new lightweight model (recommended default if no other input)**
- Add a small `UserStory` model to the `projects` app (`title`, `description`,
  maybe `status`).
- Add a `user_story` FK on `Task` (nullable at first, so it can be backfilled;
  a follow-up decision is whether to eventually make it required).
- On the ticket create/edit form, add a "+ Create user story" affordance for
  tickets that don't have one yet — creates and links it in one step, no
  separate page needed first.
- Self-contained. No dependency on Azure DevOps or the existing `WorkItem`
  import/sync pipeline.

**Option B — reuse the existing `WorkItem` model**
- `WorkItem` (`teams/models.py`) already represents an Azure DevOps- or
  Excel-imported user story, but today it's scoped to an `Employee`, not a
  `Project`/`Task`.
- Would need `WorkItem.employee` to become optional (or a separate link
  table) so a ticket can reference a `WorkItem` regardless of which
  employee it's synced under.
- Ties the Team section's Azure DevOps sync together with Projects' tickets
  more tightly — a bigger, more invasive change than Option A.

Pick A vs. B (or something else) before starting.
