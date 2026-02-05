import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px

st.set_page_config(page_title='Insights e Inconsistências na Execução da Despesa - Inova_MPRJ', layout='wide')

st.title('Insights e inconsistências na execução da despesa pública')

@st.cache_data(ttl=600)

def load_data():
    db_config = st.secrets['postgres']

    try:
        conn = psycopg2.connect(
            host=db_config['host'],
            database=db_config['dbname'],
            user=db_config['user'],
            password=db_config['password'],
            port=db_config['port']
        )

        # Total de pagamentos sem empenho
        q_no_empenho = """
        select p.id_pagamento,
            p.id_empenho id_empenho_inexistente,
            p.valor
        from pagamento p
        left join empenho e
            on p.id_empenho = e.id_empenho
        where e.id_empenho is null;
        """
        df_no_empenho = pd.read_sql(q_no_empenho, conn)
        count_no_empenho = len(df_no_empenho)

        # CNPJs inválidos
        q_cnpj_forn = """
        select id_fornecedor "ID",
            nome "Nome",
            documento "Documento",
            'Fornecedor' "Tipo"
        from fornecedor
        where length(replace(replace(replace(trim(documento), '.', ''), '/', ''), '-', '')) != 14;
        """
        df_forn = pd.read_sql(q_cnpj_forn, conn)

        q_cnpj_ent = """
        select id_entidade "ID",
            nome "Nome",
            cnpj "Documento",
            'Entidade' "Tipo"
        from entidade
        where length(replace(replace(replace(trim(cnpj), '.', ''), '/', ''), '-', '')) != 14;
        """
        df_ent = pd.read_sql(q_cnpj_ent, conn)
        
        df_cnpjs = pd.concat([df_forn, df_ent], ignore_index=True)
        count_cnpj = len(df_cnpjs)
        
        # Contratos e excesso de pagamentos
        q_contratos = """
        select c.id_contrato contrato, 
            c.valor valor_contratado, 
            coalesce(sum(p.valor), 0) valor_pago,
            round(((sum(p.valor)-c.valor)/nullif(c.valor,0))*100, 2) porcentagem_excesso
        from contrato c
        left join empenho e
            on e.id_contrato = c.id_contrato
        left join pagamento p
            on p.id_empenho = e.id_empenho 
        group by c.id_contrato, c.valor
        having coalesce(sum(p.valor), 0) > c.valor;
        """
        df_contratos = pd.read_sql(q_contratos, conn)

        q_pag_liq = """
        with res_liquidacao as (
            select id_empenho, sum(valor) total_liquidado
            from liquidacao_nota_fiscal
            group by id_empenho
        ), res_pagamento as (
            select id_empenho, sum(valor) total_pago
            from pagamento
            group by id_empenho
        ) select e.id_empenho,
            coalesce(l.total_liquidado, 0) total_liquidado,
            coalesce(p.total_pago, 0) total_pago,
            (coalesce(p.total_pago, 0) - coalesce(l.total_liquidado, 0)) diferenca
        from empenho e
        left join res_liquidacao l on e.id_empenho = l.id_empenho
        left join res_pagamento p on e.id_empenho = p.id_empenho
        where coalesce(p.total_pago, 0) > coalesce(l.total_liquidado, 0);
        """
        df_pag_liq = pd.read_sql(q_pag_liq, conn)

        q_cron_pag = """
        select e.id_empenho, p.id_pagamento, p.datapagamentoempenho, e.data_empenho
        from pagamento p
        join empenho e on e.id_empenho = p.id_empenho
        where e.data_empenho > p.datapagamentoempenho;
        """
        df_cron_pag = pd.read_sql(q_cron_pag, conn)

        q_cron_liq = """
        select e.id_empenho, lnf.id_liquidacao_empenhonotafiscal, lnf.data_emissao, e.data_empenho
        from liquidacao_nota_fiscal lnf
        join empenho e on e.id_empenho = lnf.id_empenho
        where e.data_empenho > lnf.data_emissao;
        """
        df_cron_liq = pd.read_sql(q_cron_liq, conn)
        
        conn.close()
        return count_no_empenho, count_cnpj, df_contratos, df_cnpjs, df_pag_liq, df_cron_pag, df_cron_liq, df_no_empenho

    except Exception as e:
        st.error(f'Erro na conexão: {e}')
        return 0, 0, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

qtd_sem_empenho, qtd_cnpj_invalido, df_contratos_irreg, df_cnpjs_invalidos, df_pag_liq, df_cron_pag, df_cron_liq, df_no_empenho = load_data()

st.header('Resumo das Principais Irregularidades')
st.markdown('Quantidade de registros inconsistentes por categoria de análise:')

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        label='Pagamentos sem empenho',
        value=qtd_sem_empenho,
        help='Pagamentos que não possuem nota de empenho válida.'
    )

