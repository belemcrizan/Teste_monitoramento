# Contribuindo

## Regra central

Uma mudança precisa melhorar detecção, evidência ou operação sem transformar correlação em conclusão. Preserve as fronteiras `Feature → Finding → Alert → Case`.

## Fluxo

1. Crie uma branch.
2. Escreva/ajuste golden cases antes do código.
3. Implemente reason codes, evidências, missing data e limitações.
4. Atualize a versão do detector/política quando o comportamento mudar.
5. Execute `make test`, `make quality` e `make build`.
6. Documente impacto, risco e rollback.

## Requisitos para detectores

- fórmula e unidade documentadas;
- janela/coorte explícitas;
- denominador zero e nulos testados;
- dados mínimos e cobertura condicionada;
- explicações benignas consideradas;
- caminho inconclusivo;
- IDs determinísticos;
- golden case adverso e controle benigno;
- nenhuma linguagem de culpa/intenção na saída técnica.

## Commit e PR

Inclua no PR:

- problema e hipótese;
- versão anterior/nova;
- testes e resultados;
- impacto esperado no volume da fila;
- limitações;
- plano de replay/rollback.

