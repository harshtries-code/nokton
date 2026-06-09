"""Quick smoke test for Phase 1 fixes."""
import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def test_providers_list():
    from backend.providers import registry
    ps = registry.list_providers()
    assert len(ps) == 9, f"expected 9 providers, got {len(ps)}"
    ids = {p["id"] for p in ps}
    expected = {"openrouter", "openai", "anthropic", "deepseek", "google", "groq", "ollama", "custom", "opencode"}
    assert ids == expected, f"provider ids mismatch: {ids} != {expected}"
    print(f"  OK: {len(ps)} providers registered")


def test_config_to_dict_includes_providers():
    from backend.config import Config, ProviderAuth
    c = Config()
    c.providers["openrouter"] = ProviderAuth(api_key="sk-test-1234", base_url="https://openrouter.ai/api/v1")
    d = c.to_dict()
    assert "providers" in d, "providers missing from to_dict"
    assert d["providers"]["openrouter"]["api_key"] == "sk-test-1234", "api key not preserved"
    print("  OK: config.to_dict() includes providers")


def test_config_save_load_roundtrip():
    import os
    from backend.config import Config, ProviderAuth, USER_CONFIG_PATH
    if USER_CONFIG_PATH.exists():
        USER_CONFIG_PATH.unlink()
    c = Config()
    c.providers["openrouter"] = ProviderAuth(api_key="sk-roundtrip-9999", base_url="https://openrouter.ai/api/v1")
    c.save()
    c2 = Config.load()
    assert c2.providers.get("openrouter") is not None, "openrouter missing after reload"
    assert c2.providers["openrouter"].api_key == "sk-roundtrip-9999", f"expected key preserved, got {c2.providers['openrouter'].api_key!r}"
    print("  OK: config save/load preserves api keys")
    if USER_CONFIG_PATH.exists():
        USER_CONFIG_PATH.unlink()


def test_model_catalog_roundtrip():
    from backend.providers.model_catalog import ModelCatalog, CACHE_PATH
    from backend.providers.base import ModelInfo, ModelCapabilities, ModelPricing
    if CACHE_PATH.exists():
        CACHE_PATH.unlink()
    catalog = ModelCatalog()
    models = [
        ModelInfo(id="gpt-4o", provider_id="openai", name="GPT-4o", context_window=128000,
                  capabilities=ModelCapabilities(vision=True),
                  pricing=ModelPricing(input_per_1m=2.5, output_per_1m=10.0, is_free=False)),
    ]
    catalog.update("openai", models)
    catalog2 = ModelCatalog()
    loaded = catalog2.load_cache()
    assert loaded, "cache did not load"
    m = catalog2.find_model("gpt-4o")
    assert m is not None, "model not found after reload"
    assert m.pricing is not None, "pricing is None after reload"
    assert m.pricing.input_per_1m == 2.5, f"expected 2.5, got {m.pricing.input_per_1m}"
    assert m.capabilities.vision is True, "capabilities lost"
    print("  OK: model catalog roundtrip preserves pricing+capabilities")
    if CACHE_PATH.exists():
        CACHE_PATH.unlink()


def test_all_tools_register():
    from backend.tools import tool_registry
    tools = tool_registry.list_tools()
    assert len(tools) == 32, f"expected 32 tools, got {len(tools)}"
    print(f"  OK: {len(tools)} tools registered (no import errors)")


def test_command_injection_blocked():
    from backend.tools import tool_registry
    import asyncio
    async def run():
        return await tool_registry.execute("run_command", {"exe": "rm", "args": ["-rf", "/"]}, None)
    r = asyncio.run(run())
    assert not r.get("success", True) or "not in the allowlist" in (r.get("output") or ""), \
        f"command injection should be blocked: {r}"
    print("  OK: terminal.run_command blocks non-allowlisted exes")


def test_powershell_dangerous_blocked():
    from backend.tools import tool_registry
    import asyncio
    async def run():
        return await tool_registry.execute("run_powershell", {"command": "Invoke-Expression 'evil'"}, None)
    r = asyncio.run(run())
    assert "blocked" in (r.get("output") or "").lower(), f"powershell injection should be blocked: {r}"
    print("  OK: terminal.run_powershell blocks Invoke-Expression")


def test_search_files_relative_to():
    from backend.tools import tool_registry
    import asyncio
    from backend.config import ToolsConfig
    async def run():
        return await tool_registry.execute("search_files", {"query": "*.md", "folder": "C:/Windows/System32/drivers/etc"}, ToolsConfig())
    r = asyncio.run(run())
    # Should not crash with ValueError
    assert r.get("success"), f"search_files crashed: {r}"
    print("  OK: search_files handles paths outside search root")


