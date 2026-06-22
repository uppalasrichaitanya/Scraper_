"""
crawler/celery_app.py — PHASE E ADDITIONS
==========================================
This file shows ONLY the changes needed for Phase E.
Merge these additions into your existing celery_app.py.

Changes:
  1. Add alert_tasks, health_tasks, lifecycle_tasks to `include` list.
  2. Replace existing health-check beat entry.
  3. Replace existing cleanup-stale-jobs beat entry.
  4. Add daily + weekly alert dispatch entries.

All times are in IST (UTC+5:30), converted to UTC for Celery Beat.
IST 08:00 = UTC 02:30
IST 02:00 = UTC 20:30 (previous day)
"""

# ── 1. ADD TO `include` LIST ──────────────────────────────────────── #
#
# Find your existing `app = Celery(...)` call and update its include= :
#
# include=[
#     "crawler.tasks.crawl_tasks",
#     "crawler.tasks.search_tasks",
#     "crawler.tasks.alert_tasks",    # ← ADD
#     "crawler.tasks.health_tasks",   # ← ADD
#     "crawler.tasks.lifecycle_tasks", # ← ADD
# ]


# ── 2. BEAT SCHEDULE — REPLACE & ADD ─────────────────────────────── #
#
# In your app.conf.beat_schedule dict, make these changes:

BEAT_SCHEDULE_ADDITIONS = {
    # ── Replace "health-check-all-sources" ──
    "adapter-health-check": {
        "task": "health_tasks.check_adapter_health",
        "schedule": 3600,  # every 60 minutes
        "options": {"queue": "default"},
    },

    # ── Replace "cleanup-stale-jobs" ──
    "stale-job-lifecycle": {
        "task": "lifecycle_tasks.mark_stale_jobs",
        # IST 02:00 = UTC 20:30 (runs just after midnight IST)
        "schedule": {"type": "crontab", "hour": "20", "minute": "30"},
        "options": {"queue": "default"},
    },

    # ── New: daily alert dispatch at 08:00 IST = 02:30 UTC ──
    "dispatch-daily-alerts": {
        "task": "alert_tasks.dispatch_alerts",
        "schedule": {"type": "crontab", "hour": "2", "minute": "30"},
        "args": ("daily",),
        "options": {"queue": "default"},
    },

    # ── New: weekly alert dispatch, Monday 08:00 IST = Mon 02:30 UTC ──
    "dispatch-weekly-alerts": {
        "task": "alert_tasks.dispatch_alerts",
        "schedule": {
            "type": "crontab",
            "day_of_week": "1",  # Monday
            "hour": "2",
            "minute": "30",
        },
        "args": ("weekly",),
        "options": {"queue": "default"},
    },
}

# ─────────────────────────────────────────────────────────────────── #
# FULL EXAMPLE of what your beat_schedule should look like after merge:
# (Only showing structure — keep your existing naukri/remoteok/wwr entries)
# ─────────────────────────────────────────────────────────────────── #
#
# app.conf.beat_schedule = {
#     # === Crawlers ===
#     "naukri-crawl": {
#         "task": "crawl_tasks.run_adapter",
#         "schedule": {"type": "crontab", "hour": "*/4"},
#         "args": ("naukri",),
#     },
#     "remoteok-crawl": { ... },
#     "wwr-crawl": { ... },
#
#     # === Search sync ===
#     # (your existing search tasks)
#
#     # === Health & Lifecycle (Phase E — replace existing stubs) ===
#     "adapter-health-check": {
#         "task": "health_tasks.check_adapter_health",
#         "schedule": 3600,
#     },
#     "stale-job-lifecycle": {
#         "task": "lifecycle_tasks.mark_stale_jobs",
#         "schedule": crontab(hour=20, minute=30),
#     },
#
#     # === Alerts (Phase E — new) ===
#     "dispatch-daily-alerts": {
#         "task": "alert_tasks.dispatch_alerts",
#         "schedule": crontab(hour=2, minute=30),
#         "args": ("daily",),
#     },
#     "dispatch-weekly-alerts": {
#         "task": "alert_tasks.dispatch_alerts",
#         "schedule": crontab(hour=2, minute=30, day_of_week=1),
#         "args": ("weekly",),
#     },
# }
