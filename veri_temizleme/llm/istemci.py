"""Claude istemcisi: JSON şemalı çağrı, disk önbelleği, token ve maliyet takibi.

Aynı istek ikinci kez gönderilmez, önbellekten okunur. Böylece ölçüm tekrar çalıştırıldığında ücretsiz ve birebir
aynı sonucu verir.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

VARSAYILAN_MODEL = "claude-opus-5"

# $ / 1M token (girdi, çıktı). Önbellekten okuma girdinin %10'u, önbelleğe yazma %125'i.
FIYATLAR = {
    "claude-fable-5-1": (10.0, 50.0), "claude-opus-5-5": (4.0, 20.0), "claude-opus-5": (5.0, 25.0),
    "claude-opus-4-8": (5.0, 25.0), "claude-sonnet-5": (2.0, 10.0), "claude-haiku-4-5": (1.0, 5.0),
}


@dataclass
class Kullanim:
    cagri: int = 0
    onbellekten: int = 0
    girdi: int = 0
    cikti: int = 0
    onbellek_okuma: int = 0
    onbellek_yazma: int = 0
    ret: int = 0
    hata: int = 0
    maliyet: float = 0.0
    sure: float = 0.0
    kilit: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def sozluk(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if k != "kilit"}


def maliyet_hesapla(model: str, girdi: int, cikti: int, okuma: int = 0, yazma: int = 0) -> float:
    fg, fc = FIYATLAR.get(model, FIYATLAR[VARSAYILAN_MODEL])
    return (girdi * fg + cikti * fc + okuma * fg * 0.1 + yazma * fg * 1.25) / 1_000_000


class LLMIstemci:
    def __init__(self, model: str = VARSAYILAN_MODEL, effort: str = "medium", onbellek: Path | None = None,
                 geri_donus: bool = True, client: anthropic.Anthropic | None = None):
        self.model = model
        self.effort = effort
        self.geri_donus = geri_donus
        self.onbellek = Path(onbellek) if onbellek else None
        if self.onbellek:
            self.onbellek.mkdir(parents=True, exist_ok=True)
        self._client = client
        self.kullanim = Kullanim()

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic(max_retries=5)
        return self._client

    def _anahtar(self, sistem: str, mesaj: str, sema: dict) -> str:
        ham = json.dumps([self.model, self.effort, sistem, mesaj, sema], ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(ham.encode()).hexdigest()

    def json_iste(self, sistem: str, mesaj: str, sema: dict, max_tokens: int = 16000) -> dict | None:
        """Şemaya uyan JSON döner. Model reddederse veya çağrı başarısız olursa None döner."""
        anahtar = self._anahtar(sistem, mesaj, sema)
        yol = self.onbellek / f"{anahtar}.json" if self.onbellek else None
        if yol and yol.exists():
            kayit = json.loads(yol.read_text(encoding="utf-8"))
            # Önbellekten okunan çağrının ilk çalıştırmadaki maliyeti ve süresi yöntemin maliyetine sayılır.
            self._ekle(kayit["kullanim"], onbellekten=True)
            return kayit["cevap"]

        istek = dict(
            model=self.model, max_tokens=max_tokens,
            # Sabit sistem metni önbelleğe alınır: her grup aynı talimatları ve referans listeleri taşır.
            system=[{"type": "text", "text": sistem, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": mesaj}],
            output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": sema}},
        )
        bas = time.monotonic()
        try:
            if self.geri_donus:
                # Güvenlik sınıflandırıcısı reddederse istek sunucu tarafında uygun modelle yeniden çalışır.
                yanit = self.client.beta.messages.create(**istek, betas=["server-side-fallback-2026-07-01"],
                                                         fallbacks="default")
            else:
                yanit = self.client.messages.create(**istek)
        except anthropic.BadRequestError:
            raise  # İstek biçimi yanlış: sessizce geçilmez.
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError, anthropic.NotFoundError):
            raise
        except (anthropic.RateLimitError, anthropic.APIStatusError, anthropic.APIConnectionError):
            with self.kullanim.kilit:
                self.kullanim.hata += 1
            return None
        sure = time.monotonic() - bas

        u = yanit.usage
        okuma = getattr(u, "cache_read_input_tokens", 0) or 0
        yazma = getattr(u, "cache_creation_input_tokens", 0) or 0
        kullanim = {"girdi": u.input_tokens, "cikti": u.output_tokens, "onbellek_okuma": okuma,
                    "onbellek_yazma": yazma, "sure": sure, "ret": int(yanit.stop_reason == "refusal"),
                    "maliyet": maliyet_hesapla(yanit.model, u.input_tokens, u.output_tokens, okuma, yazma)}
        self._ekle(kullanim)
        if yanit.stop_reason in ("refusal", "max_tokens"):
            return None
        metin = next((b.text for b in yanit.content if b.type == "text"), None)
        if metin is None:
            return None
        cevap = json.loads(metin)
        if yol:
            yol.write_text(json.dumps({"model": yanit.model, "kullanim": kullanim, "cevap": cevap},
                                      ensure_ascii=False), encoding="utf-8")
        return cevap

    def _ekle(self, kullanim: dict, onbellekten: bool = False):
        with self.kullanim.kilit:
            k = self.kullanim
            k.cagri += 1
            k.onbellekten += int(onbellekten)
            for alan, deger in kullanim.items():
                setattr(k, alan, getattr(k, alan) + deger)
