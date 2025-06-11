# juntar_bases.py

import streamlit as st
import pandas as pd

# A anotação @st.cache_data foi removida daqui, pois a moveremos para o app.py
def juntar_bases(files):
    """
    Recebe uma lista de objetos de arquivo do Streamlit e os concatena.
    """
    dataframes = []
    # 'files' aqui é a lista de objetos UploadedFile
    for arquivo in files:
        try:
            # Lê o objeto de arquivo diretamente
            df = pd.read_csv(arquivo, low_memory=False)
            if df.empty:
                st.warning(f"O arquivo {arquivo.name} está vazio.")
            else:
                dataframes.append(df)
        except Exception as e:
            # Como 'arquivo' é um objeto, arquivo.name funciona corretamente
            st.error(f"Erro ao carregar {arquivo.name}: {e}")
            continue
            
    if dataframes:
        return pd.concat(dataframes, ignore_index=True)
    else:
        st.error("Nenhum arquivo válido foi carregado.")
        return pd.DataFrame()