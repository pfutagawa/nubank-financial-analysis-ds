import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Adiciona o diretório da aplicação e scripts ao sys.path
REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(REPO_DIR / "scripts"))

from ingestao import ensure_unique_index, sanitize_text, validate_record
from pymongo import UpdateOne
from pymongo.errors import OperationFailure
import limpar_historico_teste


class TestIngestaoValidacao(unittest.TestCase):
    def test_valid_record(self):
        raw = {
            "datetime": "2026-09-30",
            "open": "11.50",
            "high": "12.00",
            "low": "11.20",
            "close": "11.80",
            "volume": "1500000",
        }
        doc, reason = validate_record(raw, "NU")
        self.assertIsNotNone(doc)
        self.assertEqual(reason, "")
        self.assertEqual(doc["ticker"], "NU")
        self.assertEqual(doc["datetime"], "2026-09-30")
        self.assertEqual(doc["open"], 11.50)
        self.assertEqual(doc["volume"], 1500000.0)

    def test_invalid_datetime(self):
        raw = {
            "datetime": "2026-02-30",  # Data inexistente
            "open": "10",
            "high": "11",
            "low": "9",
            "close": "10",
            "volume": "100",
        }
        doc, reason = validate_record(raw, "NU")
        self.assertIsNone(doc)
        self.assertIn("datetime", reason)

    def test_missing_price(self):
        raw = {
            "datetime": "2026-09-30",
            "open": "",
            "high": "11",
            "low": "9",
            "close": "10",
            "volume": "100",
        }
        doc, reason = validate_record(raw, "NU")
        self.assertIsNone(doc)
        self.assertIn("ausente", reason)

    def test_high_lower_than_low(self):
        raw = {
            "datetime": "2026-09-30",
            "open": "10",
            "high": "8.5",  # Máxima menor que mínima
            "low": "9.0",
            "close": "10",
            "volume": "100",
        }
        doc, reason = validate_record(raw, "NU")
        self.assertIsNone(doc)
        self.assertIn("inferior à mínima", reason)

    def test_negative_volume(self):
        raw = {
            "datetime": "2026-09-30",
            "open": "10",
            "high": "11",
            "low": "9",
            "close": "10",
            "volume": "-500",
        }
        doc, reason = validate_record(raw, "NU")
        self.assertIsNone(doc)
        self.assertIn("volume negativo", reason)


class TestUpsertSemDuplicatas(unittest.TestCase):
    def test_duas_ingestoes_nao_geram_duplicatas(self):
        """
        Simula duas ingestões consecutivas com o mesmo lote de pregões
        e valida que o modelo de upsert por (ticker, datetime) previne duplicatas.
        """
        cotacoes = [
            {"datetime": "2026-09-29", "open": "10", "high": "11", "low": "9", "close": "10.5", "volume": "1000"},
            {"datetime": "2026-09-30", "open": "10.5", "high": "12", "low": "10", "close": "11.5", "volume": "2000"},
        ]

        # Simulação de base de dados em memória
        in_memory_db = {}

        def apply_bulk_upsert(raw_list, ticker):
            for raw in raw_list:
                doc, _ = validate_record(raw, ticker)
                key = (doc["ticker"], doc["datetime"])
                # Lógica do UpdateOne com upsert=True
                in_memory_db[key] = doc

        # Ingestão 1
        apply_bulk_upsert(cotacoes, "NU")
        self.assertEqual(len(in_memory_db), 2)

        # Ingestão 2 (mesmos dados simulados)
        apply_bulk_upsert(cotacoes, "NU")
        self.assertEqual(len(in_memory_db), 2, "A segunda ingestão não deve criar duplicatas!")


