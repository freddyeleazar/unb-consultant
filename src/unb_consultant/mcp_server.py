"""MCP Server for unb-consultant.

Provides tools for AI agents to create and query NotebookLM experts
via the Model Context Protocol (stdio transport).
"""

import json
import sys
from pathlib import Path

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from unb_consultant.i18n import _
from unb_consultant.auth import auth_check, login, refresh
from unb_consultant.config import get_config
from unb_consultant.expert import create_expert, list_experts, delete_expert
from unb_consultant.ask import ask_expert
from unb_consultant.catalog import generate_catalog
from unb_consultant.skill_gen import generate_skill
from unb_consultant.source import add_sources
from unb_consultant.tier import detect_tier


def create_server() -> "Server | None":
    """Create and configure the MCP server.
    
    Returns None if mcp package is not available.
    """
    if not MCP_AVAILABLE:
        return None

    server = Server("unb-consultant")

    # ─── Tool definitions ───

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="create_expert",
                description="Create a new NotebookLM expert from URLs, files, or directories. REQUIRES USER CONFIRMATION.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Expert name (lowercase, hyphens allowed)"},
                        "description": {"type": "string", "description": "Description of the expert"},
                        "urls": {"type": "array", "items": {"type": "string"}, "description": "Source URLs"},
                        "files": {"type": "array", "items": {"type": "string"}, "description": "Local file paths"},
                        "directory": {"type": "string", "description": "Directory with source files"},
                        "drive_docs": {"type": "array", "items": {"type": "string"}, "description": "Google Drive document IDs"},
                        "auto": {"type": "boolean", "description": "Auto-generate catalog and skill after creation"},
                        "dry_run": {"type": "boolean", "description": "Preview merge plan without uploading"},
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="ask_expert",
                description="Ask a question to a NotebookLM expert. Gets cited answer from sources.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Expert name"},
                        "question": {"type": "string", "description": "Question to ask"},
                        "json_output": {"type": "boolean", "description": "Return structured JSON with references"},
                    },
                    "required": ["name", "question"],
                },
            ),
            Tool(
                name="list_experts",
                description="List all registered NotebookLM experts.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="add_sources",
                description="Add sources to an existing expert. REQUIRES USER CONFIRMATION.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Expert name"},
                        "urls": {"type": "array", "items": {"type": "string"}, "description": "Source URLs"},
                        "files": {"type": "array", "items": {"type": "string"}, "description": "Local file paths"},
                        "directory": {"type": "string", "description": "Directory with source files"},
                        "drive_docs": {"type": "array", "items": {"type": "string"}, "description": "Google Drive document IDs"},
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="generate_catalog",
                description="Generate thematic catalog for an expert. REQUIRES USER CONFIRMATION.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Expert name"},
                        "output": {"type": "string", "description": "Optional output file path"},
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="delete_expert",
                description="Delete an expert and its notebook. REQUIRES USER CONFIRMATION.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Expert name"},
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="generate_skill",
                description="Generate a SKILL.md file for an expert in the current project. REQUIRES USER CONFIRMATION if writing files.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Expert name"},
                        "output": {"type": "string", "description": "Output path for SKILL.md"},
                        "auto": {"type": "boolean", "description": "Auto-confirm all decisions"},
                        "dry_run": {"type": "boolean", "description": "Preview without writing files"},
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="suggest_experts",
                description="Suggest creating an expert based on domain keywords. Returns recommended sources if known domain.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain_keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Keywords describing the domain/topic",
                        },
                    },
                    "required": ["domain_keywords"],
                },
            ),
            Tool(
                name="auth_check",
                description="Check if NotebookLM authentication is valid.",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    # ─── Tool handlers ───

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "create_expert":
            result = create_expert(
                name=arguments["name"],
                description=arguments.get("description", ""),
                urls=arguments.get("urls"),
                files=[Path(f) for f in arguments.get("files", [])] if arguments.get("files") else None,
                directory=Path(arguments["directory"]) if arguments.get("directory") else None,
                drive_docs=arguments.get("drive_docs"),
                auto=arguments.get("auto", False),
                dry_run=arguments.get("dry_run", False),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "ask_expert":
            result = ask_expert(
                name=arguments["name"],
                question=arguments["question"],
                json_output=arguments.get("json_output", False),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "list_experts":
            experts = list_experts()
            return [TextContent(type="text", text=json.dumps(experts, indent=2))]

        elif name == "add_sources":
            result = add_sources(
                expert_name=arguments["name"],
                urls=arguments.get("urls"),
                files=[Path(f) for f in arguments.get("files", [])] if arguments.get("files") else None,
                directory=Path(arguments["directory"]) if arguments.get("directory") else None,
                drive_docs=arguments.get("drive_docs"),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "generate_catalog":
            result = generate_catalog(
                name=arguments["name"],
                output_path=arguments.get("output"),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "delete_expert":
            result = delete_expert(
                name=arguments["name"],
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "generate_skill":
            result = generate_skill(
                name=arguments["name"],
                output_path=arguments.get("output"),
                auto=arguments.get("auto", False),
                dry_run=arguments.get("dry_run", False),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "suggest_experts":
            result = suggest_experts(
                domain_keywords=arguments.get("domain_keywords", [])
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "auth_check":
            result = auth_check(test=True)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        else:
            return [TextContent(type="text", text=json.dumps({"status": "error", "error": f"Unknown tool: {name}"}))]

    return server


def suggest_experts(domain_keywords: list[str]) -> dict:
    """Suggest creating an expert based on domain keywords.
    
    Matches against a small database of known domains.
    """
    known_domains = [
        {
            "keywords": ["cvss", "cve", "vulnerability", "scoring"],
            "name": "cvss-v4",
            "desc": "CVSS v4.0 scoring expert",
            "urls": [
                "https://www.first.org/cvss/v4-0/specification-document",
                "https://www.first.org/cvss/v4-0/user-guide",
            ],
        },
        {
            "keywords": ["fair", "risk", "analysis", "quantitative"],
            "name": "fair-analysis",
            "desc": "FAIR risk analysis standard",
            "urls": ["https://www.fairinstitute.org/"],
        },
        {
            "keywords": ["musicxml", "music", "notation", "score"],
            "name": "musicxml",
            "desc": "MusicXML notation format",
            "urls": ["https://www.musicxml.com/for-developers/"],
        },
        {
            "keywords": ["skyrim", "creation kit", "papyrus", "modding"],
            "name": "skyrim-creation-kit",
            "desc": "Skyrim Creation Kit modding",
            "urls": ["https://ck.uesp.net/wiki/Main_Page"],
        },
        {
            "keywords": ["0ad", "0 a.d.", "modding", "entity", "template"],
            "name": "0ad-modding",
            "desc": "0 A.D. modding reference",
            "urls": ["https://gitea.wildfiregames.com/0ad/0ad/wiki"],
        },
    ]

    kw_lower = [k.lower() for k in domain_keywords]
    matches = []
    for domain in known_domains:
        score = sum(1 for dk in domain["keywords"] if any(dk in kw or kw in dk for kw in kw_lower))
        if score > 0:
            matches.append({
                "matched": True,
                "domain": domain["name"],
                "suggested_name": domain["name"],
                "rationale": domain["desc"],
                "recommended_sources": domain["urls"],
                "match_score": score,
            })

    if matches:
        matches.sort(key=lambda m: -m["match_score"])
        return {
            "matched": True,
            "suggestions": matches,
            "message": f"Found {len(matches)} domain match(es) for your keywords. "
                       "Use create_expert to create one.",
        }

    return {
        "matched": False,
        "suggestions": [],
        "message": "No known domain matches. Use create_expert with custom URLs.",
    }
