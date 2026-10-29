# Ungari Vínculos

Plataforma de diagnóstico de vínculos organizacionais e cultura (Comprometimento, Consentimento e Entrincheiramento, lidos pelos níveis da cultura de Schein). A metodologia está em [METODOLOGIA.md](METODOLOGIA.md).

## Rodar no Mac

```bash
cd ~/Desktop/ungari-vinculos && ./venv/bin/uvicorn app.main:app --port 8010
```

Abra http://localhost:8010. No primeiro start é criado o usuário Master (`diegoungari04@gmail.com`) com senha aleatória, gravada em `data/CREDENCIAIS_INICIAIS.txt`. Troque a senha em **Minha conta** e apague o arquivo.

Empresa de demonstração com 26 pessoas e respostas simuladas (a senha das contas demo também vai para o arquivo de credenciais):

```bash
cd ~/Desktop/ungari-vinculos && ./venv/bin/python -m app.seed_demo
```

Para remover a demo: menu **Empresas**, excluir "Empresa Demonstração".

## Níveis de acesso

| Nível | Pode |
|---|---|
| Colaborador | Responder e ver o próprio resultado |
| Gestor | + ver e comparar o resultado de todas as pessoas abaixo dele na hierarquia (diretas e indiretas) |
| Admin | + cadastrar e excluir pessoas e áreas, gerar convites, disparar e encerrar coletas, ver agregados de áreas e empresa (sem relatórios individuais de quem não é do seu time) |
| Master | Tudo, em todas as empresas, mais edição do questionário (versões) e cadastro de empresas |

## Fluxo de uso

1. **Empresas** (Master): cadastre a empresa cliente.
2. **Cadastro**: crie áreas e pessoas (uma a uma ou colando uma lista). Defina o gestor direto de cada pessoa: é isso que dá ao gestor acesso ao time.
3. **Coletas**: dispare o questionário para todos, para áreas ou para pessoas específicas. Sem e-mail configurado, a tela entrega os links e as mensagens prontas para copiar ou abrir no e-mail.
4. Cada pessoa cria a senha pelo link de convite, responde (cerca de 7 minutos) e vê o relatório na hora.
5. **Meu time**, **Áreas e empresa**: dashboards com comparação de pessoas e áreas.

## Envio de e-mail (opcional)

Defina `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` e `APP_BASE_URL` (endereço público). Para Gmail, use uma senha de app.

## Publicar

Mesma receita do Ungari Perfil (Render ou Railway): comando de start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, variáveis `APP_BASE_URL`, `MASTER_PASSWORD` e `DATABASE_PATH` apontando para um **disco persistente** (o SQLite precisa de volume, senão os dados somem a cada deploy).

## Estrutura

- `app/instrument.py`: itens, perfis, textos dos relatórios e pontuação
- `app/main.py`: API, autenticação e permissões
- `app/seed_demo.py`: dados de demonstração
- `static/`: interface (HTML, CSS e JS, gráficos com Chart.js)

### Render (passo a passo)

O arquivo `render.yaml` já descreve o serviço: plano Starter (o grátis não tem disco), disco de 1 GB em `/var/data` e as variáveis `DATABASE_PATH` e `APP_BASE_URL`.

1. Envie esta pasta para um repositório no GitHub.
2. No Render: **New > Blueprint**, escolha o repositório e confirme.
3. Se o endereço gerado for diferente de `https://ungari-vinculos.onrender.com`, ajuste `APP_BASE_URL` em Environment.
4. Em produção (APP_BASE_URL com https e sem MASTER_PASSWORD), o Master não recebe senha: abra **Logs** e procure "Primeiro acesso Master". O link leva à tela de criar a sua senha.
