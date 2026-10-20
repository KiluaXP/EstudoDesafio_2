"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

DICAS DE IMPLEMENTAÇÃO:

- O push é feito pelo cliente do LangSmith:

      from langsmith import Client
      from langchain_core.prompts import ChatPromptTemplate

      client = Client()
      prompt = ChatPromptTemplate.from_messages([
          ("system", system_prompt),
          ("user", user_prompt),
      ])
      url = client.push_prompt(
          f"{username}/bug_to_user_story_v2",
          object=prompt,
          is_public=True,
          description="...",
          tags=[...],
      )

- `username` vem de USERNAME_LANGSMITH_HUB no .env e precisa ser o seu handle
  do Hub. Se você ainda não tem um handle, veja as instruções no .env.example.

- A variável do template precisa ser {bug_report}, que é a chave de entrada
  usada no dataset de avaliação.

- Use `load_yaml` de utils.py para ler o arquivo .yml.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header

load_dotenv()

PROMPT_KEY = "bug_to_user_story_v2"
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / f"{PROMPT_KEY}.yml"
INPUT_VARIABLE = "{bug_report}"


def build_tags(prompt_data: dict) -> list:
    """Combina as tags do YAML com a versão e as técnicas aplicadas."""
    tags = list(prompt_data.get("tags", []))
    tags.append(prompt_data.get("version", ""))
    tags += [f"technique:{t}" for t in prompt_data.get("techniques_applied", [])]
    return [t for t in dict.fromkeys(tags) if t]


def build_description(prompt_data: dict) -> str:
    """Monta a descrição exibida no Hub, incluindo as técnicas aplicadas."""
    description = prompt_data.get("description", "").strip()
    techniques = prompt_data.get("techniques_applied", [])
    if techniques:
        description += f" | Técnicas: {', '.join(techniques)}"
    return description


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    full_name = f"{os.getenv('USERNAME_LANGSMITH_HUB')}/{prompt_name}"

    prompt = ChatPromptTemplate.from_messages([
        ("system", prompt_data["system_prompt"]),
        ("user", prompt_data["user_prompt"]),
    ])
    tags = build_tags(prompt_data)
    description = build_description(prompt_data)
    client = Client()

    print(f"Fazendo push: {full_name}")
    print(f"   Variáveis: {prompt.input_variables}")
    print(f"   Tags: {', '.join(tags)}")

    try:
        url = client.push_prompt(
            full_name,
            object=prompt,
            is_public=True,
            description=description,
            tags=tags,
        )
    except Exception as e:
        # O Hub rejeita um commit idêntico ao último: o conteúdo já está atualizado,
        # mas ainda garantimos visibilidade pública e metadados
        if "nothing to commit" in str(e).lower():
            client.update_prompt(full_name, is_public=True, description=description, tags=tags)
            print("   ✓ Nenhuma alteração no conteúdo; metadados e visibilidade atualizados")
            return True
        print(f"❌ Erro ao fazer push: {e}")
        return False

    print(f"   ✓ Push concluído: {url}")
    return True


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    errors = []

    for field in ["description", "system_prompt", "user_prompt", "version"]:
        if not str(prompt_data.get(field, "")).strip():
            errors.append(f"Campo obrigatório faltando ou vazio: {field}")

    system_prompt = prompt_data.get("system_prompt", "")
    user_prompt = prompt_data.get("user_prompt", "")

    if "TODO" in system_prompt or "TODO" in user_prompt:
        errors.append("O prompt ainda contém TODOs")

    if INPUT_VARIABLE not in user_prompt:
        errors.append(f"user_prompt precisa conter a variável {INPUT_VARIABLE}")

    if INPUT_VARIABLE in system_prompt:
        errors.append(f"{INPUT_VARIABLE} deve aparecer apenas no user_prompt")

    techniques = prompt_data.get("techniques_applied", [])
    if len(techniques) < 2:
        errors.append(f"Mínimo de 2 técnicas requeridas, encontradas: {len(techniques)}")

    return (len(errors) == 0, errors)


def main():
    """Função principal"""
    print_section_header("PUSH DE PROMPTS PARA O LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    data = load_yaml(str(PROMPT_PATH))
    if not data or PROMPT_KEY not in data:
        print(f"❌ Chave '{PROMPT_KEY}' não encontrada em {PROMPT_PATH.name}")
        return 1

    prompt_data = data[PROMPT_KEY]

    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt inválido:")
        for error in errors:
            print(f"   - {error}")
        return 1
    print("✓ Prompt validado\n")

    return 0 if push_prompt_to_langsmith(PROMPT_KEY, prompt_data) else 1


if __name__ == "__main__":
    sys.exit(main())
