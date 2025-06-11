# config.py
from dataclasses import dataclass, field
from typing import List, Optional, Any
from datetime import date

@dataclass
class BancoConfig:
    """Estrutura para armazenar a configuração de um único banco."""
    banco: str
    coeficiente: float
    comissao: float
    parcelas: int
    coluna_condicional: str
    valor_condicional: Any
    coeficiente2: Optional[float] = None
    margem_seguranca: Optional[float] = None
    coeficiente_parcela: Optional[float] = None
    usar_margem_compra: bool = False
    cartao_escolhido: Optional[str] = None
    margem_minima_cartao: Optional[float] = None

@dataclass
class AppConfig:
    """Estrutura para armazenar todas as configurações da aplicação."""
    campanha: str
    convenio: str
    comissao_minima: float
    margem_emprestimo_limite: float
    data_limite: Optional[date]
    selecao_lotacao: Optional[List[str]]
    selecao_vinculos: Optional[List[str]]
    equipes: str
    convai: float
    bancos_config: List[BancoConfig] = field(default_factory=list)