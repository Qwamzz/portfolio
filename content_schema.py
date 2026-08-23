"""Definition of every editable collection on the site.

The admin page builds its forms from this, and the API validates against it, so
adding a field here is all it takes to make it editable.

Field types:
  text      single line
  textarea  paragraph; blank lines separate paragraphs where the page supports it
  lines     one entry per line, stored as a list
  select    fixed set of options
  url       single line, must start with http:// or https://
  file      upload stored on the persistent volume
"""

ILLUSTRATIONS = [
    "assets/img/cloud-hero.svg",
    "assets/img/devops.svg",
    "assets/img/security.svg",
    "assets/img/data.svg",
    "assets/img/education.svg",
    "assets/img/experience.svg",
    "assets/img/projects.svg",
    "assets/img/contact.svg",
]

EXPERIENCE_GROUPS = ["Cloud Engineering", "Data & AI", "Earlier Roles"]
CERT_CATEGORIES = ["Microsoft", "Cloud & Cloud Native", "Security & Standards", "Other"]

SCHEMA = {
    "profile": {
        "label": "Home - intro",
        "page": "Home",
        "single": True,
        "title_field": "name",
        "fields": [
            {"name": "name", "label": "Name", "type": "text", "required": True},
            {"name": "tagline", "label": "Tagline", "type": "text"},
            {"name": "lede", "label": "Introduction", "type": "textarea"},
        ],
    },
    "stats": {
        "label": "Home - headline numbers",
        "page": "Home",
        "title_field": "value",
        "fields": [
            {"name": "value", "label": "Number", "type": "text", "required": True},
            {"name": "label", "label": "Caption", "type": "text", "required": True},
        ],
    },
    "skills": {
        "label": "Home - what I do",
        "page": "Home",
        "title_field": "title",
        "fields": [
            {"name": "title", "label": "Heading", "type": "text", "required": True},
            {"name": "tags", "label": "Tags (one per line)", "type": "lines"},
            {"name": "bullets", "label": "Bullet points (one per line)", "type": "lines"},
            {"name": "image", "label": "Illustration", "type": "select", "options": ILLUSTRATIONS},
        ],
    },
    "education": {
        "label": "Education - degrees",
        "page": "Education",
        "title_field": "degree",
        "fields": [
            {"name": "degree", "label": "Qualification", "type": "text", "required": True},
            {"name": "school", "label": "Institution", "type": "text", "required": True},
            {"name": "period", "label": "Dates", "type": "text"},
            {"name": "badge", "label": "Badge initials", "type": "text"},
            {"name": "bullets", "label": "Details (one per line)", "type": "lines"},
        ],
    },
    "extras": {
        "label": "Education - beyond the classroom",
        "page": "Education",
        "title_field": "title",
        "fields": [
            {"name": "title", "label": "Heading", "type": "text", "required": True},
            {"name": "body", "label": "Description", "type": "textarea"},
            {"name": "link_label", "label": "Link text", "type": "text"},
            {"name": "link_url", "label": "Link address", "type": "url"},
        ],
    },
    "experience": {
        "label": "Experience - roles",
        "page": "Experience",
        "title_field": "role",
        "fields": [
            {"name": "role", "label": "Job title", "type": "text", "required": True},
            {"name": "org", "label": "Employer and location", "type": "text", "required": True},
            {"name": "period", "label": "Dates", "type": "text"},
            {"name": "group", "label": "Section", "type": "select", "options": EXPERIENCE_GROUPS},
            {"name": "bullets", "label": "Responsibilities (one per line)", "type": "lines"},
        ],
    },
    "projects": {
        "label": "Projects - selected work",
        "page": "Projects",
        "title_field": "title",
        "fields": [
            {"name": "title", "label": "Project", "type": "text", "required": True},
            {"name": "body", "label": "Description (blank line starts a new paragraph)", "type": "textarea"},
            {"name": "meta", "label": "Technology line", "type": "text"},
        ],
    },
    "repos": {
        "label": "Projects - GitHub repositories",
        "page": "Projects",
        "title_field": "name",
        "fields": [
            {"name": "name", "label": "Repository name", "type": "text", "required": True},
            {"name": "url", "label": "Repository link", "type": "url", "required": True},
            {"name": "description", "label": "Description", "type": "textarea"},
            {"name": "lang", "label": "Language or focus", "type": "text"},
        ],
    },
    "writing": {
        "label": "Projects - writing",
        "page": "Projects",
        "title_field": "title",
        "fields": [
            {"name": "title", "label": "Publication", "type": "text", "required": True},
            {"name": "body", "label": "Description", "type": "textarea"},
            {"name": "link_label", "label": "Link text", "type": "text"},
            {"name": "link_url", "label": "Link address", "type": "url"},
        ],
    },
    "certifications": {
        "label": "Certifications",
        "page": "Certifications",
        "title_field": "name",
        "fields": [
            {"name": "name", "label": "Certification", "type": "text", "required": True},
            {"name": "code", "label": "Short code", "type": "text"},
            {"name": "issuer", "label": "Issued by", "type": "text"},
            {"name": "category", "label": "Category", "type": "select", "options": CERT_CATEGORIES},
            {"name": "note", "label": "Note", "type": "text"},
            {"name": "url", "label": "Credential link", "type": "url"},
            {"name": "file", "label": "Certificate file", "type": "file"},
        ],
    },
    "recognition": {
        "label": "Certifications - community and recognition",
        "page": "Certifications",
        "title_field": "title",
        "fields": [
            {"name": "title", "label": "Heading", "type": "text", "required": True},
            {"name": "body", "label": "Description", "type": "textarea"},
        ],
    },
    "contact": {
        "label": "Contact - details",
        "page": "Contact",
        "single": True,
        "title_field": "email",
        "fields": [
            {"name": "lede", "label": "Introduction", "type": "textarea"},
            {"name": "email", "label": "Email address", "type": "text", "required": True},
            {"name": "phone", "label": "Phone number", "type": "text"},
            {"name": "phone_link", "label": "Phone link (tel:)", "type": "text"},
            {"name": "location", "label": "Location", "type": "text"},
        ],
    },
    "services": {
        "label": "Contact - what I can help with",
        "page": "Contact",
        "title_field": "title",
        "fields": [
            {"name": "title", "label": "Heading", "type": "text", "required": True},
            {"name": "body", "label": "Description", "type": "textarea"},
        ],
    },
}

# Certifications keep their own file so data already on the volume is untouched.
SEPARATE_FILES = {"certifications"}
