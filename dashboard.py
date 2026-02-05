import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px

st.set_page_config(page_title='Análise exploratória - Inova_MPRJ', layout='wide')

st.title('Principais insights de irregularidades no dados')

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
        select count(*) 
        from pagamento p 
        left join empenho e on p.id_empenho = e.id_empenho 
        where e.id_empenho is null;
        """
        count_no_empenho = pd.read_sql(q_no_empenho, conn).iloc[0,0]

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
            select id_empenho, sum(valor) as total_pago
            from pagamento
            group by id_empenho
        ) select e.id_empenho,
            coalesce(l.total_liquidado, 0) as total_liquidado,
            coalesce(p.total_pago, 0) as total_pago,
            (coalesce(p.total_pago, 0) - coalesce(l.total_liquidado, 0)) as diferenca
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
        return count_no_empenho, count_cnpj, df_contratos, df_cnpjs, df_pag_liq, df_cron_pag, df_cron_liq

    except Exception as e:
        st.error(f'Erro na conexão: {e}')
        return 0, 0, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# Carrega Dados
qtd_sem_empenho, qtd_cnpj_invalido, df_contratos_irreg, df_cnpjs_invalidos, df_pag_liq, df_cron_pag, df_cron_liq = load_data()


# Resumo
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
        "Erro Cronológico",
        len(df_cron_pag) + len(df_cron_liq),
        help="Pagamento ou Liquidação antes do Empenho")

st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Pagamentos sem empenho", "Pagamentos Excedentes", "CNPJs inválidos", "Pagamento > Liquidação", "Erro cronológico"])

with tab2:
    st.subheader('Contratos com Pagamentos Excedentes')
    if not df_contratos_irreg.empty:
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
        
        with st.expander('Ver lista de contratos irregulares'):
            st.dataframe(
                df_contratos_irreg.sort_values(by='porcentagem_excesso', ascending=False),
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
    st.subheader('Valor Pago > Valor Liquidado')
        
    if not df_pag_liq.empty:
        col_l, col_r = st.columns([2, 1])
        with col_l:
            fig_bar = px.bar(
                df_pag_liq.head(20), # Top 20 para não poluir
                x='id_empenho',
                y=['total_liquidado', 'total_pago'],
                barmode='group',
                title='Top 20 Empenhos com Diferença (Pago vs Liquidado)',
                labels={'value': 'Valor (R$)', 'variable': 'Etapa'}
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with col_r:
            st.metric("Total da Diferença", f"R$ {df_pag_liq['diferenca'].sum():,.2f}")
            st.dataframe(df_pag_liq[['id_empenho', 'diferenca']].sort_values(by='diferenca', ascending=False), hide_index=True)
    else:
        st.success("Nenhum caso de Pagamento > Liquidado encontrado.")

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