with col2:
    st.metric(
        label='Contratos estourados',
        value=len(df_contratos_irreg),
        help='Contratos cuja soma dos pagamentos é maior que o valor original contratado.'
    )

with col3:
    st.metric(
        label='CNPJs inválidos',
        value=qtd_cnpj_invalido,
        help='Fornecedores e entidades com documento fora do padrão de 14 dígitos.'
    )

with col4:
    st.metric(
        "Pagamento > Liquidação",
        len(df_pag_liq),
        help="Empenhos onde valor pago é maior que o liquidado"
    )

with col5:
    st.metric(
        "Erros Cronológicos",
        len(df_cron_pag) + len(df_cron_liq),
        help="Pagamento ou Liquidação antes do Empenho")

st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Pagamentos sem empenho", "Pagamentos Excedentes", "CNPJs inválidos", "Pagamento > Liquidação", "Erro cronológico"])

with tab1:
    st.warning(f"**{qtd_sem_empenho}** Pagamentos sem empenho")
    if not df_no_empenho.empty:
        st.dataframe(
            df_no_empenho,
            hide_index=True,
            use_container_width=True,
        )

with tab2:
    st.subheader('Contratos com pagamentos excedentes')
    if not df_contratos_irreg.empty:
        df_pag_liq['porcentagem_excesso'] = df_pag_liq.apply(
            lambda x: (x['diferenca'] / x['total_liquidado'] * 100) if x['total_liquidado'] > 0 else 100.0, 
            axis=1
        )

        fig = px.scatter(
            df_pag_liq,
            x='total_liquidado',
            y='porcentagem_excesso',
            size='diferenca', 
            color='porcentagem_excesso',
            color_continuous_scale='Reds',
            hover_name='id_empenho',
            hover_data={
                'id_empenho': False,
                'total_liquidado': ':,.2f',
                'porcentagem_excesso': ':.2f', 
                'diferenca': ':,.2f'
            },
            title='Porcentagem de pagamento excedido por empenho (Pago > Liquidado)',
            labels={
                'total_liquidado': 'Valor liquidado (R$)',
                'porcentagem_excesso': 'Porcentagem excedida (%)',
                'diferenca': 'Excesso em reais (R$)',
            }
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(
                df_pag_liq.sort_values(by='porcentagem_excesso', ascending=False),
                hide_index=True
            )
    else:
        st.success("Nenhum contrato irregular encontrado.")

with tab3:
    st.warning(f"**{qtd_cnpj_invalido}** CNPJs inválidos")
    if not df_cnpjs_invalidos.empty:
        st.dataframe(
            df_cnpjs_invalidos,
            hide_index=True,
            use_container_width=True
        )

with tab4:
    st.subheader('Valor pago maior que valor liquidado')
        
    if not df_pag_liq.empty:
  
        df_contratos_irreg['excesso_reais'] = df_contratos_irreg['valor_pago'] - df_contratos_irreg['valor_contratado']
        fig = px.scatter(df_contratos_irreg,
        x='valor_contratado',
        y='porcentagem_excesso',
        size='excesso_reais',
        color='porcentagem_excesso',
        color_continuous_scale='Reds',
        hover_name='contrato',
        hover_data={
            'contrato': False,
            'valor_contratado': ':.2f',
            'porcentagem_excesso': ':.2f', 
            'excesso_reais': ':,.2f'
        },
        title='Porcentagem de pagamento excedido por contrato',
        labels={
            'valor_contratado': 'Valor original do contrato (R$)',
            'porcentagem_excesso': 'Porcentagem excedida (%)',
            'excesso_reais': 'Excesso em reais (R$)',
        }
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(
                df_contratos_irreg.sort_values(by='porcentagem_excesso', ascending=False),
                hide_index=True
            )
    else:
        st.success("Nenhum caso onde o valor do pagamento seja maior que o valor Liquidado encontrado.")

with tab5:
    st.subheader('Pagamentos/Liquidações feitas antes do empenho')
    
    col_cron1, col_cron2 = st.columns(2)
    
    with col_cron1:
        st.warning(f"**{len(df_cron_pag)}** Pagamentos antes do Empenho")
        if not df_cron_pag.empty:
            st.dataframe(df_cron_pag, hide_index=True)
            
    with col_cron2:
        st.warning(f"**{len(df_cron_liq)}** Liquidações antes do Empenho")
        if not df_cron_liq.empty:
            st.dataframe(df_cron_liq, hide_index=True)

st.divider()



st.caption('Dashboard desenvolvido por **Priscila Leite** para o **Desafio Técnico Inova_MPRJ**')