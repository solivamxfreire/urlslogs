"""urlslogs URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path

# from urlslogs.apps.valorvendasugerido.create import cadastro_valor_venda_sugerido
# from urlslogs.apps.valorvendasugerido.list import lista_valor_venda_sugerido, dropdown_valor_venda_sugerido
from urlslogs.apps.cloudwatch.views import registra_log_requisicao, view_log_events

urlpatterns = [

    path('registra_log_requisicao/', registra_log_requisicao),
    path('busca_log_requisicao/', view_log_events),
    # path('grupo/<int:pk>/', lista_grupo),
    #
    # path('cria_grupo/', grava_grupo),
    # path('altera_grupo/<int:pk>/', grava_grupo),

]
