# filter_handler.py
import pandas as pd
import re 
from datetime import datetime
from config import AppConfig
from constants import *
from strategies import FiltroStrategy

class FiltroHandler:
    """
    Orquestra todo o processo de filtragem, aplicando etapas comuns de pré e pós-processamento,
    e utilizando uma estratégia específica para a lógica de negócio da campanha.
    """
    def __init__(self, df: pd.DataFrame, config: AppConfig, strategy_class: type[FiltroStrategy]):
        self.df = df.copy()
        self.config = config
        self.strategy_class = strategy_class
        # Atributos para guardar as matrículas que já usaram os produtos no GOVSP
        self.usou_beneficio_matriculas = set()
        self.usou_cartao_matriculas = set()

    def _identificar_uso_previo_govsp(self):
        """
        Passo 1: Executado sobre o dataframe COMPLETO, antes de qualquer filtro.
        Identifica e memoriza as matrículas de clientes do GOVSP que já utilizaram
        o cartão benefício ou consignado.
        """
        if self.config.convenio == 'govsp':
            # Calcula a margem usada para o benefício
            margem_beneficio_usada = self.df[COL_MG_BENEFICIO_SAQUE_TOTAL] - self.df[COL_MG_BENEFICIO_SAQUE_DISP]
            df_usou_beneficio = self.df.loc[margem_beneficio_usada > 0]
            if not df_usou_beneficio.empty:
                self.usou_beneficio_matriculas = set(df_usou_beneficio[COL_MATRICULA])

            # Calcula a margem usada para o cartão
            margem_cartao_usada = self.df[COL_MG_CARTAO_TOTAL] - self.df[COL_MG_CARTAO_DISP]
            df_usou_cartao = self.df.loc[margem_cartao_usada > 0]
            if not df_usou_cartao.empty:
                self.usou_cartao_matriculas = set(df_usou_cartao[COL_MATRICULA])

    def _pre_processamento(self):
        """
        Passo 2: Aplica todos os filtros globais (lotação, vínculo, idade, etc.)
        sobre o dataframe.
        """
        if self.df.empty:
            raise ValueError("A base de dados está vazia.")

        self.df = self.df.iloc[:, :26]
        
        # Limpezas de dados
        if COL_NOME_CLIENTE in self.df.columns:
            self.df[COL_NOME_CLIENTE] = self.df[COL_NOME_CLIENTE].apply(lambda x: x.title() if isinstance(x, str) else x)
        if COL_CPF in self.df.columns:
            self.df[COL_CPF] = self.df[COL_CPF].str.replace(r"[.-]", "", regex=True)

        # Filtros de Exclusão Globais
        if self.config.selecao_lotacao and COL_LOTACAO in self.df.columns:
            padrao_lotacao = '|'.join([re.escape(k) for k in self.config.selecao_lotacao if k])
            if padrao_lotacao: self.df = self.df[~self.df[COL_LOTACAO].str.contains(padrao_lotacao, case=False, na=False)]

        if self.config.selecao_vinculos and COL_VINCULO in self.df.columns:
            padrao_vinculo = '|'.join([re.escape(k) for k in self.config.selecao_vinculos if k])
            if padrao_vinculo: self.df = self.df[~self.df[COL_VINCULO].str.contains(padrao_vinculo, case=False, na=False)]
        
        if self.config.selecao_secretaria and COL_SECRETARIA in self.df.columns:
            padrao_secretaria = '|'.join([re.escape(k) for k in self.config.selecao_secretaria if k])
            if padrao_secretaria: self.df = self.df[~self.df[COL_SECRETARIA].str.contains(padrao_secretaria, case=False, na=False)]

        # Filtro de Idade
        if self.config.data_limite and COL_DATA_NASCIMENTO in self.df.columns and self.df[COL_DATA_NASCIMENTO].notna().any():
            self.df[COL_DATA_NASCIMENTO] = pd.to_datetime(self.df[COL_DATA_NASCIMENTO], dayfirst=True, errors='coerce')
            self.df = self.df.dropna(subset=[COL_DATA_NASCIMENTO])
            self.df = self.df[self.df[COL_DATA_NASCIMENTO].dt.date >= self.config.data_limite]

        # Outros filtros específicos de convênios que se aplicam a todos os produtos
        if self.config.convenio == 'govsp':
            self.df = self.df[self.df[COL_LOTACAO] != "ALESP"] # Remove ALESP
            if COL_MG_EMPRESTIMO_DISP in self.df.columns:
                negativos = self.df.loc[self.df[COL_MG_EMPRESTIMO_DISP] < 0]
                if not negativos.empty: self.df = self.df.loc[~self.df[COL_MATRICULA].isin(negativos[COL_MATRICULA])]
        
        elif self.config.convenio == 'govmt':
            if COL_MG_COMPULSORIA_DISP in self.df.columns:
                self.df = self.df.loc[self.df[COL_MG_COMPULSORIA_DISP] >= 0]
    
    def _post_processamento(self):
        """
        Passo 4: Aplica formatação final, remove duplicados e faz a verificação final
        contra as matrículas memorizadas.
        """
        # Verificação final contra a lista de uso prévio do GOVSP
        if self.config.convenio == 'govsp':
            if 'valor_liberado_beneficio' in self.df.columns:
                self.df.loc[self.df[COL_MATRICULA].isin(self.usou_beneficio_matriculas), 'valor_liberado_beneficio'] = 0
            if 'valor_liberado_cartao' in self.df.columns:
                self.df.loc[self.df[COL_MATRICULA].isin(self.usou_cartao_matriculas), 'valor_liberado_cartao'] = 0
        
        # O resto do pós-processamento
        if COL_CPF in self.df.columns:
            self.df = self.df.drop_duplicates(subset=[COL_CPF])

        for col in COLUNAS_FINAIS:
            if col not in self.df.columns: self.df[col] = ''
        
        colunas_presentes = [col for col in COLUNAS_FINAIS if col in self.df.columns]
        self.df = self.df[colunas_presentes]
        self.df.rename(columns=COLUNAS_MAPEAMENTO_SAIDA, inplace=True)
        self.df = self.df.drop(columns=['tratado', 'tratado_beneficio', 'tratado_cartao', 'comissao_total'], errors='ignore')

        self._gerar_nome_campanha()

    def _gerar_nome_campanha(self):
        """Gera o nome da campanha para a coluna final."""
        data_hoje = datetime.today().strftime('%d%m%Y')
        nome_campanha_slug = self.config.campanha.lower().replace(' & ', '&')
        nome_campanha_base = f"{self.config.convenio}_{data_hoje}_{nome_campanha_slug}"
        self.df['Campanha'] = f"{nome_campanha_base}_{self.config.equipes}"

        if self.config.convai > 0:
            n_convai = int((self.config.convai / 100) * len(self.df))
            if n_convai > 0 and not self.df.empty:
                indices_convai = self.df.sample(n=n_convai, random_state=42).index
                self.df.loc[indices_convai, 'Campanha'] = f"{nome_campanha_base}_convai"

    def processar(self) -> pd.DataFrame:
        """Executa o pipeline completo de filtragem na ordem correta."""
        # Passo 1: Identificar uso prévio na base completa
        self._identificar_uso_previo_govsp()
        
        # Passo 2: Aplicar filtros gerais
        self._pre_processamento()

        # Passo 3: Deixar a estratégia fazer os cálculos
        strategy_instance = self.strategy_class(self.df, self.config)
        self.df = strategy_instance.aplicar_regras_especificas()

        # Passo 4: Aplicar formatação e validações finais
        self._post_processamento()

        return self.df