def test_delete_file_recursive():
    import os, tempfile
    from backend.tools import tool_registry
    import asyncio
    from backend.config import ToolsConfig
    async def run():
        with tempfile.TemporaryDirectory() as tmp:
            nested = os.path.join(tmp, "subdir")
            os.makedirs(nested)
            with open(os.path.join(nested, "file.txt"), "w") as f:
                f.write("x")
            return await tool_registry.execute("delete_file", {"path": tmp, "recursive": True}, ToolsConfig())
    r = asyncio.run(run())
    assert r.get("success"), f"delete_file recursive failed: {r}"
    print("  OK: delete_file recursive removes non-empty directories")


def test_permission_unknown_category():
    from backend.tools.permission import get_permission_level, PermissionLevel
    from backend.config import ToolsConfig
    cfg = ToolsConfig()
    # Unknown category with requires_confirm=True should still ASK but not raise
    level = get_permission_level("totally-fake-category", requires_confirm=True, tools_config=cfg)
    assert level == PermissionLevel.ASK, f"unknown+confirm should ASK, got {level}"
    # User safe_categories override
    cfg2 = ToolsConfig()
    cfg2.safe_categories = ["file_write"]
    level = get_permission_level("file_write", requires_confirm=True, tools_config=cfg2)
    assert level == PermissionLevel.AUTO, f"user-configured safe should win, got {level}"
    print("  OK: permission system honors user config over requires_confirm")


def test_cost_tracker_session_cost_persists():
    from backend.agent.cost_tracker import CostTracker
    from backend.providers.model_catalog import ModelCatalog
    from backend.providers.base import ModelInfo, ModelPricing
    catalog = ModelCatalog()
    catalog.update("openai", [ModelInfo(id="gpt-4o", provider_id="openai", name="GPT-4o",
                                        pricing=ModelPricing(input_per_1m=2.5, output_per_1m=10.0))])
    ct = CostTracker(catalog=catalog)
    ct.add_usage("openai", "gpt-4o", 1_000_000, 0)  # $2.50
    assert abs(ct.session_cost - 2.5) < 0.001, f"expected 2.5, got {ct.session_cost}"
    ct.reset_session()
    assert ct.session_cost == 0.0, f"after reset should be 0, got {ct.session_cost}"
    ct.add_usage("openai", "gpt-4o", 1_000_000, 0)
    assert abs(ct.session_cost - 2.5) < 0.001, f"after reset+add, expected 2.5, got {ct.session_cost}"
    print("  OK: CostTracker.session_cost survives reset_session")


def test_engine_runs_with_no_key():
    import asyncio
    from backend.config import Config
    from backend.providers import registry as provider_registry
    from backend.tools.registry import tool_registry
    from backend.agent.engine import AgentEngine
    from backend.agent.conversation_manager import ConversationManager
    from backend.agent.cost_tracker import CostTracker
    from backend.providers.model_catalog import ModelCatalog

    async def run():
        config = Config.load()
        engine = AgentEngine(
            provider_registry=provider_registry,
            tool_registry=tool_registry,
            config=config,
            conversation_manager=ConversationManager(),
            cost_tracker=CostTracker(catalog=ModelCatalog()),
        )
        events = []
        async for ev in engine.run_conversation("hi"):
            events.append(ev)
            if ev.get("type") in ("error", "assistant_done", "interrupted"):
                break
        return events

    events = asyncio.run(run())
    types = [e.get("type") for e in events]
    assert "error" in types or "assistant_done" in types, f"engine produced no terminal event: {types}"
    print(f"  OK: engine runs end-to-end (no key, but no crash) — events: {types[:5]}")


if __name__ == "__main__":
    print("=== Phase 1 smoke tests ===")
    for fn in [
        test_providers_list,
        test_config_to_dict_includes_providers,
        test_config_save_load_roundtrip,
        test_model_catalog_roundtrip,
        test_all_tools_register,
        test_command_injection_blocked,
        test_powershell_dangerous_blocked,
        test_search_files_relative_to,
        test_delete_file_recursive,
        test_permission_unknown_category,
        test_cost_tracker_session_cost_persists,
        test_engine_runs_with_no_key,
    ]:
        try:
            fn()
        except AssertionError as e:
            print(f"  FAIL: {fn.__name__}: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"  ERROR: {fn.__name__}: {type(e).__name__}: {e}")
            sys.exit(1)
    print("\nAll Phase 1 tests passed.")
