"""
Create and verify jws-js format Ed25519 signatures.
"""

import json
try:
    import ed25519ll
except ImportError:
    ed25519ll = None
from wheel.util import urlsafe_b64decode, urlsafe_b64encode


def sign(payload, keypair):
    """Return a JWS-JS format signature given a JSON-serializable payload and 
    an Ed25519 keypair."""
    header = {"typ": "JWT",
              "alg": "Ed25519",
              "key": {"alg": "Ed25519",
                      "vk": urlsafe_b64encode(keypair.vk)}}
    
    encoded_header = urlsafe_b64encode(json.dumps(header, sort_keys=True)) 
    encoded_payload = urlsafe_b64encode(json.dumps(payload, sort_keys=True))
    secured_input = ".".join((encoded_header, encoded_payload))
    sig_msg = ed25519ll.crypto_sign(secured_input, keypair.sk)
    signature = sig_msg[:ed25519ll.SIGNATUREBYTES]
    encoded_signature = urlsafe_b64encode(signature)
    
    return {"headers": [encoded_header],
            "payload": encoded_payload,
            "signatures": [encoded_signature]}
    
def verify(jwsjs):
    """Return (decoded headers, payload) if all signatures in jwsjs are
    consistent, else raise ValueError.
    
    Caller must decide whether the keys are actually trusted."""
    # XXX forbid duplicate keys in JSON input
    encoded_headers = jwsjs["headers"]
    encoded_payload = jwsjs["payload"]
    encoded_signatures = jwsjs["signatures"]
    headers = []
    for h, s in zip(encoded_headers, encoded_signatures):
        header = json.loads(urlsafe_b64decode(h))
        assert header["alg"] == "Ed25519"
        assert header["key"]["alg"] == "Ed25519"
        vk = urlsafe_b64decode(header["key"]["vk"].encode('latin1'))
        secured_input = ".".join((h, encoded_payload))
        sig = urlsafe_b64decode(s.encode('latin1'))
        sig_msg = sig+secured_input
        verified_input = ed25519ll.crypto_sign_open(sig_msg, vk)
        verified_header, verified_payload = verified_input.split('.')
        headers.append(json.loads(urlsafe_b64decode(verified_header)))

    # only return header, payload that have passed through the crypto library.
    payload = json.loads(urlsafe_b64decode(verified_payload))

    return headers, payload

def test():
    if ed25519ll is None:
        return
    # Takes less than 25 milliseconds.
    kp = ed25519ll.crypto_sign_keypair()
    payload = {'test': 'onstartup'}
    jwsjs = sign(payload, kp)
    verify(jwsjs)
    jwsjs['payload'] += 'x'
    try:
        verify(jwsjs)
    except ValueError:
        pass
    else: # pragma no cover
        raise RuntimeError("No error from bad wheel.signatures payload.")
    
test()