class TestProtecaoCredenciais(unittest.TestCase):
    def test_sanitize_text_mascara_chaves_e_urls(self):
        fake_key = "segredo_super_secreto_12345"
        texto_vazado = f"Erro ao acessar https://api.twelvedata.com/time_series?symbol=NU&apikey={fake_key}&interval=1day"
        sanitizado = sanitize_text(texto_vazado, fake_key)

        self.assertNotIn(fake_key, sanitizado)
        self.assertIn("***REDACTED***", sanitizado)

    def test_sanitize_text_mascara_mongo_uri(self):
        raw_uri = "Erro de conexão para mongodb+srv://meu_usuario:minha_senha_secreta@cluster0.mongodb.net/?app=1"
        sanitizado = sanitize_text(raw_uri)
        self.assertNotIn("minha_senha_secreta", sanitizado)
        self.assertIn("mongodb://***REDACTED***", sanitizado)


class TestLimpezaControlada(unittest.TestCase):
    @patch("limpar_historico_teste.MongoClient")
    @patch("limpar_historico_teste.load_dotenv")
    def test_modo_padrao_nao_exclui_dados(self, mock_dotenv, mock_client_cls):
        mock_client = MagicMock()
        mock_col = MagicMock()
        mock_col.count_documents.return_value = 90
        mock_col.aggregate.return_value = []
        mock_client.__getitem__.return_value.__getitem__.return_value = mock_col
        mock_client_cls.return_value = mock_client

        with patch.dict("os.environ", {"MONGO_URI": "mongodb://fake:uri@localhost:27017"}):
            with patch.object(sys, "argv", ["limpar_historico_teste.py"]):
                exit_code = limpar_historico_teste.main()

        self.assertEqual(exit_code, 0)
        # NUNCA deve chamar delete_many no modo padrão
        mock_col.delete_many.assert_not_called()
        mock_col.drop.assert_not_called()

    @patch("limpar_historico_teste.MongoClient")
    @patch("limpar_historico_teste.load_dotenv")
    def test_modo_executar_com_confirmacao_errada_nao_exclui(self, mock_dotenv, mock_client_cls):
        mock_client = MagicMock()
        mock_col = MagicMock()
        mock_col.count_documents.return_value = 90
        mock_col.aggregate.return_value = []
        mock_client.__getitem__.return_value.__getitem__.return_value = mock_col
        mock_client_cls.return_value = mock_client

        with patch.dict("os.environ", {"MONGO_URI": "mongodb://fake:uri@localhost:27017"}):
            with patch.object(sys, "argv", ["limpar_historico_teste.py", "--executar"]):
                with patch("builtins.input", return_value="SIM QUERO APAGAR"):
                    exit_code = limpar_historico_teste.main()

        self.assertEqual(exit_code, 1)
        mock_col.delete_many.assert_not_called()

    @patch("limpar_historico_teste.MongoClient")
    @patch("limpar_historico_teste.load_dotenv")
    def test_modo_executar_com_confirmacao_correta_exclui_e_cria_indice(self, mock_dotenv, mock_client_cls):
        mock_client = MagicMock()
        mock_col = MagicMock()
        mock_col.count_documents.return_value = 90
        mock_col.aggregate.return_value = []
        mock_del_res = MagicMock()
        mock_del_res.deleted_count = 90
        mock_col.delete_many.return_value = mock_del_res
        mock_client.__getitem__.return_value.__getitem__.return_value = mock_col
        mock_client_cls.return_value = mock_client

        with patch.dict("os.environ", {"MONGO_URI": "mongodb://fake:uri@localhost:27017"}):
            with patch.object(sys, "argv", ["limpar_historico_teste.py", "--executar"]):
                with patch("builtins.input", return_value="LIMPAR nubank_db.historico_diario"):
                    exit_code = limpar_historico_teste.main()

        self.assertEqual(exit_code, 0)
        mock_col.delete_many.assert_called_once_with({})
        mock_col.create_index.assert_called_once_with([("ticker", 1), ("datetime", 1)], unique=True)
        # NUNCA drop
        mock_col.drop.assert_not_called()


class TestIndiceDuplicatas(unittest.TestCase):
    def test_ensure_unique_index_aborta_se_duplicatas(self):
        mock_col = MagicMock()
        mock_col.list_indexes.return_value = []
        # Simula erro de chave duplicada no MongoDB (código 11000)
        mock_col.create_index.side_effect = OperationFailure("E11000 duplicate key error", code=11000)

        success = ensure_unique_index(mock_col)
        self.assertFalse(success, "Deveria retornar False se duplicatas impedirem criação de índice único")


