import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_modal import Modal
import streamlit.components.v1 as components
from streamlit.components.v1 import html
import matplotlib.pyplot as plt

st.set_page_config(layout="wide",page_title="Prefeitura de Fortaleza", page_icon='./logo.png')

def formatar_moeda(valor):
    valor_formatado = f'{valor:,.2f}'
    # Substitui o separador decimal por uma letra que não seja dígito
    valor_formatado = valor_formatado.replace('.', 'X').replace(',', '.').replace('X', ',')
    return f'R$ {valor_formatado}'

# Função para carregar os dados do Excel
@st.cache_data
def carregar_dados():
    return pd.read_excel("planilha_impacto_salarial.xlsx", sheet_name="amc", decimal=',')

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
    quantidade_pessoas = df.groupby(['Cargo', 'CH', 'Ref'])['0996-TOT.PROVENTO'].size().reset_index(name='Quantidade')
    
    # Calcular o consolidado do VENCIMENTO BASE
    consolidado_vencimento_base = df.groupby(['Cargo', 'CH', 'Ref'])['0996-TOT.PROVENTO'].sum().reset_index(name='Consolidado VENCIMENTO BASE')
    
    # Concatenar o consolidado com a tabela de quantidade de pessoas
    quantidade_pessoas = pd.merge(quantidade_pessoas, consolidado_vencimento_base, on=['Cargo', 'CH', 'Ref'])

    return quantidade_pessoas

@st.cache_data
def tabela_novo_salario(df):
    # Contar pessoas por cargo, carga horária e referência
    tabela_nome_novo_salario = df[['Nome','CH','Ref', '0996-TOT.PROVENTO', 'novo_0996-TOT.PROVENTO']]
    return tabela_nome_novo_salario

@st.cache_data
def calcular_impacto(df):
    # Agrupar por cargo e calcular a quantidade de funcionários, a remuneração anterior e a remuneração nova
    resumo_cargos = df.groupby('Cargo').agg({'Nome': 'count', '0996-TOT.PROVENTO': 'sum', 'novo_0996-TOT.PROVENTO': 'sum'}).reset_index()

    # Calcular o impacto
    resumo_cargos['Impacto'] = resumo_cargos['novo_0996-TOT.PROVENTO'] - resumo_cargos['0996-TOT.PROVENTO']

    # Renomear colunas
    resumo_cargos.rename(columns={'Nome': 'Quantidade', '0996-TOT.PROVENTO': 'Remuneração Anterior', 'novo_0996-TOT.PROVENTO': 'Remuneração Nova'}, inplace=True)

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

def atualizar_ita(row, taxa):
    if row['Grau de instrução'] == "Médio Profissionalizante":
        return (taxa / 100)
    elif row['Grau de instrução'] == "Médio Tecnólogo":
        return (taxa / 100)
    elif row['Grau de instrução'] == "Graduação":
        return (taxa / 100)
    elif row['Grau de instrução'] == "Especialização":
        return (taxa / 100)
    elif row['Grau de instrução'] == "Mestrado":
        return (taxa / 100)
    elif row['Grau de instrução'] == "Doutorado":
        return (taxa / 100)
    else:
        return row['REF-ITA']
    
def atualizar_geef(row, taxa):
    if row['Enquadramento do GEEF'] == "Inciso I":
        return (taxa / 100)
    elif row['Enquadramento do GEEF'] == "Incisos II e V":
        return (taxa / 100)
    elif row['Enquadramento do GEEF'] == "Inciso IV":
        return (taxa / 100)
    elif row['Enquadramento do GEEF'] == "Inciso III, VI e VII":
        return (taxa / 100)
    else:
        return row['REF-GEEF-AMC']
    
def atualizar_gat(row, taxa):
    if row['Cargo'] == "AGENTE MUNIC FISCALIZ DE TRANS":
        return (taxa / 100)
    else:
        return row['REF-GAT']
    
def atualizar_ge_amc(row, taxa):
    if row['Cargo'] == "AGENTE MUNIC FISCALIZ DE TRANS":
        return (taxa / 100)
    else:
        return ((taxa/2)/100)
    
    # Função para calcular o novo salário com a dedução da gratificação
def calcular_novo_salario_com_deducao(df, gratificacao, porcentagem):
    # Deduz a porcentagem da gratificação escolhida
    df[gratificacao] -= df[gratificacao] * (porcentagem / 100)
    # Atualiza o novo salário somando a gratificação deduzida
    df['Novo Salário'] = df['Novo Salário'] + df[gratificacao]
    return df

