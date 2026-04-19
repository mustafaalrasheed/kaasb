"""
Kaasb Platform - Seed Gig Categories
Run: python -m scripts.seed_categories
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.core.database import async_session as async_session_factory
from app.models.gig import Category, Subcategory


CATEGORIES = [
    {
        "name_en": "Programming & Tech",
        "name_ar": "البرمجة والتقنية",
        "slug": "programming-tech",
        "icon": "💻",
        "subcategories": [
            {"name_en": "Web Development", "name_ar": "تطوير المواقع"},
            {"name_en": "Mobile Apps", "name_ar": "تطبيقات الجوال"},
            {"name_en": "Backend Development", "name_ar": "تطوير الخوادم"},
            {"name_en": "WordPress", "name_ar": "ووردبريس"},
            {"name_en": "AI & Machine Learning", "name_ar": "الذكاء الاصطناعي"},
            {"name_en": "Database", "name_ar": "قواعد البيانات"},
            {"name_en": "DevOps & Cloud", "name_ar": "الحوسبة السحابية"},
            {"name_en": "Cybersecurity", "name_ar": "الأمن السيبراني"},
        ],
    },
    {
        "name_en": "Design & Creative",
        "name_ar": "التصميم والإبداع",
        "slug": "design-creative",
        "icon": "🎨",
        "subcategories": [
            {"name_en": "Logo Design", "name_ar": "تصميم الشعارات"},
            {"name_en": "UI/UX Design", "name_ar": "تصميم واجهات المستخدم"},
            {"name_en": "Social Media Graphics", "name_ar": "تصميم السوشيال ميديا"},
            {"name_en": "Video Editing", "name_ar": "مونتاج الفيديو"},
            {"name_en": "Motion Graphics", "name_ar": "الجرافيك المتحرك"},
            {"name_en": "Illustration", "name_ar": "الرسم والتوضيح"},
            {"name_en": "Brand Identity", "name_ar": "الهوية البصرية"},
            {"name_en": "Photography", "name_ar": "التصوير الفوتوغرافي"},
        ],
    },
    {
        "name_en": "Writing & Translation",
        "name_ar": "الكتابة والترجمة",
        "slug": "writing-translation",
        "icon": "✍️",
        "subcategories": [
            {"name_en": "Content Writing", "name_ar": "كتابة المحتوى"},
            {"name_en": "Copywriting", "name_ar": "كتابة الإعلانات"},
            {"name_en": "Arabic-English Translation", "name_ar": "ترجمة عربي-إنجليزي"},
            {"name_en": "Proofreading", "name_ar": "التدقيق اللغوي"},
            {"name_en": "Technical Writing", "name_ar": "الكتابة التقنية"},
            {"name_en": "Blog Writing", "name_ar": "كتابة المدونات"},
            {"name_en": "CV Writing", "name_ar": "كتابة السيرة الذاتية"},
        ],
    },
    {
        "name_en": "Digital Marketing",
        "name_ar": "التسويق الرقمي",
        "slug": "digital-marketing",
        "icon": "📊",
        "subcategories": [
            {"name_en": "Social Media Management", "name_ar": "إدارة السوشيال ميديا"},
            {"name_en": "SEO", "name_ar": "تحسين محركات البحث"},
            {"name_en": "Google Ads", "name_ar": "إعلانات جوجل"},
            {"name_en": "Facebook & Instagram Ads", "name_ar": "إعلانات فيسبوك وانستغرام"},
            {"name_en": "Email Marketing", "name_ar": "التسويق بالبريد الإلكتروني"},
            {"name_en": "Influencer Marketing", "name_ar": "التسويق بالمؤثرين"},
            {"name_en": "Market Research", "name_ar": "أبحاث السوق"},
        ],
    },
    {
        "name_en": "Business",
        "name_ar": "الأعمال",
        "slug": "business",
        "icon": "💼",
        "subcategories": [
            {"name_en": "Virtual Assistant", "name_ar": "مساعد افتراضي"},
            {"name_en": "Data Entry", "name_ar": "إدخال البيانات"},
            {"name_en": "Business Plans", "name_ar": "خطط العمل"},
            {"name_en": "Financial Consulting", "name_ar": "الاستشارات المالية"},
            {"name_en": "Legal Consulting", "name_ar": "الاستشارات القانونية"},
            {"name_en": "HR & Recruiting", "name_ar": "الموارد البشرية"},
            {"name_en": "Project Management", "name_ar": "إدارة المشاريع"},
        ],
    },
    {
        "name_en": "Education & Training",
        "name_ar": "التعليم والتدريب",
        "slug": "education-training",
        "icon": "📚",
        "subcategories": [
            {"name_en": "Online Tutoring", "name_ar": "التدريس الخصوصي"},
            {"name_en": "Arabic Language", "name_ar": "اللغة العربية"},
            {"name_en": "English Language", "name_ar": "اللغة الإنجليزية"},
            {"name_en": "Programming Courses", "name_ar": "دورات البرمجة"},
            {"name_en": "Course Creation", "name_ar": "إنشاء الدورات"},
            {"name_en": "Math & Science", "name_ar": "الرياضيات والعلوم"},
        ],
    },
    {
        "name_en": "Engineering & Architecture",
        "name_ar": "الهندسة والعمارة",
        "slug": "engineering-architecture",
        "icon": "🏗️",
        "subcategories": [
            {"name_en": "Civil Engineering", "name_ar": "الهندسة المدنية"},
            {"name_en": "Interior Design", "name_ar": "التصميم الداخلي"},
            {"name_en": "3D Modeling", "name_ar": "النمذجة ثلاثية الأبعاد"},
            {"name_en": "AutoCAD", "name_ar": "أوتوكاد"},
            {"name_en": "Electrical Engineering", "name_ar": "الهندسة الكهربائية"},
            {"name_en": "Architecture Design", "name_ar": "التصميم المعماري"},
        ],
    },
    {
        "name_en": "Audio & Music",
        "name_ar": "الصوت والموسيقى",
        "slug": "audio-music",
        "icon": "🎵",
        "subcategories": [
            {"name_en": "Voice Over", "name_ar": "التعليق الصوتي"},
            {"name_en": "Music Production", "name_ar": "إنتاج الموسيقى"},
            {"name_en": "Podcast Editing", "name_ar": "تحرير البودكاست"},
            {"name_en": "Audio Transcription", "name_ar": "النسخ الصوتي"},
            {"name_en": "Jingles & Ads", "name_ar": "الجينغل والإعلانات"},
        ],
    },
]


async def seed_categories() -> None:
    async with async_session_factory() as db:
        created = 0
        skipped = 0

        for cat_data in CATEGORIES:
            # Check if category already exists
            result = await db.execute(
                select(Category).where(Category.slug == cat_data["slug"])
            )
            cat = result.scalar_one_or_none()

            if not cat:
                cat = Category(
                    name_en=cat_data["name_en"],
                    name_ar=cat_data["name_ar"],
                    slug=cat_data["slug"],
                    icon=cat_data.get("icon"),
                )
                db.add(cat)
                await db.flush()
                created += 1
                print(f"  ✅ Created: {cat_data['name_en']}")
            else:
                skipped += 1
                print(f"  ⏭  Exists:  {cat_data['name_en']}")

            # Add subcategories
            for sub_data in cat_data.get("subcategories", []):
                sub_slug = cat_data["slug"] + "-" + sub_data["name_en"].lower().replace(" ", "-").replace("/", "-").replace("&", "and")
                sub_result = await db.execute(
                    select(Subcategory).where(Subcategory.slug == sub_slug)
                )
                if not sub_result.scalar_one_or_none():
                    sub = Subcategory(
                        category_id=cat.id,
                        name_en=sub_data["name_en"],
                        name_ar=sub_data["name_ar"],
                        slug=sub_slug,
                    )
                    db.add(sub)

        await db.commit()
        print(f"\n✅ Done — {created} categories created, {skipped} already existed.")


if __name__ == "__main__":
    print("Seeding gig categories...")
    asyncio.run(seed_categories())
