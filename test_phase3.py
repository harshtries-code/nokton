import sys
import json
import tempfile
from pathlib import Path


def test_estimate_tokens():
    from backend.agent.context_compressor import estimate_tokens
    from backend.providers.base import Message
    msgs = [
        Message(role="user", content="hello world"),
        Message(role="assistant", content="hi there"),
    ]
    tokens = estimate_tokens(msgs)
    assert tokens > 0, f"estimate_tokens should be > 0, got {tokens}"


def test_compressor_compresses():
    from backend.agent.context_compressor import ContextCompressor
    from backend.providers.base import Message
    msgs = [Message(role="system", content="You are helpful")]
    msgs += [Message(role="user", content=f"msg {i}") for i in range(20)]
    msgs += [Message(role="assistant", content=f"reply {i}") for i in range(20)]
    c = ContextCompressor(protect_first_n=3, protect_last_n=5)
    out = c.compress(msgs)
    assert len(out) < len(msgs), f"compressed should be smaller ({len(out)} < {len(msgs)})"
    has_summary = any(isinstance(m.content, str) and "summary" in m.content.lower() for m in out)
    assert has_summary, "compressed messages should contain summary"


def test_compressor_no_op_for_short():
    from backend.agent.context_compressor import ContextCompressor
    from backend.providers.base import Message
    msgs = [Message(role="user", content="hi")]
    c = ContextCompressor()
    out = c.compress(msgs)
    assert len(out) == len(msgs)


def test_skill_manager_discovers_skill_md(tmp_path=None):
    from backend.agent.skill_manager import SkillManager
    if tmp_path is None:
        tmp_path = Path(tempfile.mkdtemp())
    skill = tmp_path / "SKILL.md"
    skill.write_text("# My skill\nDo this thing.", encoding="utf-8")
    sm = SkillManager(search_paths=[tmp_path])
    found = sm.discover()
    assert skill in found
    content = sm.load_all()
    assert "My skill" in content


def test_skill_manager_empty_dir():
    from backend.agent.skill_manager import SkillManager
    sm = SkillManager(search_paths=[Path(tempfile.mkdtemp())])
    assert sm.load_all() == ""


def test_conversation_search():
    from backend.agent.conversation_manager import ConversationManager
    with tempfile.TemporaryDirectory() as td:
        cm = ConversationManager(storage_dir=td)
        c = cm.create(provider="openrouter", model="x")
        cm.add_message("user", "How do I bake sourdough bread?")
        cm.add_message("assistant", "First you need a starter.")
        cm.save()
        results = cm.search("sourdough")
        assert len(results) == 1
        assert results[0]["id"] == c.id
        results2 = cm.search("zzzzz")
        assert len(results2) == 0
        results3 = cm.search("")
        assert results3 == []


def test_conversation_set_title():
    from backend.agent.conversation_manager import ConversationManager
    with tempfile.TemporaryDirectory() as td:
        cm = ConversationManager(storage_dir=td)
        c = cm.create(provider="openrouter", model="x")
        cm.save()
        assert cm.set_title(c.id, "New Title")
        loaded = cm.load(c.id)
        assert loaded.title == "New Title"
        assert not cm.set_title("nope", "x")


def test_config_fallback_providers_default():
    from backend.config import Config, ModelConfig
    cfg = Config()
    assert cfg.model.fallback_providers == []


def test_config_to_dict_includes_fallback():
    from backend.config import Config
    cfg = Config()
    cfg.model.fallback_providers = ["openai", "anthropic"]
    d = cfg.to_dict()
    assert d["model"]["fallback_providers"] == ["openai", "anthropic"]


def test_api_key_manager_roundtrip():
    from backend.util import api_key_manager as akm_mod
    from backend.util.api_key_manager import ApiKeyManager
    with tempfile.TemporaryDirectory() as td:
        salt = Path(td) / ".salt"
        keys_path = str(Path(td) / "keys.enc")
        akm_mod.SALT_FILE = salt
        km = ApiKeyManager(storage_path=keys_path)
        km.set_key("openrouter", "sk-test-12345")
        km2 = ApiKeyManager(storage_path=keys_path)
        assert km2.get_key("openrouter") == "sk-test-12345"


def test_config_uses_api_key_manager():
    from backend.config import Config
    from backend.util import api_key_manager as akm_mod
    from backend.util.api_key_manager import ApiKeyManager
    with tempfile.TemporaryDirectory() as td:
        salt = Path(td) / ".salt"
        keys_path = str(Path(td) / "keys.enc")
        akm_mod.SALT_FILE = salt
        km = ApiKeyManager(storage_path=keys_path)
        km.set_key("openrouter", "sk-encrypted-1")
        cfg = Config()
        cfg.set_key_manager(km)
        assert cfg.get_provider_api_key("openrouter") == "sk-encrypted-1"
        cfg.set_provider_api_key("anthropic", "sk-anthro-1")
        assert km.get_key("anthropic") == "sk-anthro-1"


