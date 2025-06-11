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
            # Escapa o valor condicional para uso em regex
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
        # Lógica de especificidade de convênio
        if self.config.convenio == 'govsp':
            self.df = self.df[self.df[COL_LOTACAO] != "ALESP"]
            self.df = self.df.loc[self.df[COL_MG_BENEFICIO_SAQUE_DISP] == self.df[COL_MG_BENEFICIO_SAQUE_TOTAL]]
        
        conv_excluidos = ['prefrj', 'govpi', 'goval', 'govce']
        if self.config.convenio not in conv_excluidos:
            self.df = self.df.loc[self.df[COL_MG_BENEFICIO_SAQUE_DISP] == self.df[COL_MG_BENEFICIO_SAQUE_TOTAL]]

        self.df['tratado'] = False
        
        for config_banco in self.config.bancos_config:
            mask = self._get_mask(config_banco, 'tratado')
            
            # Lógica centralizada de coeficiente com margem de segurança
            eff_coef = config_banco.coeficiente * (config_banco.margem_seguranca or 1.0)
            eff_coef2 = config_banco.coeficiente2 * (config_banco.margem_seguranca or 1.0) if config_banco.coeficiente2 else None

            # Lógica por convênio
            if self.config.convenio == 'goval':
                cond_goval = (self.df[COL_MG_BENEFICIO_SAQUE_DISP] == self.df[COL_MG_BENEFICIO_SAQUE_TOTAL]) & \
                             (self.df[COL_MG_BENEFICIO_COMPRA_DISP] == self.df[COL_MG_BENEFICIO_COMPRA_TOTAL])
                
                margem_total = self.df[COL_MG_BENEFICIO_SAQUE_DISP] + self.df[COL_MG_BENEFICIO_COMPRA_DISP]
                self.df.loc[mask & cond_goval, 'valor_liberado_beneficio'] = (margem_total * eff_coef).round(2)
                self.df.loc[mask & ~cond_goval, 'valor_liberado_beneficio'] = (self.df[COL_MG_BENEFICIO_SAQUE_DISP] * eff_coef2).round(2) if eff_coef2 else 0

            else: # Lógica para outros convênios (simplificada, pode adicionar mais casos)
                 self.df.loc[mask, 'valor_liberado_beneficio'] = (self.df.loc[mask, COL_MG_BENEFICIO_SAQUE_DISP] * eff_coef).round(2)

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
        # Filtro inicial específico da campanha
        self.df = self.df.loc[self.df[COL_MG_CARTAO_DISP] == self.df[COL_MG_CARTAO_TOTAL]]

        self.df['tratado'] = False
        for config_banco in self.config.bancos_config:
            mask = self._get_mask(config_banco, 'tratado')
            self.df.loc[mask, 'valor_liberado_cartao'] = (self.df.loc[mask, COL_MG_CARTAO_DISP] * config_banco.coeficiente).round(2)
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
                self.df.loc[mask, 'tratado_beneficio'] = True
            elif config_banco.cartao_escolhido == 'Consignado':
                mask = self._get_mask(config_banco, 'tratado_cartao')
                # Adicionar lógica de cálculo para cartão consignado aqui
                self.df.loc[mask, 'valor_liberado_cartao'] = (self.df.loc[mask, COL_MG_CARTAO_DISP] * config_banco.coeficiente).round(2)
                self.df.loc[mask, 'comissao_cartao'] = (self.df['valor_liberado_cartao'] * (config_banco.comissao / 100)).round(2)
                self.df.loc[mask, 'banco_cartao'] = config_banco.banco
                self.df.loc[mask, 'prazo_cartao'] = str(config_banco.parcelas)
                self.df.loc[mask, 'tratado_cartao'] = True
        
        self.df['comissao_total'] = self.df['comissao_beneficio'] + self.df['comissao_cartao']
        self.df = self.df.loc[self.df['comissao_total'] >= self.config.comissao_minima]
        self.df = self.df.sort_values(by='comissao_total', ascending=False)
        return self.df