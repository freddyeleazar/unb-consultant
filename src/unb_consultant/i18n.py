"""Internationalization system for unb-consultant.

Detects user locale automatically and loads the appropriate string table.
Override with UNB_LANG environment variable or config setting.
"""

import os
from pathlib import Path

_STRINGS = {
    "en": {
        # General
        "yes": "yes",
        "no": "no",
        "ok": "OK",
        "error": "Error",
        "warning": "Warning",
        "proceed": "Proceed? [y/N]",
        "proceed_yes": "Proceed? [Y/n]",
        "aborted": "Aborted.",
        "done": "Done.",
        "not_found": "Not found: {item}",
        "already_exists": "Already exists: {item}",

        # Auth
        "auth_ok": "Authentication is valid.",
        "auth_expired": "Authentication has expired. Run 'unb auth refresh' or 'unb login'.",
        "auth_checking": "Checking authentication...",
        "auth_login_opening": "Opening browser for Google login...",
        "auth_login_ok": "Login successful. Account: {email}",
        "auth_refreshing": "Refreshing authentication...",
        "auth_refresh_ok": "Authentication refreshed.",

        # Tier
        "tier_detecting": "Detecting NotebookLM subscription tier...",
        "tier_detected": "Tier: {tier} ({limit} sources per notebook)",
        "tier_fallback": "Could not detect tier. Assuming Standard (50 sources).",
        "tier_limit_used": "Using {pct}% of tier limit ({used}/{limit} sources). Space remaining: {free}.",

        # Expert CRUD
        "expert_creating": "Creating expert '{name}'...",
        "expert_created": "Expert '{name}' created.",
        "expert_notebook": "Notebook ID: {id}",
        "expert_list_header": "Registered experts:",
        "expert_list_empty": "No experts registered. Create one with 'unb expert create'.",
        "expert_delete_confirm": "Delete expert '{name}'? This will also delete the notebook from Google. [y/N]",
        "expert_deleted": "Expert '{name}' deleted.",
        "expert_not_found": "Expert '{name}' not found. Available: {available}",
        "expert_name_invalid": "Invalid expert name. Use lowercase letters, numbers, and hyphens only.",
        "expert_name_taken": "Expert '{name}' already exists. Use --force to overwrite.",
        "expert_force": "Expert '{name}' already exists. Overwriting (--force).",

        # Sources
        "sources_uploading": "Uploading {count} source(s)...",
        "sources_ok": "{ok}/{total} sources uploaded successfully.",
        "sources_fail": "{fail} source(s) failed:",
        "sources_waiting": "Waiting for sources to be indexed...",
        "sources_ready": "All sources indexed and ready.",
        "sources_timeout": "Timeout waiting for sources ({count} still processing). You can check later with 'unb source list'.",
        "sources_limit_warn": "This would exceed the tier limit ({limit}). Currently at {current}, adding {adding}.",
        "source_added": "Source added: {title} ({type})",
        "source_plan_header": "Source merging plan for {count} raw files:",
        "source_plan_group": "  [{i}] {name}: {files} files, {size}KB",
        "source_plan_final": "Final: {merged} sources (target: {target}, tier: {tier})",

        # Catalog
        "catalog_generating": "Generating thematic catalog...",
        "catalog_ok": "Catalog generated and saved as note.",
        "catalog_saved": "Catalog written to {path}",
        "catalog_fail": "Catalog generation failed: {reason}",

        # Skill generation
        "skill_detecting": "Detecting project structure...",
        "skill_no_structure": "No skill directory detected. Create .opencode/skills/? [y/N]",
        "skill_creating": "Creating skill at {path}...",
        "skill_created": "Skill created: {path}",
        "skill_exists_same": "SKILL.md already exists for this expert. No changes needed.",
        "skill_exists_diff": "SKILL.md exists but for a different expert. Overwrite? [y/N]",
        "skill_updated": "SKILL.md updated.",
        "skill_agents_found": "AGENTS.md found. Checking for existing entry...",
        "skill_agents_entry_exists": "AGENTS.md already has an entry for this expert. Skipping.",
        "skill_agents_entry_added": "Entry added to AGENTS.md.",
        "skill_agents_not_found": "AGENTS.md not found. Create one? [y/N]",

        # MCP
        "mcp_starting": "Starting unb-consultant MCP server (stdio)...",
        "mcp_tool_confirm": "This action requires confirmation. Run with 'unb mcp' interactively or approve in client.",

        # Merging
        "merger_planning": "Planning source merge for {count} files (tier: {tier}, limit: {limit})...",
        "merger_auto_individual": "{count} files > 50KB kept individually.",
        "merger_auto_merged": "{count} files < 50KB merged into {groups} groups.",
        "merger_target": "Target: {target} sources ({pct}% of {limit}).",

        # Suggestions
        "suggest_catalog": "Generate a thematic catalog of what this expert knows",
        "suggest_skill_gen": "Create a local SKILL.md and update AGENTS.md for this project",
        "next_steps": "Next steps:",

        # Generic errors
        "error_network": "Network error: {msg}. Check your connection.",
        "error_timeout": "Operation timed out after {seconds}s.",
        "error_unexpected": "Unexpected error: {msg}",
    },
    "es": {
        # General
        "yes": "sí",
        "no": "no",
        "ok": "OK",
        "error": "Error",
        "warning": "Aviso",
        "proceed": "Proceder? [y/N]",
        "proceed_yes": "Proceder? [Y/n]",
        "aborted": "Cancelado.",
        "done": "Listo.",
        "not_found": "No encontrado: {item}",
        "already_exists": "Ya existe: {item}",

        # Auth
        "auth_ok": "Autenticación válida.",
        "auth_expired": "Autenticación expirada. Ejecuta 'unb auth refresh' o 'unb login'.",
        "auth_checking": "Verificando autenticación...",
        "auth_login_opening": "Abriendo navegador para login de Google...",
        "auth_login_ok": "Login exitoso. Cuenta: {email}",
        "auth_refreshing": "Renovando autenticación...",
        "auth_refresh_ok": "Autenticación renovada.",

        # Tier
        "tier_detecting": "Detectando plan de NotebookLM...",
        "tier_detected": "Plan: {tier} ({limit} fuentes por cuaderno)",
        "tier_fallback": "No se pudo detectar el plan. Asumiendo Standard (50 fuentes).",
        "tier_limit_used": "Usando {pct}% del límite ({used}/{limit} fuentes). Espacio restante: {free}.",

        # Expert CRUD
        "expert_creating": "Creando experto '{name}'...",
        "expert_created": "Experto '{name}' creado.",
        "expert_notebook": "ID del cuaderno: {id}",
        "expert_list_header": "Expertos registrados:",
        "expert_list_empty": "No hay expertos registrados. Crea uno con 'unb expert create'.",
        "expert_delete_confirm": "Borrar experto '{name}'? También borrará el cuaderno de Google. [y/N]",
        "expert_deleted": "Experto '{name}' eliminado.",
        "expert_not_found": "Experto '{name}' no encontrado. Disponibles: {available}",
        "expert_name_invalid": "Nombre de experto inválido. Usa solo minúsculas, números y guiones.",
        "expert_name_taken": "El experto '{name}' ya existe. Usa --force para sobrescribir.",
        "expert_force": "El experto '{name}' ya existe. Sobrescribiendo (--force).",

        # Sources
        "sources_uploading": "Subiendo {count} fuente(s)...",
        "sources_ok": "{ok}/{total} fuentes subidas exitosamente.",
        "sources_fail": "{fail} fuente(s) fallaron:",
        "sources_waiting": "Esperando a que las fuentes sean indexadas...",
        "sources_ready": "Todas las fuentes indexadas y listas.",
        "sources_timeout": "Tiempo de espera agotado ({count} aún procesando). Puedes verificar luego con 'unb source list'.",
        "sources_limit_warn": "Esto excedería el límite del plan ({limit}). Actualmente {current}, añadiendo {adding}.",
        "source_added": "Fuente añadida: {title} ({type})",
        "source_plan_header": "Plan de merging para {count} archivos fuente:",
        "source_plan_group": "  [{i}] {name}: {files} archivos, {size}KB",
        "source_plan_final": "Final: {merged} fuentes (objetivo: {target}, plan: {tier})",

        # Catalog
        "catalog_generating": "Generando catálogo temático...",
        "catalog_ok": "Catálogo generado y guardado como nota.",
        "catalog_saved": "Catálogo escrito en {path}",
        "catalog_fail": "Error al generar catálogo: {reason}",

        # Skill generation
        "skill_detecting": "Detectando estructura del proyecto...",
        "skill_no_structure": "No se detectó directorio de skills. Crear .opencode/skills/? [y/N]",
        "skill_creating": "Creando skill en {path}...",
        "skill_created": "Skill creado: {path}",
        "skill_exists_same": "SKILL.md ya existe para este experto. Sin cambios.",
        "skill_exists_diff": "SKILL.md existe pero para otro experto. Sobrescribir? [y/N]",
        "skill_updated": "SKILL.md actualizado.",
        "skill_agents_found": "AGENTS.md encontrado. Verificando entrada existente...",
        "skill_agents_entry_exists": "AGENTS.md ya tiene una entrada para este experto. Omitiendo.",
        "skill_agents_entry_added": "Entrada añadida a AGENTS.md.",
        "skill_agents_not_found": "AGENTS.md no encontrado. Crear uno? [y/N]",

        # MCP
        "mcp_starting": "Iniciando servidor MCP de unb-consultant (stdio)...",
        "mcp_tool_confirm": "Esta acción requiere confirmación. Ejecuta 'unb mcp' interactivamente o aprueba en el cliente.",

        # Merging
        "merger_planning": "Planificando merge de {count} archivos (plan: {tier}, límite: {limit})...",
        "merger_auto_individual": "{count} archivos > 50KB mantenidos individualmente.",
        "merger_auto_merged": "{count} archivos < 50KB fusionados en {groups} grupos.",
        "merger_target": "Objetivo: {target} fuentes ({pct}% de {limit}).",

        # Suggestions
        "suggest_catalog": "Generar un cat\u00e1logo tem\u00e1tico de lo que sabe este experto",
        "suggest_skill_gen": "Crear un SKILL.md local y actualizar AGENTS.md para este proyecto",
        "next_steps": "Siguientes pasos:",

        # Generic errors
        "error_network": "Error de red: {msg}. Verifica tu conexión.",
        "error_timeout": "Operación agotó el tiempo de espera ({seconds}s).",
        "error_unexpected": "Error inesperado: {msg}",
    },
}

