"""Small deterministic email composer used before confirmation-gated delivery."""

from __future__ import annotations


def compose_formal_email(brief: str, contact_name: str, *, bangla: bool = False) -> tuple[str, str]:
    clean = " ".join((brief or "").strip().split())
    absence = any(token in clean.lower() for token in ("কাল", "tomorrow", "আসতে পারব না", "আসতে পারবো না", "cannot come", "can't come"))
    if bangla:
        if absence:
            return (
                "আগামীকাল অনুপস্থিত থাকার বিষয়ে",
                "সম্মানিত স্যার/ম্যাডাম,\n\nদুঃখিত, অনিবার্য কারণে আমি আগামীকাল কর্মস্থলে উপস্থিত হতে পারব না। "
                "বিষয়টি অনুগ্রহ করে বিবেচনা করবেন। প্রয়োজনীয় কোনো কাজ থাকলে আমি যথাসম্ভব সমন্বয় করার চেষ্টা করব।\n\n"
                "শুভেচ্ছান্তে",
            )
        return (
            "গুরুত্বপূর্ণ বিষয়ে অবহিতকরণ",
            f"সম্মানিত {contact_name},\n\nআপনাকে আনুষ্ঠানিকভাবে জানাতে চাই যে {clean}। "
            "বিষয়টি অনুগ্রহ করে বিবেচনা করবেন।\n\nশুভেচ্ছান্তে",
        )
    if absence:
        return (
            "Unable to Attend Tomorrow",
            "Dear Sir/Madam,\n\nI regret to inform you that, due to unavoidable circumstances, I will be unable to attend work tomorrow. "
            "Please accept my apologies for the inconvenience. I will do my best to coordinate any necessary work.\n\nKind regards,",
        )
    return (
        "Important Update",
        f"Dear {contact_name},\n\nI am writing to formally let you know that {clean}. Please take this into consideration.\n\nKind regards,",
    )