def test_engine_picks_provider_fallback():
    from backend.agent.engine import AgentEngine
    from backend.config import Config
    from backend.providers import registry as provider_registry
    from backend.tools.registry import tool_registry
    cfg = Config()
    cfg.model.fallback_providers = ["ollama"]
    eng = AgentEngine(
        provider_registry=provider_registry,
        tool_registry=tool_registry,
        config=cfg,
    )
    provider, pid = eng._pick_provider("nonexistent")
    assert pid == "ollama"
    assert provider is not None


def test_engine_no_fallback_returns_none():
    from backend.agent.engine import AgentEngine
    from backend.config import Config
    from backend.providers import registry as provider_registry
    from backend.tools.registry import tool_registry
    cfg = Config()
    cfg.model.fallback_providers = []
    eng = AgentEngine(
        provider_registry=provider_registry,
        tool_registry=tool_registry,
        config=cfg,
    )
    provider, pid = eng._pick_provider("nonexistent")
    assert provider is None
    assert pid == "nonexistent"


def test_engine_provider_has_credentials_ollama():
    from backend.agent.engine import AgentEngine
    from backend.config import Config
    from backend.providers import registry as provider_registry
    from backend.tools.registry import tool_registry
    cfg = Config()
    eng = AgentEngine(
        provider_registry=provider_registry,
        tool_registry=tool_registry,
        config=cfg,
    )
    assert eng._provider_has_credentials("ollama") is True


def test_cost_endpoints_registered():
    from backend import main
    paths = {r.path for r in main.app.routes if hasattr(r, "path")}
    assert "/api/cost" in paths
    assert "/api/cost/reset" in paths
    assert "/api/conversations-search" in paths


def test_skill_manager_handles_missing_dir():
    from backend.agent.skill_manager import SkillManager
    sm = SkillManager(search_paths=[Path("Z:/nonexistent/path/here")])
    assert sm.discover() == []
    assert sm.load_all() == ""


def test_engine_build_messages_passes_images():
    from backend.agent.engine import AgentEngine
    from backend.config import Config
    from backend.providers import registry as provider_registry
    from backend.tools.registry import tool_registry
    from backend.providers.base import ContentImage, ContentText

    cfg = Config()
    eng = AgentEngine(
        provider_registry=provider_registry,
        tool_registry=tool_registry,
        config=cfg,
    )
    fake_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNgAAIAAAUAAen63NgAAAAASUVORK5CYII="
    msgs = eng._build_messages("describe this", [fake_b64])
    last = msgs[-1]
    assert last.role == "user"
    assert isinstance(last.content, list), f"expected multimodal list, got {type(last.content)}"
    has_image = any(isinstance(p, ContentImage) for p in last.content)
    has_text = any(isinstance(p, ContentText) and "describe this" in p.text for p in last.content)
    assert has_image, "ContentImage missing from multimodal user message"
    assert has_text, "ContentText with user input missing from multimodal user message"


def test_engine_build_messages_text_only():
    from backend.agent.engine import AgentEngine
    from backend.config import Config
    from backend.providers import registry as provider_registry
    from backend.tools.registry import tool_registry

    cfg = Config()
    eng = AgentEngine(
        provider_registry=provider_registry,
        tool_registry=tool_registry,
        config=cfg,
    )
    msgs = eng._build_messages("hello", None)
    last = msgs[-1]
    assert last.role == "user"
    assert isinstance(last.content, str), f"expected str for no-images path, got {type(last.content)}"
    assert last.content == "hello"


def main():
    print("=== Phase 3 smoke tests ===")
    tests = [
        test_estimate_tokens,
        test_compressor_compresses,
        test_compressor_no_op_for_short,
        test_skill_manager_discovers_skill_md,
        test_skill_manager_empty_dir,
        test_conversation_search,
        test_conversation_set_title,
        test_config_fallback_providers_default,
        test_config_to_dict_includes_fallback,
        test_api_key_manager_roundtrip,
        test_config_uses_api_key_manager,
        test_engine_picks_provider_fallback,
        test_engine_no_fallback_returns_none,
        test_engine_provider_has_credentials_ollama,
        test_cost_endpoints_registered,
        test_skill_manager_handles_missing_dir,
        test_engine_build_messages_passes_images,
        test_engine_build_messages_text_only,
    ]
    for t in tests:
        try:
            t()
            print(f"  OK: {t.__name__}")
        except Exception as e:
            print(f"  FAIL: {t.__name__}: {e}")
            import traceback
            traceback.print_exc()
            return 1
    print("All Phase 3 tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