_DEFAULT_LANG = "en"


def _detect_lang() -> str:
    """Detect user language from environment, config, or system locale."""
    env_lang = os.environ.get("UNB_LANG")
    if env_lang and env_lang in _STRINGS:
        return env_lang

    try:
        import os as _os
        sys_lang = _os.environ.get("LANG") or _os.environ.get("LC_ALL") or _os.environ.get("LC_MESSAGES", "")
        if sys_lang:
            code = sys_lang[:2].lower()
            if code in _STRINGS:
                return code
    except Exception:
        pass

    return _DEFAULT_LANG


class LazyStr:
    """Lazy string that resolves at format time with given kwargs."""

    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs

    def __str__(self):
        return _(self.key, **self.kwargs)

    def __repr__(self):
        return f"LazyStr({self.key}, {self.kwargs})"


class Translator:
    """Simple translator that loads string tables by language code."""

    def __init__(self, lang: str | None = None):
        self.lang = lang or _detect_lang()
        if self.lang not in _STRINGS:
            self.lang = _DEFAULT_LANG
        self.table = _STRINGS[self.lang]

    def get(self, key: str, **kwargs) -> str:
        """Get translated string for key, formatted with kwargs."""
        template = self.table.get(key)
        if template is None:
            if self.lang != _DEFAULT_LANG:
                template = _STRINGS[_DEFAULT_LANG].get(key, key)
            else:
                template = key
        if kwargs:
            try:
                return template.format(**kwargs)
            except KeyError:
                return template
        return template

    def __call__(self, key: str, **kwargs) -> str:
        return self.get(key, **kwargs)

    def lazy(self, key: str, **kwargs) -> LazyStr:
        """Return a lazy string object (for CLI decorators)."""
        return LazyStr(key, **kwargs)


# Global translator instance
_current: Translator = Translator()


def _(key: str, **kwargs) -> str:
    """Global translate function."""
    return _current.get(key, **kwargs)


def set_lang(lang: str):
    """Override global language."""
    global _current
    _current = Translator(lang)


def get_lang() -> str:
    """Get current language code."""
    return _current.lang
