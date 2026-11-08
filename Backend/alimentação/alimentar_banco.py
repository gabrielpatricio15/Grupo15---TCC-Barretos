import requests
import pyodbc
import time
from bs4 import BeautifulSoup

# Configuração da Conexão com o seu SQL Server
CONEXAO_SQL = (
    r"DRIVER={SQL Server};"
    r"SERVER=127.0.0.1, 1433;"
    r"DATABASE=TransparenciaBarretos;"
    r"Trusted_Connection=yes;"
)

# ==========================================
# 1. FUNÇÃO DE EXTRAÇÃO DE DESPESAS
# ==========================================
def alimentar_despesas(ano, mes):
    print(f"📉 Baixando DESPESAS ({mes}/{ano})...")
    url = f"https://transparencia.tce.sp.gov.br/api/json/despesas/barretos/{ano}/{mes}"
    
    try:
        resposta = requests.get(url)
        if resposta.status_code == 200:
            dados = resposta.json()
            conexao = pyodbc.connect(CONEXAO_SQL)
            cursor = conexao.cursor()
            
            qtd_salva = 0
            for item in dados:
                try:
                    valor_str = str(item.get('vl_despesa', '0')).replace('.', '').replace(',', '.')
                    if not valor_str.replace('.','').isdigit(): continue
                    valor = float(valor_str)
                    
                    categoria = str(item.get('nm_fornecedor', 'Despesas Gerais'))[:250]
                    fornecedor = str(item.get('id_fornecedor', 'Origem não detalhada'))[:250]
                    descricao = str(item.get('evento', ''))[:4000]
                    
                    try:
                        d, m_str, a = item.get('dt_emissao_despesa', f'01/{mes}/{ano}').split('/')
                        data_sql = f"{a}-{m_str}-{d}"
                    except:
                        data_sql = f"{ano}-{mes}-01"
                    
                    sql = "INSERT INTO Despesas (ano, mes, data_lancamento, categoria, fornecedor_origem, descricao, valor) VALUES (?, ?, ?, ?, ?, ?, ?)"
                    cursor.execute(sql, (ano, mes, data_sql, categoria, fornecedor, descricao, valor))
                    qtd_salva += 1
                except Exception as erro_linha:
                    print(f"   ❌ Erro ao salvar linha: {erro_linha}")
                    continue
                
            conexao.commit()
            conexao.close()
            print(f"   ✅ {qtd_salva} despesas salvas.")
    except Exception as e: print(f"   ❌ Erro: {e}")

# ==========================================
# 2. FUNÇÃO DE EXTRAÇÃO DE RECEITAS
# ==========================================
def alimentar_receitas(ano, mes):
    print(f"📈 Baixando RECEITAS ({mes}/{ano})...")
    url = f"https://transparencia.tce.sp.gov.br/api/json/receitas/barretos/{ano}/{mes}"
    
    try:
        resposta = requests.get(url)
        if resposta.status_code == 200:
            dados = resposta.json()
            conexao = pyodbc.connect(CONEXAO_SQL)
            cursor = conexao.cursor()
            
            qtd_salva = 0
            for item in dados:
                try:
                    valor_str = str(item.get('vl_arrecadacao', '0')).replace('.', '').replace(',', '.')
                    if not valor_str.replace('.','').isdigit(): continue
                    valor = float(valor_str)
                    
                    categoria = str(item.get('ds_fonte_recurso', 'Receita Geral'))[:250]
                    origem = str(item.get('ds_cd_aplicacao_fixo', 'Origem não detalhada'))[:250]
                    descricao = str(item.get('ds_alinea', ''))[:4000]
                    
                    # Nas receitas usamos o dia 01 como padrão para organizar no banco
                    data_sql = f"{ano}-{mes}-01"
                    
                    sql = "INSERT INTO Receitas (ano, mes, data_lancamento, categoria, fornecedor_origem, descricao, valor) VALUES (?, ?, ?, ?, ?, ?, ?)"
                    cursor.execute(sql, (ano, mes, data_sql, categoria, origem, descricao, valor))
                    qtd_salva += 1
                except Exception as erro_linha:
                    print(f"   ❌ Erro ao salvar linha: {erro_linha}")
                    continue
                
            conexao.commit()
            conexao.close()
            print(f"   ✅ {qtd_salva} receitas salvas.")
    except Exception as e: print(f"   ❌ Erro: {e}")

# ==========================================
# 3. ROBÔ DE CARGA EM LOTE (A MÁGINA ACONTECE AQUI)
# ==========================================
# Anos para serem migrados os dados 
anos_para_baixar = ["2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026"]

print("🚀 INICIANDO MEGA EXTRAÇÃO DE DADOS...")

for ano in anos_para_baixar:
    print(f"\n--- PROCESSANDO O ANO DE {ano} ---")
    
    # Se for o ano atual, ele para no mês 9 (Setembro). Se for ano passado, vai até 12.
    meses_limite = 9 if ano == "2026" else 12 
    
    for mes_num in range(1, meses_limite + 1):
        mes_formatado = f"{mes_num:02d}"
        
        alimentar_despesas(ano, mes_formatado)
        alimentar_receitas(ano, mes_formatado)
        
        # Pausa de 1 segundo para não sobrecarregar e ser bloqueado pelo site do Governo
        time.sleep(1)

print("\n🎉 MEGA CARGA DE DADOS CONCLUÍDA! Seu Banco de Dados agora é um gigante.")

def buscar_prefeito_seade(ano_eleicao):
    print(f"Buscando prefeito eleito em {ano_eleicao} no SEADE...")
    
    # O SEADE usa códigos internos. Barretos geralmente é '3505500' ou um ID específico da plataforma deles
    # Esta é a estrutura base de envio de formulário (POST) para sites de consulta
    url = "https://produtos.seade.gov.br/produtos/eleicoes/candidatos/index.php?page=ele_sel"
    
    payload = {
        'ano': ano_eleicao,
        'cargo': '11', # Código usual para Prefeito
        'mun': '3505500' # Código IBGE de Barretos (ajuste conforme o padrão do SEADE)
    }
    
    try:
        # Finge ser um navegador acessando a página
        resposta = requests.post(url, data=payload)
        sopa = BeautifulSoup(resposta.text, 'html.parser')
        
        # Procura a tabela de resultados e pega o candidato com status "Eleito"
        # Nota: A classe e o ID exatos dependem da estrutura HTML do SEADE no momento do acesso
        tabela = sopa.find('table', {'class': 'tabela_resultados'})
        if tabela:
            for linha in tabela.find_all('tr'):
                colunas = linha.find_all('td')
                if colunas and "Eleito" in linha.text:
                    nome_prefeito = colunas[0].text.strip()
                    print(f"Prefeito encontrado: {nome_prefeito}")
                    return nome_prefeito
                    
        print("Candidato eleito não encontrado no HTML retornado.")
        return "Não localizado"
        
    except Exception as e:
        print(f"Erro na raspagem: {e}")
        return "Erro de conexão"