# app.py (Versão 5.5 com Depurador Melhorado)

import streamlit as st
import pandas as pd
from datetime import datetime

# Funções e classes refatoradas
from juntar_bases import juntar_bases
from config import AppConfig, BancoConfig
from constants import *
from strategies import NovoStrategy, BeneficioStrategy, CartaoStrategy, BeneficioECartaoStrategy
from filter_handler import FiltroHandler
from db_utils import connect_to_mongodb, carregar_regras_da_bd

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
    st.set_page_config(layout="wide", page_title='Filtrador de Campanhas V5.5')
    st.title("🚀 Filtro de Campanhas - Konsi V5.5")
    st.sidebar.header("⚙️ Painel de Controle")

    regras_collection = connect_to_mongodb()

    arquivos = st.sidebar.file_uploader('Arraste os arquivos CSV de higienização', accept_multiple_files=True, type=['csv'])

    if not arquivos:
        st.info("Por favor, carregue um ou mais arquivos CSV para começar.")
        return

    base = carregar_e_juntar_arquivos_cache(arquivos)
    
    st.write("Prévia dos dados carregados:")
    st.dataframe(base.head())

    convenio_atual = base.loc[0, COL_CONVENIO].strip().lower()

    with st.sidebar.expander("1. Configurações Gerais", expanded=True):
        campanha = st.selectbox("Tipo da Campanha:", list(STRATEGY_MAPEAMENTO.keys()))
        comissao_minima = st.number_input("Comissão mínima da campanha:", value=0.0)
        margem_emprestimo_limite = st.number_input("Margem de empréstimo mínima:", value=0.0)
        idade_max = st.number_input("Idade máxima", 0, 120, 72)
        equipes = st.selectbox("Equipe da Campanha:", ['outbound', 'csapp', 'csativacao', 'cscdx', 'csport', 'outbound_virada'])
        convai = st.slider("Porcentagem para IA (%)", 0.0, 100.0, 0.0, 1.0)

    regras_da_campanha = carregar_regras_da_bd(regras_collection, convenio_atual, campanha)

    with st.sidebar.expander("2. Filtros de Exclusão", expanded=True):
        
        opcoes_lotacao = base[COL_LOTACAO].dropna().unique()
        lotacoes_salvas = regras_da_campanha.get('lotacoes', [])
        lotacoes_default_validas = [l for l in lotacoes_salvas if l in opcoes_lotacao]
        lotacoes_selecionadas = st.multiselect(
            "Selecionar lotações para excluir:", options=opcoes_lotacao,
            default=lotacoes_default_validas, key=f"ms_lotacoes_{campanha}"
        )
        lotacoes_por_chave_str = st.text_area("Digitar palavras-chave de lotação:", key=f"ta_lotacoes_{campanha}")
        
        opcoes_vinculo = base[COL_VINCULO].dropna().unique()
        vinculos_salvos = regras_da_campanha.get('vinculos', [])
        vinculos_default_validos = [v for v in vinculos_salvos if v in opcoes_vinculo]
        vinculos_selecionados = st.multiselect(
            "Selecionar vínculos para excluir:", options=opcoes_vinculo,
            default=vinculos_default_validos, key=f"ms_vinculos_{campanha}"
        )
        vinculos_por_chave_str = st.text_area("Digitar palavras-chave de vínculo:", key=f"ta_vinculos_{campanha}")
        
        opcoes_secretaria = base[COL_SECRETARIA].dropna().unique()
        secretarias_salvas = regras_da_campanha.get('secretarias', [])
        secretarias_default_validas = [s for s in secretarias_salvas if s in opcoes_secretaria]
        secretarias_selecionadas = st.multiselect(
            "Selecionar secretarias para excluir:", options=opcoes_secretaria,
            default=secretarias_default_validas, key=f"ms_secretarias_{campanha}"
        )
        secretarias_por_chave_str = st.text_area("Digitar palavras-chave de secretaria:", key=f"ta_secretarias_{campanha}")

    # <<< DEPURADOR MELHORADO >>>
    with st.sidebar.expander("🔍 Depurador de Regras", expanded=False):
        campanha_key = campanha.lower().replace(' & ', '_').replace(' ', '_')
        st.write("Valores usados para a busca na BD:")
        st.code(f"Convenio: '{convenio_atual}'\nProduto: '{campanha_key}'", language="text")
        st.write("---")
        st.write("Resultado da busca (JSON):")
        st.json(regras_da_campanha)

    st.header("3. Configurações dos Bancos")
    quant_bancos = st.number_input("Quantidade de Bancos:", min_value=1, max_value=10, value=1)
    
    bancos_config_list = []
    for i in range(quant_bancos):
        banco_cfg = render_bank_config(i, campanha, base)
        bancos_config_list.append(banco_cfg)
        
    st.write("---") 
    
    if st.button("⚡️ APLICAR FILTROS E PROCESSAR ⚡️", type="primary"):
        selecao_lotacao_final = list(set(lotacoes_selecionadas + [k.strip() for k in lotacoes_por_chave_str.strip().split('\n') if k.strip()]))
        selecao_vinculos_final = list(set(vinculos_selecionados + [k.strip() for k in vinculos_por_chave_str.strip().split('\n') if k.strip()]))
        selecao_secretaria_final = list(set(secretarias_selecionadas + [k.strip() for k in secretarias_por_chave_str.strip().split('\n') if k.strip()]))

        with st.spinner("Processando... A mágica está acontecendo! ✨"):
            try:
                data_limite = (datetime.today() - pd.DateOffset(years=idade_max)).date()
                app_config = AppConfig(
                    campanha=campanha, convenio=convenio_atual, comissao_minima=comissao_minima,
                    margem_emprestimo_limite=margem_emprestimo_limite, data_limite=data_limite,
                    selecao_lotacao=selecao_lotacao_final,
                    selecao_vinculos=selecao_vinculos_final,
                    selecao_secretaria=selecao_secretaria_final,
                    equipes=equipes, convai=convai, bancos_config=bancos_config_list
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
            file_name=st.session_state['nome_arquivo'], mime='text/csv'
        )

if __name__ == "__main__":
    if 'show_results' not in st.session_state:
        st.session_state['show_results'] = False
    main()
