# Desafio Técnico - Inova MPRJ (Dados & Analytics)

Este repositório contém a solução desenvolvida para o Desafio Técnico do Processo Seletivo para Estágio em Dados & Analytics do **Inova MPRJ**.

O projeto consiste na estruturação, análise e visualização de dados referentes ao fluxo da despesa pública (Empenho, Liquidação e Pagamento), com foco na identificação de inconsistências, anomalias e possíveis indícios de irregularidades, conforme a Lei 4.320/64.

---

## 📂 Estrutura do Repositório

* `dashboard`: Código fonte do painel interativo desenvolvido em Python (Streamlit).
* `dashboard/requirements.txt`: Lista de dependências necessárias para execução do projeto.
* `sql`: Contém o arquivo sql com as queries SQL utilizadas para investigação e validação das hipóteses.
* `relatorio.pdf`: Contém o documento detalhando a modelagem de dados, metodologia e conclusões da análise em pdt e tex. Também contém as imagens do modelos relacionais.

---

## 🚀 Como Executar o Projeto

Para visualizar o dashboard localmente, siga os passos abaixo:

### 1. Pré-requisitos
Certifique-se de ter o **Python 3.8+** instalado.

### 2. Instalação das Dependências
Clone este repositório e instale as bibliotecas necessárias utilizando o arquivo `requirements.txt` na pasta `dashboard`:

```bash
pip install -r dashboard\requirements.txt
```
### 3. Configuração de Acesso ao Banco de Dados
O projeto conecta-se diretamente ao banco de dados PostgreSQL fornecido no desafio. Por questões de segurança, as credenciais **não** estão expostas no código.

Você deve configurar as credenciais localmente:

1.  Na raiz do projeto, crie uma pasta chamada `.streamlit`.
2.  Dentro dela, crie um arquivo chamado `secrets.toml`.
3.  Insira as credenciais de acesso (enviadas por e-mail no edital) no seguinte formato:

```toml
[postgres]
host = "host_do_banco"
port = "5432"
dbname = "nome_do_banco"
user = "seu_usuario"
password = "sua_senha"
```

### 4. Executando o Dashboard
No terminal, execute o comando:
``` bash
streamlit run dashboard.py
```

O painel abrirá automaticamente no seu navegador padrão (geralmente em http://localhost:8501).
