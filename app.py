# app.py

import streamlit as st
import pandas as pd
from datetime import datetime

# Funções e classes refatoradas
from juntar_bases import juntar_bases
from config import AppConfig, BancoConfig
from constants import *
from strategies import NovoStrategy, BeneficioStrategy, CartaoStrategy, BeneficioECartaoStrategy
from filter_handler import FiltroHandler
from utils import carregar_regras_de_exclusao

@st.cache_data
def carregar_e_juntar_arquivos_cache(lista_de_arquivos):
    """Função "invólucro" para cachear o resultado da junção de arquivos."""
    return juntar_bases(lista_de_arquivos)

# Mapeamento de estratégias para o tipo de campanha
STRATEGY_MAPEAMENTO = {
    'Novo': NovoStrategy,
    'Benefício': BeneficioStrategy,
    'Cartão': CartaoStrategy,
    'Benefício & Cartão': BeneficioECartaoStrategy,
}

def render_bank_config(index: int, campanha: str, base: pd.DataFrame) -> BancoConfig:
    """Renderiza os widgets do Streamlit para um banco e retorna um objeto BancoConfig."""
    with st.expander(f"Configurações do Banco {index + 1}"):
        
        banco_selecionado_str = st.selectbox(f"Selecione o Banco {index + 1}:", 
                                             options=list(BANCOS_MAPEAMENTO.keys()),
                                             key=f"banco_{index}")
        banco = BANCOS_MAPEAMENTO[banco_selecionado_str]

        if campanha == 'Benefício & Cartão':
            opcao = st.radio("Escolha o tipo:", ['Benefício', 'Consignado'], key=f'opcao{index}')
        else:
            opcao = None
            
        coeficiente = st.number_input(f"Coeficiente Banco {index + 1}:", min_value=0.0, step=0.01, key=f"coef_{index}")
        comissao = st.number_input(f"Comissão Banco {index + 1} (%):", min_value=0.0, max_value=100.0, step=0.01, key=f"comissao_{index}")
        parcelas = st.number_input(f"Parcelas Banco {index + 1}:", min_value=1, step=1, key=f"parcelas_{index}")
        
        coeficiente_parcela_str = st.text_input(f"Coeficiente da Parcela Banco {index + 1}:", key=f"coef_parcela_{index}").replace(",", ".")
        coeficiente_parcela = float(coeficiente_parcela_str) if coeficiente_parcela_str else None

        margem_seguranca_val = None
        if st.checkbox("Aplicar Margem de Segurança?", key=f"margem_bool_{index}"):
            percentual = st.number_input("Valor percentual da Margem de Segurança", min_value=0.0, max_value=100.0, step=0.01, key=f"margem_val_{index}")
            margem_seguranca_val = 1 - (percentual / 100)

        coluna_condicional = st.selectbox('Aplicar configuração para:', options=COLUNAS_CONDICAO, key=f"coluna_{index}")
        valor_condicional = None
        if coluna_condicional != 'Aplicar a toda a base':
            valores_disponiveis = base[coluna_condicional].dropna().unique()
            valor_condicional = st.selectbox(f"Onde a coluna '{coluna_condicional}' for:", options=valores_disponiveis, key=f"valor_{index}")

        return BancoConfig(
            banco=banco, coeficiente=coeficiente, comissao=comissao, parcelas=parcelas,
            coluna_condicional=coluna_condicional, valor_condicional=valor_condicional,
            coeficiente_parcela=coeficiente_parcela, margem_seguranca=margem_seguranca_val,
            cartao_escolhido=opcao
        )

