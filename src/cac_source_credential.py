"""Portable independent source API and existing-authority credentials."""


def definition():
    """Preserve the already-used URL/token schema without adding inputs."""
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
            ],
            "required": ["source_url", "api_token"],
        },
        "injectors": {
            "env": {
                "AAP_CAC_SOURCE_URL": "{{ source_url }}",
                "AAP_CAC_SOURCE_TOKEN": "{{ api_token }}",
            }
        },
    }


def ca_definition():
    """Optional separate attachment; its sole CA input is required when attached."""
    return {
        "name": "AAP CaC source CA",
        "kind": "cloud",
        "inputs": {
            "fields": [
                {
                    "id": "source_ca_pem",
                    "label": "Existing trusted source CA PEM",
                    "type": "string",
                    "secret": True,
                    "multiline": True,
                }
            ],
            "required": ["source_ca_pem"],
        },
        "injectors": {
            "env": {"AAP_CAC_SOURCE_CA_FILE": "{{ tower.filename }}"},
            "file": {"template": "{{ source_ca_pem }}"},
        },
    }
