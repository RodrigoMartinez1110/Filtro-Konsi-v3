# **Documentação do Projeto: Filtrador de Campanhas Konsi V4**

## **1. Visão Geral**

Este é um aplicativo web desenvolvido com a biblioteca Streamlit para automatizar e padronizar o processo de filtragem de bases de dados para a criação de campanhas na Konsi.

O objetivo principal da ferramenta é receber arquivos CSV brutos de higienização, aplicar uma série de regras de negócio complexas e dinâmicas (definidas pelo usuário na interface), e gerar como saída um arquivo CSV final, pronto para ser utilizado pela equipe de operações.

### **Principais Funcionalidades**

* **Interface Web Interativa:** Permite que usuários sem conhecimento de programação configurem e executem os filtros.
* **Múltiplos Tipos de Campanha:** Suporta lógicas de negócio distintas para campanhas de `Novo`, `Benefício`, `Cartão` e `Benefício & Cartão`.
* **Configuração Dinâmica de Bancos:** Permite configurar coeficientes, comissões e regras específicas para múltiplos bancos em uma única execução.
* **Filtros de Exclusão Flexíveis:** O usuário pode excluir `Lotações` e `Vínculos` tanto selecionando de uma lista quanto digitando palavras-chave.
* **Memória de Regras (Configuração Persistente):** Utiliza um arquivo externo (`regras_exclusao.json`) para salvar e carregar automaticamente regras de exclusão para cada convênio, eliminando trabalho repetitivo.
* **Performance Otimizada:** Utiliza técnicas de cache e formulários para garantir uma experiência de uso fluida, mesmo com múltiplos arquivos e filtros.

## **2. Estrutura do Projeto**

O projeto é organizado de forma modular para facilitar a manutenção e a adição de novas funcionalidades.

```
FILTRADOR_KONS_V4/
├── app.py                 # Ponto de entrada e interface do usuário
├── config.py              # Define as estruturas de dados de configuração
├── constants.py           # Centraliza valores fixos como nomes de colunas
├── filter_handler.py      # Orquestra a lógica de filtragem comum
├── juntar_bases.py        # Utilitário para unir arquivos CSV
├── strategies.py          # Contém a lógica de negócio específica de cada campanha
├── utils.py               # Funções utilitárias gerais (ex: carregar JSON)
├── regras_exclusao.json   # Arquivo de regras de exclusão editável pelo usuário
└── requirements.txt       # Lista de dependências do projeto para instalação
```

## **3. Descrição dos Arquivos**

* `app.py`
    * **Propósito:** É o "rosto" e o "cérebro" da aplicação. Ele cria toda a interface gráfica com o Streamlit, captura as interações e configurações do usuário, e coordena a chamada dos outros módulos para executar a filtragem.
* `filter_handler.py`
    * **Propósito:** É o "gerente de operações". A classe `FiltroHandler` contida aqui executa todas as etapas que são comuns a *todas* as campanhas, como a limpeza inicial dos dados, aplicação de filtros de idade e exclusão, e a formatação final do arquivo de saída. Isso evita a repetição de código.
* `strategies.py`
    * **Propósito:** Contém os "especialistas". Para cada tipo de campanha (`Novo`, `Benefício`, etc.), existe uma classe de "Estratégia" correspondente que contém a lógica de cálculo específica e única daquela campanha.
* `config.py`
    * **Propósito:** Serve como um "molde". Define as classes `AppConfig` e `BancoConfig` para garantir que os dados de configuração coletados da interface sejam armazenados de forma estruturada e consistente.
* `constants.py`
    * **Propósito:** É o "dicionário" do projeto. Armazena valores constantes, como os nomes exatos das colunas do CSV e mapeamentos. Se um nome de coluna mudar no futuro, basta alterá-lo em um único lugar.
* `juntar_bases.py` & `utils.py`
    * **Propósito:** São as "caixas de ferramentas". Contêm funções de ajuda reutilizáveis. `juntar_bases` é responsável por carregar e concatenar os múltiplos arquivos CSV, enquanto `utils` carrega as regras do arquivo JSON.
