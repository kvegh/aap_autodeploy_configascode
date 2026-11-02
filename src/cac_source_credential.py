"""Portable source-reader credential schema using Controller's single-file injector."""


def definition():
    return {
        "name": "AAP CaC source reader",
        "kind": "cloud",
        "inputs": {
            "fields": [
                {
                    "id": "source_url",
                    "label": "Source Controller HTTPS origin",
                    "type": "string",
                },
                {
                    "id": "api_token",
                    "label": "Source Controller API token",
                    "type": "string",
                    "secret": True,
                },
                {
                    "id": "source_ca_pem",
                    "label": "Existing trusted source CA PEM (optional)",
                    "type": "string",
                    "secret": True,
                    "multiline": True,
                },
            ],
            "required": ["source_url", "api_token"],
        },
        "injectors": {
            "env": {
                "AAP_CAC_SOURCE_URL": "{{ source_url }}",
                "AAP_CAC_SOURCE_TOKEN": "{{ api_token }}",
                "AAP_CAC_SOURCE_CA_FILE": "{{ tower.filename if (source_ca_pem | default('') | trim) else '' }}",
            },
            "file": {"template": "{{ source_ca_pem | default('') }}"},
        },
    }
