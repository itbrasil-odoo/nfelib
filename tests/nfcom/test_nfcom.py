# Copyright (C) 2026 - TODAY IT Brasil

import os
from pathlib import Path
from unittest import TestCase

from lxml import etree
from xmldiff import main
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.serializers import XmlSerializer
from xsdata.formats.dataclass.serializers.config import SerializerConfig

from nfelib.nfcom.bindings.v1_0.nfcom_v1_00 import Nfcom

SAMPLES = os.path.join("nfelib", "nfcom", "samples", "v1_0")
SCHEMA = os.path.join("nfelib", "nfcom", "schemas", "v1_0", "nfcom_v1.00.xsd")


class NFComTests(TestCase):
    """A NFCom (modelo 62) substitui os modelos 21 e 22 e é obrigatória desde
    01/10/2026. A amostra usada aqui foi transmitida de verdade ao ambiente de
    homologação da SVRS, que é o autorizador da maioria das UFs."""

    def test_in_out_nfcom(self):
        """Ler e reescrever a amostra tem de devolver o mesmo XML."""
        for filename in os.listdir(SAMPLES):
            if not filename.endswith(".xml"):
                continue
            input_file = os.path.join(SAMPLES, filename)
            obj = XmlParser().from_path(Path(input_file))
            xml = XmlSerializer(config=SerializerConfig(indent="  ")).render(
                obj=obj, ns_map={None: "http://www.portalfiscal.inf.br/nfcom"}
            )
            output_file = "tests/output_nfcom.xml"
            with open(output_file, "w") as f:
                f.write(xml)

            diff = main.diff_files(input_file, output_file)
            self.assertEqual(
                len(diff),
                0,
                f"Error {output_file} != {input_file}. "
                "Stopping tests here so you can compare XML files.",
            )

    def test_sample_is_valid_against_official_xsd(self):
        """A amostra tem de passar no XSD oficial, e não só no parser.

        É a diferença entre "o binding leu" e "o fisco aceita": a SEFAZ valida o
        arquivo contra este mesmo schema antes de olhar qualquer regra de
        negócio, e rejeita com cStat 215 quando ele não bate.
        """
        schema = etree.XMLSchema(etree.parse(SCHEMA))
        for filename in os.listdir(SAMPLES):
            if not filename.endswith(".xml"):
                continue
            doc = etree.parse(os.path.join(SAMPLES, filename))
            self.assertTrue(
                schema.validate(doc),
                f"{filename} não valida no XSD oficial: {schema.error_log}",
            )

    def test_reads_the_fields_that_matter(self):
        """Os grupos que só existem na NFCom, e que nenhum outro modelo tem."""
        obj = XmlParser().from_path(
            Path(os.path.join(SAMPLES, "nfcom_homologacao_svrs.xml")), Nfcom
        )
        inf = obj.infNFCom
        self.assertEqual(inf.versao, "1.00")
        self.assertEqual(inf.ide.mod.value, "62")
        # `assinante` e `gFat` são o que distingue a NFCom de uma NF-e: ela é a
        # fatura do serviço de comunicação, com contrato e competência.
        self.assertTrue(inf.assinante.iCodAssinante)
        self.assertTrue(inf.gFat.CompetFat)
        self.assertTrue(inf.gFat.codBarras)
        self.assertTrue(inf.det[0].prod.cClass)
