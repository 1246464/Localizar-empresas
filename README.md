# Localizador de empresas

Aplicativo desktop em Python e PyQt5 para encontrar empresas por proximidade com OpenStreetMap, Google Places, Yelp e Foursquare.

![Interface do aplicativo](screenshot.png)

## Executar no Windows

Requer Python 3.10 ou superior.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe localizador_empresas.py
```

## Como usar

1. Escolha a fonte. O **OSM** vem selecionado e não exige chave.
2. Para outros provedores, informe uma chave com acesso à API correspondente. A chave fica mascarada e não é salva pelo aplicativo.
3. Escolha um segmento em português ou digite um termo compatível com o provedor.
4. Defina o raio em metros: até 50.000 m, ou 40.000 m para Yelp.
5. Informe latitude e longitude (ponto ou vírgula decimal) ou clique em **Usar localização por IP**. Essa ação consulta o serviço HTTPS ipwho.is. A posição é aproximada: confirme antes de buscar. Não existe localização padrão silenciosa.
6. Clique em **Buscar empresas**. Filtre a tabela por texto e clique nos cabeçalhos para ordenar.
7. **Exportar Excel** salva apenas as linhas visíveis, na ordem exibida, com filtros e cabeçalho congelado.

## Provedores e limites

- **OpenStreetMap:** consulta Overpass incluindo pontos, áreas e relações. Categorias conhecidas usam tags apropriadas (`amenity`, `shop`, `tourism`, `leisure`). Termos personalizados devem ser valores de `amenity`, como `dentist`. Não fornece avaliações. Dados © colaboradores do OpenStreetMap, ODbL.
- **Google:** usa Places API (New), Nearby Search, com até 20 resultados por consulta. Ative essa API na conta. Campos de avaliações podem afetar a cobrança. [Documentação oficial](https://developers.google.com/maps/documentation/places/web-service/nearby-search).
- **Yelp:** busca até 50 resultados por consulta, com endereço completo quando disponível.
- **Foursquare:** usa Places API atual com token Bearer e versão `2025-06-17`, até 50 resultados. [Documentação oficial](https://docs.foursquare.com/fsq-developers-places/reference/place-search).

Os resultados não constituem uma listagem exaustiva de empresas. Cobertura, disponibilidade, limites e cobrança dependem do provedor e da conta. Consulte os termos de cada fonte antes de reutilizar os dados.

## Melhorias desta versão

- Layout redimensionável, painel de busca, estados vazios e indicador de atividade.
- Localização, pesquisa e exportação em segundo plano.
- Coordenadas editáveis e validação de intervalos e valores não finitos.
- Categorias em português e OSM disponível sem configuração inicial.
- Ordenação numérica, tabela sem edição acidental e filtro textual.
- Resultados anteriores preservados quando uma nova consulta falha.
- Chaves não incluídas nas mensagens de erro e textos externos exportados como texto, nunca como fórmulas.
- Fechamento impedido durante uma operação para evitar destruir uma thread ativa. As requisições possuem timeout.
- Serviços separados da interface e remoção da dependência de pandas.

## Testes

```powershell
.\.venv\Scripts\python.exe -m unittest -v
```

Os testes usam respostas simuladas: não consomem cota e não validam credenciais reais. Validam normalização, coordenadas, limites, erros, exportação e comportamento da interface.
