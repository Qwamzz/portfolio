"""Corrections to starting content that is already sitting in a live store.

The seed in data/content.seed.json is only copied into a store once, so fixing
a mistake in the seed does not reach a site that was set up before the fix.
Each correction below names the exact text that was originally seeded; it is
applied only while the stored value still matches that text. Anything edited
through /admin no longer matches and is left alone.
"""

FIELD_FIXES = [
    # Availability line reworded.
    ("profile", "profile", "availability",
     "Open to cloud and security engagements", "Open to cloud and AI engagements"),

    # Education detail that was not in the CV.
    ("education", "edu-msc", "bullets",
     ["Advanced study in software engineering, distributed systems and applied machine learning.",
      "Extending hands-on cloud and data engineering practice with formal computer science theory."],
     []),
    ("education", "edu-bsc", "bullets",
     ["Engineering fundamentals in modelling, data interpretation and quantitative analysis.",
      "Applied during national service at GNPC through basin, source rock and reservoir modelling."],
     ["Applied during national service at GNPC through basin, source rock and reservoir modelling."]),

    # Repository descriptions that promised content the repositories do not hold.
    ("repos", "repo-cloudarch", "description",
     "Reference architectures, landing zone patterns and cloud design work from migration and platform engagements.",
     "Collection repository for cloud engineering and architecture projects."),
    ("repos", "repo-azure", "description",
     "Azure platform work - architecture, infrastructure-as-code and platform automation samples drawn from day-to-day delivery.",
     "Collection repository for Microsoft Azure projects."),
    ("repos", "repo-dl", "description",
     "Neural network experiments and training runs across vision, audio and sequence models.",
     "Collection repository for deep learning projects."),
    ("repos", "repo-cv", "description",
     "Image and video work - detection, classification and image processing pipelines.",
     "Classical computer vision: image segmentation and object measurement, object detection and "
     "localisation, feature-based panorama construction, and road lane boundary detection."),
    ("repos", "repo-cv", "lang", "Computer Vision", "Computer vision"),

    # CV bullets that were left out.
    ("experience", "exp-cloudware", "bullets",
     ["Conducted cloud adoption assessments using Microsoft's Cloud Adoption Framework, guiding clients through structured migration and deployment phases.",
      "Migrated customer workloads to Azure PaaS and IaaS - on-premises servers, VMware/Hyper-V environments and web services from AWS - reducing infrastructure and operational costs.",
      "Deployed Microsoft Sentinel and advanced security solutions with data connectors, alerts, automation rules, workbooks and custom analytics rules tailored to client use cases.",
      "Designed fault-tolerant architectures across App Service, Azure Functions, Azure VMs and Azure Site Recovery for high availability and business continuity.",
      "Built and maintained CI/CD pipelines in Azure DevOps, reducing deployment times and improving integration consistency.",
      "Automated provisioning with Terraform, Bicep and PowerShell, minimising manual error and accelerating delivery.",
      "Configured Site-to-Site VPN hybrid connectivity, Azure File Sync with lifecycle policies, and IAM roles with MFA.",
      "Monitored infrastructure with Log Analytics and Azure Monitor, improving reliability and reducing downtime.",
      "Developed technical proposals, presentations and product demos that turned business requirements into cloud solutions, increasing project approval rates."],
     None),  # None = append the missing bullet, see APPENDS
    ("experience", "exp-reliance", "bullets",
     ["Implemented cloud security infrastructure and secure architectures for in-house Azure applications, improving security posture and compliance adherence.",
      "Conducted comprehensive cloud security risk assessments, identifying vulnerabilities and recommending mitigations.",
      "Deployed Microsoft Sentinel, Azure Arc and Azure Monitor to improve threat detection, monitoring and operational visibility.",
      "Defined and enforced enterprise-level cloud security controls aligned to industry standards.",
      "Configured Azure Key Vault and key management policies to strengthen data security and regulatory compliance.",
      "Implemented BCDR solutions for mission-critical workloads, ensuring data availability and minimising downtime.",
      "Automated Azure deployments with Bicep, ARM templates and Terraform.",
      "Translated high-level customer requirements into detailed technical specifications and solution designs."],
     None),
]

APPENDS = {
    ("experience", "exp-cloudware", "bullets"):
        "Used Azure DevOps for sprint planning, task assignment and progress tracking, improving team collaboration and delivery timelines.",
    ("experience", "exp-reliance", "bullets"):
        "Collaborated with QA and business analyst teams to define accurate project requirements and improve delivery timelines.",
}

