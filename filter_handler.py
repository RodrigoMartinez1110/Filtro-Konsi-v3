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

    def _pre_processamento(self):
        """Aplica todas as limpezas e filtros iniciais que são comuns a todas as campanhas."""
        if self.df.empty:
            raise ValueError("A base de dados está vazia.")

        self.df = self.df.iloc[:, :26]
        
        if COL_NOME_CLIENTE in self.df.columns:
            self.df[COL_NOME_CLIENTE] = self.df[COL_NOME_CLIENTE].apply(
                lambda x: x.title() if isinstance(x, str) else x)

        if COL_CPF in self.df.columns:
            self.df[COL_CPF] = self.df[COL_CPF].str.replace(r"[.-]", "", regex=True)

        # Lógica de exclusão por palavra-chave para LOTAÇÃO
        if self.config.selecao_lotacao:
            padrao_lotacao = '|'.join([re.escape(k) for k in self.config.selecao_lotacao if k])
            if padrao_lotacao and COL_LOTACAO in self.df.columns:
                self.df = self.df[~self.df[COL_LOTACAO].str.contains(padrao_lotacao, case=False, na=False)]

        # Lógica de exclusão por palavra-chave para VÍNCULO
        if self.config.selecao_vinculos:
            padrao_vinculo = '|'.join([re.escape(k) for k in self.config.selecao_vinculos if k])
            if padrao_vinculo and COL_VINCULO in self.df.columns:
                self.df = self.df[~self.df[COL_VINCULO].str.contains(padrao_vinculo, case=False, na=False)]
        
        # Lógica de exclusão por palavra-chave para SECRETARIA
        if self.config.selecao_secretaria:
            padrao_secretaria = '|'.join([re.escape(k) for k in self.config.selecao_secretaria if k])
            if padrao_secretaria and COL_SECRETARIA in self.df.columns:
                self.df = self.df[~self.df[COL_SECRETARIA].str.contains(padrao_secretaria, case=False, na=False)]

        # Filtro por data de nascimento (idade)
        if self.config.data_limite and COL_DATA_NASCIMENTO in self.df.columns and self.df[COL_DATA_NASCIMENTO].notna().any():
            self.df[COL_DATA_NASCIMENTO] = pd.to_datetime(self.df[COL_DATA_NASCIMENTO], dayfirst=True, errors='coerce')
            self.df = self.df.dropna(subset=[COL_DATA_NASCIMENTO])
            self.df = self.df[self.df[COL_DATA_NASCIMENTO].dt.date >= self.config.data_limite]

        # Filtro por margem mínima
        if COL_MG_EMPRESTIMO_DISP in self.df.columns:
             self.df = self.df.loc[self.df[COL_MG_EMPRESTIMO_DISP] >= self.config.margem_emprestimo_limite]
        
        # Especificidades de convênios
        if self.config.convenio == 'govsp':
            if COL_MG_EMPRESTIMO_DISP in self.df.columns:
                negativos = self.df.loc[self.df[COL_MG_EMPRESTIMO_DISP] < 0]
                self.df = self.df.loc[~self.df[COL_MATRICULA].isin(negativos[COL_MATRICULA])]
        elif self.config.convenio == 'govmt':
            if COL_MG_COMPULSORIA_DISP in self.df.columns:
                self.df = self.df.loc[self.df[COL_MG_COMPULSORIA_DISP] >= 0]


    def _post_processamento(self):
        """Aplica formatação final, remove duplicados e gera colunas finais."""
        if COL_CPF in self.df.columns:
            self.df = self.df.drop_duplicates(subset=[COL_CPF])

        # Adiciona colunas faltantes e define a ordem final
        for col in COLUNAS_FINAIS:
            if col not in self.df.columns:
                self.df[col] = ''

        colunas_presentes = [col for col in COLUNAS_FINAIS if col in self.df.columns]
        self.df = self.df[colunas_presentes]
        
        self.df.rename(columns=COLUNAS_MAPEAMENTO_SAIDA, inplace=True)

        # Limpa colunas temporárias
        self.df = self.df.drop(columns=['tratado', 'tratado_beneficio', 'tratado_cartao', 'comissao_total'],
                               errors='ignore')

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
        """Executa o pipeline completo de filtragem."""
        self._pre_processamento()

        strategy_instance = self.strategy_class(self.df, self.config)
        self.df = strategy_instance.aplicar_regras_especificas()

        self._post_processamento()

        return self.df
