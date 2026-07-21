"""Tests for unb-consultant core modules."""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from unb_consultant.i18n import _, set_lang, Translator, get_lang
from unb_consultant.config import Config, reset_config, get_config, CONFIG_PATH
from unb_consultant.merger import plan_merge, execute_merge, _extract_keywords, _keyword_affinity


# Module-level backup of the real config (taken ONCE before any test runs)
_CONFIG_BACKUP = CONFIG_PATH.read_bytes() if CONFIG_PATH.exists() else None


@pytest.fixture(autouse=True)
def isolate_config():
    """Backup and restore the real config file around each test.
    
    Tests must NEVER write to the real config file. This fixture
    ensures isolation by backing up the real config once at module
    load time and restoring it after each test.
    """
    reset_config()
    yield
    reset_config()
    if _CONFIG_BACKUP is not None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_bytes(_CONFIG_BACKUP)
    else:
        if CONFIG_PATH.exists():
            CONFIG_PATH.unlink()


class TestI18n:
    def test_spanish(self):
        set_lang("es")
        assert _("auth_ok") == "Autenticación válida."
        assert _("expert_created", name="test") == "Experto 'test' creado."

    def test_english(self):
        set_lang("en")
        assert _("auth_ok") == "Authentication is valid."
        assert _("expert_created", name="test") == "Expert 'test' created."

    def test_fallback(self):
        """Unknown keys should return the key itself."""
        set_lang("en")
        result = _("nonexistent_key_xyz")
        assert result == "nonexistent_key_xyz"

    def test_lazy_str(self):
        t = Translator("en")
        lazy = t.lazy("proceed")
        assert "Proceed" in str(lazy)

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("UNB_LANG", "es")
        t = Translator()
        assert t.lang == "es"


class TestConfig:
    def test_default_values(self):
        reset_config()
        c = get_config()
        assert c.expert_count() == 0
        assert c.tier is None

    def test_add_remove_expert(self):
        reset_config()
        c = get_config()
        c.add_expert("test-expert", {
            "notebook_id": "abc-123",
            "title": "Test Expert",
        })
        assert c.expert_count() == 1
        assert c.get_expert("test-expert")["notebook_id"] == "abc-123"
        c.remove_expert("test-expert")
        assert c.expert_count() == 0

    def test_list_experts(self):
        reset_config()
        c = get_config()
        c.add_expert("exp1", {"notebook_id": "1"})
        c.add_expert("exp2", {"notebook_id": "2"})
        experts = c.list_experts()
        assert len(experts) == 2


class TestMerger:
    def test_extract_keywords(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Entity Template\nThis document describes XML entity templates and inheritance.\n")
        kw = _extract_keywords(f)
        assert "entity" in kw
        assert "template" in kw
        assert "inheritance" in kw
        assert "describes" in kw
        assert "inheritance" in kw
        # Stopwords filtered
        assert "this" not in kw
        assert "and" not in kw

    def test_keyword_affinity(self):
        s1 = {"entity", "template", "xml", "inheritance"}
        s2 = {"entity", "template", "gui", "javascript"}
        score = _keyword_affinity(s1, s2)
        assert 0.0 < score <= 1.0
        assert score == pytest.approx(2 / 6, rel=0.01)

        # Empty sets
        assert _keyword_affinity(set(), s1) == 0.0
        assert _keyword_affinity(s1, set()) == 0.0

    def test_plan_merge_no_merge_needed(self, tmp_path):
        """When under target count, no merging occurs."""
        files = []
        for name in ["aa.md", "bb.md", "cc.md"]:
            f = tmp_path / name
            f.write_text(f"# {name}\nContent\n")
            files.append(f)

        plan = plan_merge(files, target_count=5, tier_limit=50)
        assert plan.merged_count == 3  # All kept individual
        assert plan.raw_count == 3

    def test_plan_merge_merges_small_files(self, tmp_path):
        """When over target, small files with keyword affinity merge."""
        files = []
        # Create 10 files, 5 with similar keywords
        for i in range(5):
            f = tmp_path / f"entity_{i}.md"
            f.write_text(f"# Entity {i}\nentity template xml inheritance.\n")
            files.append(f)
        for i in range(5):
            f = tmp_path / f"gui_{i}.md"
            f.write_text(f"# GUI {i}\ngui interface javascript button.\n")
            files.append(f)

        plan = plan_merge(files, target_count=5, tier_limit=50,
                          large_file_threshold=1024 * 1024)  # All considered small
        assert plan.merged_count <= 5  # Merged down to target
        assert plan.raw_count == 10

    def test_execute_merge(self, tmp_path):
        """Execute merge produces concatenated files."""
        files = []
        for name in ["a.md", "b.md"]:
            f = tmp_path / name
            f.write_text(f"Content of {name}\n")
            files.append(f)

        plan = plan_merge(files, target_count=3, tier_limit=50)
        out_dir = tmp_path / "merged"
        written = execute_merge(plan, out_dir)

        assert len(written) == plan.merged_count
        for w in written:
            assert w.exists()
            assert w.stat().st_size > 0
