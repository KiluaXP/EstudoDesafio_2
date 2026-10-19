"""
Testes automatizados para validação de prompts.
"""
import re
import pytest
import yaml
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def prompt():
    data = load_prompts(PROMPT_FILE)
    assert PROMPT_KEY in data, f"Chave '{PROMPT_KEY}' não encontrada em {PROMPT_FILE.name}"
    return data[PROMPT_KEY]


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert "system_prompt" in prompt
        assert prompt["system_prompt"].strip()

    def test_prompt_has_role_definition(self, prompt):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        assert re.search(r"Você é um[a]? ", prompt["system_prompt"])
        assert "Product Manager" in prompt["system_prompt"]

    def test_prompt_mentions_format(self, prompt):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        system_prompt = prompt["system_prompt"]
        assert "User Story" in system_prompt
        assert "Como um" in system_prompt and "eu quero" in system_prompt and "para que" in system_prompt
        assert all(step in system_prompt for step in ["Dado", "Quando", "Então"])

    def test_prompt_has_few_shot_examples(self, prompt):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        system_prompt = prompt["system_prompt"]
        examples = re.findall(r"## Exemplo \d+", system_prompt)
        assert len(examples) >= 2, "São necessários pelo menos 2 exemplos"
        assert system_prompt.count("Relato:") >= len(examples)
        assert system_prompt.count("Resposta:") >= len(examples)

    def test_prompt_no_todos(self, prompt):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        for field in ["system_prompt", "user_prompt", "description"]:
            assert "TODO" not in prompt.get(field, ""), f"TODO encontrado em {field}"

    def test_minimum_techniques(self, prompt):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        techniques = prompt.get("techniques_applied", [])
        assert len(techniques) >= 2
        assert "Few-shot Learning" in techniques

    def test_bug_report_variable_only_in_user_prompt(self, prompt):
        """O {bug_report} deve ir no user prompt, e não duplicado no system prompt (problema da v1)."""
        assert "{bug_report}" in prompt["user_prompt"]
        assert "{bug_report}" not in prompt["system_prompt"]

    def test_prompt_structure_is_valid(self, prompt):
        """Usa a validação de utils.py como checagem final."""
        is_valid, errors = validate_prompt_structure(prompt)
        assert is_valid, errors


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