* `regras_exclusao.json`
    * **Propósito:** É a "memória" do aplicativo. Este arquivo permite que o usuário salve regras de exclusão permanentes para cada convênio. É um arquivo de texto simples que pode ser editado manualmente para adicionar ou remover regras sem tocar no código.
* `requirements.txt`
    * **Propósito:** É a "lista de compras". Define todas as bibliotecas Python que o projeto precisa para funcionar. É essencial para a instalação do ambiente.

## **4. Como Configurar e Rodar o Projeto**

Siga os passos abaixo para executar o aplicativo na sua máquina.

### **Pré-requisitos**

* Python (versão 3.9 ou superior) instalado.

### **Passos de Instalação**

1.  **Crie uma Pasta para o Projeto:** Crie uma pasta no seu computador e coloque todos os arquivos do projeto (`app.py`, `constants.py`, etc.) dentro dela.
2.  **Crie e Ative um Ambiente Virtual:** Abra o terminal ou prompt de comando, navegue até a pasta do projeto e execute os seguintes comandos. Isso isola as dependências do seu projeto.
    ```bash
    # Cria o ambiente virtual
    python -m venv venv

    # Ativa o ambiente (Windows)
    venv\Scripts\activate

    # Ativa o ambiente (Mac/Linux)
    source venv/bin/activate
    ```
3.  **Instale as Dependências:** Com o ambiente ativado, instale todas as bibliotecas necessárias de uma só vez usando o arquivo `requirements.txt`.
    ```bash
    pip install -r requirements.txt
    ```
4.  **Execute o Aplicativo:** Agora você está pronto para iniciar a aplicação.
    ```bash
    streamlit run app.py
    ```
    O aplicativo será aberto automaticamente no seu navegador de internet.

## **5. Como Usar a Aplicação**

1.  **Carregar Arquivos:** Na barra lateral à esquerda, arraste e solte um ou mais arquivos CSV de higienização.
2.  **Configurar Filtros na Sidebar:**
    * **Configurações Gerais:** Defina o tipo de campanha, comissão mínima, idade, etc.
    * **Filtros de Exclusão:** Use os campos para excluir `Lotações` e `Vínculos`. Você pode tanto selecionar itens pré-existentes na lista (que são pré-carregados a partir do `regras_exclusao.json`) quanto digitar novas palavras-chave no campo de texto abaixo.
3.  **Configurar os Bancos:** No painel principal, defina quantos bancos deseja configurar e preencha os detalhes (coeficiente, comissão, etc.) para cada um.
4.  **Processar:** Após preencher todas as configurações na sidebar, clique no botão **"⚡️ APLICAR FILTROS E PROCESSAR ⚡️"**.
5.  **Baixar o Resultado:** O aplicativo irá processar os dados e, ao final, mostrará uma prévia do resultado e um botão para baixar o arquivo CSV final, já formatado.

## **6. Como Atualizar as Regras de Exclusão**

Para adicionar ou remover uma regra de exclusão permanente para um convênio:

1.  **Abra o arquivo `regras_exclusao.json`** em um editor de texto simples (como Bloco de Notas, VS Code, etc.).
2.  **Encontre o convênio** que deseja modificar (ex: `"prefsp"`). Se o convênio não existir, você pode adicioná-lo, seguindo o formato dos outros.
3.  **Encontre a categoria** que deseja alterar (ex: `"lotacoes"`).
4.  **Adicione ou remova a palavra-chave** da lista. Lembre-se de que cada item deve estar entre aspas duplas `"` e separado por vírgulas `,`.

**Exemplo:** Para adicionar "SEFIN" à lista de lotações excluídas de "goval":

```json
// Antes
"goval": {
  "lotacoes": [ "SEDUC", "SESAU" ],
  ...
}

// Depois
"goval": {
  "lotacoes": [ "SEDUC", "SESAU", "SEFIN" ],
  ...
}
```

5.  Salve o arquivo. Na próxima vez que você carregar um arquivo CSV daquele convênio, a nova regra já será aplicada automaticamente.
