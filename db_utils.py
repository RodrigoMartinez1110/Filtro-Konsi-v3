# db_utils.py
import streamlit as st
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# --- FUNÇÃO DE CONEXÃO CACHEADA ---
# O intuito do cache é para que nao fique puxando sempre os dados
@st.cache_resource
def connect_to_mongodb():
    """
    Tenta conectar-se ao MongoDB usando a Connection String dos segredos do Streamlit.
    Retorna o objeto da coleção de regras.
    """
    # Apanha a connection string dos segredos do Streamlit
    connection_string = st.secrets.get("mongo", {}).get("connection_string")

    if not connection_string:
        st.error("A Connection String do MongoDB não foi encontrada nos segredos do Streamlit.")
        return None

    try:
        # Tenta criar um cliente e conectar-se
        client = MongoClient(connection_string)
        # Pinga a base de dados para confirmar uma conexão bem-sucedida
        client.admin.command('ping')
        st.success("Conexão com o MongoDB estabelecida com sucesso!", icon="🍃")
        # Seleciona a sua base de dados e a coleção
        db = client.growth
        return db.covenant_restrictions 
    except ConnectionFailure as e:
        st.error(f"Falha na conexão com o MongoDB. Verifique a sua Connection String e as configurações de rede. Erro: {e}")
        return None
    except OperationFailure as e:
        st.error(f"Falha na autenticação. Verifique o utilizador e a senha na sua Connection String. Erro: {e}")
        return None
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao conectar-se ao MongoDB: {e}")
        return None


# --- FUNÇÃO PARA BUSCAR REGRAS ---
def carregar_regras_da_bd(collection, convenio, campanha):
    """
    Busca um documento de regras na coleção do MongoDB com base no convênio e na campanha.
    """
    if collection is None:
        return {} # Retorna um dicionário vazio se não houver conexão

    try:
        # Cria a chave da campanha no formato correto (ex: 'beneficio_cartao')
        campanha_key = campanha.lower().replace(' & ', '_').replace(' ', '_')

        # Consulta a base de dados para encontrar o documento que corresponde
        query = {"convenio": convenio, "produto": campanha_key}
        regra = collection.find_one(query)

        if regra:
            # Retorna o documento inteiro da regra se encontrado
            return regra
        else:
            # Retorna um dicionário vazio se nenhuma regra for encontrada para essa combinação
            return {}
    except Exception as e:
        st.error(f"Erro ao buscar regras na base de dados: {e}")
        return {}
