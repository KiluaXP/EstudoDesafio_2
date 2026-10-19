"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do prompt semente do desafio
3. Salva localmente em prompts/bug_to_user_story_v1.yml

DICAS DE IMPLEMENTAÇÃO:

- O pull é feito pelo cliente do LangSmith:

      from langsmith import Client
      client = Client()
      prompt = client.pull_prompt(
          "leonanluppi/bug_to_user_story_v1",
          dangerously_pull_public_prompt=True,
      )

- O parâmetro `dangerously_pull_public_prompt=True` é obrigatório sempre que o
  identificador tem dono explícito ("owner/nome"). O LangSmith bloqueia esse pull
  por padrão porque um prompt do Hub é um objeto LangChain serializado, que pode
  vir de terceiros. Aqui o prompt é o do desafio, então o risco é conhecido.

- O retorno é um ChatPromptTemplate. Para extrair o conteúdo das mensagens,
  use a serialização nativa do LangChain (`prompt.messages`, e o atributo
  `.prompt.template` de cada mensagem).

- Use `save_yaml` de utils.py para gravar o resultado no arquivo .yml.
"""

import os
import sys
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

SOURCE_PROMPT = "leonanluppi/bug_to_user_story_v1"
PROMPT_KEY = "bug_to_user_story_v1"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "prompts" / f"{PROMPT_KEY}.yml"

# Mapeia o tipo da mensagem do LangChain para o campo correspondente no YAML
MESSAGE_TYPE_TO_FIELD = {
    "SystemMessagePromptTemplate": "system_prompt",
    "HumanMessagePromptTemplate": "user_prompt",
}


def prompt_to_dict(prompt) -> dict:
    """Converte o ChatPromptTemplate retornado pelo Hub no formato YAML do projeto."""
    data = {"description": "Prompt para converter relatos de bugs em User Stories"}

    for message in prompt.messages:
        field = MESSAGE_TYPE_TO_FIELD.get(type(message).__name__)
        template = getattr(getattr(message, "prompt", None), "template", None)
        if field and template is not None:
            data[field] = template

    data["version"] = "v1"
    data["source"] = SOURCE_PROMPT
    data["pulled_at"] = date.today().isoformat()
    data["input_variables"] = list(prompt.input_variables)
    data["tags"] = ["bug-analysis", "user-story", "product-management"]
    return data


def pull_prompts_from_langsmith():
    """Faz pull do prompt semente e salva em prompts/bug_to_user_story_v1.yml."""
    client = Client()

    print(f"Puxando prompt: {SOURCE_PROMPT}")
    prompt = client.pull_prompt(SOURCE_PROMPT, dangerously_pull_public_prompt=True)
    print(f"   ✓ {len(prompt.messages)} mensagens recebidas")

    if not save_yaml({PROMPT_KEY: prompt_to_dict(prompt)}, str(OUTPUT_PATH)):
        return False

    print(f"   ✓ Salvo em {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")
    return True


def main():
    """Função principal"""
    print_section_header("PULL DE PROMPTS DO LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    try:
        return 0 if pull_prompts_from_langsmith() else 1
    except Exception as e:
        print(f"❌ Erro ao fazer pull do prompt: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
