import pytest

from veri_temizleme.uretici import uret


@pytest.fixture(scope="session")
def kucuk_veri(tmp_path_factory):
    klasor = tmp_path_factory.mktemp("calisma")
    uret(klasor / "veri", seed=7, siparis=1500, musteri=400, urun=80)
    return klasor
