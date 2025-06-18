# strategies.py
import pandas as pd
import numpy as np
import re
from abc import ABC, abstractmethod
from config import AppConfig, BancoConfig
from constants import *

class FiltroStrategy(ABC):
    """Classe base abstrata para todas as estratégias de filtro."""
    def __init__(self, df: pd.DataFrame, app_config: AppConfig):
        self.df = df
        self.config = app_config

    @abstractmethod
    def aplicar_regras_especificas(self) -> pd.DataFrame:
        """Aplica as regras de cálculo e filtro específicas da campanha."""
        pass

    def _get_mask(self, banco_cfg: BancoConfig, tratado_col: str):
        """Cria a máscara de condição para aplicar as regras do banco."""
        if banco_cfg.coluna_condicional != "Aplicar a toda a base":
            safe_valor = re.escape(str(banco_cfg.valor_condicional))
            return (self.df[banco_cfg.coluna_condicional].str.contains(safe_valor, na=False, case=False)) & (~self.df[tratado_col])
        else:
            return ~self.df[tratado_col]

class NovoStrategy(FiltroStrategy):
    def aplicar_regras_especificas(self) -> pd.DataFrame:
        self.df['tratado'] = False
        for config_banco in self.config.bancos_config:
            mask = self._get_mask(config_banco, 'tratado')
            
            margem_a_usar = self.df.loc[mask, COL_MG_EMPRESTIMO_DISP].copy()
            if config_banco.margem_seguranca:
                 margem_a_usar *= config_banco.margem_seguranca

            self.df.loc[mask, 'valor_liberado_emprestimo'] = (margem_a_usar * config_banco.coeficiente).round(2)
            self.df.loc[mask, 'valor_parcela_emprestimo'] = margem_a_usar.round(2)
            self.df.loc[mask, 'comissao_emprestimo'] = (self.df.loc[mask, 'valor_liberado_emprestimo'] * (config_banco.comissao / 100)).round(2)
            self.df.loc[mask, 'banco_emprestimo'] = config_banco.banco
            self.df.loc[mask, 'prazo_emprestimo'] = str(config_banco.parcelas)
            self.df.loc[mask, 'tratado'] = True

        self.df = self.df.loc[self.df['comissao_emprestimo'] >= self.config.comissao_minima]
        self.df = self.df.sort_values(by='valor_liberado_emprestimo', ascending=False)
        return self.df

class BeneficioStrategy(FiltroStrategy):
    def aplicar_regras_especificas(self) -> pd.DataFrame:
        usou_beneficio = pd.Series(dtype='object')
        
        # <<< LÓGICA GOVSP REINTRODUZIDA >>>
        if self.config.convenio == 'govsp':
            self.df['margem_beneficio_usado'] = self.df[COL_MG_BENEFICIO_SAQUE_TOTAL] - self.df[COL_MG_BENEFICIO_SAQUE_DISP]
            usou_beneficio = self.df.loc[self.df['margem_beneficio_usado'] > 0]
            self.df = self.df.loc[self.df[COL_MG_BENEFICIO_SAQUE_DISP] == self.df[COL_MG_BENEFICIO_SAQUE_TOTAL]]

        conv_excluidos = ['prefrj', 'govpi', 'goval', 'govce']
        if self.config.convenio not in conv_excluidos and self.config.convenio != 'govsp':
            self.df = self.df.loc[self.df[COL_MG_BENEFICIO_SAQUE_DISP] == self.df[COL_MG_BENEFICIO_SAQUE_TOTAL]]

        self.df['tratado'] = False
        
        for config_banco in self.config.bancos_config:
            mask = self._get_mask(config_banco, 'tratado')
            
            eff_coef = config_banco.coeficiente * (config_banco.margem_seguranca or 1.0)
            
            self.df.loc[mask, 'valor_liberado_beneficio'] = (self.df.loc[mask, COL_MG_BENEFICIO_SAQUE_DISP] * eff_coef).round(2)
            
            # <<< VALIDAÇÃO GOVSP REINTRODUZIDA >>>
            if self.config.convenio == 'govsp' and not usou_beneficio.empty:
                self.df.loc[(self.df['valor_liberado_beneficio'] > 0) & (self.df[COL_MATRICULA].isin(usou_beneficio[COL_MATRICULA])), 'valor_liberado_beneficio'] = 0

            self.df.loc[mask, 'valor_parcela_beneficio'] = (self.df['valor_liberado_beneficio'] / config_banco.coeficiente_parcela).round(2) if config_banco.coeficiente_parcela else 0
            self.df.loc[mask, 'comissao_beneficio'] = (self.df['valor_liberado_beneficio'] * (config_banco.comissao / 100)).round(2)
            self.df.loc[mask, 'banco_beneficio'] = config_banco.banco
            self.df.loc[mask, 'prazo_beneficio'] = str(config_banco.parcelas)
            self.df.loc[mask, 'tratado'] = True

        self.df = self.df.loc[self.df['comissao_beneficio'] >= self.config.comissao_minima]
        self.df = self.df.sort_values(by='valor_liberado_beneficio', ascending=False)
        return self.df


