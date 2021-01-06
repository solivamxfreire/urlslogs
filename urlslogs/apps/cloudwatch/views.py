import json
import boto3

from datetime import date, datetime

import pytz
from rest_framework.decorators import api_view
from rest_framework.response import Response
from urlslogs import settings
from urlslogs.apps.cloudwatch.create import teste_cloud_log


# processar_requisicao(request=None, nome_api=None, body=None, pk=None, campo_body=None, nome_endpoint="tabelao",
#                          parametros_dict=None, metodo=None, headers=None)

@api_view(('POST',))
def registra_log_requisicao(request):
    """
    View que pega o json enviado na requisicao, para registra-lo no cloudwatch log.
    A estrutura no cloudwatch para encontrar o registro salvo será "nome_inquilino-requests/mm-yyyy". Primeiro verifica se
    existe essa estrutura, caso não, cria o log Group (nome_inquilino-requests) e o log Stream (mes/ano) para então registrar
    o log de alteração;

    O formato esperado do json é:
         {
            "nome_tenant": "pernambucanas",
            "mensagem": "GET method - lista_funcionario/ 200",
            "usuario": "eduardo_edu",
            "usuario_id": 1,
            "funcionario": "Eduardo Edu",
            "funcionario_id": 2
        }
    * Observe o que significa cada campo da requisicao:
        - nome_tenant: deverá ser o mesmo nome do schema do inquilino.
        - mensagem: mensagem formatada informando qual url o usuario chamou e demais infos necessárias.
        - usuario: username de quem salvou/alterou o registro
        - usuario_id: pk do user
        - funcionario: nome do funcionario
        - funcionario_id: pk do funcionario


    :param request:
    :return:
    """
    usuario_logado = '-'

    # formata o json da requisicao do usuario, e manda pra funcao de registro no cloudwatch log
    try:
        body_unicode = request.body.decode('utf-8')
        body_data = json.loads(body_unicode)

        objeto = body_data

        fuso_horario = pytz.timezone('America/Sao_Paulo')
        data_hora = datetime.now().astimezone(fuso_horario)
        objeto['info_data_hora'] = data_hora.strftime("%d/%m/%Y, %H:%M:%S")

        # nome do inquilino para criar no log que é dele
        nome_tenant = body_data.pop('nome_tenant', None)

        # chama funcao de criar log do objeto
        # TODO: usar futuramente funcao do log no celery para ficar assíncrona numa fila de tarefas.
        teste_cloud_log(objeto, nome_tenant)

    except Exception as e:
        print(e)
        msg = {'Erro': 'Dados Informados não estão no formato esperado.'}

        return Response(msg, content_type='application/json')

    return Response({'mensagem': 'Sucesso ao registrar log da requisição.'}, content_type='application/json')


@api_view(['GET'])
def view_log_events(request):
    """
    Busca registros de log do CloudWatch aws. Busca na estrutura <nome_inquilino-requests>/<mes-ano>, onde estarão as requisicoes de url
    registradas daquele inquilino:

    O formato de json esperado é:
        {
            "mes/ano": "12/2020",
            "inquilino": "americanas"
        }

    Você pode opcionalmente informar no "params" da requisição, os seguintes campos:
        - nome_usuario  Trazer os registros do usuario "Fulano"
    :return:
    """
    # nome log group:
    LOG_GROUP = ''

    try:
        # pegar o body da requisição e transforma em python object
        body_unicode = request.body.decode('utf-8')
        body_data = json.loads(body_unicode)
        data_log = body_data['mes/ano']
        LOG_GROUP = body_data['inquilino'] + "-requests"

    except Exception as e:
        print(e)
        msg = {'Retorno': 'dados Informados não estão no formato { "mes/ano": "mm/yyyy", "inquilino": "<nome>" } .'}
        return Response(msg, content_type='application/json')

    # nome do logStream => será mes/ano, virando o mes, novo logStream será criado dentro daquele logGroup
    data_hoje = date.today()
    data_hoje_str = data_hoje.strftime("%m/%Y")
    LOG_STREAM = data_log

    # instancia o cliente boto3 que acessa o servico cloudwatch-logs com as credenciais de um user com permissao
    logs = boto3.client('logs', region_name=settings.AWS_DEFAULT_REGION, aws_access_key_id=settings.CLOUDWATCH_AWS_ID,
                        aws_secret_access_key=settings.CLOUDWATCH_AWS_KEY)

    try:
        # buscar os logs do inquilino no mes/ano informados
        response = logs.filter_log_events(
            logGroupName=LOG_GROUP,
            logStreamNames=[
                LOG_STREAM,
            ],
            # logStreamNamePrefix='string', # prefix pesquisa por logstream que comecam com a str informada
            # startTime=123,
            # endTime=123,
            # filterPattern='string',
            # nextToken='string',
            # limit=123,
            # interleaved=True | False
        )

    except logs.exceptions.ResourceNotFoundException:
        msg = {'Retorno': 'Não há registros de log disponíveis para consulta.'}
        return Response(msg, content_type='application/json')

    # for obj in response['events']:
    #     print(obj)
    # j = json.dumps(response)

    # pega valor da quantidade de logs retornados
    qtd_logs = len(response['events'])

    # na response, a chave events contém os logs
    events = response['events']

    cont = 0
    list_logs = []
    # Iterar sobre os logs pegando apenas a informacao de alteracao, e adicionando na lista de resposta
    while cont < qtd_logs:
        # pegar só o campo message de cada log retornado, pois message contem a fotografia da alteracao do model
        if events[cont]['message']:
            str_message = events[cont]['message']

            try:
                object_message = json.loads(str_message)
            except Exception as e:
                object_message = None

            list_logs.append(object_message)

        cont = cont + 1

    parametros = request.query_params

    # caso deseje filtrar resultados por nome do usuario
    list_logs_filtro_usuario = []
    if 'nome_usuario' in parametros:
        if parametros['nome_usuario']:

            for item in list_logs:
                if item['usuario_nome'] == parametros['nome_usuario']:
                    list_logs_filtro_usuario.append(item)

            list_logs = list_logs_filtro_usuario

    return Response(list_logs, content_type='application/json')

