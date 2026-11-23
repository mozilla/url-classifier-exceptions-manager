import asyncio

from url_classifier_exceptions_manager import auto, remoteSettings


def run_auto(monkeypatch, current_records):
    bug = {
        "id": 1234567,
        "url": "https://www.example.com/page",
        "whiteboard": "[privacy-team:diagnosed][exception-baseline]",
        "cf_user_story": "impact:site-broken\r\ntrackers-blocked:tracker.example.net\r\nclassifier-features:tracking-protection",
        "status": "NEW",
    }
    added = []

    async def fake_list_exceptions(*_):
        return current_records

    async def fake_deployed_records(*_):
        return []

    async def fake_add_exceptions(_server, _auth, new_exceptions, **_):
        added.extend(new_exceptions)

    async def fake_request_review(*_, **__):
        pass

    monkeypatch.setattr(auto, "fetch_bug_data", lambda *_: {"bugs": [bug]})
    monkeypatch.setattr(auto, "list_exceptions", fake_list_exceptions)
    monkeypatch.setattr(auto, "get_deployed_records", fake_deployed_records)
    monkeypatch.setattr(auto, "add_exceptions", fake_add_exceptions)
    monkeypatch.setattr(auto, "request_review_exceptions", fake_request_review)

    asyncio.run(auto.auto_deploy_exceptions("dev", "token", is_prod_server=False))
    return added


def test_auto_deploys_one_unfiltered_entry_per_domain(monkeypatch):
    added = run_auto(monkeypatch, [])

    assert added == [{
        "bugIds": ["1234567"],
        "urlPattern": "*://tracker.example.net/*",
        "classifierFeatures": ["tracking-protection"],
        "category": "baseline",
        "topLevelUrlPattern": "*://www.example.com/*",
    }]


def test_auto_skips_bug_whose_unfiltered_entry_exists(monkeypatch):
    existing = {
        "id": "existing-id",
        "bugIds": ["1234567"],
        "urlPattern": "*://tracker.example.net/*",
        "classifierFeatures": ["tracking-protection"],
        "category": "baseline",
        "topLevelUrlPattern": "*://www.example.com/*",
    }

    assert run_auto(monkeypatch, [existing]) == []


def test_add_exceptions_updates_legacy_entry_in_place(monkeypatch):
    legacy = {
        "id": "legacy-id",
        "bugIds": ["1234567"],
        "urlPattern": "*://tracker.example.net/*",
        "classifierFeatures": ["tracking-protection"],
        "category": "baseline",
        "topLevelUrlPattern": "*://www.example.com/*",
        "filterContentBlockingCategories": [],
        "filter_expression": 'env.version|versionCompare("142.0a1") >= 0',
    }
    new_entry = {k: v for k, v in legacy.items()
                 if k not in ("id", "filterContentBlockingCategories", "filter_expression")}
    written = []

    class FakeClient:
        async def update_record(self, id, data):
            written.append((id, dict(data)))
            return True

    async def fake_get_exceptions(*_):
        return [legacy]

    monkeypatch.setattr(remoteSettings, "get_exceptions", fake_get_exceptions)
    monkeypatch.setattr(remoteSettings, "get_async_client", lambda *_: FakeClient())

    asyncio.run(remoteSettings.add_exceptions("dev", "token", [new_entry], is_dev=True, force=True))

    assert written == [("legacy-id", {**new_entry, "id": "legacy-id"})]
