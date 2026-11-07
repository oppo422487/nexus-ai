"""Weather tool facade."""

from __future__ import annotations


def get_weather_snapshot():
    from app.chat.service import fetch_weather

    return fetch_weather()

