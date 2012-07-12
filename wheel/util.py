"""Utility functions."""

import base64
import json

__all__ = ['urlsafe_b64encode', 'urlsafe_b64decode', 'utf8', 
           'to_json', 'from_json']

def urlsafe_b64encode(data):
    """urlsafe_b64encode without padding"""
    return base64.urlsafe_b64encode(data).rstrip(b'=')

def urlsafe_b64decode(data):
    """urlsafe_b64decode without padding"""
    pad = b'=' * (4 - (len(data) & 3))
    return base64.urlsafe_b64decode(data + pad)

def to_json(o):
    return json.dumps(o, sort_keys=True)

def from_json(j):
    return json.loads(j)

try:
    unicode
    def utf8(data):
        if isinstance(data, unicode):
            return data.encode('utf-8')
        return data
except NameError:
    def utf8(data):
        if isinstance(data, str):
            return data.encode('utf-8')
        return data
    