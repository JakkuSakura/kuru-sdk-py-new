import os
from unittest.mock import MagicMock, patch
from web3 import Web3
import pytest
from kuru_sdk_py.configs import (
    ConfigManager,
    MarketConfig,
    KuruMMConfig,
    initialize_kuru_mm_config,
    market_config_from_market_address,
)
from kuru_sdk_py.exceptions import KuruConfigError


class TestInitializeKuruMMConfig:
    def test_initialize_with_valid_private_key(self, caplog):
        """Test initialization with valid private key"""
        config = initialize_kuru_mm_config(
            private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            rpc_url="https://custom-rpc.example.com",
            rpc_ws_url="ws://custom-rpc.example.com",
            kuru_ws_url="wss://custom-ws.example.com",
            kuru_api_url="https://custom-api.example.com",
        )

        assert isinstance(config, KuruMMConfig)
        assert config.rpc_url == "https://custom-rpc.example.com"
        assert config.rpc_ws_url == "ws://custom-rpc.example.com"
        assert config.kuru_ws_url == "wss://custom-ws.example.com"
        assert config.kuru_api_url == "https://custom-api.example.com"
        assert (
            config.private_key
            == "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )


class TestMarketConfigFromMarketAddress:
    def test_market_config_fetch_success(self):
        """Test successful market config fetch from blockchain with real addresses"""
        market_address = "0x065C9d28E428A0db40191a54d33d5b7c71a9C394"
        mm_entrypoint_address = "0x0B4D25ce6e9ad4C88157C2721E5DafA22934E1C8"
        margin_contract_address = "0x2A68ba1833cDf93fa9Da1EEbd7F46242aD8E90c5"
        rpc_url = os.getenv("KURU_RPC_URL", "https://rpc.monad.xyz/")

        config = market_config_from_market_address(
            market_address=market_address,
            mm_entrypoint_address=mm_entrypoint_address,
            margin_contract_address=margin_contract_address,
            rpc_url=rpc_url,
        )

        print(f"\n=== Test Market Config ===")
        print(f"Market Address: {config.market_address}")
        print(f"MM Entrypoint Address: {config.mm_entrypoint_address}")
        print(f"Margin Contract Address: {config.margin_contract_address}")
        print(f"Market Symbol: {config.market_symbol}")
        print(f"Base Token: {config.base_token}")
        print(f"Base Symbol: {config.base_symbol}")
        print(f"Base Decimals: {config.base_token_decimals}")
        print(f"Quote Token: {config.quote_token}")
        print(f"Quote Symbol: {config.quote_symbol}")
        print(f"Quote Decimals: {config.quote_token_decimals}")
        print(f"Price Precision: {config.price_precision}")
        print(f"Size Precision: {config.size_precision}")
        print(f"Orderbook Implementation: {config.orderbook_implementation}")
        print(f"Margin Account Implementation: {config.margin_account_implementation}")
        print(f"Tick Size: {config.tick_size}")
        print(f"========================\n")

        assert isinstance(config, MarketConfig)
        assert config.market_address == market_address
        assert config.mm_entrypoint_address == mm_entrypoint_address
        assert config.margin_contract_address == margin_contract_address

        assert config.base_token.startswith("0x")
        assert config.quote_token.startswith("0x")
        assert len(config.base_token) == 42
        assert len(config.quote_token) == 42

        assert isinstance(config.base_token_decimals, int)
        assert isinstance(config.quote_token_decimals, int)
        assert config.quote_token_decimals > 0

        assert isinstance(config.price_precision, int)
        assert isinstance(config.size_precision, int)
        assert config.price_precision > 0
        assert config.size_precision > 0

        assert isinstance(config.base_symbol, str)
        assert isinstance(config.quote_symbol, str)
        assert len(config.base_symbol) > 0
        assert len(config.quote_symbol) > 0

        assert config.market_symbol == f"{config.base_symbol}-{config.quote_symbol}"


class TestLoadTomlConfig:
    def test_load_toml_config_missing_file(self, tmp_path):
        """Returns empty dict when file doesn't exist."""
        result = ConfigManager.load_toml_config(str(tmp_path / "nonexistent.toml"))
        assert result == {}

    def test_load_toml_config_valid(self, tmp_path):
        """Parses a valid TOML file correctly."""
        toml_file = tmp_path / "config.toml"
        toml_file.write_text(
            '[connection]\nrpc_url = "https://my-rpc.example.com"\n'
            '[transaction]\ntimeout = 60\n'
        )
        result = ConfigManager.load_toml_config(str(toml_file))
        assert result["connection"]["rpc_url"] == "https://my-rpc.example.com"
        assert result["transaction"]["timeout"] == 60

    def test_load_toml_config_invalid(self, tmp_path):
        """Raises KuruConfigError for a malformed TOML file."""
        toml_file = tmp_path / "config.toml"
        toml_file.write_bytes(b"[invalid\nthis is not valid toml ===")
        with pytest.raises(KuruConfigError, match="Failed to parse config file"):
            ConfigManager.load_toml_config(str(toml_file))

    def test_connection_config_toml_priority(self, tmp_path):
        """TOML values are applied when no env vars or explicit args override."""
        toml_file = tmp_path / "config.toml"
        toml_file.write_text('[connection]\nrpc_url = "https://toml-rpc.example.com"\n')
        toml_config = ConfigManager.load_toml_config(str(toml_file))

        # Clear env so TOML wins
        with patch.dict(os.environ, {}, clear=True):
            config = ConfigManager.load_connection_config(auto_env=True, toml_config=toml_config)
        assert config.rpc_url == "https://toml-rpc.example.com"

    def test_env_overrides_toml(self, tmp_path):
        """Environment variable wins over TOML."""
        toml_file = tmp_path / "config.toml"
        toml_file.write_text('[connection]\nrpc_url = "https://toml-rpc.example.com"\n')
        toml_config = ConfigManager.load_toml_config(str(toml_file))

        with patch.dict(os.environ, {"RPC_URL": "https://env-rpc.example.com"}):
            config = ConfigManager.load_connection_config(auto_env=True, toml_config=toml_config)
        assert config.rpc_url == "https://env-rpc.example.com"

    def test_explicit_arg_overrides_toml(self, tmp_path):
        """Explicit function argument wins over TOML and env var."""
        toml_file = tmp_path / "config.toml"
        toml_file.write_text('[connection]\nrpc_url = "https://toml-rpc.example.com"\n')
        toml_config = ConfigManager.load_toml_config(str(toml_file))

        with patch.dict(os.environ, {"RPC_URL": "https://env-rpc.example.com"}):
            config = ConfigManager.load_connection_config(
                rpc_url="https://explicit-rpc.example.com",
                auto_env=True,
                toml_config=toml_config,
            )
        assert config.rpc_url == "https://explicit-rpc.example.com"

    def test_order_execution_toml_bool_native(self, tmp_path):
        """Native TOML booleans are handled correctly for order execution config."""
        toml_file = tmp_path / "config.toml"
        toml_file.write_text(
            '[order_execution]\npost_only = false\nauto_approve = true\nuse_access_list = false\n'
        )
        toml_config = ConfigManager.load_toml_config(str(toml_file))

        with patch.dict(os.environ, {}, clear=True):
            config = ConfigManager.load_order_execution_config(auto_env=True, toml_config=toml_config)
        assert config.post_only is False
        assert config.auto_approve is True
        assert config.use_access_list is False


class TestLoadMarketConfig:
    def test_load_market_config_fetches_from_chain_with_resolved_inputs(self, monkeypatch):
        toml_config = {
            "market": {
                "market_address": "0x00000000000000000000000000000000000000AA",
                "mm_entrypoint_address": "0x00000000000000000000000000000000000000BB",
                "margin_contract_address": "0x00000000000000000000000000000000000000CC",
                "orderbook_implementation": "0x00000000000000000000000000000000000000DD",
                "margin_account_implementation": "0x00000000000000000000000000000000000000EE",
            }
        }
        captured = {}
        expected = MagicMock(spec=MarketConfig)

        def fake_market_config_from_market_address(**kwargs):
            captured.update(kwargs)
            return expected

        monkeypatch.setattr(
            "kuru_sdk_py.configs.market_config_from_market_address",
            fake_market_config_from_market_address,
        )

        with patch.dict(
            os.environ,
            {"MARKET_ADDRESS": "0x00000000000000000000000000000000000000FF"},
            clear=True,
        ):
            result = ConfigManager.load_market_config(
                rpc_url="https://explicit-rpc.example.com",
                auto_env=True,
                toml_config=toml_config,
            )

        assert result is expected
        assert captured == {
            "market_address": "0x00000000000000000000000000000000000000FF",
            "rpc_url": "https://explicit-rpc.example.com",
            "mm_entrypoint_address": "0x00000000000000000000000000000000000000BB",
            "margin_contract_address": "0x00000000000000000000000000000000000000CC",
            "orderbook_implementation": "0x00000000000000000000000000000000000000DD",
            "margin_account_implementation": "0x00000000000000000000000000000000000000EE",
        }

    def test_load_market_config_requires_market_address(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(KuruConfigError, match="market_address is required"):
                ConfigManager.load_market_config(auto_env=True, toml_config={})


class TestLoadAllConfigs:
    def test_load_all_configs_returns_bundle_without_fetch_flag(self, monkeypatch):
        toml_config = {"connection": {"rpc_url": "https://toml-rpc.example.com"}}
        market_calls = []

        monkeypatch.setattr(
            ConfigManager,
            "load_toml_config",
            staticmethod(lambda path: toml_config),
        )
        monkeypatch.setattr(
            ConfigManager,
            "load_wallet_config",
            staticmethod(lambda auto_env=True: "wallet"),
        )
        monkeypatch.setattr(
            ConfigManager,
            "load_connection_config",
            staticmethod(lambda auto_env=True, toml_config=None: "connection"),
        )
        monkeypatch.setattr(
            ConfigManager,
            "load_market_config",
            staticmethod(
                lambda market_address=None, rpc_url=None, mm_entrypoint_address=None,
                margin_contract_address=None, orderbook_implementation=None,
                margin_account_implementation=None, auto_env=True, toml_config=None: (
                    market_calls.append(
                        {
                            "market_address": market_address,
                            "rpc_url": rpc_url,
                            "mm_entrypoint_address": mm_entrypoint_address,
                            "margin_contract_address": margin_contract_address,
                            "orderbook_implementation": orderbook_implementation,
                            "margin_account_implementation": margin_account_implementation,
                            "auto_env": auto_env,
                            "toml_config": toml_config,
                        }
                    ) or "market"
                )
            ),
        )
        monkeypatch.setattr(
            ConfigManager,
            "load_transaction_config",
            staticmethod(lambda auto_env=True, toml_config=None: "transaction"),
        )
        monkeypatch.setattr(
            ConfigManager,
            "load_websocket_config",
            staticmethod(lambda auto_env=True, toml_config=None: "websocket"),
        )
        monkeypatch.setattr(
            ConfigManager,
            "load_order_execution_config",
            staticmethod(lambda auto_env=True, toml_config=None: "order_execution"),
        )
        monkeypatch.setattr(
            ConfigManager,
            "load_cache_config",
            staticmethod(lambda auto_env=False, toml_config=None: "cache"),
        )

        configs = ConfigManager.load_all_configs(
            market_address="0x0000000000000000000000000000000000000001",
            auto_env=False,
            toml_path="custom.toml",
        )

        assert configs == {
            "wallet_config": "wallet",
            "connection_config": "connection",
            "market_config": "market",
            "transaction_config": "transaction",
            "websocket_config": "websocket",
            "order_execution_config": "order_execution",
            "cache_config": "cache",
        }
        assert market_calls == [
            {
                "market_address": "0x0000000000000000000000000000000000000001",
                "rpc_url": None,
                "mm_entrypoint_address": None,
                "margin_contract_address": None,
                "orderbook_implementation": None,
                "margin_account_implementation": None,
                "auto_env": False,
                "toml_config": toml_config,
            }
        ]
