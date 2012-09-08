"""
Create and verify jws-js format Ed25519 signatures.
"""

__all__ = [ 'sign', 'verify' ]

import json
from ..util import urlsafe_b64decode, urlsafe_b64encode, native, binary

ed25519ll = None

def get_ed25519ll():
    """Lazy import-and-test of ed25519 module"""
    global ed25519ll
    
    if not ed25519ll:
        try:
            import ed25519ll # fast (thousands / s)
        except (ImportError, OSError):
            from . import ed25519py as ed25519ll # pure Python (hundreds / s)
        test()
    
    return ed25519ll

def sign(payload, keypair):
    """Return a JWS-JS format signature given a JSON-serializable payload and 
    an Ed25519 keypair."""
    get_ed25519ll()
    #
    header = {"typ": "JWT",
              "alg": "Ed25519",
              "key": {"alg": "Ed25519",
                      "vk": native(urlsafe_b64encode(keypair.vk))}}
    
    encoded_header = urlsafe_b64encode(binary(json.dumps(header, sort_keys=True)))
    encoded_payload = urlsafe_b64encode(binary(json.dumps(payload, sort_keys=True)))
    secured_input = b".".join((encoded_header, encoded_payload))
    sig_msg = ed25519ll.crypto_sign(secured_input, keypair.sk)
    signature = sig_msg[:ed25519ll.SIGNATUREBYTES]
    encoded_signature = urlsafe_b64encode(signature)
    
    return {"headers": [native(encoded_header)],
            "payload": native(encoded_payload),
            "signatures": [native(encoded_signature)]}
    
def verify(jwsjs):
    """Return (decoded headers, payload) if all signatures in jwsjs are
    consistent, else raise ValueError.
    
    Caller must decide whether the keys are actually trusted."""
    get_ed25519ll()    
    # XXX forbid duplicate keys in JSON input
    encoded_headers = jwsjs["headers"]
    encoded_payload = binary(jwsjs["payload"])
    encoded_signatures = jwsjs["signatures"]
    headers = []
    for h, s in zip(encoded_headers, encoded_signatures):
        h = binary(h)
        s = binary(s)
        header = json.loads(native(urlsafe_b64decode(h)))
        assert header["alg"] == "Ed25519"
        assert header["key"]["alg"] == "Ed25519"
        vk = urlsafe_b64decode(binary(header["key"]["vk"]))
        secured_input = b".".join((h, encoded_payload))
        sig = urlsafe_b64decode(s)
        sig_msg = sig+secured_input
        verified_input = native(ed25519ll.crypto_sign_open(sig_msg, vk))
        verified_header, verified_payload = verified_input.split('.')
        verified_header = binary(verified_header)
        decoded_payload = native(urlsafe_b64decode(verified_header))
        headers.append(json.loads(decoded_payload))

    verified_payload = binary(verified_payload)

    # only return header, payload that have passed through the crypto library.
    payload = json.loads(native(urlsafe_b64decode(verified_payload)))

    return headers, payload

def test():
    kp = ed25519ll.crypto_sign_keypair()
    payload = {'test': 'onstartup'}
    jwsjs = json.loads(json.dumps(sign(payload, kp)))
    verify(jwsjs)
    jwsjs['payload'] += 'x'
    try:
        verify(jwsjs)
    except ValueError:
        pass
    else: # pragma no cover
        raise RuntimeError("No error from bad wheel.signatures payload.")