class CartaoStrategy(FiltroStrategy):
    def aplicar_regras_especificas(self) -> pd.DataFrame:
        usou_cartao = pd.Series(dtype='object')

        # <<< LÓGICA GOVSP REINTRODUZIDA >>>
        if self.config.convenio == 'govsp':
            self.df['margem_cartao_usada'] = self.df[COL_MG_CARTAO_TOTAL] - self.df[COL_MG_CARTAO_DISP]
            usou_cartao = self.df.loc[self.df['margem_cartao_usada'] > 0]
        
        self.df = self.df.loc[self.df[COL_MG_CARTAO_DISP] == self.df[COL_MG_CARTAO_TOTAL]]

        self.df['tratado'] = False
        for config_banco in self.config.bancos_config:
            mask = self._get_mask(config_banco, 'tratado')
            self.df.loc[mask, 'valor_liberado_cartao'] = (self.df.loc[mask, COL_MG_CARTAO_DISP] * config_banco.coeficiente).round(2)

            # <<< VALIDAÇÃO GOVSP REINTRODUZIDA >>>
            if self.config.convenio == 'govsp' and not usou_cartao.empty:
                self.df.loc[(self.df['valor_liberado_cartao'] > 0) & (self.df[COL_MATRICULA].isin(usou_cartao[COL_MATRICULA])), 'valor_liberado_cartao'] = 0

            self.df.loc[mask, 'valor_parcela_cartao'] = (self.df['valor_liberado_cartao'] / config_banco.coeficiente_parcela).round(2) if config_banco.coeficiente_parcela else 0
            self.df.loc[mask, 'comissao_cartao'] = (self.df['valor_liberado_cartao'] * (config_banco.comissao / 100)).round(2)
            self.df.loc[mask, 'banco_cartao'] = config_banco.banco
            self.df.loc[mask, 'prazo_cartao'] = str(config_banco.parcelas)
            self.df.loc[mask, 'tratado'] = True
            
        self.df = self.df.loc[self.df['comissao_cartao'] >= self.config.comissao_minima]
        self.df = self.df.sort_values(by='valor_liberado_cartao', ascending=False)
        return self.df

class BeneficioECartaoStrategy(FiltroStrategy):
    def aplicar_regras_especificas(self) -> pd.DataFrame:
        usou_beneficio = pd.Series(dtype='object')
        usou_cartao = pd.Series(dtype='object')

        # <<< LÓGICA GOVSP REINTRODUZIDA >>>
        if self.config.convenio == 'govsp':
            self.df['margem_beneficio_usado'] = self.df[COL_MG_BENEFICIO_SAQUE_TOTAL] - self.df[COL_MG_BENEFICIO_SAQUE_DISP]
            usou_beneficio = self.df.loc[self.df['margem_beneficio_usado'] > 0]
            
            self.df['margem_cartao_usada'] = self.df[COL_MG_CARTAO_TOTAL] - self.df[COL_MG_CARTAO_DISP]
            usou_cartao = self.df.loc[self.df['margem_cartao_usada'] > 0]

        self.df['tratado_beneficio'] = False
        self.df['tratado_cartao'] = False
        self.df['valor_liberado_beneficio'] = 0.0
        self.df['valor_liberado_cartao'] = 0.0
        self.df['comissao_beneficio'] = 0.0
        self.df['comissao_cartao'] = 0.0
        
        for config_banco in self.config.bancos_config:
            if config_banco.cartao_escolhido == 'Benefício':
                mask = self._get_mask(config_banco, 'tratado_beneficio')
                # Adicionar lógica de cálculo para benefício aqui
                self.df.loc[mask & (self.df[COL_MG_BENEFICIO_SAQUE_DISP] == self.df[COL_MG_BENEFICIO_SAQUE_TOTAL]), 'valor_liberado_beneficio'] = (self.df[COL_MG_BENEFICIO_SAQUE_DISP] * config_banco.coeficiente).round(2)
                
                # <<< VALIDAÇÃO GOVSP REINTRODUZIDA >>>
                if self.config.convenio == 'govsp' and not usou_beneficio.empty:
                    self.df.loc[self.df[COL_MATRICULA].isin(usou_beneficio[COL_MATRICULA]), 'valor_liberado_beneficio'] = 0

                self.df.loc[mask, 'comissao_beneficio'] = (self.df['valor_liberado_beneficio'] * (config_banco.comissao / 100)).round(2)
                self.df.loc[mask, 'tratado_beneficio'] = True

            elif config_banco.cartao_escolhido == 'Consignado':
                mask = self._get_mask(config_banc, 'tratado_cartao')
                self.df.loc[mask & (self.df[COL_MG_CARTAO_DISP] == self.df[COL_MG_CARTAO_TOTAL]), 'valor_liberado_cartao'] = (self.df[COL_MG_CARTAO_DISP] * config_banco.coeficiente).round(2)
                
                # <<< VALIDAÇÃO GOVSP REINTRODUZIDA >>>
                if self.config.convenio == 'govsp' and not usou_cartao.empty:
                    self.df.loc[self.df[COL_MATRICULA].isin(usou_cartao[COL_MATRICULA]), 'valor_liberado_cartao'] = 0
                
                self.df.loc[mask, 'comissao_cartao'] = (self.df['valor_liberado_cartao'] * (config_banco.comissao / 100)).round(2)
                self.df.loc[mask, 'tratado_cartao'] = True
        
        self.df['comissao_total'] = self.df['comissao_beneficio'] + self.df['comissao_cartao']
        self.df = self.df.loc[self.df['comissao_total'] >= self.config.comissao_minima]
        self.df = self.df.sort_values(by='comissao_total', ascending=False)
        return self.df
