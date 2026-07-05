# Arquigrafia Uploader CLI 🚀

Uma interface de terminal (TUI/CLI) moderna, rápida e inteligente para automatizar o envio de fotografias arquitetônicas para a plataforma [Arquigrafia](https://www.arquigrafia.org.br).

O projeto conta com identidade visual em tom **Marsala**, barra de progresso customizada inspirada no estilo **Flow TUI** e integração com **Inteligência Artificial (BLIP)** local para descrição de fotos e geração automática de tags.

---

## ✨ Recursos

- **IA Visual Local (BLIP-base):** Analisa a estrutura física da foto e gera uma descrição textual complementar em português automaticamente.
- **Geolocalização Inteligente (GPS + Nominatim):** Extrai latitude/longitude dos dados EXIF e obtém o nome exato da rua, bairro, cidade e pontos de interesse (POI).
- **Nomeação por Local:** Renomeia o título da imagem no upload de forma inteligente a partir do local (ex: *Sesc 24 de Maio*, *Fórum João Mendes*).
- **Compressão Inteligente:** Reduz o tamanho de arquivos pesados para menos de 10 MB para garantir o envio no limite do servidor, preservando os metadados EXIF.
- **TUI Marsala & Flow Columns:** Interface elegante com questionários e barra de progresso contendo estimativa em tempo real da velocidade de upload (`KB/s`).
- **Seleção Flexível:** Permite selecionar uma pasta inteira ou apenas um arquivo de imagem único (`.jpg`, `.jpeg`, `.png`, `.webp`).
- **Persistência de Sessão Segura:** Armazena o login e senha cifrados usando o chaveiro seguro do sistema (Windows Keyring).

---

## 🛠️ Instalação e Execução

### Opção 1: Executável (Pronto para Uso)
Você pode rodar diretamente o executável independente pré-compilado:
1. Vá até a pasta `dist/` do projeto.
2. Execute o arquivo `arquigrafia.exe`.

### Opção 2: A partir do Código-Fonte
Se preferir rodar no seu ambiente Python (requer Python 3.10+):

1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Inicie a aplicação:
   ```bash
   python main.py
   ```

---

## 📝 Estrutura do Projeto

```
arquigrafia-cli/
├── cli/
│   ├── screens/         # Telas da TUI (Login, Pasta, Config)
│   └── utils.py         # Configurações de tema, fontes e console
├── core/
│   ├── auth.py          # Autenticação e persistência de sessão
│   ├── exif.py          # Extração de metadados das imagens
│   ├── geo.py           # Geolocalização com cache local (.geo_cache.json)
│   ├── ia.py            # Integração com IA BLIP
│   └── uploader.py      # Lógica e motor do upload HTTP
├── main.py              # Ponto de entrada e orquestrador do loop
└── requirements.txt     # Dependências do Python
```

---

## 🔒 Segurança de Credenciais
A aplicação utiliza a biblioteca `keyring` para interagir com o gerenciador de credenciais do Windows (Credential Manager), salvando sua senha de forma criptografada pelo sistema operacional. Nenhum dado de acesso é enviado a servidores de terceiros além do próprio Arquigrafia.
