import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_modal import Modal
import streamlit.components.v1 as components
from streamlit.components.v1 import html

st.set_page_config(layout="wide",page_title="Prefeitura de Fortaleza", page_icon='./logo.png')

def formatar_moeda(valor):
    valor_formatado = f'{valor:,.2f}'
    # Substitui o separador decimal por uma letra que não seja dígito
    valor_formatado = valor_formatado.replace('.', 'X').replace(',', '.').replace('X', ',')
    return f'R$ {valor_formatado}'

# Função para carregar os dados do Excel
@st.cache_data
def carregar_dados():
    return pd.read_excel("folha_geral.xlsx", sheet_name="folha_geral", decimal=',')

# Função para substituir o ponto pela vírgula nos valores do DataFrame
@st.cache_data
def substituir_ponto_por_virgula(df):
    return df.applymap(lambda x: str(x).replace('.', ','))

# Função para criar e exibir a tabela de salários por classe e referência
@st.cache_data
def exibir_tabela_salarios(TC, TR, num_classes, num_referencias, salario_base, nome_tabela):
    # Criando um DataFrame para armazenar os resultados
    tabela = pd.DataFrame(index=range(1, num_referencias + 1), columns=range(1, num_classes + 1))
    valores = {}  # Dicionário para armazenar os valores
    # Preenchendo a tabela com os valores de salário
    for j in range(1, num_classes + 1):
        for i in range(1, num_referencias + 1):
            if i == 1 and j == 1:
                valor = salario_base
            elif i == 1:
                valor = float(tabela.loc[num_referencias, j - 1]) * (1+(TC/100))
            else:
                valor = float(tabela.loc[i - 1, j]) * (1+(TR/100))
            
            # Armazenando o valor no dicionário
            valores[(i, j)] = valor, i + (j - 1) * num_referencias
            tabela.loc[i, j] = f"{valor:.2f}"  # Atribuindo o índice da célula com duas casas decimais
                        
    # Renomeando índices e colunas
    tabela.index.name = 'Referência'
    tabela.columns.name = 'Classe'
    
    return tabela, valores

@st.cache_data
def contar_pessoas(df):
    # Contar pessoas por cargo, carga horária e referência
    quantidade_pessoas = df.groupby(['Cargo', 'CH', 'Ref'])['VENCIMENTO BASE'].size().reset_index(name='Quantidade')
    
    # Calcular o consolidado do VENCIMENTO BASE
    consolidado_vencimento_base = df.groupby(['Cargo', 'CH', 'Ref'])['VENCIMENTO BASE'].sum().reset_index(name='Consolidado VENCIMENTO BASE')
    
    # Concatenar o consolidado com a tabela de quantidade de pessoas
    quantidade_pessoas = pd.merge(quantidade_pessoas, consolidado_vencimento_base, on=['Cargo', 'CH', 'Ref'])

    return quantidade_pessoas

@st.cache_data
def tabela_novo_salario(df):
    # Contar pessoas por cargo, carga horária e referência
    tabela_nome_novo_salario = df[['Nome','CH','Ref', 'VENCIMENTO BASE', 'Novo Salário']]
    return tabela_nome_novo_salario

@st.cache_data
def calcular_impacto(df):
    # Agrupar por cargo e calcular a quantidade de funcionários, a remuneração anterior e a remuneração nova
    resumo_cargos = df.groupby('Cargo').agg({'Nome': 'count', 'VENCIMENTO BASE': 'sum', 'Novo Salário': 'sum'}).reset_index()

    # Calcular o impacto
    resumo_cargos['Impacto'] = resumo_cargos['Novo Salário'] - resumo_cargos['VENCIMENTO BASE']

    # Renomear colunas
    resumo_cargos.rename(columns={'Nome': 'Quantidade', 'VENCIMENTO BASE': 'Remuneração Anterior', 'Novo Salário': 'Remuneração Nova'}, inplace=True)

    return resumo_cargos

def calcular_irpf(base_irpf):
    if base_irpf > 4664.68:
        return base_irpf * 0.275 - 869.36
    elif base_irpf>3751.05:
        return base_irpf *0.225-636.13
    elif base_irpf>2826.65:
        return base_irpf *0.15-354.8
    elif base_irpf>1903.98:
        return base_irpf*0.075-142.8
    else:
        return 0
    
def calcular_novo_salario(df, salario_base_b_180,salario_base_c_180,salario_base_d_180,salario_base_b_240,salario_base_c_240,salario_base_d_240, pular_indice=0):
    novo_salario = []  
    for indice_ref, ch, primeiro_caractere in zip(df['Ref'],df['CH'],df['primeiro_caractere']): 
            indice_alvo = indice_ref #+ pular_indice
            if ch == 180 and primeiro_caractere == 'B':
                tabela = salario_base_b_180
            elif ch == 180 and primeiro_caractere == 'C':
                tabela = salario_base_c_180                
            elif ch == 180 and primeiro_caractere == 'D':
                tabela = salario_base_d_180     
            elif ch == 240 and primeiro_caractere == 'B':
                tabela = salario_base_b_240       
            elif ch == 240 and primeiro_caractere == 'C':
                tabela = salario_base_c_240       
            elif ch == 240 and primeiro_caractere == 'D':
                tabela = salario_base_d_240            
            for chave, valor in tabela.items():
                if indice_alvo == valor[1]:
                    novo_salario.append(valor[0])
                    break  #Encerrar o loop interno após encontrar a correspondência
            else:
                novo_salario.append(None)  # Adicionar None se não houver correspondência encontrada
    return novo_salario

def main():
    
    st.header(' :orange[Prefeitura de Fortaleza] ', divider='rainbow')
    
    # Carregar dados
    df = carregar_dados()

    # Adicionando imagem centralizada acima do título da sidebar
    st.sidebar.image('logo.png', width=150, use_column_width=True)
    
    st.sidebar.subheader('Selecione as opções abaixo: ')
    
    # Seletor de filtro multiselect para Ambiente na barra lateral
    ambientes_selecionados = st.sidebar.multiselect('Selecione o(s) Ambiente(s):', df['Ambiente'].unique())

    # Filtrar DataFrame com base nos ambientes selecionados
    df_filtrado = df[df['Ambiente'].isin(ambientes_selecionados)]

    # Exibir tabela
    st.write(df_filtrado[['Nome', 'Orgao', 'Cat', 'Cargo', 'Ambiente', 'Tab', 'Pla', 'Niv', 'Ref', 'CH', '0100-VENCIMENTO']])


    
if __name__ == '__main__':
    main()