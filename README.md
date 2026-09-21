# Acompanhamento de Turnos GO

Aplicativo Streamlit que apresenta os turnos das equipes GOOL, GOOC, GOOK e GOOH.
Os dados são consultados por meio do Google Apps Script conectado à planilha
`acompanha turnos`.

## Publicação no Streamlit Community Cloud

Use `streamlit_app.py` como arquivo principal.

Em **App settings → Secrets**, configure:

```toml
[apps_script]
url = "URL_FINAL_DO_APPS_SCRIPT_TERMINADA_EM_EXEC"
read_token = "READ_TOKEN_CONFIGURADO_NO_APPS_SCRIPT"
```

O arquivo real `.streamlit/secrets.toml` não deve ser enviado ao GitHub.