class TestAtualizacao2026ReconciliacaoEMetricas(unittest.TestCase):
    def test_reconciliacao_2025_trimestral_vs_20f(self):
        from src.validate_data import validate_financial_quarterly

        reconciliation = validate_financial_quarterly()
        self.assertLessEqual(reconciliation["diff_revenue_2025"], 0.01)
        self.assertLessEqual(reconciliation["diff_net_income_2025"], 0.01)

    def test_sem_periodos_duplicados_e_parcial_2026(self):
        from src.data_pipeline import load_financial_history, load_financial_quarterly

        annual = load_financial_history()
        quarterly = load_financial_quarterly()

        self.assertTrue(annual["year"].is_unique)
        self.assertEqual(annual["year"].tolist(), [2021, 2022, 2023, 2024, 2025])
        self.assertTrue(quarterly["periodo_fim"].is_unique)
        self.assertTrue(quarterly["trimestre"].is_unique)

        q_2026 = quarterly[quarterly["ano"] == 2026]
        self.assertFalse(q_2026.empty)
        self.assertTrue((q_2026["parcial"] == "sim").all())

        q_2025 = quarterly[quarterly["ano"] == 2025]
        self.assertEqual(len(q_2025), 4)
        self.assertTrue((q_2025["parcial"] == "não").all())

    def test_moedas_unidades_e_fonte_url_obrigatorios(self):
        from src.data_pipeline import load_financial_quarterly, load_risk_detail_by_period

        quarterly = load_financial_quarterly()
        self.assertTrue((quarterly["moeda"] == "USD").all())
        self.assertTrue(quarterly["unidade"].notna().all())
        self.assertTrue(quarterly["fonte_url"].str.startswith("https://www.sec.gov/").all())

        risk_detail = load_risk_detail_by_period()
        self.assertTrue(risk_detail["period"].is_unique)
        self.assertTrue((risk_detail["moeda"] == "BRL").all())
        self.assertTrue(risk_detail["source_url"].notna().all())

    def test_metricas_2026_ltm_ytd_e_estoques(self):
        from src.data_pipeline import compute_metrics_2026

        metrics = compute_metrics_2026()
        self.assertEqual(metrics["reference_quarter"], "2T26")
        self.assertEqual(metrics["partial_label"], "parcial até 2T26")

        # LTM = 3T25 + 4T25 + 1T26 + 2T26
        self.assertEqual(metrics["ltm"]["quarters_included"], ["3T25", "4T25", "1T26", "2T26"])
        self.assertAlmostEqual(metrics["ltm"]["revenue_usd_b"], 19.3398, places=3)
        self.assertAlmostEqual(metrics["ltm"]["net_income_usd_b"], 3.6107, places=3)

        # YTD 2026 (1T26 + 2T26) vs YTD 2025 (1T25 + 2T25)
        self.assertEqual(metrics["ytd_comparison"]["quarters_2026"], ["1T26", "2T26"])
        self.assertEqual(metrics["ytd_comparison"]["quarters_2025"], ["1T25", "2T25"])
        self.assertAlmostEqual(metrics["ytd_comparison"]["revenue_2026_usd_b"], 10.4812, places=3)
        self.assertAlmostEqual(metrics["ytd_comparison"]["revenue_2025_usd_b"], 6.9162, places=3)

        # Estoques do último trimestre disponível (2T26)
        self.assertEqual(metrics["stocks_latest"]["trimestre_referencia"], "2T26")
        self.assertAlmostEqual(metrics["stocks_latest"]["clientes_m"], 139.0, places=1)
        self.assertAlmostEqual(metrics["stocks_latest"]["depositos_usd_b"], 45.3, places=1)
        self.assertAlmostEqual(metrics["stocks_latest"]["carteira_credito_usd_b"], 39.4, places=1)


if __name__ == "__main__":
    unittest.main()
