from __future__ import annotations

from fastapi.testclient import TestClient

from app.audit import event_log
from app.chat import service as chat_service
from app.contacts import store as contact_store
from app.llm import router as llm_router
from app.llm.schemas import LLMResponse
from app.main import app
from app.permissions import store as permission_store
from app.search import service as search_service
from app.search.service import SearchAnswer, SearchProviderResult
from app.search.providers import serper as serper_provider
from app.schemas.action_execution import ActionExecutionResponse, ActionTarget
from app.schemas.chat import ChatWeatherSnapshot
from app.memory.pending_tasks import clear_pending_task


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr(permission_store, "PERMISSIONS_FILE", tmp_path / "permissions.json")
    monkeypatch.setattr(event_log, "AUDIT_DB_PATH", tmp_path / "audit.sqlite3")
    monkeypatch.setattr(contact_store, "CONTACTS_FILE", tmp_path / "whatsapp_contacts.json")
    return TestClient(app)


def test_chat_endpoint_works(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post("/api/chat/message", json={"message": "hello"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["intent"] == "greeting"
    assert data["execution_enabled"] is False


def test_voice_email_draft_requires_yes_before_sending(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    clear_pending_task()
    contact_store.save_contact(
        "Office Boss",
        "01712345678",
        aliases=["boss", "বস"],
        relationship="boss",
        default_tone="formal",
        email_address="boss@example.com",
    )
    sends: list[dict[str, str]] = []
    monkeypatch.setattr(chat_service, "send_email", lambda **kwargs: sends.append(kwargs) or {"sent": True, "provider": "test"})

    draft = client.post(
        "/api/chat/message",
        json={"message": "আমার বসকে একটা ইমেইল লিখে দাও যে আমি কালকে আসতে পারব না", "source": "voice_room"},
    ).json()

    assert draft["status"] == "needs_confirmation"
    assert draft["intent"] == "email_skill"
    assert draft["requires_confirmation"] is True
    assert "Subject:" in draft["answer"]
    assert sends == []

    unclear = client.post("/api/chat/message", json={"message": "উম", "source": "voice_room"}).json()
    assert unclear["status"] == "needs_confirmation"
    assert sends == []

    confirmed = client.post("/api/chat/message", json={"message": "হ্যাঁ", "source": "voice_room"}).json()
    assert confirmed["status"] == "completed"
    assert confirmed["execution_enabled"] is True
    assert sends[0]["recipient"] == "boss@example.com"
    clear_pending_task()


def test_hi_returns_personal_greeting(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post("/api/chat/message", json={"message": "hi", "address_style": "Boss"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["intent"] == "greeting"
    assert data["provider"] == "Nexa local assistant"
    assert data["execution_enabled"] is False
    assert "Boss" in data["answer"]
    assert "help" in data["answer"].lower() or "সাহায্য" in data["answer"]


def test_assalamu_alaikum_returns_banglish_greeting(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post("/api/chat/message", json={"message": "assalamu alaikum", "address_style": "Vai"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["intent"] == "greeting"
    assert "Wa alaikum assalam" in data["answer"]
    assert "ভাই" in data["answer"] or "Vai" in data["answer"]


def test_capability_question_returns_summary_without_web_search(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post("/api/chat/message", json={"message": "tumi ki korte paro", "address_style": "Sir"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["intent"] == "capabilities"
    assert data["provider"] == "Nexa local assistant"
    assert "web" in data["answer"].lower()
    assert "weather" in data["answer"].lower()
    assert "Sir" in data["answer"]


def test_address_style_neutral_omits_personal_title(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post("/api/chat/message", json={"message": "hello", "address_style": "Neutral"})

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "greeting"
    assert "Boss" not in data["answer"]
    assert "Sir" not in data["answer"]
    assert "Hello" in data["answer"]


def test_casual_project_chat_asks_how_to_help(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post(
        "/api/chat/message",
        json={"message": "ami ekta project niye kaj kortesi", "address_style": "Boss"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "casual_chat"
    assert "Project" in data["answer"] or "project" in data["answer"]
    assert "help" in data["answer"].lower()


def test_how_are_you_returns_casual_chat_not_web_search(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    calls: list[str] = []

    def fake_search(query: str):
        calls.append(query)
        return SearchAnswer(answer="Should not be used", provider="Test")

    monkeypatch.setattr(chat_service, "search_answer", fake_search)

    response = client.post("/api/chat/message", json={"message": "how are you", "address_style": "Boss"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["intent"] == "casual_chat"
    assert data["provider"] == "Nexa local assistant"
    assert "Boss" in data["answer"]
    assert not data["search_results"]
    assert calls == []


def test_how_are_u_returns_casual_chat_not_web_search(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    calls: list[str] = []

    def fake_search(query: str):
        calls.append(query)
        return SearchAnswer(answer="Should not be used", provider="Test")

    monkeypatch.setattr(chat_service, "search_answer", fake_search)

    response = client.post("/api/chat/message", json={"message": "how are u", "address_style": "Boss"})

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "casual_chat"
    assert data["provider"] == "Nexa local assistant"
    assert data["search_results"] == []
    assert data["chips"] == []
    assert calls == []


def test_casual_replies_vary_with_history(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    first = client.post("/api/chat/message", json={"message": "how are u", "address_style": "Boss"}).json()
    second = client.post(
        "/api/chat/message",
        json={
            "message": "how are u",
            "address_style": "Boss",
            "history": [{"role": "assistant", "content": first["answer"]}],
        },
    ).json()

    assert first["intent"] == "casual_chat"
    assert second["intent"] == "casual_chat"
    assert first["answer"] != second["answer"]


def test_ki_koro_returns_assistant_style_reply(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post("/api/chat/message", json={"message": "ki koro", "address_style": "Boss"})

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "casual_chat"
    assert "command" in data["answer"].lower()
    assert "Boss" in data["answer"]
    assert data["search_results"] == []


def test_tension_message_returns_supportive_reply(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post("/api/chat/message", json={"message": "ami tension e achi", "address_style": "Boss"})

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "user_frustration"
    assert "tension" in data["answer"].lower()
    assert "Boss" in data["answer"]
    assert data["search_results"] == []


def test_achi_alone_does_not_trigger_greeting(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post("/api/chat/message", json={"message": "achi", "address_style": "Boss"})

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] != "greeting"


def test_project_help_message_asks_which_part(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post(
        "/api/chat/message",
        json={"message": "amar project niye help lagbe", "address_style": "Boss"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "casual_chat"
    assert "Project" in data["answer"] or "project" in data["answer"]
    assert "bug" in data["answer"].lower() or "documentation" in data["answer"].lower()
    assert data["search_results"] == []


def test_conversation_address_style_respected(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post("/api/chat/message", json={"message": "how are you", "address_style": "Sir"})

    assert response.status_code == 200
    data = response.json()
    assert "Sir" in data["answer"]
    assert "Boss" not in data["answer"]


def test_universal_web_query_intent_and_query_cleaning(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    seen: dict[str, str] = {}

    def fake_search(query: str):
        seen["query"] = query
        return SearchAnswer(
            answer="Python latest version result.",
            provider="Wikipedia Search",
            source_url="https://en.wikipedia.org/wiki/Python",
            results=[
                SearchProviderResult(
                    title="Python",
                    snippet="Python latest version result.",
                    source_url="https://en.wikipedia.org/wiki/Python",
                    provider="Wikipedia Search",
                    confidence="medium",
                )
            ],
            confidence="medium",
        )

    monkeypatch.setattr(chat_service, "search_answer", fake_search)

    response = client.post(
        "/api/chat/message",
        json={"message": "google theke search kore bolo python latest version"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["intent"] == "web_search"
    assert seen["query"] == "python latest version"
    assert "Python" in data["answer"]
    assert data["search_results"]


def test_market_query_returns_related_sources_without_generic_failure(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    def fake_search(query: str):
        return SearchAnswer(
            answer=(
                "I found related sources but could not verify one exact live price. "
                "Live market data may change; use the source cards below for verification."
            ),
            provider="DuckDuckGo Related Topics",
            source_url="https://example.com/gold",
            results=[
                SearchProviderResult(
                    title="Gold price Bangladesh",
                    snippet="Related source snippet about gold price in Bangladesh.",
                    source_url="https://example.com/gold",
                    provider="DuckDuckGo Related Topics",
                    confidence="low",
                )
            ],
            exact=False,
            confidence="low",
            live_data=True,
        )

    monkeypatch.setattr(chat_service, "search_answer", fake_search)

    response = client.post("/api/chat/message", json={"message": "today gold price Bangladesh"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["intent"] == "market_search"
    assert data["live_data"] is True
    assert "could not verify one exact live price" in data["answer"]
    assert data["search_results"][0]["title"] == "Gold price Bangladesh"
    assert "No reliable result" not in data["answer"]


def test_gold_price_snippets_return_synthesized_answer(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    def fake_search(query: str):
        return SearchAnswer(
            answer="Raw provider placeholder should be replaced.",
            provider="Serper.dev",
            source_url="https://example.com/bajus",
            results=[
                SearchProviderResult(
                    title="BAJUS gold price",
                    snippet="22K gold price is BDT 12,500 per gram today.",
                    source_url="https://example.com/bajus",
                    provider="Serper.dev",
                    confidence="medium",
                ),
                SearchProviderResult(
                    title="Al-Amin Jewellers gold price",
                    snippet="22K gold is Tk 12,450 per gram in Bangladesh.",
                    source_url="https://example.com/alamin",
                    provider="Serper.dev",
                    confidence="medium",
                ),
            ],
            exact=False,
            confidence="medium",
        )

    monkeypatch.setattr(chat_service, "search_answer", fake_search)

    response = client.post("/api/chat/message", json={"message": "today gold price Bangladesh"})

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "market_search"
    assert data["live_data_warning"] is True
    assert data["show_search_results_by_default"] is False
    assert data["sources"][:2] == ["BAJUS gold price", "Al-Amin Jewellers gold price"]
    assert "Raw provider placeholder" not in data["answer"]
    assert "12,500" in data["answer"] or "12,450" in data["answer"]


def test_conflicting_market_snippets_do_not_hallucinate_one_exact_answer(monkeypatch) -> None:
    result = SearchAnswer(
        answer="Raw related source answer.",
        provider="Serper.dev",
        results=[
            SearchProviderResult(
                title="Source A",
                snippet="Gold price BDT 12,500 per gram.",
                source_url="https://example.com/a",
                provider="Serper.dev",
            ),
            SearchProviderResult(
                title="Source B",
                snippet="Gold price BDT 12,900 per gram.",
                source_url="https://example.com/b",
                provider="Serper.dev",
            ),
        ],
        exact=False,
    )

    synthesized = search_service.synthesize_related_answer(
        "today gold price bangladesh",
        result,
        live_data=True,
    )

    assert "vary" in synthesized.answer.lower() or "different" in synthesized.answer.lower()
    assert "12,500" in synthesized.answer
    assert "12,900" in synthesized.answer
    assert synthesized.exact is False


def test_provider_fallback_order(monkeypatch) -> None:
    calls: list[str] = []

    def first_provider(query: str):
        calls.append("duck")
        return None

    def second_provider(query: str):
        calls.append("wiki_summary")
        return None

    def third_provider(query: str):
        calls.append("wiki_search")
        return SearchAnswer(
            answer="Fallback answer",
            provider="Wikipedia Search",
            results=[
                SearchProviderResult(
                    title="Fallback",
                    snippet="Fallback snippet",
                    source_url="https://example.com",
                    provider="Wikipedia Search",
                )
            ],
        )

    monkeypatch.setattr(search_service, "duckduckgo_instant", first_provider)
    monkeypatch.setattr(search_service, "wikipedia_summary", second_provider)
    monkeypatch.setattr(search_service, "wikipedia_search", third_provider)
    monkeypatch.setenv("NEXA_SEARCH_PROVIDER", "free")

    result = search_service.search_answer("python latest version")

    assert result.provider == "Wikipedia Search"
    assert calls == ["duck", "wiki_summary", "wiki_search"]


def test_no_google_html_scraping() -> None:
    assert "google.com/search" not in search_service.google_cse_search.__code__.co_consts
    assert "https://www.googleapis.com/customsearch/v1?" in search_service.google_cse_search.__code__.co_consts


def test_serper_provider_selected_when_configured(monkeypatch) -> None:
    calls: list[str] = []

    def fake_serper(query: str):
        calls.append(query)
        return SearchAnswer(
            answer="Serper answer",
            provider="Serper.dev",
            source_url="https://example.com",
            results=[
                SearchProviderResult(
                    title="Serper source",
                    snippet="Serper snippet",
                    source_url="https://example.com",
                    provider="Serper.dev",
                    confidence="high",
                )
            ],
            exact=True,
            confidence="high",
        )

    monkeypatch.setenv("NEXA_SEARCH_PROVIDER", "serper")
    monkeypatch.setenv("SERPER_API_KEY", "present")
    monkeypatch.setattr(search_service, "serper_search", fake_serper)

    result = search_service.search_answer("python latest version")

    assert result.provider == "Serper.dev"
    assert result.answer == "Serper answer"
    assert calls == ["python latest version"]


def test_serper_market_query_returns_source_cards(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    def fake_serper(query: str):
        return SearchAnswer(
            answer="I found related live sources, but could not verify one exact value.",
            provider="Serper.dev",
            source_url="https://example.com/gold",
            results=[
                SearchProviderResult(
                    title="Gold price Bangladesh today",
                    snippet="Gold price related snippet.",
                    source_url="https://example.com/gold",
                    provider="Serper.dev",
                    confidence="medium",
                )
            ],
            exact=False,
            confidence="medium",
        )

    monkeypatch.setenv("NEXA_SEARCH_PROVIDER", "serper")
    monkeypatch.setenv("SERPER_API_KEY", "present")
    monkeypatch.setattr(search_service, "serper_search", fake_serper)

    response = client.post("/api/chat/message", json={"message": "today gold price Bangladesh"})

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "market_search"
    assert data["provider"] == "Serper.dev"
    assert data["live_data"] is True
    assert data["search_results"][0]["provider"] == "Serper.dev"


def test_serper_python_latest_returns_source_backed_answer(monkeypatch) -> None:
    def fake_post(*args, **kwargs):
        class Response:
            status_code = 200

            def json(self):
                return {
                    "answerBox": {
                        "title": "Python",
                        "answer": "Python 3.14.2",
                        "link": "https://www.python.org/downloads/",
                    },
                    "organic": [
                        {
                            "title": "Download Python",
                            "snippet": "Latest Python releases.",
                            "link": "https://www.python.org/downloads/",
                        }
                    ],
                }

        return Response()

    monkeypatch.setenv("SERPER_API_KEY", "present")
    monkeypatch.setattr(serper_provider.httpx, "post", fake_post)

    result = serper_provider.serper_search("python latest version")

    assert result is not None
    assert result.provider == "Serper.dev"
    assert result.exact is True
    assert "Python 3.14.2" in result.answer
    assert result.results[0].provider == "Serper.dev"


def test_serper_failure_falls_back_to_free_provider(monkeypatch) -> None:
    def failing_serper(query: str):
        return None

    def fallback_duck(query: str):
        return SearchAnswer(
            answer="Free fallback answer",
            provider="DuckDuckGo Instant Answer",
            exact=True,
            confidence="high",
        )

    monkeypatch.setenv("NEXA_SEARCH_PROVIDER", "serper")
    monkeypatch.setenv("SERPER_API_KEY", "present")
    monkeypatch.setattr(search_service, "serper_search", failing_serper)
    monkeypatch.setattr(search_service, "duckduckgo_instant", fallback_duck)

    result = search_service.search_answer("python latest version")

    assert result.provider == "DuckDuckGo Instant Answer"
    assert result.answer == "Free fallback answer"


def test_missing_serper_key_does_not_crash(monkeypatch) -> None:
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    result = serper_provider.serper_search("python latest version")
    assert result is None


def test_weather_and_time_do_not_use_serper(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    calls: list[str] = []

    def fake_search(query: str):
        calls.append(query)
        return SearchAnswer(answer="Should not be used", provider="Serper.dev")

    monkeypatch.setattr(chat_service, "search_answer", fake_search)
    monkeypatch.setattr(
        chat_service,
        "fetch_weather",
        lambda: ChatWeatherSnapshot(
            location="Dhaka, Bangladesh",
            temperature_c=30,
            condition="Clear sky",
            wind_kph=5,
            humidity_percent=50,
        ),
    )

    weather = client.post("/api/chat/message", json={"message": "ajker weather ki"}).json()
    time_answer = client.post("/api/chat/message", json={"message": "india te koita baje"}).json()

    assert weather["provider"] == "Open-Meteo"
    assert time_answer["provider"] == "Local timezone database"
    assert calls == []


def test_time_intent_india(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post("/api/chat/message", json={"message": "india te koita baje"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["intent"] == "current_time"
    assert data["provider"] == "Local timezone database"
    assert "Asia/Kolkata" in data["answer"]


def test_translation_intent(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post(
        "/api/chat/message",
        json={"message": "ei sentence er Bangla ki: I am working on my project"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["intent"] == "translation"
    assert "প্রজেক্টে কাজ করছি" in data["answer"]


def test_ajker_weather_detects_weather(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(
        chat_service,
        "fetch_weather",
        lambda: ChatWeatherSnapshot(
            location="Dhaka, Bangladesh",
            temperature_c=31.5,
            condition="Partly cloudy",
            wind_kph=12.0,
            humidity_percent=70,
        ),
    )

    response = client.post("/api/chat/message", json={"message": "ajker weather ki"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["intent"] == "weather"
    assert data["provider"] == "Open-Meteo"
    assert data["weather"]["location"] == "Dhaka, Bangladesh"
    assert "31.5" in data["answer"]


def test_dangerous_chat_command_blocked(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post("/api/chat/message", json={"message": "delete system32"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    assert data["intent"] == "blocked_dangerous"
    assert data["blocked"] is True
    assert data["execution_enabled"] is False


def test_delete_all_files_still_blocked(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post("/api/chat/message", json={"message": "delete all files"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    assert data["intent"] == "blocked_dangerous"
    assert data["blocked"] is True


def test_safe_app_launch_requires_confirmation_when_quick_launch_off(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post("/api/chat/message", json={"message": "calculator open koro"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "preview_only"
    assert data["intent"] == "app_open_request"
    assert data["requires_confirmation"] is True
    assert data["execution_enabled"] is False
    assert data["action"]["label"] == "Calculator"


def test_safe_app_launch_auto_allowed_only_when_trusted_mode_enabled(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    client.put("/api/permissions", json={"key": "trusted_quick_launch", "enabled": True})

    def fake_execute(request):
        return ActionExecutionResponse(
            status="executed",
            intent="open_app",
            target=ActionTarget(kind="app", value="calc", label="Calculator"),
            safety_level="confirmation_required",
            can_execute=True,
            executed=True,
            dry_run=False,
            user_confirmed=True,
            message="Opened app safely.",
        )

    monkeypatch.setattr(chat_service, "execute_open_app", fake_execute)

    response = client.post("/api/chat/message", json={"message": "calculator open koro"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "executed"
    assert data["intent"] == "app_open_request"
    assert data["execution_enabled"] is True
    assert data["action"]["executed"] is True
    assert "Opened Calculator" in data["answer"]


def test_unknown_app_does_not_execute(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    client.put("/api/permissions", json={"key": "trusted_quick_launch", "enabled": True})

    response = client.post("/api/chat/message", json={"message": "unknownapp open koro"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_found"
    assert data["execution_enabled"] is False
    assert "could not find" in data["answer"].lower()


def test_save_whatsapp_contact_from_chat(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post("/api/chat/message", json={"message": "Rahim er number save koro 01712345678"})

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "contact_save"
    assert data["status"] == "saved"
    assert "8801712345678" in data["answer"]


def test_save_contact_with_relationship_and_tone(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post(
        "/api/chat/message",
        json={"message": "Boss er number save koro 01712345678 relationship boss"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "contact_save"
    contact = contact_store.get_contact("boss")
    assert contact is not None
    assert contact.relationship == "boss"
    assert contact.default_tone == "formal"


def test_add_whatsapp_contact_alias_from_chat(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    client.post("/api/chat/message", json={"message": "Rahim er number save koro 01712345678"})

    response = client.post("/api/chat/message", json={"message": "Rahim er alias Rohim add koro"})

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "contact_alias_add"
    assert data["status"] == "saved"
    assert contact_store.get_contact("Rohim") is not None


def test_retrieve_whatsapp_contact_from_chat(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    client.post("/api/chat/message", json={"message": "Rahim er number save koro 01712345678"})

    response = client.post("/api/chat/message", json={"message": "Rahim er number ki"})

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "contact_lookup"
    assert data["status"] == "completed"
    assert "8801712345678" in data["answer"]


def test_malformed_whatsapp_contact_number_rejected(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post("/api/chat/message", json={"message": "Rahim er number save koro 123"})

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "contact_save"
    assert data["status"] == "blocked"
    assert data["blocked"] is True
    assert "Malformed phone number" in data["answer"]


def test_delete_whatsapp_contact_from_chat(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    client.post("/api/chat/message", json={"message": "Rahim er number save koro 01712345678"})

    response = client.post("/api/chat/message", json={"message": "Rahim er WhatsApp contact delete koro"})

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "contact_delete"
    assert data["status"] == "deleted"


def test_youtube_open_trusted_auto_open_returns_executed(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    def fake_execute(request):
        assert request.target.value == "https://www.youtube.com"
        return ActionExecutionResponse(
            status="executed",
            intent="open_website",
            target=ActionTarget(kind="url", value=request.target.value, label="YouTube"),
            safety_level="confirmation_required",
            can_execute=True,
            executed=True,
            dry_run=False,
            user_confirmed=True,
            message="Opened website safely.",
        )

    monkeypatch.setattr(chat_service, "execute_open_website", fake_execute)

    response = client.post("/api/chat/message", json={"message": "youtube open koro"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "executed"
    assert data["intent"] == "youtube_open"
    assert data["requires_confirmation"] is False
    assert data["execution_enabled"] is True
    assert data["auto_execute_safe"] is True
    assert data["action"]["kind"] == "website"
    assert data["action"]["target"] == "https://www.youtube.com"
    assert data["action"]["executed"] is True


def test_youtube_search_intent_uses_safe_search_url_without_confirmation(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    def fake_execute(request):
        assert request.target.value == "https://www.youtube.com/results?search_query=python+tutorial"
        return ActionExecutionResponse(
            status="executed",
            intent="open_website",
            target=ActionTarget(kind="url", value=request.target.value, label="YouTube search: python tutorial"),
            safety_level="confirmation_required",
            can_execute=True,
            executed=True,
            dry_run=False,
            user_confirmed=True,
            message="Opened website safely.",
        )

    monkeypatch.setattr(chat_service, "execute_open_website", fake_execute)

    response = client.post("/api/chat/message", json={"message": "youtube e python tutorial search koro"})

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "youtube_search"
    assert data["status"] == "executed"
    assert data["requires_confirmation"] is False
    assert data["auto_execute_safe"] is True
    assert data["action"]["target"] == "https://www.youtube.com/results?search_query=python+tutorial"


def test_bangla_youtube_song_command_routes_to_safe_search(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    def fake_execute(request):
        assert request.target.value.startswith("https://www.youtube.com/results?search_query=")
        assert "bangla" in request.target.value.lower() or "%E0%A6%AC" in request.target.value
        return ActionExecutionResponse(
            status="executed",
            intent="open_website",
            target=ActionTarget(kind="url", value=request.target.value, label="YouTube search"),
            safety_level="confirmation_required",
            can_execute=True,
            executed=True,
            dry_run=False,
            user_confirmed=True,
            message="Opened website safely.",
        )

    monkeypatch.setattr(chat_service, "execute_open_website", fake_execute)

    data = client.post("/api/chat/message", json={"message": "ইউটিউব খুলে একটা বাংলা গান চালাও"}).json()

    assert data["intent"] == "youtube_search"
    assert data["auto_execute_safe"] is True
    assert "YouTube" in data["answer"]


def test_whatsapp_open_trusted_auto_open_returns_executed(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    def fake_execute(request):
        assert request.target.value == "https://web.whatsapp.com"
        return ActionExecutionResponse(
            status="executed",
            intent="open_website",
            target=ActionTarget(kind="url", value=request.target.value, label="WhatsApp Web"),
            safety_level="confirmation_required",
            can_execute=True,
            executed=True,
            dry_run=False,
            user_confirmed=True,
            message="Opened website safely.",
        )

    monkeypatch.setattr(chat_service, "execute_open_website", fake_execute)

    response = client.post("/api/chat/message", json={"message": "whatsapp open koro"})

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "whatsapp_open"
    assert data["requires_confirmation"] is False
    assert data["execution_enabled"] is True
    assert data["auto_execute_safe"] is True
    assert data["action"]["target"] == "https://web.whatsapp.com"


def test_whatsapp_draft_known_contact_auto_opens_safe_url(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    client.post("/api/chat/message", json={"message": "Rahim er number save koro 01712345678"})

    def fake_execute(request):
        assert request.target.value.startswith("https://wa.me/8801712345678?text=")
        return ActionExecutionResponse(
            status="executed",
            intent="open_website",
            target=ActionTarget(kind="url", value=request.target.value, label="WhatsApp draft to Rahim"),
            safety_level="confirmation_required",
            can_execute=True,
            executed=True,
            dry_run=False,
            user_confirmed=True,
            message="Opened website safely.",
        )

    monkeypatch.setattr(chat_service, "execute_open_website", fake_execute)

    response = client.post(
        "/api/chat/message",
        json={
            "message": "whatsapp e Rahim ke bolo ami pore call korbo",
            "whatsapp_draft_open_target": "wa_me",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "whatsapp_draft"
    assert data["status"] == "executed"
    assert data["requires_confirmation"] is False
    assert data["execution_enabled"] is True
    assert data["auto_execute_safe"] is True
    assert data["action"]["kind"] == "whatsapp_draft"
    assert data["action"]["recipient"] == "Rahim"
    assert "call" in data["action"]["draft_text"]
    assert data["action"]["target"].startswith("https://wa.me/8801712345678?text=")
    assert "did not click Send" in data["answer"]


def test_whatsapp_draft_auto_prefers_app_protocol_with_fallback(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    client.post("/api/chat/message", json={"message": "Rahim er number save koro 01712345678"})
    opened: list[str] = []

    def fake_execute(request):
        opened.append(request.target.value)
        if request.target.value.startswith("whatsapp://send?phone=8801712345678&text="):
            return ActionExecutionResponse(
                status="failed",
                intent="open_website",
                target=ActionTarget(kind="url", value=request.target.value, label="WhatsApp draft to Rahim"),
                safety_level="confirmation_required",
                can_execute=True,
                executed=False,
                dry_run=False,
                user_confirmed=True,
                message="Browser could not open the website.",
                error="Protocol unavailable.",
            )
        assert request.target.value.startswith("https://wa.me/8801712345678?text=")
        return ActionExecutionResponse(
            status="executed",
            intent="open_website",
            target=ActionTarget(kind="url", value=request.target.value, label="WhatsApp draft to Rahim"),
            safety_level="confirmation_required",
            can_execute=True,
            executed=True,
            dry_run=False,
            user_confirmed=True,
            message="Opened website safely.",
        )

    monkeypatch.setattr(chat_service, "execute_open_website", fake_execute)

    data = client.post(
        "/api/chat/message",
        json={
            "message": "whatsapp e Rahim ke bolo ami pore call korbo",
            "whatsapp_draft_open_target": "auto",
        },
    ).json()

    assert data["intent"] == "whatsapp_draft"
    assert data["status"] == "executed"
    assert opened[0].startswith("whatsapp://send?phone=8801712345678&text=")
    assert opened[1].startswith("https://wa.me/8801712345678?text=")
    assert data["action"]["target"].startswith("https://wa.me/8801712345678?text=")
    assert "Please review and press Send manually" in data["answer"]


def test_whatsapp_draft_web_preference_uses_web_url(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    client.post("/api/chat/message", json={"message": "Rahim er number save koro 01712345678"})

    def fake_execute(request):
        assert request.target.value.startswith("https://web.whatsapp.com/send?phone=8801712345678&text=")
        return ActionExecutionResponse(
            status="executed",
            intent="open_website",
            target=ActionTarget(kind="url", value=request.target.value, label="WhatsApp draft to Rahim"),
            safety_level="confirmation_required",
            can_execute=True,
            executed=True,
            dry_run=False,
            user_confirmed=True,
            message="Opened website safely.",
        )

    monkeypatch.setattr(chat_service, "execute_open_website", fake_execute)

    data = client.post(
        "/api/chat/message",
        json={
            "message": "whatsapp e Rahim ke bolo ami pore call korbo",
            "whatsapp_draft_open_target": "web",
        },
    ).json()

    assert data["intent"] == "whatsapp_draft"
    assert data["action"]["target"].startswith("https://web.whatsapp.com/send?phone=8801712345678&text=")
    assert "Send manually" in data["answer"]


def test_whatsapp_draft_wa_me_preference_still_works(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    client.post("/api/chat/message", json={"message": "Rahim er number save koro 01712345678"})

    def fake_execute(request):
        assert request.target.value.startswith("https://wa.me/8801712345678?text=")
        return ActionExecutionResponse(
            status="executed",
            intent="open_website",
            target=ActionTarget(kind="url", value=request.target.value, label="WhatsApp draft to Rahim"),
            safety_level="confirmation_required",
            can_execute=True,
            executed=True,
            dry_run=False,
            user_confirmed=True,
            message="Opened website safely.",
        )

    monkeypatch.setattr(chat_service, "execute_open_website", fake_execute)

    data = client.post(
        "/api/chat/message",
        json={
            "message": "whatsapp e Rahim ke bolo ami pore call korbo",
            "whatsapp_draft_open_target": "wa_me",
        },
    ).json()

    assert data["intent"] == "whatsapp_draft"
    assert data["action"]["target"].startswith("https://wa.me/8801712345678?text=")


def test_whatsapp_draft_resolves_contact_case_alias_and_typo(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    contact_store.save_contact("Rahim", "01712345678", nickname="Boss Rahim")
    opened: list[str] = []

    def fake_execute(request):
        opened.append(request.target.value)
        return ActionExecutionResponse(
            status="executed",
            intent="open_website",
            target=ActionTarget(kind="url", value=request.target.value, label="WhatsApp draft to Rahim"),
            safety_level="confirmation_required",
            can_execute=True,
            executed=True,
            dry_run=False,
            user_confirmed=True,
            message="Opened website safely.",
        )

    monkeypatch.setattr(chat_service, "execute_open_website", fake_execute)

    alias_response = client.post(
        "/api/chat/message",
        json={"message": "whatsapp e boss rahim ke bolo ami pore call korbo"},
    ).json()
    typo_response = client.post(
        "/api/chat/message",
        json={"message": "whatsapp e Rohim ke bolo ami pore call korbo"},
    ).json()

    assert alias_response["intent"] == "whatsapp_draft"
    assert alias_response["status"] == "executed"
    assert alias_response["action"]["recipient"] == "Rahim"
    assert typo_response["intent"] == "whatsapp_draft"
    assert typo_response["status"] == "executed"
    assert typo_response["action"]["recipient"] == "Rahim"
    assert len(opened) == 2


def test_whatsapp_draft_ambiguous_contact_asks_clarification(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    contact_store.save_contact("Rahim", "01712345678")
    contact_store.save_contact("Karim", "01812345678", nickname="Rahim")

    response = client.post(
        "/api/chat/message",
        json={"message": "whatsapp e Rahim ke bolo ami pore call korbo"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "whatsapp_draft"
    assert data["status"] == "needs_more_info"
    assert data["execution_enabled"] is False
    assert "Multiple local WhatsApp contacts match" in data["answer"]


def test_whatsapp_draft_unknown_contact_asks_for_phone_number(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post(
        "/api/chat/message",
        json={"message": "whatsapp e Karim ke bolo ami pore call korbo"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "whatsapp_draft"
    assert data["status"] == "needs_more_info"
    assert data["execution_enabled"] is False
    assert data["requires_confirmation"] is False
    assert "phone number" in data["answer"].lower()


def test_pending_whatsapp_number_reply_saves_contact_and_continues_draft(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    first = client.post(
        "/api/chat/message",
        json={"message": "whatsapp e Rahim ke bolo ami pore call korbo"},
    ).json()
    assert first["intent"] == "whatsapp_draft"
    assert first["status"] == "needs_more_info"
    assert "phone number" in first["answer"].lower()

    def fake_execute(request):
        assert request.target.value.startswith("https://wa.me/8801922869012?text=")
        return ActionExecutionResponse(
            status="executed",
            intent="open_website",
            target=ActionTarget(kind="url", value=request.target.value, label="WhatsApp draft to Rahim"),
            safety_level="confirmation_required",
            can_execute=True,
            executed=True,
            dry_run=False,
            user_confirmed=True,
            message="Opened website safely.",
        )

    monkeypatch.setattr(chat_service, "execute_open_website", fake_execute)

    second = client.post(
        "/api/chat/message",
        json={
            "message": "rahim number 01922869012",
            "whatsapp_draft_open_target": "wa_me",
            "history": [
                {"role": "user", "content": "whatsapp e Rahim ke bolo ami pore call korbo"},
                {"role": "assistant", "content": first["answer"]},
            ],
        },
    ).json()

    assert second["intent"] == "whatsapp_draft"
    assert second["status"] == "executed"
    assert second["action"]["recipient"] == "Rahim"
    assert second["auto_execute_safe"] is True
    assert contact_store.get_contact("Rahim").phone_number == "8801922869012"


def test_whatsapp_draft_missing_message_asks_message_text(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    client.post("/api/chat/message", json={"message": "Rahim er number save koro 01712345678"})

    response = client.post("/api/chat/message", json={"message": "WhatsApp Rahim draft"})

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "whatsapp_draft"
    assert data["status"] == "needs_more_info"
    assert "message ta ki likhbo" in data["answer"]


def test_boss_formal_draft_generated_with_local_template(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    client.post("/api/chat/message", json={"message": "Boss er number save koro 01712345678 relationship boss"})

    def fake_execute(request):
        assert request.target.value.startswith("https://wa.me/8801712345678?text=")
        assert "Assalamu+Alaikum+Sir" in request.target.value
        assert "office+tomorrow" in request.target.value
        return ActionExecutionResponse(
            status="executed",
            intent="open_website",
            target=ActionTarget(kind="url", value=request.target.value, label="WhatsApp draft to Boss"),
            safety_level="confirmation_required",
            can_execute=True,
            executed=True,
            dry_run=False,
            user_confirmed=True,
            message="Opened website safely.",
        )

    monkeypatch.setattr(chat_service, "execute_open_website", fake_execute)
    monkeypatch.setattr(chat_service, "complete_llm", lambda *args, **kwargs: None)

    data = client.post(
        "/api/chat/message",
        json={
            "message": "whatsapp e amar boss ke sms dao kalke ami office e aste parbo na",
            "whatsapp_draft_open_target": "wa_me",
        },
    ).json()

    assert data["intent"] == "whatsapp_draft"
    assert data["action"]["recipient"] == "Boss"
    assert "Assalamu Alaikum Sir" in data["action"]["draft_text"]
    assert data["llm_used"] is False


def test_friend_friendly_draft_generated(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    contact_store.save_contact("Rahim", "01712345678", relationship="friend")

    def fake_execute(request):
        assert request.target.value.startswith("https://wa.me/8801712345678?text=")
        return ActionExecutionResponse(
            status="executed",
            intent="open_website",
            target=ActionTarget(kind="url", value=request.target.value, label="WhatsApp draft to Rahim"),
            safety_level="confirmation_required",
            can_execute=True,
            executed=True,
            dry_run=False,
            user_confirmed=True,
            message="Opened website safely.",
        )

    monkeypatch.setattr(chat_service, "execute_open_website", fake_execute)

    data = client.post(
        "/api/chat/message",
        json={
            "message": "whatsapp e Rahim ke bolo ami pore call korbo",
            "whatsapp_draft_open_target": "wa_me",
        },
    ).json()

    assert data["intent"] == "whatsapp_draft"
    assert "ভাই" in data["action"]["draft_text"]
    assert "call" in data["action"]["draft_text"]


def test_exact_whatsapp_message_not_over_edited(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    contact_store.save_contact("Rahim", "01712345678", relationship="friend")

    def fake_execute(request):
        assert "meeting+ta+5tay" in request.target.value
        return ActionExecutionResponse(
            status="executed",
            intent="open_website",
            target=ActionTarget(kind="url", value=request.target.value, label="WhatsApp draft to Rahim"),
            safety_level="confirmation_required",
            can_execute=True,
            executed=True,
            dry_run=False,
            user_confirmed=True,
            message="Opened website safely.",
        )

    monkeypatch.setattr(chat_service, "execute_open_website", fake_execute)
    monkeypatch.setattr(chat_service, "complete_llm", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("LLM should not be called")))

    data = client.post(
        "/api/chat/message",
        json={"message": "Rahim ke WhatsApp e likho exact message meeting ta 5tay"},
    ).json()

    assert data["intent"] == "whatsapp_draft"
    assert data["action"]["draft_text"] == "meeting ta 5tay"


def test_whatsapp_auto_send_not_allowed(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post(
        "/api/chat/message",
        json={"message": "Amit ke WhatsApp e send ami pore call korbo"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "whatsapp_draft"
    assert data["requires_confirmation"] is False
    assert data["execution_enabled"] is False
    assert "phone number" in data["answer"].lower()
    assert "send anything automatically" in data["answer"]


def test_llm_provider_fallback_uses_groq_when_gemini_missing(monkeypatch) -> None:
    calls: list[str] = []

    def fake_call(name: str, request):
        calls.append(name)
        if name == "groq":
            return LLMResponse(answer="Groq answer", provider="Groq", model="test")
        return None

    monkeypatch.setenv("NEXA_LLM_ROUTER_ENABLED", "true")
    monkeypatch.setenv("NEXA_LLM_PRIMARY", "gemini")
    monkeypatch.setattr(llm_router, "_call_provider", fake_call)

    result = llm_router.complete("write code for a button", address_style="Boss")

    assert result is not None
    assert result.provider == "Groq"
    assert result.fallback_used is True
    assert calls[:2] == ["gemini", "groq"]


def test_missing_llm_keys_fall_back_safely(monkeypatch) -> None:
    monkeypatch.setenv("NEXA_LLM_ROUTER_ENABLED", "true")
    for key in (
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "OPENROUTER_API_KEY",
        "CLOUDFLARE_ACCOUNT_ID",
        "CLOUDFLARE_API_TOKEN",
        "MISTRAL_API_KEY",
        "CEREBRAS_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    result = llm_router.complete("write code for a button", address_style="Boss")

    assert result is None


def test_weather_does_not_call_llm(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    calls: list[str] = []
    monkeypatch.setenv("NEXA_LLM_ROUTER_ENABLED", "true")
    monkeypatch.setattr(chat_service, "complete_llm", lambda *args, **kwargs: calls.append("llm") or None)
    monkeypatch.setattr(
        chat_service,
        "fetch_weather",
        lambda: ChatWeatherSnapshot(
            location="Dhaka, Bangladesh",
            temperature_c=30,
            condition="Clear sky",
            wind_kph=5,
            humidity_percent=50,
        ),
    )

    data = client.post("/api/chat/message", json={"message": "ajker weather ki"}).json()

    assert data["intent"] == "weather"
    assert data["llm_used"] is False
    assert calls == []


def test_how_are_you_does_not_call_llm(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    calls: list[str] = []
    monkeypatch.setenv("NEXA_LLM_ROUTER_ENABLED", "true")
    monkeypatch.setattr(chat_service, "complete_llm", lambda *args, **kwargs: calls.append("llm") or None)

    data = client.post("/api/chat/message", json={"message": "how are you", "address_style": "Boss"}).json()

    assert data["intent"] == "casual_chat"
    assert data["llm_used"] is False
    assert calls == []


def test_coding_request_uses_llm_when_enabled(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    def fake_llm(*args, **kwargs):
        return LLMResponse(answer="Here is safe example code.", provider="Gemini", model="test")

    monkeypatch.setenv("NEXA_LLM_ROUTER_ENABLED", "true")
    monkeypatch.setattr(chat_service, "complete_llm", fake_llm)

    data = client.post("/api/chat/message", json={"message": "write code for a React button"}).json()

    assert data["intent"] == "llm_assist"
    assert data["llm_used"] is True
    assert data["llm_provider"] == "Gemini"
    assert data["source_type"] == "llm"


def test_whatsapp_formal_draft_can_use_llm_but_never_auto_sends(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    client.post("/api/chat/message", json={"message": "Rahim er number save koro 01712345678"})

    def fake_llm(*args, **kwargs):
        return LLMResponse(answer="Assalamu alaikum Rahim, ami pore call korbo.", provider="Gemini", model="test")

    def fake_execute(request):
        assert "Assalamu+alaikum" in request.target.value
        return ActionExecutionResponse(
            status="executed",
            intent="open_website",
            target=ActionTarget(kind="url", value=request.target.value, label="WhatsApp draft to Rahim"),
            safety_level="confirmation_required",
            can_execute=True,
            executed=True,
            dry_run=False,
            user_confirmed=True,
            message="Opened website safely.",
        )

    monkeypatch.setenv("NEXA_LLM_ROUTER_ENABLED", "true")
    monkeypatch.setattr(chat_service, "complete_llm", fake_llm)
    monkeypatch.setattr(chat_service, "execute_open_website", fake_execute)

    data = client.post(
        "/api/chat/message",
        json={"message": "whatsapp e Rahim ke bolo formal friendly ami pore call korbo"},
    ).json()

    assert data["intent"] == "whatsapp_draft"
    assert data["llm_used"] is True
    assert data["llm_provider"] == "Gemini"
    assert data["auto_execute_safe"] is True
    assert "did not click Send" in data["answer"]


def test_live_gold_price_uses_search_before_llm(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    calls: list[str] = []

    def fake_search(query: str):
        calls.append(f"search:{query}")
        return SearchAnswer(
            answer="Gold source summary.",
            provider="Serper.dev",
            results=[
                SearchProviderResult(
                    title="Gold price Bangladesh",
                    snippet="22K gold price source snippet.",
                    source_url="https://example.com/gold",
                    provider="Serper.dev",
                )
            ],
            live_data=True,
        )

    def fake_llm(*args, **kwargs):
        calls.append("llm")
        return LLMResponse(answer="Polished sourced gold summary.", provider="Gemini", model="test")

    monkeypatch.setenv("NEXA_LLM_ROUTER_ENABLED", "true")
    monkeypatch.setattr(chat_service, "search_answer", fake_search)
    monkeypatch.setattr(chat_service, "complete_llm", fake_llm)

    data = client.post("/api/chat/message", json={"message": "today gold price Bangladesh"}).json()

    assert data["intent"] == "market_search"
    assert calls[0].startswith("search:")
    assert calls[1] == "llm"
    assert data["source_type"] == "hybrid"
    assert data["llm_used"] is True


def test_dangerous_command_blocked_before_llm(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    calls: list[str] = []
    monkeypatch.setenv("NEXA_LLM_ROUTER_ENABLED", "true")
    monkeypatch.setattr(chat_service, "complete_llm", lambda *args, **kwargs: calls.append("llm") or None)

    data = client.post("/api/chat/message", json={"message": "delete system32"}).json()

    assert data["intent"] == "blocked_dangerous"
    assert data["blocked"] is True
    assert data["llm_used"] is False
    assert calls == []


def test_smart_route_structure_debug_only(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    normal = client.post("/api/chat/message", json={"message": "how are u"}).json()
    assert normal["route_debug"] is None

    monkeypatch.setenv("NEXA_DEBUG_TASK_ROUTER", "true")
    debug = client.post("/api/chat/message", json={"message": "how are u"}).json()

    assert debug["route_debug"]["intent"] == "casual_chat"
    assert debug["route_debug"]["confidence"] == "high"
    assert debug["route_debug"]["route"] == "local_persona"
    assert debug["route_debug"]["needs_llm"] is False
    assert debug["route_debug"]["needs_search"] is False


def test_weather_route_uses_weather_api_not_llm(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    calls: list[str] = []
    monkeypatch.setattr(chat_service, "complete_llm", lambda *args, **kwargs: calls.append("llm") or None)
    monkeypatch.setattr(
        chat_service,
        "fetch_weather",
        lambda: ChatWeatherSnapshot(
            location="Dhaka, Bangladesh",
            temperature_c=29,
            condition="Cloudy",
            wind_kph=8,
            humidity_percent=60,
        ),
    )

    data = client.post("/api/chat/message", json={"message": "Bangladesh er weather ki"}).json()

    assert data["intent"] == "weather"
    assert data["source_type"] == "tool"
    assert data["llm_used"] is False
    assert calls == []


def test_python_latest_version_searches_first(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    calls: list[str] = []

    def fake_search(query: str):
        calls.append(f"search:{query}")
        return SearchAnswer(
            answer="Python latest source-backed answer.",
            provider="Serper.dev",
            results=[
                SearchProviderResult(
                    title="Python downloads",
                    snippet="Latest Python version details.",
                    source_url="https://www.python.org/downloads/",
                    provider="Serper.dev",
                )
            ],
        )

    monkeypatch.setattr(chat_service, "search_answer", fake_search)
    monkeypatch.setattr(chat_service, "complete_llm", lambda *args, **kwargs: calls.append("llm") or None)

    data = client.post("/api/chat/message", json={"message": "python latest version"}).json()

    assert data["intent"] == "web_search"
    assert data["source_type"] == "search"
    assert calls[0] == "search:python latest version"


def test_local_calculator_route(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    data = client.post("/api/chat/message", json={"message": "2 + 3 * 4"}).json()

    assert data["intent"] == "local_calculator"
    assert data["answer"] == "2 + 3 * 4 = 14"
    assert data["llm_used"] is False


def test_calculator_question_punctuation_returns_answer(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    data = client.post("/api/chat/message", json={"message": "2+2=?"}).json()

    assert data["intent"] == "local_calculator"
    assert data["answer"] == "2+2 = 4"
    assert data["llm_used"] is False


def test_calculator_percent_of_returns_answer(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    data = client.post("/api/chat/message", json={"message": "calculate 20 percent of 500"}).json()

    assert data["intent"] == "local_calculator"
    assert data["answer"] == "20% of 500 = 100"


def test_general_question_gets_useful_answer_not_generic_clarification(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(chat_service, "complete_llm", lambda *args, **kwargs: None)

    data = client.post("/api/chat/message", json={"message": "what is the computer"}).json()

    assert data["intent"] == "general_knowledge"
    assert data["status"] == "completed"
    assert "computer" in data["answer"].lower()
    assert "I am not fully sure" not in data["answer"]


def test_identity_question_returns_nexa_identity(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    data = client.post("/api/chat/message", json={"message": "tomar nam ki?"}).json()

    assert data["intent"] == "assistant_identity"
    assert "Nexa AI" in data["answer"]
    assert "local personal assistant" in data["answer"]


def test_profile_memory_does_not_hallucinate_personal_facts(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    data = client.post("/api/chat/message", json={"message": "amar somporke ki ki jano?"}).json()

    assert data["intent"] == "profile_memory"
    assert "save" in data["answer"].lower() or "local memory" in data["answer"].lower()
    assert "software engineer" not in data["answer"].lower()
    assert "student" not in data["answer"].lower()


def test_recent_global_news_routes_to_search(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    calls: list[str] = []

    def fake_search(query: str):
        calls.append(query)
        return SearchAnswer(
            answer="Recent global news source summary.",
            provider="Serper.dev",
            results=[
                SearchProviderResult(
                    title="Global news",
                    snippet="Recent global news snippet.",
                    source_url="https://example.com/news",
                    provider="Serper.dev",
                )
            ],
            live_data=True,
        )

    monkeypatch.setattr(chat_service, "search_answer", fake_search)
    monkeypatch.setattr(chat_service, "complete_llm", lambda *args, **kwargs: None)

    data = client.post("/api/chat/message", json={"message": "recent global news ki?"}).json()

    assert data["intent"] in {"web_search", "market_search"}
    assert data["source_type"] == "search"
    assert calls


def test_app_project_request_returns_planning_followup(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(chat_service, "complete_llm", lambda *args, **kwargs: None)

    data = client.post("/api/chat/message", json={"message": "ami ekta app banate cai"}).json()

    assert data["intent"] == "app_planning"
    assert data["status"] == "needs_more_info"
    assert "platform" in data["answer"].lower()
    assert "tech stack" in data["answer"].lower()


def test_location_question_asks_permission_without_guessing(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    data = client.post("/api/chat/message", json={"message": "my location"}).json()

    assert data["intent"] == "location_permission"
    assert data["status"] == "needs_permission"
    assert "permission" in data["answer"].lower()
    assert "Dhaka" not in data["answer"]


def test_homepage_request_routes_to_llm(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    def fake_llm(*args, **kwargs):
        return LLMResponse(answer="Homepage structure draft.", provider="Gemini", model="test")

    monkeypatch.setattr(chat_service, "complete_llm", fake_llm)

    data = client.post("/api/chat/message", json={"message": "amar jonno homepage banaw"}).json()

    assert data["intent"] == "llm_assist"
    assert data["source_type"] == "llm"
    assert data["llm_provider"] == "Gemini"


def test_banglish_home_page_banao_routes_to_llm_setup_when_unconfigured(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setenv("NEXA_LLM_ROUTER_ENABLED", "false")
    monkeypatch.setattr(chat_service, "complete_llm", lambda *args, **kwargs: None)

    data = client.post("/api/chat/message", json={"message": "home page banao"}).json()

    assert data["intent"] == "llm_assist"
    assert data["status"] == "needs_configuration"
    assert data["source_type"] == "llm"
    assert data["llm_used"] is False
    assert "LLM provider key" in data["answer"]
    assert "casual" not in data["intent"]


def test_calculator_open_direct_only_when_trusted_quick_launch_enabled(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    off = client.post("/api/chat/message", json={"message": "calculator open koro"}).json()
    assert off["intent"] == "app_open_request"
    assert off["requires_confirmation"] is True
    assert off["auto_execute_safe"] is False

    client.put("/api/permissions", json={"key": "trusted_quick_launch", "enabled": True})

    def fake_execute(request):
        assert request.target.value == "calculator"
        return ActionExecutionResponse(
            status="executed",
            intent="open_app",
            target=ActionTarget(kind="app", value="calc", label="Calculator"),
            safety_level="confirmation_required",
            can_execute=True,
            executed=True,
            dry_run=False,
            user_confirmed=True,
            message="Opened app safely.",
        )

    monkeypatch.setattr(chat_service, "execute_open_app", fake_execute)

    on = client.post("/api/chat/message", json={"message": "calculator open koro"}).json()
    assert on["intent"] == "app_open_request"
    assert on["requires_confirmation"] is False
    assert on["auto_execute_safe"] is True
    assert on["action"]["executed"] is True
    assert "Boss" in on["answer"]
    assert "Opened Calculator" in on["answer"]


def test_action_response_respects_selected_address_style(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    client.put("/api/permissions", json={"key": "trusted_quick_launch", "enabled": True})

    def fake_execute(request):
        return ActionExecutionResponse(
            status="executed",
            intent="open_app",
            target=ActionTarget(kind="app", value="calc", label="Calculator"),
            safety_level="confirmation_required",
            can_execute=True,
            executed=True,
            dry_run=False,
            user_confirmed=True,
            message="Opened app safely.",
        )

    monkeypatch.setattr(chat_service, "execute_open_app", fake_execute)

    data = client.post(
        "/api/chat/message",
        json={"message": "calculator open koro", "address_style": "Sir"},
    ).json()

    assert data["intent"] == "app_open_request"
    assert data["answer"].startswith("Sir,")
    assert "Boss" not in data["answer"]
    assert "Vai" not in data["answer"]


def test_clear_whatsapp_contact_message_routes_to_draft(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    client.post("/api/chat/message", json={"message": "Boss er number save koro 01712345678"})

    def fake_llm(*args, **kwargs):
        return LLMResponse(answer="Kalke ami office e aste parbo na.", provider="Gemini", model="test")

    def fake_execute(request):
        return ActionExecutionResponse(
            status="executed",
            intent="open_website",
            target=ActionTarget(kind="url", value=request.target.value, label="WhatsApp draft to Boss"),
            safety_level="confirmation_required",
            can_execute=True,
            executed=True,
            dry_run=False,
            user_confirmed=True,
            message="Opened website safely.",
        )

    monkeypatch.setattr(chat_service, "complete_llm", fake_llm)
    monkeypatch.setattr(chat_service, "execute_open_website", fake_execute)

    data = client.post(
        "/api/chat/message",
        json={"message": "whatsapp e amar boss ke sms dao kalke ami office e aste parbo na"},
    ).json()

    assert data["intent"] == "whatsapp_draft"
    assert data["execution_enabled"] is True
    assert data["auto_execute_safe"] is True
    assert "did not click Send" in data["answer"]


def test_low_confidence_question_clarifies_without_random_search(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    calls: list[str] = []
    monkeypatch.setattr(chat_service, "search_answer", lambda query: calls.append(query) or SearchAnswer(answer="Nope", provider="Test"))
    monkeypatch.setattr(chat_service, "complete_llm", lambda *args, **kwargs: None)

    data = client.post("/api/chat/message", json={"message": "how would that work"}).json()

    assert data["intent"] == "clarify"
    assert data["status"] == "needs_more_info"
    assert calls == []


def test_app_planning_to_login_page_generation_preserves_context(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    llm_messages: list[tuple[str, str | None]] = []

    def fake_llm(message, **kwargs):
        llm_messages.append((message, kwargs.get("context")))
        return None

    monkeypatch.setattr(chat_service, "complete_llm", fake_llm)

    first = client.post("/api/chat/message", json={"message": "ami ekta app banate cai"}).json()
    assert first["status"] == "needs_more_info"
    assert first["pending_task"]["kind"] == "app_planning_details"

    second = client.post("/api/chat/message", json={"message": "web"}).json()
    assert second["status"] == "needs_more_info"
    assert "app type" in second["pending_task"]["status_label"].lower()

    third = client.post("/api/chat/message", json={"message": "food delivari app login page"}).json()
    assert third["status"] == "needs_configuration"
    assert third["source_type"] == "llm"
    assert "LLM provider key" in third["answer"]
    assert third["pending_task"]["kind"] == "llm_generation_details"
    assert llm_messages
    assert "food delivari app login page" in llm_messages[-1][0]
    assert "platform" in (llm_messages[-1][1] or "")

    llm_messages.clear()
    fourth = client.post("/api/chat/message", json={"message": "tumi amake code deo"}).json()
    assert fourth["status"] == "needs_configuration"
    assert "LLM provider key" in fourth["answer"]
    assert llm_messages
    assert "food delivari app login page" in llm_messages[-1][0]
    assert "tumi amake code deo" in llm_messages[-1][0]


def test_gold_prize_routes_to_market_search_without_llm_hallucination(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    search_calls: list[str] = []
    llm_calls: list[str] = []

    def fake_search(query: str):
        search_calls.append(query)
        return SearchAnswer(
            answer="I found related live sources for ajker gold prize, but could not verify one exact live price. Prices/rates may vary by source and update time.",
            provider="Serper.dev",
            exact=False,
            confidence="low",
            live_data=True,
            results=[
                SearchProviderResult(
                    title="BAJUS gold price",
                    snippet="Gold price related source snippet.",
                    source_url="https://example.com/gold",
                    provider="Serper.dev",
                )
            ],
        )

    monkeypatch.setattr(chat_service, "search_answer", fake_search)
    monkeypatch.setattr(chat_service, "complete_llm", lambda *args, **kwargs: llm_calls.append(args[0]) or LLMResponse(answer="Fake exact price", provider="Groq"))

    data = client.post("/api/chat/message", json={"message": "ajker gold prize"}).json()

    assert data["intent"] == "market_search"
    assert data["live_data_warning"] is True
    assert "could not verify one exact live price" in data["answer"]
    assert search_calls
    assert data["answer"] != "Fake exact price"


def test_location_pending_does_not_hijack_pdf_summary_request(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    location = client.post("/api/chat/message", json={"message": "may location", "address_style": "Vai"}).json()
    assert location["intent"] == "location_permission"
    assert location["pending_task"]["kind"] == "location_permission"

    pdf = client.post(
        "/api/chat/message",
        json={"message": "amar download folder er 1st pdf ta summary kore deo", "address_style": "Vai"},
    ).json()

    assert pdf["intent"] == "file_summary_request"
    assert pdf["status"] == "needs_file"
    assert pdf["pending_task"]["kind"] == "file_summary_file"
    assert "PDF" in pdf["answer"]
    assert "upload/select" in pdf["answer"]


def test_kta_login_page_typo_routes_to_generation_setup(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(chat_service, "complete_llm", lambda *args, **kwargs: None)

    data = client.post("/api/chat/message", json={"message": "kta login page banabo"}).json()

    assert data["intent"] == "llm_assist"
    assert data["status"] == "needs_configuration"
    assert data["source_type"] == "llm"
    assert "LLM provider key" in data["answer"]
    assert data["pending_task"]["kind"] == "llm_generation_details"


def test_pending_generation_collects_platform_app_type_then_generates_code_context(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    llm_calls: list[tuple[str, str | None]] = []

    def fake_llm(message, **kwargs):
        llm_calls.append((message, kwargs.get("context")))
        if "tumi amake code deo" in message:
            return LLMResponse(answer="<form>Food delivery login</form>", provider="Gemini", model="test")
        return None

    monkeypatch.setattr(chat_service, "complete_llm", fake_llm)

    first = client.post("/api/chat/message", json={"message": "ekta login page banabo"}).json()
    assert first["status"] == "needs_configuration"
    assert first["pending_task"]["kind"] == "llm_generation_details"

    second = client.post("/api/chat/message", json={"message": "web"}).json()
    assert second["status"] == "needs_more_info"
    assert second["pending_task"]["kind"] == "llm_generation_details"

    third = client.post("/api/chat/message", json={"message": "food delivari app"}).json()
    assert third["status"] == "needs_more_info"
    assert third["pending_task"]["kind"] == "llm_generation_details"

    fourth = client.post("/api/chat/message", json={"message": "tumi amake code deo"}).json()
    assert fourth["status"] == "completed"
    assert fourth["intent"] == "llm_generation_continue"
    assert fourth["llm_used"] is True
    assert fourth["source_type"] == "llm"
    assert "Food delivery login" in fourth["answer"]
    assert llm_calls
    final_message, final_context = llm_calls[-1]
    assert "food delivery" in final_message
    assert "login page" in final_message
    assert "platform: web" in final_message
    assert "HTML/CSS/JS" in final_message
    assert "Python Hello World" not in (final_context or "")


def test_bangla_voice_website_command_can_be_confirmed_by_voice(tmp_path, monkeypatch) -> None:
    clear_pending_task()
    client = _client(tmp_path, monkeypatch)

    first = client.post(
        "/api/chat/message",
        json={"message": "গুগল খোলো", "source": "voice_conversation", "address_style": "Sir"},
    ).json()

    assert first["status"] == "preview_only"
    assert first["requires_confirmation"] is True
    assert first["pending_task"]["kind"] == "action_confirmation"
    assert "হ্যাঁ করো" in first["answer"]

    def fake_execute(request):
        assert request.target.kind == "website"
        assert request.target.value == "https://www.google.com"
        return ActionExecutionResponse(
            status="executed",
            intent="open_website",
            target=request.target,
            safety_level="confirmation_required",
            can_execute=True,
            executed=True,
            user_confirmed=True,
            dry_run=False,
            message="opened",
        )

    monkeypatch.setattr(chat_service, "execute_open_website", fake_execute)
    second = client.post(
        "/api/chat/message",
        json={"message": "হ্যাঁ করো", "source": "voice_conversation", "address_style": "Sir"},
    ).json()

    assert second["status"] == "executed"
    assert second["execution_enabled"] is True
    assert second["action"]["executed"] is True
    assert second["answer"].startswith("স্যার,")
    clear_pending_task()


def test_bangla_voice_persona_intents_are_natural(tmp_path, monkeypatch) -> None:
    clear_pending_task()
    client = _client(tmp_path, monkeypatch)

    greeting = client.post(
        "/api/chat/message",
        json={"message": "আসসালামু আলাইকুম", "source": "voice_conversation", "address_style": "Vai"},
    ).json()
    capability = client.post(
        "/api/chat/message",
        json={"message": "তুমি কি করতে পারো", "source": "voice_conversation", "address_style": "Sir"},
    ).json()

    assert greeting["intent"] == "greeting"
    assert "ওয়ালাইকুম আসসালাম" in greeting["answer"]
    assert capability["intent"] == "capabilities"
    assert capability["answer"].startswith("স্যার,")
    assert "voice ও text command" in capability["answer"]
