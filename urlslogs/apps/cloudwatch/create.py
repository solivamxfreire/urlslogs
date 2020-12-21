import time
from datetime import date

import boto3

from django.core.serializers.json import DjangoJSONEncoder

# Create your models here.
from django.db.models.fields.files import ImageFieldFile, FileField

import json
from urlslogs import settings


class LazyEncoder(DjangoJSONEncoder):
    """
    Enconder que faz o json.dumps converter corretamente os dicts que possuem campos do tipo ImageField, FileField
    e outros tipos que forem necessários tratamento especial.
    """

    def default(self, obj):
        if isinstance(obj, ImageFieldFile):
            return str(obj)
        if isinstance(obj, FileField):
            return str(obj)
        return super().default(obj)


# from front.celery import app
# logger = get_task_logger(__name__)
# @app.task()


def teste_cloud_log(self, inquilino):
    """
    Salva no CloudWatch Log, dentro da estrutura [nome_inquilino-requests/mm-yyyy] as informacoes das urls
    acessadas pelos usuarios do automotivo.
    :param self:
    :param inquilino:
    :return:
    """

    # passa para str o dict com o objeto
    registro_str = json.dumps(self)

    # instanciar o cliente boto3 que acessa o servico cloudwatch-logs com as credenciais de um user com permissao
    logs = boto3.client('logs', region_name=settings.AWS_DEFAULT_REGION, aws_access_key_id=settings.CLOUDWATCH_AWS_ID,
                        aws_secret_access_key=settings.CLOUDWATCH_AWS_KEY)

    # nome do grupo de log: será o nome do inquilino
    LOG_GROUP = inquilino + "-requests"

    # nome do logStream => será mes/ano, virando o mes, novo logStream será criado dentro daquele grupo de log
    data_hoje = date.today()
    data_hoje_str = data_hoje.strftime("%m/%Y")
    LOG_STREAM = data_hoje_str

    # Checa existencia do Grupo de log, se nao existir, cria ele
    log_group_existe = logs.describe_log_groups(logGroupNamePrefix=LOG_GROUP)

    if len(log_group_existe['logGroups']) == 0:
        logs.create_log_group(logGroupName=LOG_GROUP)

    # Checa existencia do log Stream [mm/yyyy] , se nao existir, cria ele
    log_stream_existe = logs.describe_log_streams(logGroupName=LOG_GROUP, logStreamNamePrefix=LOG_STREAM)

    if len(log_stream_existe['logStreams']) == 0:
        logs.create_log_stream(logGroupName=LOG_GROUP, logStreamName=LOG_STREAM)

    timestamp = int(round(time.time() * 1000))
    # time.strftime('%Y-%m-%d %H:%M:%S')

    # registra o log no cloudwatch:
    try:
        response = logs.put_log_events(
            logGroupName=LOG_GROUP,
            logStreamName=LOG_STREAM,
            logEvents=[
                {
                    'timestamp': timestamp,
                    'message': registro_str
                }
            ]
        )
    # caso peça o token sequence, enviá-lo na hora do registro
    except logs.exceptions.InvalidSequenceTokenException as exception:

        sequence_token = exception.response['expectedSequenceToken']

        response = logs.put_log_events(
            logGroupName=LOG_GROUP,
            logStreamName=LOG_STREAM,
            sequenceToken=sequence_token,
            logEvents=[
                {
                    'timestamp': timestamp,
                    'message': registro_str
                }
            ]
        )


# def monta_json_log(self):
#     """
#     :param self:
#     :return:
#     """
#     # registro = self.__dict__
#     registro = model_to_dict(self)
#
#     nome_model = self.__class__.__name__
#     # pega usuario que salvou a alteracao
#     quem = 'cipriano'
#     registro['info_usuario'] = quem.username
#
#     # pega data da alteração
#     data = datetime.now()
#     registro['info_data_modificado'] = data.strftime("%d/%m/%Y, %H:%M:%S")
#
#     # nome do model
#     registro['info_tabela'] = nome_model
#
#     # remover campo desnecessário
#     # del registro['_state']
#
#     # converte dict em json str
#     registro_str = ''
#     try:
#         registro_str = json.dumps(registro, ensure_ascii=False, cls=LazyEncoder)
#
#     except Exception as e:
#         pass
#
#     return registro_str
