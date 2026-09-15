"""Generated public protocol registry, including the OBS04 control/replay API."""
from .contracts import CONTRACTS as FOUNDATION_CONTRACTS
from .api_contracts import API_CONTRACTS
from .recording import RECORDING_CONTRACTS

CONTRACTS = {**FOUNDATION_CONTRACTS, **API_CONTRACTS, **RECORDING_CONTRACTS}