def main():
    st.set_page_config(layout="wide", page_title='Filtrador de Campanhas V4.4')
    st.title("🚀 Filtro de Campanhas - Konsi V4.4")
    st.sidebar.header("⚙️ Painel de Controle")

    regras_exclusao = carregar_regras_de_exclusao()

    arquivos = st.sidebar.file_uploader('Arraste os arquivos CSV de higienização', accept_multiple_files=True, type=['csv'])

    if not arquivos:
        st.info("Por favor, carregue um ou mais arquivos CSV para começar.")
        return

    base = carregar_e_juntar_arquivos_cache(arquivos)
    
    st.write("Prévia dos dados carregados:")
    st.dataframe(base.head())

    convenio_atual = base.loc[0, COL_CONVENIO].strip().lower()

    # --- INÍCIO DA SIDEBAR ---
    with st.sidebar.expander("1. Configurações Gerais", expanded=True):
        campanha = st.selectbox("Tipo da Campanha:", list(STRATEGY_MAPEAMENTO.keys()), key="campanha")
        comissao_minima = st.number_input("Comissão mínima da campanha:", value=0.0, key="comissao_minima")
        margem_emprestimo_limite = st.number_input("Margem de empréstimo mínima:", value=0.0, key="margem_limite")
        idade_max = st.number_input("Idade máxima", 0, 120, 72, key="idade_max")
        equipes = st.selectbox("Equipe da Campanha:", ['outbound', 'csapp', 'csativacao', 'cscdx', 'csport', 'outbound_virada'], key="equipes")
        convai = st.slider("Porcentagem para IA (%)", 0.0, 100.0, 0.0, 1.0, key="convai")

    # Lógica para buscar regras por convênio E campanha >>>
    campanha_key = campanha.lower().replace(' & ', '_').replace(' ', '_')
    regras_do_convenio = regras_exclusao.get(convenio_atual, {})
    regras_da_campanha = regras_do_convenio.get(campanha_key, {}) # Pega as regras da campanha específica

    with st.sidebar.expander("2. Filtros de Exclusão", expanded=True):
        lotacoes_salvas = regras_da_campanha.get('lotacoes', [])
        lotacoes_selecionadas = st.multiselect(
            "Selecionar lotações para excluir:",
            options=base[COL_LOTACAO].dropna().unique(),
            default=lotacoes_salvas,
            key="lotacoes_selecionadas"
        )
        lotacoes_por_chave_str = st.text_area("Digitar palavras-chave de lotação (uma por linha):", key="lotacoes_chave")
        
        vinculos_salvos = regras_da_campanha.get('vinculos', [])
        vinculos_selecionados = st.multiselect(
            "Selecionar vínculos para excluir:",
            options=base[COL_VINCULO].dropna().unique(),
            default=vinculos_salvos,
            key="vinculos_selecionados"
        )
        vinculos_por_chave_str = st.text_area("Digitar palavras-chave de vínculo (uma por linha):", key="vinculos_chave")
    # --- FIM DA SIDEBAR ---

    st.header("3. Configurações dos Bancos")
    quant_bancos = st.number_input("Quantidade de Bancos:", min_value=1, max_value=10, value=1, key="quant_bancos")
    
    bancos_config_list = []
    for i in range(quant_bancos):
        banco_cfg = render_bank_config(i, st.session_state.campanha, base)
        bancos_config_list.append(banco_cfg)
        
    st.write("---") 
    
    if st.button("⚡️ APLICAR FILTROS E PROCESSAR ⚡️", type="primary"):
        lotacoes_por_chave = [k.strip() for k in st.session_state.lotacoes_chave.strip().split('\n') if k.strip()]
        selecao_lotacao_final = list(set(st.session_state.lotacoes_selecionadas + lotacoes_por_chave))

        vinculos_por_chave = [k.strip() for k in st.session_state.vinculos_chave.strip().split('\n') if k.strip()]
        selecao_vinculos_final = list(set(st.session_state.vinculos_selecionados + vinculos_por_chave))

        with st.spinner("Processando... A mágica está acontecendo! ✨"):
            try:
                data_limite = (datetime.today() - pd.DateOffset(years=st.session_state.idade_max)).date()
                app_config = AppConfig(
                    campanha=st.session_state.campanha, convenio=convenio_atual, comissao_minima=st.session_state.comissao_minima,
                    margem_emprestimo_limite=st.session_state.margem_limite, data_limite=data_limite,
                    selecao_lotacao=selecao_lotacao_final,
                    selecao_vinculos=selecao_vinculos_final,
                    equipes=st.session_state.equipes, convai=st.session_state.convai, bancos_config=bancos_config_list
                )
                
                strategy_class = STRATEGY_MAPEAMENTO[app_config.campanha]
                handler = FiltroHandler(df=base, config=app_config, strategy_class=strategy_class)
                base_filtrada = handler.processar()
                
                st.session_state['df_filtrado'] = base_filtrada
                st.session_state['nome_arquivo'] = f"{app_config.convenio}-{app_config.campanha}.csv"
                st.session_state['show_results'] = True

            except Exception as e:
                st.error(f"Ocorreu um erro durante o processamento: {e}")
                st.session_state['show_results'] = False

    if st.session_state.get('show_results', False):
        st.header("Resultados")
        df_resultado = st.session_state['df_filtrado']
        st.success(f"Filtro concluído! {len(df_resultado)} linhas encontradas.")
        st.dataframe(df_resultado)

        csv = df_resultado.to_csv(index=False, sep=';', encoding='utf-8-sig')
        st.download_button(
            label="📥 Baixar CSV Filtrado", data=csv,
            file_name=st.session_state['nome_arquivo'], mime='text/csv',
        )

if __name__ == "__main__":
    if 'show_results' not in st.session_state:
        st.session_state['show_results'] = False
    main()
