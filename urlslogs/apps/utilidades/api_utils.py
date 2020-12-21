# 08/12/2020

import inspect
from json import JSONDecodeError
from django.http import HttpResponse
from django.template.response import ContentNotRenderedError
from rest_framework.response import Response
import requests
from rest_framework.utils import json


# retorna o nome da função que chamar esta função
def nome_api_url():
    return inspect.stack()[2][3]


def get_parametro(request, nome_parametro):
    try:
        parametro = request.query_params[nome_parametro]
    except KeyError:
        parametro = None

    return parametro


def get_val(dicionario, chave):
    try:
        parametro = dicionario[chave]
    except KeyError:
        parametro = None
    except TypeError:
        parametro = None
    return parametro


def get_result(resposta):
    try:
        dados = resposta.data
        if type(dados) == str:
            dados = json.loads(dados)
        results = dados['results']
        if len(results) > 0:
            return results[0]
        return None
    except KeyError:
        return None
    except TypeError:
        return None


def obter_validador(caminho, nome_api_uri="generica"):
    """
    Obtem o validador específico da função da api.
    O validador precisa estar no diretório da api com o nome validacao_nome_da_api.py e
    deve conter os métodos "validar_antes", "validar_depois" carregados com os métodos de validação
    personalizados. Veja o exemplo "validacao_exemplo.py" para ter uma noção melhor sobre o assunto.

    caminho: Especificar __name__ no parâmetro ao chamar;
    nome_api_url: O nome da api. Se não for especificado, pegará pelo nome detectado da função chamadora
    """
    if not nome_api_uri:
        nome_api_uri = nome_api_url()

    try:
        # Retorna a validação da api específica
        return __import__(caminho + "validacao_" + nome_api_uri)
    except ModuleNotFoundError:
        return None


# Função que retorna o settings do projeto atual
def settings():
    repositorio = __import__(str(__name__).split(".")[0])
    return repositorio.settings


# Obtem o body que vier no request, já convertendo para objeto python
def obter_body(request):
    """
    Decodifica o corpo da requisição, de uma string json passa para dicionário python.
    Caso o corpo da requisição seja de formato inválido, retorna mensagem de erro 400 bad request.
    """
    try:
        # formato nosso utf-8
        body_decode = request.body.decode('utf-8')
        if body_decode == '':
            return True, None
        return True, json.loads(body_decode)

    except Exception as e:
        # Retorna um erro e o código http 400 = Bad Request
        erro = {"erro": "O corpo da requisição é invalido!",
                "info": str(e)}
        return False, Response(erro,
                               content_type='application/json', status=400)


def monta_uri_endpoint(nome_api, nome_endpoint, *args):
    """
    Formata uma string url para chamar a api do tabelão de acordo com o sufixo
    e os demais paràmetros informados.
.
    Esta função já está pronta para processar vários campos de entrada (*args)
    """

    # Criar a mascara de string a partir dos parâmetros fornecidos
    # parametros iniciais (url e nome da api)
    if len(args) > 0 and args[0]:
        parametros = (settings().ENDPOINT[nome_endpoint], nome_api,)
    else:
        return settings().ENDPOINT[nome_endpoint] + "/" + nome_api

    # se tem parametros adicionais, adicionar na url
    if args[0]:
        args = parametros + args

    # senão, apenas o url e sufixo será montado na url
    else:
        args = parametros

    # monta a url de acordo com a quantidade de parametros informados
    mascara = "{}/" * len(args)

    # retorna a url da api formatada com os parametros preenchidos (sufixo, pk se tiver, filtros, etc)
    return mascara.format(*args)


