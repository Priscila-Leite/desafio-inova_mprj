
-- Consulta 2.1
select p.id_pagamento,
	p.id_empenho id_empenho_inexistente,
	p.valor
from pagamento p
left join empenho e
	on p.id_empenho = e.id_empenho
where e.id_empenho is null;

-- Consulta 2.2
select c.id_contrato,
	c.valor valor_contrato,
	coalesce(sum(p.valor), 0) total_pago,
    round(((sum(p.valor)-c.valor)/nullif(c.valor,0))*100, 2) porcentagem_excesso
from contrato c
left join empenho e
	on e.id_contrato = c.id_contrato
left join pagamento p
	on p.id_empenho = e.id_empenho 
group by c.id_contrato, c.valor
having coalesce(sum(p.valor), 0) > c.valor;

-- Consultas 2.3
	-- Verifica entidades
select c.id_contrato,
	c.id_entidade
from contrato c
left join entidade e 
	on c.id_entidade = e.id_entidade
where e.id_entidade is null;

	-- Verifica fornecedores
select c.id_contrato,
	c.id_fornecedor
from contrato c
left join fornecedor f 
	on c.id_fornecedor = f.id_fornecedor 
where f.id_fornecedor is null;

-- Consultas 2.4
	-- verifica fornecedores
select id_fornecedor,
	nome,
	documento CNPJ
from fornecedor
where length(replace(replace(replace(trim(documento), '.', ''), '/', ''), '-', '')) != 14;

	-- verifica entidades
select id_entidade,
	nome,
	cnpj CNPJ
from entidade
where length(replace(replace(replace(trim(cnpj), '.', ''), '/', ''), '-', '')) != 14;

-- Consulta 2.5

with res_liquidacao as (
	select id_empenho, sum(valor) total_liquidado
	from liquidacao_nota_fiscal
	group by id_empenho
), res_pagamento as (
	select id_empenho, sum(valor) as total_pago
	from pagamento
	group by id_empenho
) select e.id_empenho,
	coalesce(l.total_liquidado, 0) total_liquidado,
	coalesce(p.total_pago, 0) total_pago
from empenho e
left join res_liquidacao l
	on e.id_empenho = l.id_empenho
left join res_pagamento p
	on e.id_empenho = p.id_empenho
where coalesce(p.total_pago, 0) > coalesce(l.total_liquidado, 0);

-- Consulta 2.6
select e.id_empenho,
	p.id_pagamento,
	p.datapagamentoempenho,
	e.data_empenho
from pagamento p
join empenho e
	on e.id_empenho = p.id_empenho
where e.data_empenho > p.datapagamentoempenho;

-- Consulta 2.7
select e.id_empenho,
	lnf.id_liquidacao_empenhonotafiscal,
	lnf.data_emissao,
	e.data_empenho
from liquidacao_nota_fiscal lnf
join empenho e
	on e.id_empenho = lnf.id_empenho
where e.data_empenho > lnf.data_emissao;