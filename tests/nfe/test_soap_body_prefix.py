"""The SOAP Body prefix is chosen by the server and must not be hardcoded.

SEFAZ-MG answers NFeConsultaProtocolo4 with an uppercase ``S:`` prefix::

    <S:Envelope xmlns:S="http://www.w3.org/2003/05/soap-envelope"><S:Body>

The previous pattern only accepted ``env``, ``soap`` and ``soapenv``, so the
search never matched, ``analisar_retorno_raw_xsdata`` fell through and returned
``None``, and callers blew up far from here: ``l10n_br_nfe`` does
``check_response.resposta.xMotivo`` and raises ``AttributeError: 'NoneType'
object has no attribute 'resposta'``.

Cost of the silent ``None``: an NF-e authorized at SEFAZ was recorded as
rejected in the ERP, and the operator could not find out otherwise — the very
button meant to answer "is this note authorized?" was the one that crashed.
"""

import unittest

from nfelib.nfe.ws.edoc_legacy import SOAP_BODY_PATTERN

CORPO = "<nfeResultMsg><retConsSitNFe><cStat>100</cStat></retConsSitNFe></nfeResultMsg>"


def _envelope(prefixo):
    marca = f"{prefixo}:" if prefixo else ""
    return (
        f'<{marca}Envelope xmlns:{prefixo or "x"}="http://www.w3.org/2003/05/soap-envelope">'
        f"<{marca}Body>{CORPO}</{marca}Body></{marca}Envelope>"
    )


class TestSoapBodyPrefix(unittest.TestCase):
    def test_aceita_os_prefixos_conhecidos(self):
        for prefixo in ("soap", "env", "soapenv"):
            with self.subTest(prefixo=prefixo):
                achado = SOAP_BODY_PATTERN.search(_envelope(prefixo))
                self.assertIsNotNone(achado)
                self.assertEqual(achado.group(1), CORPO)

    def test_aceita_o_S_maiusculo_da_sefaz_mg(self):
        achado = SOAP_BODY_PATTERN.search(_envelope("S"))
        self.assertIsNotNone(achado, "SEFAZ-MG usa <S:Body>")
        self.assertEqual(achado.group(1), CORPO)

    def test_aceita_envelope_sem_prefixo(self):
        achado = SOAP_BODY_PATTERN.search(_envelope(""))
        self.assertIsNotNone(achado)
        self.assertEqual(achado.group(1), CORPO)

    def test_atravessa_quebras_de_linha(self):
        """Antes o chamador removia os `\\n` da resposta inteira, o que também
        os removia de dentro do conteúdo. `re.DOTALL` resolve sem tocar no XML."""
        xml = f"<S:Envelope>\n<S:Body>\n{CORPO}\n</S:Body>\n</S:Envelope>"
        achado = SOAP_BODY_PATTERN.search(xml)
        self.assertIsNotNone(achado)
        self.assertIn("cStat", achado.group(1))

    def test_nao_casa_o_que_nao_e_envelope(self):
        """Resposta de proxy ou página de erro não pode passar por SOAP."""
        self.assertIsNone(SOAP_BODY_PATTERN.search("<html><body>erro</body></html>"))
