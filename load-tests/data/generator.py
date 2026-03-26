"""
Kaasb Load Test — Iraqi Market Test Data Generator
Generates realistic users, jobs, messages, and payment data
for the Iraqi freelancing market.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Any

# ── Iraqi names ────────────────────────────────────────────────────────────────
ARABIC_FIRST_NAMES_MALE = [
    "محمد", "علي", "أحمد", "عمر", "حسن", "حسين", "يوسف", "إبراهيم",
    "عبدالله", "خالد", "سامي", "كريم", "طارق", "زياد", "ماجد",
    "فهد", "وليد", "باسم", "هيثم", "لؤي",
]
ARABIC_FIRST_NAMES_FEMALE = [
    "فاطمة", "زينب", "مريم", "نور", "هند", "رنا", "سارة", "ليلى",
    "أميرة", "هبة", "دينا", "ريم", "غادة", "وفاء", "إيمان",
    "رهف", "سلمى", "لارا", "شيماء", "دلال",
]
ARABIC_LAST_NAMES = [
    "الحسني", "العراقي", "البغدادي", "الموصلي", "البصري",
    "الكريمي", "الجبوري", "التميمي", "الشمري", "العبيدي",
    "الربيعي", "الزبيدي", "الدليمي", "السامرائي", "الكرخي",
]
LATIN_FIRST_NAMES = [
    "Ahmed", "Ali", "Mohammed", "Omar", "Hassan", "Yousuf", "Ibrahim",
    "Khalid", "Sami", "Karim", "Fatima", "Zaynab", "Maryam", "Noor",
    "Sarah", "Hind", "Rana", "Layla", "Amira", "Dina",
]
LATIN_LAST_NAMES = [
    "Al-Hussaini", "Al-Iraqi", "Al-Baghdadi", "Al-Mosuli", "Al-Basri",
    "Al-Karimi", "Al-Jubouri", "Al-Tamimi", "Al-Shamri", "Al-Obeidi",
]

# ── Iraqi cities ───────────────────────────────────────────────────────────────
IRAQI_CITIES = [
    "Baghdad", "Basra", "Erbil", "Mosul", "Najaf",
    "Karbala", "Kirkuk", "Sulaymaniyah", "Nasiriyah", "Amarah",
    "Hillah", "Diwaniyah", "Samawah", "Ramadi", "Tikrit",
]

# ── Iraqi phone numbers ────────────────────────────────────────────────────────
IRAQI_PHONE_PREFIXES = [
    "07901", "07902", "07903", "07904",  # Zain Iraq
    "07800", "07801", "07802",           # Asiacell
    "07700", "07701", "07702",           # Korek
]

# ── Freelancing skills (tech-focused, common in Iraqi market) ──────────────────
SKILLS_POOL = [
    "Python", "JavaScript", "React", "Node.js", "Django", "FastAPI",
    "Vue.js", "Next.js", "TypeScript", "PostgreSQL", "MySQL", "MongoDB",
    "Docker", "AWS", "Linux", "Git", "REST API", "GraphQL",
    "UI/UX Design", "Figma", "Adobe XD", "Photoshop", "Illustrator",
    "Mobile Development", "Flutter", "React Native", "iOS", "Android",
    "Arabic Translation", "English-Arabic", "Content Writing",
    "SEO", "Digital Marketing", "Social Media",
    "Video Editing", "Motion Graphics", "After Effects",
    "Data Analysis", "Excel", "Power BI", "Tableau",
    "Cybersecurity", "Network Administration", "DevOps",
]

# ── Job categories ─────────────────────────────────────────────────────────────
JOB_CATEGORIES = [
    "Web Development", "Mobile Development", "UI/UX Design",
    "Graphic Design", "Content Writing", "Translation",
    "Digital Marketing", "Data Analysis", "Video Production",
    "Cybersecurity", "DevOps & Cloud", "Database Administration",
]

# ── Job titles by category ─────────────────────────────────────────────────────
JOB_TITLES = {
    "Web Development": [
        "Build a React e-commerce website",
        "Develop FastAPI backend for mobile app",
        "Create Next.js landing page with Arabic RTL support",
        "Build RESTful API with PostgreSQL integration",
        "Fix bugs in existing Django application",
        "Integrate payment gateway (Qi Card / Stripe)",
        "Build admin dashboard with charts and analytics",
        "Develop real-time chat using WebSockets",
    ],
    "Mobile Development": [
        "Build Flutter app for food delivery in Baghdad",
        "Develop React Native app with Arabic UI",
        "Create iOS app for local marketplace",
        "Build Android app for ride-sharing service",
        "Add push notifications to existing mobile app",
    ],
    "UI/UX Design": [
        "Design Arabic-first mobile app UI in Figma",
        "Create responsive web design mockups",
        "Redesign existing website for better UX",
        "Design dashboard for analytics platform",
        "Create brand identity and style guide",
    ],
    "Graphic Design": [
        "Design logo for Iraqi startup",
        "Create social media graphics package",
        "Design brochure for local business",
        "Create infographics for data visualization",
    ],
    "Content Writing": [
        "Write Arabic blog posts about technology",
        "Create product descriptions in Arabic",
        "Write technical documentation in English",
        "Create marketing copy for Iraqi audience",
    ],
    "Translation": [
        "Translate technical documents Arabic to English",
        "Localize mobile app strings to Arabic",
        "Translate legal documents English to Arabic",
    ],
    "Digital Marketing": [
        "Manage social media accounts (Arabic content)",
        "Run Google Ads campaign for local business",
        "SEO optimization for Arabic website",
        "Create email marketing campaign",
    ],
    "Data Analysis": [
        "Analyze sales data and create Excel reports",
        "Build Power BI dashboard for business metrics",
        "Python data analysis and visualization",
        "Create automated reporting system",
    ],
}

# ── IQD price ranges (realistic for Iraqi market) ─────────────────────────────
BUDGET_RANGES = {
    "micro":   (25_000,   100_000),    # ~$19–77 USD
    "small":   (100_000,  500_000),    # ~$77–385 USD
    "medium":  (500_000,  2_000_000),  # ~$385–1,538 USD
    "large":   (2_000_000, 8_000_000), # ~$1,538–6,153 USD
}

HOURLY_RATES_IQD = {
    "entry":        (15_000,  35_000),   # ~$11.5–27/hr
    "intermediate": (35_000,  80_000),   # ~$27–61/hr
    "expert":       (80_000,  200_000),  # ~$61–154/hr
}

# ── Message templates ──────────────────────────────────────────────────────────
MESSAGE_TEMPLATES = [
    "مرحباً، أنا مهتم بهذا المشروع. هل يمكنك إرسال المزيد من التفاصيل؟",
    "شكراً لاهتمامك. سأرسل لك عرضاً تفصيلياً قريباً.",
    "هل لديك خبرة سابقة في مشاريع مماثلة؟",
    "نعم، لدي خبرة 3 سنوات في هذا المجال. يمكنك مراجعة ملفي الشخصي.",
    "متى يمكنك البدء؟ المشروع عاجل.",
    "يمكنني البدء غداً. ما هي المواصفات التقنية المطلوبة؟",
    "هل الدفع عبر Qi Card أم Stripe؟",
    "نفضل الدفع عبر Qi Card بالدينار العراقي.",
    "تم استلام الملفات. سأبدأ العمل الآن.",
    "لدي بعض الأسئلة حول المشروع قبل البدء.",
    "Hi, I'm interested in this project. Can you share more details?",
    "I can complete this within the specified timeline.",
    "Please check my portfolio for similar work.",
    "I'll send you the first deliverable by end of week.",
    "Could you clarify the requirements for milestone 2?",
]


class IraqiDataGenerator:
    """Generates realistic Iraqi market test data."""

    def __init__(self, seed: int | None = None):
        if seed is not None:
            random.seed(seed)
        self._counter = 0

    def _next_id(self) -> int:
        self._counter += 1
        return self._counter

    # ── Users ──────────────────────────────────────────────────────────────────

    def user(self, role: str = "freelancer", index: int | None = None) -> dict[str, Any]:
        """Generate a realistic Iraqi user."""
        suffix = index if index is not None else self._next_id()
        gender = random.choice(["male", "female"])

        if gender == "male":
            first_name = random.choice(ARABIC_FIRST_NAMES_MALE)
        else:
            first_name = random.choice(ARABIC_FIRST_NAMES_FEMALE)
        last_name = random.choice(ARABIC_LAST_NAMES)

        # Use latin transliteration for login credentials
        latin_first = random.choice(LATIN_FIRST_NAMES)
        latin_last = random.choice(LATIN_LAST_NAMES).replace("-", "").lower()
        username = f"{latin_first.lower()}{latin_last}{suffix}"

        city = random.choice(IRAQI_CITIES)
        skills = random.sample(SKILLS_POOL, k=random.randint(3, 7))

        return {
            "email":      f"test_{username}_{suffix}@loadtest.kaasb.com",
            "username":   username[:30],
            "password":   "TestPass123!@#",
            "first_name": first_name,
            "last_name":  last_name,
            "primary_role": role,
            # Profile data (used in PUT /users/profile)
            "title":      f"{random.choice(skills)} Developer" if role == "freelancer" else "Business Owner",
            "bio":        f"مطور متخصص في {skills[0]} و {skills[1]} مع خبرة {random.randint(1,8)} سنوات. أقيم في {city}.",
            "city":       city,
            "country":    "Iraq",
            "skills":     skills,
            "hourly_rate": random.randint(*HOURLY_RATES_IQD[random.choice(["entry", "intermediate", "expert"])]),
            "experience_level": random.choice(["entry", "intermediate", "expert"]),
            "phone":      f"+964{random.choice(IRAQI_PHONE_PREFIXES)}{random.randint(10000, 99999)}",
        }

    def client_user(self, index: int | None = None) -> dict[str, Any]:
        return self.user(role="client", index=index)

    def freelancer_user(self, index: int | None = None) -> dict[str, Any]:
        return self.user(role="freelancer", index=index)

    # ── Jobs ───────────────────────────────────────────────────────────────────

    def job(self, job_type: str | None = None) -> dict[str, Any]:
        """Generate a realistic job posting."""
        category = random.choice(JOB_CATEGORIES)
        titles = JOB_TITLES.get(category, JOB_TITLES["Web Development"])
        title = random.choice(titles)
        budget_tier = random.choice(["micro", "small", "medium", "large"])
        b_min, b_max = BUDGET_RANGES[budget_tier]
        budget = random.randint(b_min, b_max)

        if job_type is None:
            job_type = random.choice(["fixed", "hourly"])

        skills = random.sample(SKILLS_POOL, k=random.randint(2, 5))
        experience = random.choice(["entry", "intermediate", "expert"])
        duration = random.choice([
            "less_than_1_week", "1_to_4_weeks", "1_to_3_months", "3_to_6_months", "more_than_6_months",
        ])

        base = {
            "title":            title,
            "description":      self._job_description(title, skills, budget),
            "category":         category,
            "job_type":         job_type,
            "skills_required":  skills,
            "experience_level": experience,
            "expected_duration": duration,
            "location":         random.choice(["remote", "baghdad", "iraq"]),
        }
        if job_type == "fixed":
            base["fixed_price"] = budget
        else:
            b2 = random.randint(b_min, b_max)
            base["budget_min"] = min(budget, b2)
            base["budget_max"] = max(budget, b2)
        return base

    def _job_description(self, title: str, skills: list, budget: int) -> str:
        templates = [
            f"نبحث عن محترف متخصص في {skills[0]} لتنفيذ مشروع: {title}.\n\n"
            f"المتطلبات:\n- خبرة في {', '.join(skills[:3])}\n"
            f"- التسليم خلال الوقت المحدد\n"
            f"- التواصل الجيد باللغة العربية أو الإنجليزية\n\n"
            f"الميزانية: {budget:,} دينار عراقي",

            f"We are looking for a skilled developer to work on: {title}.\n\n"
            f"Requirements:\n- Proficiency in {', '.join(skills[:3])}\n"
            f"- Strong portfolio of similar projects\n"
            f"- Available for regular communication\n\n"
            f"Budget: {budget:,} IQD",
        ]
        return random.choice(templates)

    # ── Proposals ─────────────────────────────────────────────────────────────

    def proposal(self, job: dict[str, Any]) -> dict[str, Any]:
        """Generate a realistic proposal for a job."""
        job_type = job.get("job_type", "fixed")
        duration = random.choice([
            "less_than_1_week", "1_to_4_weeks", "1_to_3_months",
        ])

        if job_type == "fixed":
            original = job.get("fixed_price", 500_000)
            bid = int(original * random.uniform(0.7, 1.2))
        else:
            b_min = job.get("budget_min", 100_000)
            b_max = job.get("budget_max", 500_000)
            mid = (b_min + b_max) / 2
            bid = int(mid * random.uniform(0.8, 1.15))

        return {
            "cover_letter": self._cover_letter(job),
            "bid_amount":   bid,
            "duration":     duration,
            "milestones":   self._proposal_milestones(bid),
        }

    def _cover_letter(self, job: dict) -> str:
        templates = [
            f"مرحباً، أنا مهتم بمشروعك '{job.get('title', '')}'. "
            f"لدي خبرة واسعة في هذا المجال وأستطيع تسليم المشروع في الوقت المحدد. "
            f"يمكنك مراجعة ملفي الشخصي لمشاهدة أعمالي السابقة.",

            f"Hello, I'm very interested in your project. "
            f"I have extensive experience with similar work and can deliver high quality results. "
            f"I'm available to start immediately and maintain regular communication throughout.",
        ]
        return random.choice(templates)

    def _proposal_milestones(self, total: int) -> list:
        num = random.choice([1, 2, 3])
        milestones = []
        remaining = total
        for i in range(num):
            if i == num - 1:
                amount = remaining
            else:
                amount = int(total * random.uniform(0.2, 0.6))
                remaining -= amount
            milestones.append({
                "title":       f"Milestone {i + 1}",
                "description": f"Deliverable {i + 1} of {num}",
                "amount":      max(10_000, amount),
            })
        return milestones

    # ── Messages ───────────────────────────────────────────────────────────────

    def message(self) -> dict[str, Any]:
        return {"content": random.choice(MESSAGE_TEMPLATES)}

    # ── Search queries ─────────────────────────────────────────────────────────

    def job_search_query(self) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if random.random() < 0.4:
            params["q"] = random.choice([
                "Python developer", "React", "Arabic translation",
                "mobile app", "UI design", "مطور", "تصميم", "ترجمة",
            ])
        if random.random() < 0.3:
            params["category"] = random.choice(JOB_CATEGORIES)
        if random.random() < 0.4:
            params["job_type"] = random.choice(["fixed", "hourly"])
        if random.random() < 0.3:
            params["experience_level"] = random.choice(["entry", "intermediate", "expert"])
        if random.random() < 0.2:
            b_min, b_max = BUDGET_RANGES[random.choice(["micro", "small", "medium"])]
            params["budget_min"] = b_min
            params["budget_max"] = b_max
        params["page"] = random.randint(1, 5)
        params["page_size"] = random.choice([10, 20])
        return params

    def freelancer_search_query(self) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if random.random() < 0.5:
            params["q"] = random.choice([
                "Python", "React", "Flutter", "UI designer",
                "مطور", "مصمم", "مترجم",
            ])
        if random.random() < 0.3:
            skill = random.choice(SKILLS_POOL)
            params["skills"] = skill
        if random.random() < 0.3:
            params["experience_level"] = random.choice(["entry", "intermediate", "expert"])
        if random.random() < 0.2:
            r_min, r_max = HOURLY_RATES_IQD[random.choice(["entry", "intermediate"])]
            params["min_rate"] = r_min
            params["max_rate"] = r_max
        params["page"] = random.randint(1, 3)
        return params

    # ── Batch generation ───────────────────────────────────────────────────────

    def bulk_users(self, count: int, role: str = "freelancer") -> list[dict]:
        return [self.user(role=role, index=i) for i in range(count)]

    def bulk_jobs(self, count: int) -> list[dict]:
        return [self.job() for _ in range(count)]


# Singleton instance
gen = IraqiDataGenerator()


if __name__ == "__main__":
    import json

    g = IraqiDataGenerator(seed=42)
    print("=== Sample Client ===")
    print(json.dumps(g.client_user(1), ensure_ascii=False, indent=2))
    print("\n=== Sample Freelancer ===")
    print(json.dumps(g.freelancer_user(1), ensure_ascii=False, indent=2))
    print("\n=== Sample Job ===")
    j = g.job()
    print(json.dumps(j, ensure_ascii=False, indent=2))
    print("\n=== Sample Proposal ===")
    print(json.dumps(g.proposal(j), ensure_ascii=False, indent=2))
    print("\n=== Sample Job Search ===")
    print(json.dumps(g.job_search_query(), ensure_ascii=False, indent=2))