def processar_requisicao(request=None, nome_api=None, body=None, pk=None, campo_body=None, nome_endpoint="tabelao",
                         parametros_dict=None, metodo=None, headers=None):
    """
    Aqui onde de fato a api é consultada (tabelao, etc). Pega-se o sufixo da url a ser invocada na api destino,
    o body da requisição (se houver) valida ele, e depois pega-se os parametros (se houver), e no final consulta a api,
    retornando ou a mensagem com o retorno de sucesso, ou retorna o erro que porventura ocorrer.


    Faz o processamento genérico da requisão.
    Este método só deverá ser alterado para implementação de métodos http
    ou para ajustes nos métodos atuais (tratamento de erros ou de parâmetros)

    request: O request da solicitação chamadora;
    nome_api: O nome da api a ser requisitada que pertença ao tabelão;
    body: O body já processado e validado;
    pk: Caso seja passada diretamente a chave pk, informar nesse campo.
    campo_body: O campo contido no body que será incluído no caminho da URi;
    """

    if not nome_endpoint:
        nome_endpoint = "tabelao"

    if not nome_api:
        nome_api = nome_api_url()

    # Caso não haja um body e seja um request, chamar obter_body que nos retornará o erro de corpo inválido:

    if request:
        if not body or body == "":
            retorno, body = obter_body(request)
            # Se o retorno gerar um erro, retorna o response com o erro.
            if not retorno:
                body = None  # isso sim!

    # Ou usa o PK para montar a requisição, ou usa um campo do body
    # se nao for informado a pk ( get all ou post)
    if not pk:
        argumento = None
        if body:

            if type(campo_body) == tuple:
                # Trata uma tupla de argumentos
                argumento = ()
                for arg in campo_body:
                    try:
                        argumento = argumento + (body[arg],)
                    except KeyError:
                        pass

            else:
                # Trata uma unico argumentos
                if campo_body:
                    # Se um campo do body a ser usado na URi for especificado...
                    try:
                        argumento = body[campo_body]
                    except KeyError:
                        pass

    # quando tiver pk (get em registro específico, ou atualizar um registro (put)
    else:
        argumento = pk
    uri = monta_uri_endpoint(nome_api, nome_endpoint, argumento)

    # Esse 'argumento' será montado na uri da seguinte forma: .../nome_api/argumento1/argumento2...

    # Processando a requisição de um item apenas.
    # a linha a seguir obtem a função de acordo com o método http que vier: GET, POST ou seja o que vier!
    if not metodo and request:
        metodo = request.method

    if metodo:
        http_method_func = getattr(requests, str(metodo).lower())
    else:
        # Quando não for especificado o request, tem que dizer qual é o método.
        return False, Response(
            {"erro": "Metodo HTTP precisa ser especificado quando não existir uma requisição chamadora!"},
            content_type='application/json', status=400)

    # Requisições do tipo POST precisam terminar com slash
    if metodo.upper() == "POST" or metodo.upper() == "PUT":
        uri = uri + '/'

    # Caso enviem parametros na requisição (chave/valor) serão guardados em um dict para ser usado na chamada da api.
    # os parâmetros podem vir de forma automatica pelo método, quando passado um request ou manualmente
    if not parametros_dict and request:
        parametros = None
        for atributo in request.GET:
            if not parametros:
                parametros = {}
            parametros[atributo] = request.GET.get(atributo, None)
    else:
        parametros = parametros_dict

    # Aqui a requisicao é de fato executada na api tabelas, com body (se houver) e params (se houver)
    try:
        # Se não forem especificados os headers, pega-los da requisição chamadora, no request, quando houver request.
        if not headers and request:
            # headers = {"Authorization": settings().TOKEN}
            headers = request._request.headers
        uri = uri.replace("://", ":¨¨")
        uri = uri.replace("//", "/")
        uri = uri.replace(":¨¨", "://")

        it = http_method_func(uri, json=body, headers=headers, verify=False,
                              params=parametros, allow_redirects=True)
    except Exception as e:
        erro = {"erro": "Tempo esgotado na requisição!",
                "info": str(e)}
        return False, Response(erro, content_type='application/json', status=500)

    # Tratamento de status de retorno genérico - fazer demais tratamentos no método chamador.
    # se o retorno do status for 200 ou 201 - bem sucedido
    if 200 <= it.status_code <= 299:
        return True, gerar_resposta(it)

    # Em qualquer caso de redirect, retornar o redirecionamento
    elif 300 <= it.status_code <= 399:
        return True, it
    else:
        # Em outro caso, onde ocorrer um erro, retornar o conteúdo renderizado como Response.
        return False, gerar_resposta(it)


def gerar_resposta(it):
    """
    Gera uma resposta válida com o content de it.
    """
    try:
        conteudo = it.content
    except ContentNotRenderedError:
        conteudo = it.data

    if type(conteudo) == bytes:
        conteudo = conteudo.decode("utf-8")

    dados = None
    try:
        if type(conteudo) == dict:
            dados = conteudo
        elif type(conteudo) == str:
            dados = json.loads(conteudo)
        return Response(dados, content_type='application/json', status=it.status_code)
    except JSONDecodeError:
        return HttpResponse(content=conteudo, status=it.status_code, content_type=it.headers['Content-Type'])


def get_dado_resposta(it, campo):
    dado = get_val(it.data, campo)
    if not dado:
        return Response("Erro interno", 400)
    return dado
