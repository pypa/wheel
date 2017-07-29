import json

import pytest

from wheel.signatures import keys

wheel_json = """
{
  "verifiers": [
    {
      "scope": "+",
      "vk": "bp-bjK2fFgtA-8DhKKAAPm9-eAZcX_u03oBv2RlKOBc"
    },
    {
      "scope": "+",
      "vk": "KAHZBfyqFW3OcFDbLSG4nPCjXxUPy72phP9I4Rn9MAo"
    },
    {
      "scope": "+",
      "vk": "tmAYCrSfj8gtJ10v3VkvW7jOndKmQIYE12hgnFu3cvk"
    }
  ],
  "signers": [
    {
      "scope": "+",
      "vk": "tmAYCrSfj8gtJ10v3VkvW7jOndKmQIYE12hgnFu3cvk"
    },
    {
      "scope": "+",
      "vk": "KAHZBfyqFW3OcFDbLSG4nPCjXxUPy72phP9I4Rn9MAo"
    }
  ],
  "schema": 1
}
"""


@pytest.fixture
def wheel_keys(tmpdir, monkeypatch):
    def load(*args):
        return [config_path.dirname]

    def save(*args):
        return config_path.dirname

    config_path = tmpdir.join('config.json')
    config_path.write(b'')

    monkeypatch.setattr(keys, 'load_config_paths', load)
    monkeypatch.setattr(keys, 'save_config_path', save)

    wk = keys.WheelKeys()
    wk.CONFIG_NAME = config_path.basename
    return wk


def test_load_save(wheel_keys):
    wheel_keys.data = json.loads(wheel_json)

    wheel_keys.add_signer('+', '67890')
    wheel_keys.add_signer('scope', 'abcdefg')

    wheel_keys.trust('epocs', 'gfedcba')
    wheel_keys.trust('+', '12345')

    wheel_keys.save()

    del wheel_keys.data
    wheel_keys.load()

    signers = wheel_keys.signers('scope')
    assert signers[0] == ('scope', 'abcdefg'), wheel_keys.data['signers']
    assert signers[1][0] == '+', wheel_keys.data['signers']

    trusted = wheel_keys.trusted('epocs')
    assert trusted[0] == ('epocs', 'gfedcba')
    assert trusted[1][0] == '+'

    wheel_keys.untrust('epocs', 'gfedcba')
    trusted = wheel_keys.trusted('epocs')
    assert ('epocs', 'gfedcba') not in trusted


def test_load_save_incomplete(wheel_keys):
    wheel_keys.data = json.loads(wheel_json)
    del wheel_keys.data['signers']
    wheel_keys.data['schema'] = wheel_keys.SCHEMA+1
    wheel_keys.save()
    pytest.raises(ValueError, wheel_keys.load)

    del wheel_keys.data['schema']
    wheel_keys.save()
    wheel_keys.load()
