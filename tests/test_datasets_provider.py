import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from public_transport_datasets.datasets_provider import DatasetsProvider


def test_load_dataset():
    countries = DatasetsProvider.get_available_countries()
    assert len(countries) > 0
