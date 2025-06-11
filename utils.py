import streamlit as st
import json

@st.cache_data
def carregar_regras_de_exclusao(caminho_arquivo="regras_exclusao.json"):
    """
    Carrega as regras de exclusão de um arquivo JSON.
    Retorna um dicionário vazio se o arquivo não existir ou for inválido.
    """
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Se o arquivo não existir, não é um erro, apenas não há regras.
        return {}
    except json.JSONDecodeError:
        # Avisa o usuário se o arquivo JSON estiver mal formatado.
        st.error(f"Erro: O arquivo '{caminho_arquivo}' parece estar com a formatação JSON inválida. Verifique o arquivo.")
        return {}