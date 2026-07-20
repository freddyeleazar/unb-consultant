"""Query interface for expert notebooks.

Ask questions to an existing NotebookLM expert and get cited answers.
"""

import json
from unb_consultant.auth import _notebooklm_cmd
from unb_consultant.config import get_config
from unb_consultant.i18n import _


def ask_expert(
    name: str,
    question: str,
    json_output: bool = False,
) -> dict:
    """Ask a question to an expert.
    
    Args:
        name: Expert name.
        question: Question text.
        json_output: If True, return structured output with references.
    
    Returns:
        dict with answer (and references if json_output).
    """
    config = get_config()
    expert = config.get_expert(name)
    if not expert:
        return {"status": "error", "error": _("expert_not_found", name=name)}

    notebook_id = expert.get("notebook_id", "")
    if not notebook_id:
        return {"status": "error", "error": "Expert has no notebook ID."}

    cmd = ["ask", "-n", notebook_id, question]
    if json_output:
        cmd.append("--json")

    result = _notebooklm_cmd(*cmd)

    if result.returncode != 0:
        return {"status": "error", "error": result.stderr.strip() or result.stdout.strip()}

    if json_output:
        try:
            data = json.loads(result.stdout)
            return {
                "status": "ok",
                "answer": data.get("answer", ""),
                "conversation_id": data.get("conversation_id"),
                "references": data.get("references", []),
            }
        except json.JSONDecodeError:
            return {"status": "ok", "answer": result.stdout.strip()}
    else:
        # Extract answer from CLI output
        answer = _extract_answer(result.stdout)
        return {"status": "ok", "answer": answer}


def _extract_answer(cli_output: str) -> str:
    """Extract the answer portion from notebooklm CLI output."""
    lines = cli_output.split("\n")
    answer_lines = []
    in_answer = False
    for line in lines:
        if line.startswith("Answer:"):
            answer_lines.append(line[7:].strip())
            in_answer = True
        elif in_answer:
            if line.strip() and not line.startswith("Conversation:"):
                answer_lines.append(line.strip())
            elif not line.strip():
                break
    if answer_lines:
        return "\n".join(answer_lines)
    return cli_output.strip()
