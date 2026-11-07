"""Central NLU pattern groups for current assistant intents."""

from __future__ import annotations

import re

GREETING_HINTS = {"hello", "hi", "hey", "assalamu alaikum", "salam", "salaam"}
CASUAL_HINTS = {"how are you", "ki koro", "kemon aso", "ki obostha", "ami tension e achi", "কেমন আছো", "কেমন আছেন"}
IDENTITY_HINTS = {"tomar nam ki", "tumi ke", "apni ke", "who are you", "what is your name"}
PROFILE_HINTS = {"amar somporke", "amar profile", "what do you know about me", "my profile"}
LOCATION_HINTS = {"my location", "may location", "where am i", "ami ekhon kothai achi", "ami ekhon kothay achi"}

LIVE_SEARCH_HINTS = {"recent", "latest", "today", "news", "update", "current", "price", "gold price", "gold prize", "dollar rate"}
WEATHER_HINTS = {"weather", "abohawa", "আবহাওয়া", "আবহাওয়া", "temperature", "rain"}
TIME_HINTS = {"time", "koita baje", "koyta baje", "কয়টা বাজে", "কয়টা বাজে"}
TRANSLATION_HINTS = {"translate", "meaning", "mane ki", "bangla ki", "english ki", "er bangla", "er english"}

YOUTUBE_HINTS = {"youtube", "ইউটিউব"}
YOUTUBE_SEARCH_HINTS = {"search", "song search", "video search", "bangla song search", "tutorial"}
WHATSAPP_HINTS = {"whatsapp"}
MESSAGE_HINTS = {"message dao", "ke bolo", "likho", "draft", "bolo"}

YOUTUBE_HINTS.update({"ইউটিউব"})
WEATHER_HINTS.update({"আবহাওয়া", "আবহাওয়া"})
TIME_HINTS.update({"কয়টা বাজে", "কয়টা বাজে"})

APP_OPEN_HINTS = {"open", "open koro", "launch", "start", "khulo", "kholo", "ওপেন", "খোলো", "খুলুন"}
APP_TARGETS = {"calculator", "notepad", "paint", "chrome", "file explorer", "vscode", "word", "excel"}

APP_PLANNING_HINTS = {
    "app idea",
    "software create",
    "software want to create",
    "app want to create",
    "project korte chai",
    "project want to create",
    "app create",
}
CODE_GENERATION_HINTS = {
    "homepage",
    "landing page",
    "login page",
    "code create",
    "code",
    "html css",
    "html css create",
    "page create",
    "react component",
    "portfolio website",
    "website create",
}
GENERAL_QA_HINTS = {"what is", "ki", "computer", "internet", "ai", "programming"}

DANGEROUS_HINTS = {
    "delete system32",
    "delete all files",
    "format drive",
    "format c drive",
    "cmd",
    "powershell",
    "regedit",
    "rm -rf",
    "shutdown",
}

MATH_RE = re.compile(r"^\s*\d+(?:\.\d+)?(?:\s*[-+*/]\s*\d+(?:\.\d+)?)+\s*(?:=\s*)?\??\s*$")
PERCENT_RE = re.compile(r"^\s*(?:calculate\s+)?\d+(?:\.\d+)?\s*(?:%|percent)\s+of\s+\d+(?:\.\d+)?\s*\??\s*$")
CONTACT_MESSAGE_RE = re.compile(r"(?P<recipient>[a-zA-Z\u0980-\u09ff][\w\s\u0980-\u09ff]{1,40}?)\s+ke\s+(?:bolo|message dao|likho|draft)\s+(?P<message>.+)")
WHATSAPP_DRAFT_RE = re.compile(r"whatsapp\s+e\s+(?P<recipient>.+?)\s+ke\s+(?:bolo|message dao|likho|draft)\s+(?P<message>.+)")
WHATSAPP_DRAFT_ALT_RE = re.compile(r"(?P<recipient>.+?)\s+ke\s+whatsapp\s+e\s+(?:bolo|message dao|likho|draft)\s+(?P<message>.+)")
CONTACT_SAVE_RE = re.compile(r"(?P<name>.+?)\s+er\s+number\s+save\s+koro\s+(?P<phone>\+?[\d\s-]+)")
CONTACT_QUERY_RE = re.compile(r"(?P<name>.+?)\s+er\s+(?:number|whatsapp contact|contact)\s+(?:ki|bolo)")
CONTACT_DELETE_RE = re.compile(r"(?P<name>.+?)\s+er\s+(?:whatsapp contact|contact|number)\s+delete\s+koro")