def main():
    
    st.header(' :orange[Prefeitura de Fortaleza] ', divider='rainbow')
    # Adicionando imagem centralizada acima do título da sidebar
    st.sidebar.image('logo.png', width=150, use_column_width=True)
    
    
    # Carregar dados
    df = carregar_dados()
    
    df['primeiro_caractere'] = df['Niv'].str.slice(0, 1)
    
    ambientes_selecionados = st.sidebar.multiselect('Selecione o(s) Ambiente(s):', df['Ambiente'].unique(), placeholder="Ambiente", )
    categorias_selecionados = st.sidebar.multiselect('Selecione a(s) Categoria(s):', df['Cat'].unique(), placeholder="Categoria")
    niveis_selecionados = st.sidebar.multiselect('Selecione o(s) Nível(s):', df['Niv'].unique(), placeholder="Nível")
    ch_selecionados = st.sidebar.multiselect('Selecione a(s) Carga Horária(s):', df['CH'].unique(), placeholder="Carga Horária")
    
    # Preencher com todos os valores possíveis se a lista estiver vazia
    if not ambientes_selecionados:
        ambientes_selecionados = df['Ambiente'].unique()
    if not categorias_selecionados:
        categorias_selecionados = df['Cat'].unique()
    if not niveis_selecionados:
        niveis_selecionados = df['Niv'].unique()
    if not ch_selecionados:
        ch_selecionados = df['CH'].unique()

    # Aplicando filtro
    df = df[
        (df['Ambiente'].isin(ambientes_selecionados)) &
        (df['Cat'].isin(categorias_selecionados)) &
        (df['Niv'].isin(niveis_selecionados)) &
        (df['CH'].isin(ch_selecionados))
    ]
    
    st.sidebar.subheader('Configurações de parâmetros: ')
    # Parâmetros Tabela 1
    TC1 = st.sidebar.number_input('Taxa de Classe (%):', value=2)
    TR1 = st.sidebar.number_input('Taxa de Referência (%):', value=2)
    num_classes1 = st.sidebar.number_input('Número de Classes:', value=5, min_value=1)
    num_referencias1 = st.sidebar.number_input('Número de Referências:', value=6, min_value=1)
        
    indice_tabela = st.sidebar.number_input('Enquadramento:', min_value=0, value=0)
    df['Ref'] = df['Ref'] + indice_tabela
    
    gratificacoes = ['GAT','GEEF', 'GR.R.VIDA', 'GE AMC', 'HE NOTURNA']  
    
    # Definindo os valores padrão das taxas
    default_values = {
        'GAT': 100,
        'GE AMC': 100,
        'GR.R.VIDA': 100,
        'HE NOTURNA': 0
    }
    
    st.sidebar.subheader('Incorporação de Gratificação')
    gratificacoes_escolhidas = st.sidebar.multiselect("Escolha as gratificações a serem incorporadas no Salário Base: ", gratificacoes, placeholder="Escolha a gratificação")
    soma_rel  = 1
    for option in gratificacoes_escolhidas: 
        valor_input = st.sidebar.number_input(f'Insira o valor que será incorporado para {option} (%):', min_value=0, value=0)
        if valor_input != 0:
            valor_relativo = valor_input / 100 + 1  # Converte a porcentagem em número relativo
            soma_rel *= valor_relativo  # Multiplica os valores relativos
            default_values[option] -= valor_input  # Atualiza o valor original conforme necessário
        
    #inputs para as taxas de referências:
    st.sidebar.subheader('Configurações de taxas das gratificações: ')  
    st.sidebar.write('Se vazio, será usada a atual: ')
    
    taxa_gat = st.sidebar.number_input('Gat (%)',min_value=0, max_value=100, value=default_values['GAT'])
    taxa_ge_amc = st.sidebar.number_input('GE-AMC (%)',min_value=0, max_value=100, value=default_values['GE AMC'])
    taxa_gr_r_vida = st.sidebar.number_input('GR.R.VIDA (%)')
    taxa_he_noturna = st.sidebar.number_input('HE NOTURNA (%)')

    # Aplicando as atualizações na taxa de GE_AMC para que seja atualizado nas linhas de acordo com o INPUT
    if taxa_ge_amc:
        df['REF-GE AMC'] = df.apply(lambda row: atualizar_ge_amc(row, taxa_ge_amc) if row['Cargo'] == "AGENTE MUNIC FISCALIZ DE TRANS" else row['REF-GE AMC'], axis=1)    
    
    # Aplicando as atualizações na taxa de GAT para que seja atualizado nas linhas de acordo com o INPUT
    if taxa_gat:
        df['REF-GAT'] = df.apply(lambda row: atualizar_gat(row, taxa_gat) if row['Cargo'] == "AGENTE MUNIC FISCALIZ DE TRANS" else row['REF-GAT'], axis=1)
    
    # Exibindo inputs quando o botão dos ITAs quando for acionado
    show_inputs = st.sidebar.button("Alterar ITA")

    if 'show_inputs' not in st.session_state:
        st.session_state.show_inputs = False

    if show_inputs:
        st.session_state.show_inputs = True  

    if st.session_state.show_inputs:
        st.sidebar.subheader('Inclua a(s) nova(s) taxa(s) do ITA')
        if st.sidebar.button("Fechar e limpar ITA"):
            st.session_state.show_inputs = False
            st.experimental_rerun()
        taxa_profissionalizante = st.sidebar.number_input('Médio Profissionalizante  (%)', value=8)
        taxa_tecnologo  = st.sidebar.number_input('Tecnólogo  (%)', value=9)
        taxa_graduação = st.sidebar.number_input('Graduação  (%)', value=10)
        taxa_especialização = st.sidebar.number_input('Especialização (%)', value=15)
        taxa_mestrado = st.sidebar.number_input('Mestrado(%)', value=35)
        taxa_doutorado = st.sidebar.number_input('Doutorado(%)', value=45)
        # Aplicando as atualizações
        if taxa_profissionalizante:
            df['REF-ITA'] = df.apply(lambda row: atualizar_ita(row, taxa_profissionalizante) if row['Grau de instrução'] == "Médio Profissionalizante" else row['REF-ITA'], axis=1)
        if taxa_tecnologo:
            df['REF-ITA'] = df.apply(lambda row: atualizar_ita(row, taxa_tecnologo) if row['Grau de instrução'] == "Médio Tecnólogo" else row['REF-ITA'], axis=1)
        if taxa_graduação:
            df['REF-ITA'] = df.apply(lambda row: atualizar_ita(row, taxa_graduação) if row['Grau de instrução'] == "Graduação" else row['REF-ITA'], axis=1)
        if taxa_especialização:
            df['REF-ITA'] = df.apply(lambda row: atualizar_ita(row, taxa_especialização) if row['Grau de instrução'] == "Especialização" else row['REF-ITA'], axis=1)
        if taxa_mestrado:
            df['REF-ITA'] = df.apply(lambda row: atualizar_ita(row, taxa_mestrado) if row['Grau de instrução'] == "Mestrado" else row['REF-ITA'], axis=1)
        if taxa_doutorado:
            df['REF-ITA'] = df.apply(lambda row: atualizar_ita(row, taxa_doutorado) if row['Grau de instrução'] == "Doutorado" else row['REF-ITA'], axis=1)
            
    # Exibindo inputs quando o botão dos GEEFs quando for acionado
    show_inputs_geef = st.sidebar.button("Alterar GEEF")

    if 'show_inputs_geef' not in st.session_state:
        st.session_state.show_inputs_geef = False

    if show_inputs_geef:
        st.session_state.show_inputs_geef = True  
        
    if st.session_state.show_inputs_geef:
        st.sidebar.subheader('Inclua a(s) nova(s) taxa(s) do GEEF')
        if st.sidebar.button("Fechar e limpar GEEF"):
            st.session_state.show_inputs_geef = False
            st.experimental_rerun()
        taxa_inciso_i = st.sidebar.number_input('Inciso I  (%)', value=70)
        taxa_inciso_i_v  = st.sidebar.number_input('Inciso II e V  (%)', value=60)
        taxa_inciso_iv = st.sidebar.number_input('Inciso IV  (%)', value=30)
        taxa_inciso_iii_vi_vii = st.sidebar.number_input('Inciso III, VI e VII (%)', value=25)

        # Aplicando as atualizações
        if taxa_inciso_i:
            df['REF-GEEF-AMC'] = df.apply(lambda row: atualizar_geef(row, taxa_inciso_i) if row['Enquadramento do GEEF'] == "Inciso I" else row['REF-GEEF-AMC'], axis=1)
        if taxa_inciso_i_v:
            df['REF-GEEF-AMC'] = df.apply(lambda row: atualizar_geef(row, taxa_inciso_i_v) if row['Enquadramento do GEEF'] == "Incisos II e V" else row['REF-GEEF-AMC'], axis=1)
        if taxa_inciso_iv:
            df['REF-GEEF-AMC'] = df.apply(lambda row: atualizar_geef(row, taxa_inciso_iv) if row['Enquadramento do GEEF'] == "Inciso IV" else row['REF-GEEF-AMC'], axis=1)
        if taxa_inciso_iii_vi_vii:
            df['REF-GEEF-AMC'] = df.apply(lambda row: atualizar_geef(row, taxa_inciso_iii_vi_vii) if row['Enquadramento do GEEF'] == "Inciso III, VI e VII" else row['REF-GEEF-AMC'], axis=1)


    # salario_base1 = st.sidebar.number_input('Salário Base:', value=1160.66, min_value=0.0)
    st.sidebar.subheader('Configurações dos salários-base: ')      
    salario_base_b_180 = st.sidebar.number_input("Salário-base tabela B 180 horas: ", value=886.29 * soma_rel)
    salario_base_c_180 = st.sidebar.number_input("Salário-base tabela C 180 horas: ", value=1160.66 * soma_rel)
    salario_base_d_180 = st.sidebar.number_input("Salário-base tabela D 180 horas: ", value=1582.67 * soma_rel)
    salario_base_b_240 = st.sidebar.number_input("Salário-base tabela B 240 horas: ", value=1181.71 * soma_rel)
    salario_base_c_240 = st.sidebar.number_input("Salário-base tabela C 240 horas: ", value=1547.55 * soma_rel)
    salario_base_d_240 = st.sidebar.number_input("Salário-base tabela D 240 horas: ", value=2110.22 * soma_rel)
    

                        
    # Calcular novo salário usando a Tabela 1
    tabela_salarios_b_180, valores_b_180 = exibir_tabela_salarios(TC1, TR1, num_classes1, num_referencias1, salario_base_b_180, 'Tabela B - 180h')
    tabela_salarios_c_180, valores_c_180 = exibir_tabela_salarios(TC1, TR1, num_classes1, num_referencias1, salario_base_c_180, 'Tabela C - 180h')
    tabela_salarios_d_180, valores_d_180 = exibir_tabela_salarios(TC1, TR1, num_classes1, num_referencias1, salario_base_d_180, 'Tabela D - 180h')
    tabela_salarios_b_240, valores_b_240 = exibir_tabela_salarios(TC1, TR1, num_classes1, num_referencias1, salario_base_b_240, 'Tabela B - 240h')
    tabela_salarios_c_240, valores_c_240 = exibir_tabela_salarios(TC1, TR1, num_classes1, num_referencias1, salario_base_c_240, 'Tabela C - 240h')
    tabela_salarios_d_240, valores_d_240 = exibir_tabela_salarios(TC1, TR1, num_classes1, num_referencias1, salario_base_d_240, 'Tabela D - 240h')

    df['Novo Salário'] = calcular_novo_salario(df, valores_b_180,valores_c_180,valores_d_180,valores_b_240,valores_c_240,valores_d_240, pular_indice=indice_tabela)
    
        
    # Adicionando novas colunas
    df['novo_0085-ITA'] = (df['REF-ITA']  * df['Novo Salário'])
    df['novo_0107-ANUENIO'] = ((df['REF-ANUENIO']) * df['Novo Salário'])
    df['nova_105-INSALUBRIDAD'] = (( df['REF-INSALUBRIDAD']) * df['Novo Salário'])
    df['nova_0118-GR.PRODUT_'] = ((df['REF-GR.PRODUT']) * df['Novo Salário'])
    df['nova_0096-GAT'] = df['REF-GAT'] * df['Novo Salário']
    df['nova_0097-GEEF-AMC'] = (df['REF-GEEF-AMC']) * df['Novo Salário']
    df['nova_0159-GR.R.VIDA'] = (((1+ df['REF-GR.R.VIDA']) * (1 + taxa_gr_r_vida/100) - 1) * df['Novo Salário'])
    df['nova_0318-GE AMC'] = (df['REF-GE AMC']) * df['Novo Salário']
    df['novo_0817-B HR INC'] = df['0223-VP'] + df['0248-VPNI HEI'] + df['0001-G.F.INC-DNI1'] + df['0004-G.R.INC.DAS1'] + df['0005-G.R.INC.DAS2'] + df['0006-G.R.INC.DAS3'] + df['0007-G.R.INC.DNS1'] + df['0008-G.R.INC.DNS2'] + df['0009-G.R.INC.DNS3'] + df['0026-GR INC AT1'] + df['0027-GR INC AT2'] + df['Novo Salário'] + df['novo_0085-ITA'] + df['novo_0107-ANUENIO'] + df['nova_105-INSALUBRIDAD'] + df['nova_0118-GR.PRODUT_'] + df['nova_0159-GR.R.VIDA'] + df['nova_0318-GE AMC']
    df['nova_0133-HR.EXTR.INCO'] = round(df['novo_0817-B HR INC'] / df['CH'] * 1.25 * df['REF-HR.EXTR.INCO'],2)
    df['novo_0996-TOT.PROVENTO'] = df['Novo Salário'] + df['novo_0085-ITA'] + df['novo_0107-ANUENIO'] + df['nova_105-INSALUBRIDAD'] + df['nova_0118-GR.PRODUT_'] + df['nova_0096-GAT'] + df['nova_0097-GEEF-AMC'] + df['nova_0159-GR.R.VIDA'] + df['nova_0318-GE AMC'] + df['nova_0133-HR.EXTR.INCO'] + df['0223-VP'] + df['0248-VPNI HEI'] + df['0001-G.F.INC-DNI1'] + df['0004-G.R.INC.DAS1'] + df['0005-G.R.INC.DAS2'] + df['0006-G.R.INC.DAS3'] + df['0007-G.R.INC.DNS1'] + df['0008-G.R.INC.DNS2'] + df['0009-G.R.INC.DNS3'] + df['0026-GR INC AT1'] + df['0027-GR INC AT2'] + df['0308-DIF.AJ.PCCS'] + df['0320-GAJ 9903/12'] + df['0170-DIR.NIV.SUPE'] + df['0174-VRB.ESP.REP'] + df['0180-DIR.ASS.SUPE'] + df['0190-DIR.NIV.INT.'] + df['058-DIR GER 01'] + df['0326-GTRTC                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           '] + df['0206-AB.PERMANENC']
    df['nova_0872-B HR NOTURNA'] = df['nova_0133-HR.EXTR.INCO'] + df['0223-VP'] + df['0223-VP'] + df['0248-VPNI HEI'] + df['0001-G.F.INC-DNI1'] + df['0004-G.R.INC.DAS1'] + df['0005-G.R.INC.DAS2'] + df['0006-G.R.INC.DAS3'] + df['0007-G.R.INC.DNS1'] + df['0008-G.R.INC.DNS2'] + df['0009-G.R.INC.DNS3'] + df['0026-GR INC AT1'] + df['0027-GR INC AT2'] + df['Novo Salário'] + df['novo_0085-ITA'] + df['novo_0107-ANUENIO'] + df['nova_105-INSALUBRIDAD'] + df['nova_0118-GR.PRODUT_'] + df['nova_0096-GAT'] + df['nova_0097-GEEF-AMC'] + df['nova_0159-GR.R.VIDA'] + df['nova_0318-GE AMC']
    df['nova_0099-HR NOTURNAS'] = df['nova_0872-B HR NOTURNA'] / df['CH'] * 0.2 * df['REF-HR NOTURNAS']
    df['nova_0183-GR SER EXTRA'] = df['nova_0872-B HR NOTURNA'] / df['CH'] * 1.5 * df['REF-GR SER EXTRA']
    df['nova_0383-HE NOTURNA'] = df['nova_0872-B HR NOTURNA'] / df['CH'] * 1.5 * 1.2 * ((1+ df['REF-HE NOTURNA                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      ']) * ( 1+ taxa_he_noturna/100) - 1 )*100
    df['nova_0801-IPM PREVFOR'] = df['Novo Salário'] + df['novo_0085-ITA'] + df['novo_0107-ANUENIO'] + df['nova_105-INSALUBRIDAD'] + df['nova_0118-GR.PRODUT_'] + df['nova_0096-GAT'] + df['nova_0097-GEEF-AMC'] + df['nova_0318-GE AMC'] + df['nova_0133-HR.EXTR.INCO'] + df['0223-VP'] + df['0248-VPNI HEI'] + df['0001-G.F.INC-DNI1'] + df['0004-G.R.INC.DAS1'] + df['0005-G.R.INC.DAS2'] + df['0006-G.R.INC.DAS3'] + df['0007-G.R.INC.DNS1'] + df['0008-G.R.INC.DNS2'] + df['0009-G.R.INC.DNS3'] + df['0026-GR INC AT1'] + df['0027-GR INC AT2'] + df['0308-DIF.AJ.PCCS'] 
    df['nova_IPM PREVFOR-PATRONAL'] = df['nova_0801-IPM PREVFOR'] * 0.28
    df['nova_IPM PREVFOR-SERVIDOR'] = df['nova_0801-IPM PREVFOR'] * 0.14
    df['nova_base_IRPF'] = df['novo_0996-TOT.PROVENTO'] -  df['nova_IPM PREVFOR-SERVIDOR']            
    df['nova_IRPF'] = df['nova_base_IRPF'].apply(calcular_irpf) 
    
    # Quantidade de pessoas por cargo, carga horária e referência
    quantidade_pessoas = contar_pessoas(df)
    
    # Adicionando o totalizador geral
    total_quantidade = quantidade_pessoas['Quantidade'].sum()
    total_cons_venc_base = quantidade_pessoas['Consolidado VENCIMENTO BASE'].sum()
    total_geral = pd.DataFrame({'Cargo': ['Total Geral'], 'Quantidade': [total_quantidade], 'Consolidado VENCIMENTO BASE': [total_cons_venc_base]})
    
    quantidade_pessoas = pd.concat([quantidade_pessoas, total_geral], ignore_index=True)
    
    tabela_com_novo_salario = tabela_novo_salario(df)
    
    # Calcular totais para a tabela do novo salário
    total_vencimento_base = tabela_com_novo_salario['0996-TOT.PROVENTO'].sum()
    total_novo_salario = tabela_com_novo_salario['novo_0996-TOT.PROVENTO'].sum()
    subtracao = total_novo_salario - total_vencimento_base
    total_impacto = total_novo_salario - total_vencimento_base
    
    # cálculo dos encargos
    provisao_ferias_rem_anterior = (total_vencimento_base/12)/3
    provisao_ferias_nova = (total_novo_salario/12)/3
    provisao_ferias_impacto = (total_impacto/12)/3
    provisao_decimo_rem_anterior = (total_vencimento_base/12)
    provisao_decimo_nova = (total_novo_salario/12)
    provisao_decimo_impacto = (total_impacto/12)
    provisao_ipm_rem_anterior = (total_vencimento_base + provisao_ferias_rem_anterior + provisao_decimo_rem_anterior) * 0.04
    provisao_ipm_nova = ((total_novo_salario + provisao_ferias_nova + provisao_decimo_nova) * 0.04)
    provisao_ipm_impacto = provisao_ipm_nova - provisao_ipm_rem_anterior 
    ipm_previfor_anterior = df['IPM PREVFOR-PATRONAL'].sum()

    # Adicionar linha com totais à tabela do novo salário
    tabela_com_novo_salario.loc['Total', ['VENCIMENTO BASE', 'Novo Salário']] = [total_vencimento_base, total_novo_salario]

    # Calcular o resumo dos cargos
    resumo_cargos = calcular_impacto(df)

    # Totalizadores da tabela de impacto
    resumo_cargos.loc['Total', ['Cargo', 'Quantidade', 'Remuneração Anterior', 'Remuneração Nova', 'Impacto']] = ['',total_quantidade, total_vencimento_base, total_novo_salario, total_impacto]
    
    # Adicionar linha com subtítulo "Encargos" logo abaixo dos totalizadores
    resumo_cargos.loc[''] = ['Encargos', '', '', '', '']
    resumo_cargos.loc[len(resumo_cargos)] = ['Provisão de férias', '', provisao_ferias_rem_anterior, provisao_ferias_nova, provisao_ferias_impacto]
    resumo_cargos.loc[len(resumo_cargos)] = ['Provisão de 13º Salário', '', provisao_decimo_rem_anterior, provisao_decimo_nova, provisao_decimo_impacto]
    resumo_cargos.loc[len(resumo_cargos)] = ['Fortaleza Saúde- IPM (4%)', '', provisao_ipm_rem_anterior,provisao_ipm_nova , provisao_ipm_impacto]
    # resumo_cargos.loc['Total'] = []
        
    nova_ipm_previfor = df['nova_IPM PREVFOR-PATRONAL'].sum()    
    ipm_previfor_impacto = nova_ipm_previfor - ipm_previfor_anterior
    
    resumo_cargos.loc[len(resumo_cargos)] = ['IPM – PREVIFOR-FIN (28%)', '', ipm_previfor_anterior, nova_ipm_previfor, ipm_previfor_impacto]
    
    impacto_mensal_ant = total_vencimento_base + provisao_ferias_rem_anterior + provisao_decimo_rem_anterior + provisao_ipm_rem_anterior + ipm_previfor_anterior
    impacto_mensal_novo = total_novo_salario+provisao_ferias_nova + provisao_decimo_nova + provisao_ipm_nova + nova_ipm_previfor
    impacto_mensal_impacto = impacto_mensal_novo - impacto_mensal_ant
    resumo_cargos.loc[len(resumo_cargos)] = ['IMPACTO MENSAL', '', impacto_mensal_ant, impacto_mensal_novo, impacto_mensal_impacto]
    resumo_cargos.loc[len(resumo_cargos)] = ['IMPACTO ANUAL', '', impacto_mensal_ant*12, impacto_mensal_novo*12, impacto_mensal_impacto*12]
    
    # Calcular imposto de renda para a Remuneração Anterior e Nova
    imposto_renda_anterior = df['IRPF'].sum()
    imposto_renda_novo = df['nova_IRPF'].sum()
    impacto_imposto_renda = imposto_renda_novo - imposto_renda_anterior

    # Calcular IPM-PREVIFOR (Patronal) para a Remuneração Anterior e Nova
    ipm_previfor_patronal_anterior = df['IPM PREVFOR-PATRONAL'].sum()
    ipm_previfor_patronal_novo = df['nova_IPM PREVFOR-PATRONAL'].sum()
    impacto_ipm_previfor_patronal = ipm_previfor_patronal_novo - ipm_previfor_patronal_anterior

    # Calcular IPM PREVFOR-SERVIDOR para a Remuneração Anterior e Nova
    ipm_previfor_servidor_anterior = df['IPM PREVFOR-SERVIDOR'].sum()
    ipm_previfor_servidor_novo = df['nova_IPM PREVFOR-SERVIDOR'].sum()
    impacto_ipm_previfor_servidor = ipm_previfor_servidor_novo - ipm_previfor_servidor_anterior

    # Calcular valores totais
    valor_mensal_anterior = imposto_renda_anterior + ipm_previfor_patronal_anterior + ipm_previfor_servidor_anterior
    valor_mensal_novo = imposto_renda_novo + ipm_previfor_patronal_novo + ipm_previfor_servidor_novo
    impacto_mensal = valor_mensal_novo - valor_mensal_anterior

    valor_anual_anterior = valor_mensal_anterior * 12
    valor_anual_novo = valor_mensal_novo * 12
    impacto_anual = valor_anual_novo - valor_anual_anterior
    
   # ------------------------------------------------------------------ TABELAS, GRÁFICOS E DATAFRAMES ------------------------------------------------------------ #
    
    impacto_mensal_total = formatar_moeda(impacto_mensal + impacto_mensal_impacto)
    impacto_anual_total = formatar_moeda(impacto_anual + (impacto_mensal_impacto * 12))
    
    variacao_mensal_liquida = formatar_moeda(valor_mensal_novo + impacto_mensal_novo)
    variacao_anual_liquida = formatar_moeda(valor_anual_novo + (impacto_mensal_novo*12))
    
    percentual_efetivo_aumento_mensal = ((impacto_mensal + impacto_mensal_impacto)/(valor_mensal_anterior + impacto_mensal_ant))*100

    # col1, col2 = st.columns(2)
    st.markdown('##### **PERCENTUAL AUMENTO EFETIVO:**')
    st.info(f'{round(percentual_efetivo_aumento_mensal,2)} %')

    col1, col2  = st.columns(2)
    col1.text('Impacto Mensal:')
    col1.info(impacto_mensal_total)
    col2.text('Impacto Anual: ')
    col2.info(impacto_anual_total)

    col1, col2 = st.columns(2)
    col1.text('Novo Valor da folha Mensal: ')
    col1.info(variacao_mensal_liquida)
    col2.text('Novo Valor da folha Anual: ')
    col2.info(variacao_anual_liquida)
    
    col1,col2, col3, col4 = st.columns(4)
    col1.text('Taxa GAT')
    col1.info(f'{taxa_gat} %')
    col2.text('Taxa GE AMC')
    col2.info(f'{taxa_ge_amc} %')
    col3.text('Taxa GR R Vida')
    col3.info(f'{taxa_gr_r_vida} %')
    col4.text('Taxa HE Noturna ')
    col4.info(f'{taxa_he_noturna} %')
    
    # Criando um dicionário com as diferenças antes e depois do Ita
    diferencas_antes = {
        'ITA': df['0085-ITA'].sum(),
        'GAT': df['0096-GAT'].sum(),
        'GEEF-AMC': df['0097-GEEF-AMC'].sum(),
        'GR.R.VIDA': df['0159-GR.R.VIDA'].sum(),
        'GE AMC': df['0318-GE AMC'].sum()
    }

    diferencas_depois = {
        'ITA': df['novo_0085-ITA'].sum(),
        'GAT': df['nova_0096-GAT'].sum(),
        'GEEF-AMC': df['nova_0097-GEEF-AMC'].sum(),
        'GR.R.VIDA': df['nova_0159-GR.R.VIDA'].sum(),
        'GE AMC': df['nova_0318-GE AMC'].sum()
    }
    
    diferencas = {}
    for chave in diferencas_antes:
        diferencas[chave] = ((diferencas_depois[chave] - diferencas_antes[chave]) / diferencas_antes[chave]) * 100
        
    col1, col2, col3, col4, col5 = st.columns(5)
    
    col1.text('Impacto % ITA')
    col1.info(f'{round(diferencas["ITA"],2)} %')
    col2.text('Impacto % GAT')
    col2.info(f'{round(diferencas["GAT"], 2)} %')
    col3.text('Impacto % GEEF-AMC')
    col3.info(f'{round(diferencas["GEEF-AMC"], 2)} %')
    col4.text('Impacto % GR.R.VIDA')
    col4.info(f'{round(diferencas["GR.R.VIDA"], 2)} %')
    col5.text('Impacto % GE AMC')
    col5.info(f'{round(diferencas["GE AMC"], 2)} %')

    # Convertendo os dicionários em DataFrames
    df_diferencas_antes = pd.DataFrame.from_dict(diferencas_antes, orient='index', columns=['Antes'])
    df_diferencas_depois = pd.DataFrame.from_dict(diferencas_depois, orient='index', columns=['Depois'])

    # Concatenando os DataFrames de antes e depois
    df_diferencas = pd.concat([df_diferencas_antes, df_diferencas_depois], axis=1)

    # Plotando o gráfico de barras
    fig_gratificacoes, ax = plt.subplots(figsize=(8, 3))
    df_diferencas.plot(kind='bar', ax=ax)
    ax.legend(["Antes", "Depois"])
    ax.set_ylabel('Gratificações')
    # st.pyplot(fig_gratificacoes)  
    
    # Calculando as somas das colunas relevantes
    salarios_antes = df.groupby('Cargo')['0996-TOT.PROVENTO'].sum()
    salarios_depois = df.groupby('Cargo')['novo_0996-TOT.PROVENTO'].sum()

    # Criando um DataFrame com as somas antes e depois
    df_salarios = pd.DataFrame({'Antes': salarios_antes, 'Depois': salarios_depois})

    # Plotando o gráfico de barras
    fig_por_cargos, ax = plt.subplots(figsize=(8, 3))  # Definindo o tamanho da figura (largura, altura)
    df_salarios.plot(kind='bar', ax=ax)
    ax.set_ylabel('Total de Proventos')
    ax.set_title('Salários Antes e Depois por Cargo')
    
    col1, col2 = st.columns(2)
    col1.pyplot(fig_por_cargos)
    col2.pyplot(fig_gratificacoes)
    
    # Exibir e atualizar a tabela de salários por classe e referência (Tabela 1)
    tabelas = ['tabela_salarios_b_180','tabela_salarios_c_180','tabela_salarios_d_180','tabela_salarios_b_240','tabela_salarios_c_240','tabela_salarios_d_240']
    # tabela_salarios1, valores1 = exibir_tabela_salarios(TC1, TR1, num_classes1, num_referencias1, salario_base1, 'Tabela personalizável')
    st.write("Tabela de Referência")
    col1, col2 = st.columns(2)
    option_tabela = col1.selectbox('Mostrar tabela: ', tabelas,)
    col1, col2 = st.columns(2)
    if option_tabela == 'tabela_salarios_b_180': 
        st.dataframe(tabela_salarios_b_180, use_container_width=False)
    elif option_tabela == 'tabela_salarios_c_180': 
        st.dataframe(tabela_salarios_c_180, use_container_width=False) 
    elif option_tabela == 'tabela_salarios_d_180': 
        st.dataframe(tabela_salarios_d_180, use_container_width=False) 
    elif option_tabela == 'tabela_salarios_b_240': 
        st.dataframe(tabela_salarios_b_240, use_container_width=False) 
    elif option_tabela == 'tabela_salarios_c_240': 
        st.dataframe(tabela_salarios_c_240, use_container_width=False) 
    elif option_tabela == 'tabela_salarios_d_240': 
        st.dataframe(tabela_salarios_d_240, use_container_width=False) 
        

    # Nova tabela com o novo salário calculado
    st.write("Servidores:")
    st.dataframe(tabela_com_novo_salario.round(2), use_container_width=True)
    

    
    # Exibir a tabela de resumo de cargos
    st.header("Impacto da Reestruturação do PCCS da Gestão do Trânsito:",)
    st.dataframe(resumo_cargos.map(lambda x: formatar_moeda(x) if isinstance(x, (int, float)) else x),use_container_width=True)
    
    # Criar DataFrame com os resultados
    dados = {
        'Item': ['IMPOSTO DE RENDA', 'IPM-PREVIFOR (Patronal)', 'IPM-PREVIFOR (Servidor)', 'VALOR MENSAL', 'VALOR ANUAL'],
        'Remuneração Anterior': [imposto_renda_anterior, ipm_previfor_patronal_anterior, ipm_previfor_servidor_anterior, valor_mensal_anterior, valor_anual_anterior],
        'Remuneração Nova': [imposto_renda_novo, ipm_previfor_patronal_novo, ipm_previfor_servidor_novo, valor_mensal_novo, valor_anual_novo],
        'Impacto': [impacto_imposto_renda, impacto_ipm_previfor_patronal, impacto_ipm_previfor_servidor, impacto_mensal, impacto_anual]
    }

    tabela = pd.DataFrame(dados)

    # Formatando valores para exibição
    tabela['Remuneração Anterior'] = tabela['Remuneração Anterior'].apply(lambda x: formatar_moeda(x))
    tabela['Remuneração Nova'] = tabela['Remuneração Nova'].apply(lambda x: formatar_moeda(x))
    tabela['Impacto'] = tabela['Impacto'].apply(lambda x: formatar_moeda(x))
    
    styled_table = tabela.style.apply(lambda s: ['background-color: #dcdcdc; font-weight: bold' if s.name == 3 or s.name == 4 else '' for i in s], axis=1)

    st.header("Suavizações:")
    st.dataframe(styled_table, use_container_width=True)
    
    # Criar DataFrame com os totais
    dados_totais = {
        'Item': ['Impacto Líquido Mensal', 'Impacto Líquido Anual'],
        'Remuneração Anterior': [valor_mensal_anterior + impacto_mensal_ant, valor_anual_anterior + (impacto_mensal_ant*12)   ],
        'Remuneração Nova': [valor_mensal_novo + impacto_mensal_novo, valor_anual_novo + (impacto_mensal_novo*12) ],
        'Impacto': [impacto_mensal + impacto_mensal_impacto,  impacto_anual + (impacto_mensal_impacto*12)]
    }
        
    tabela_dados_totais = pd.DataFrame(dados_totais)

    # Formatando valores para exibição
    tabela_dados_totais['Remuneração Anterior'] = tabela_dados_totais['Remuneração Anterior'].apply(lambda x: formatar_moeda(x))
    tabela_dados_totais['Remuneração Nova'] = tabela_dados_totais['Remuneração Nova'].apply(lambda x: formatar_moeda(x))
    tabela_dados_totais['Impacto'] = tabela_dados_totais['Impacto'].apply(lambda x: formatar_moeda(x))
    
    st.header("Totais:")
    st.dataframe(tabela_dados_totais, use_container_width=True)
    
if __name__ == '__main__':
    main()