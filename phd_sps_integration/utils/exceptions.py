# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo.exceptions import except_orm

_logger = logging.getLogger(__name__)


class EDITransactionValidationError(except_orm):
    """Violation of EDI transaction constraints.

    .. admonition:: Example

        When you try to import a partner which is not exists in DB.
    """

    def __init__(self, msg):
        super(EDITransactionValidationError, self).__init__(msg)