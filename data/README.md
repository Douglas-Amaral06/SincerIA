# Dados da SincerIA

No Streamlit Community Cloud, o app é executado a partir da raiz deste repositório. O backend cria `sincerIA.db` nesta pasta e grava os anexos em `uploads/`. O SQLite contém as perguntas, respostas, datas, IDs de conversa e dados dos agentes; os anexos ficam em arquivos separados.

Esses arquivos são gerados durante a execução e não são enviados ao GitHub. O armazenamento local do Community Cloud pode ser perdido quando o app reinicia ou é recriado. Para guardar uma cópia, entre no **Painel admin** do site e use **Baixar todas as interações em JSON**. Quando houver um banco externo, ele deverá substituir este armazenamento temporário.

Para habilitar o painel no Cloud, configure `ADMIN_PASSWORD` em **Manage app → Settings → Secrets**. O login padrão é `ADMIN`. Nunca coloque a senha neste repositório.
