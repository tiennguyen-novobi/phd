# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from typing import List, Optional, Set, Tuple, Union


def ensure_list(obj):
    """
    Using to cast element to list
    :param obj:
    :type obj:
    :return:
    :rtype:
    """
    list_obj = obj if isinstance(obj, list) else list(obj) if isinstance(obj, (tuple, set)) else (obj and [obj] or [])
    return list_obj