# Collection order: reverse chronological within "Earlier Roles" (GNPC 2019-20 after Techbit 2019).
ORDER_FIXES = {
    "experience": (
        ["exp-cloudware", "exp-reliance", "exp-freelance", "exp-invisible", "exp-hamoye", "exp-techbit", "exp-gnpc"],
        ["exp-cloudware", "exp-reliance", "exp-freelance", "exp-invisible", "exp-hamoye", "exp-gnpc", "exp-techbit"],
    ),
}


def apply(collection, items):
    """Return items with any still-applicable corrections applied. Never mutates input."""
    items = [dict(item) for item in items]
    by_id = {item.get("id"): item for item in items}

    for name, item_id, field, old, new in FIELD_FIXES:
        if name != collection or item_id not in by_id:
            continue
        item = by_id[item_id]
        if item.get(field) != old:
            continue  # edited since it was seeded - leave it
        if new is None:
            item[field] = list(old) + [APPENDS[(name, item_id, field)]]
        else:
            item[field] = new

    if collection in ORDER_FIXES:
        old_order, new_order = ORDER_FIXES[collection]
        if [item.get("id") for item in items] == old_order:
            items = [by_id[item_id] for item_id in new_order]

    return items


# --------------------------------------------------------------------------
# One-time migrations
#
# Read-time fixes above cannot add or remove entries: an added entry would
# reappear every time it was deleted in /admin. Structural changes are applied
# once instead, written to the store and recorded in a ledger so they never run
# again. Every step still checks the stored data first and skips anything that
# has been edited since it was seeded.
# --------------------------------------------------------------------------

MIGRATIONS = [
    {
        # Updated CV, October 2026: AZ-500 replaced by SC-500, SC-100 earned,
        # MS-900 dropped, OCI AI Foundations no longer styled "Associate".
        "id": "2026-10-cv-certifications",
        "collection": "certifications",
        "steps": [
            ("update", "az-500",
             {"code": "AZ-500", "name": "Azure Security Engineer Associate"},
             {"code": "SC-500", "name": "Cloud and AI Security Engineer Associate"}),
            ("insert_after", "az-400",
             {"id": "sc-100", "code": "SC-100", "name": "Cybersecurity Architect Expert",
              "issuer": "Microsoft", "category": "Microsoft", "note": "Expert level"}),
            ("remove",
             {"id": "ms-900", "code": "MS-900", "name": "Microsoft 365 Certified: Fundamentals",
              "issuer": "Microsoft", "category": "Microsoft", "note": "Fundamentals"}),
            ("update", "oci-ai",
             {"name": "Oracle Cloud Infrastructure Certified AI Foundations Associate", "note": "Associate"},
             {"name": "Oracle Cloud Infrastructure Certified AI Foundations", "note": "Foundations"}),
        ],
    },
]


def _apply_step(items, step):
    """Apply one step to a list of entries. Returns (items, changed)."""
    kind = step[0]

    if kind == "update":
        _, item_id, expect, new = step
        for item in items:
            if item.get("id") == item_id and all(item.get(k) == v for k, v in expect.items()):
                item.update(new)
                return items, True
        return items, False

    if kind == "insert_after":
        _, anchor, entry = step
        if any(i.get("id") == entry["id"] or i.get("code") == entry.get("code") for i in items):
            return items, False  # already there, perhaps added by hand
        position = next((n + 1 for n, i in enumerate(items) if i.get("id") == anchor), len(items))
        return items[:position] + [dict(entry)] + items[position:], True

    if kind == "remove":
        _, original = step
        # Only an untouched entry is removed; one with an upload or edits stays.
        kept = [i for i in items if i != original]
        return kept, len(kept) != len(items)

    raise ValueError("Unknown migration step: %r" % (kind,))


def run_migrations(load, save, ledger_path):
    """Apply pending migrations once. load(name) / save(name, items) touch the raw store."""
    import json
    import os

    try:
        with open(ledger_path, "r", encoding="utf-8") as handle:
            done = set(json.load(handle))
    except (OSError, ValueError):
        done = set()

    lock = ledger_path + ".lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return []  # another worker is migrating right now
    applied = []
    try:
        os.close(fd)
        for migration in MIGRATIONS:
            if migration["id"] in done:
                continue
            items = load(migration["collection"])
            changed = False
            for step in migration["steps"]:
                items, step_changed = _apply_step(items, step)
                changed = changed or step_changed
            if changed:
                save(migration["collection"], items)
            done.add(migration["id"])
            applied.append(migration["id"])
        if applied:
            tmp = ledger_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(sorted(done), handle, indent=2)
            os.replace(tmp, ledger_path)
    finally:
        try:
            os.remove(lock)
        except OSError:
            pass
    return applied
